#!/usr/bin/env python3
"""Grades one reading submission Issue. Run by .github/workflows/grade-submission.yml
on every `issues: opened` event. Reads env vars set by the workflow, writes/updates
results/<github-username>.json (one student's full record) and
results/by-reading/<reading-id>/<github-username>.json (a per-reading snapshot,
for looking at how the whole class did on one specific reading), plus
leaderboard.json. Emits a `comment`/`label`/`close` output for the workflow's
comment-and-close step to use.

Identity is taken from the issue's real author (ISSUE_AUTHOR, from GitHub's own
event payload), never from any free-text field a student typed in the reading,
so it can't be spoofed by typing someone else's username.

Each GitHub Issue is a fully independent, GitHub-ordered event — there's no
"which push is most recent" ambiguity the way there can be with a rolling git
branch. This script only ever looks at the one issue that triggered this run
plus whatever's already on file, so it can't double-process or grade a stale
submission out of order.
"""
import json
import os
import re

MAX_ATTEMPTS_PER_READING = 2


def extract_json(body):
    m = re.search(r"```json\s*(\{.*?\})\s*```", body, re.S)
    if not m:
        raise ValueError("No JSON code block found in the issue body.")
    return json.loads(m.group(1))


def load(path, default):
    if os.path.exists(path):
        return json.loads(open(path, encoding="utf-8").read())
    return default


def save(path, data):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    open(path, "w", encoding="utf-8").write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def write_outputs(comment, label, close):
    out_path = os.environ.get("GITHUB_OUTPUT")
    if not out_path:
        print(comment)
        return
    with open(out_path, "a", encoding="utf-8") as f:
        f.write("comment<<MLRK_EOF\n" + comment + "\nMLRK_EOF\n")
        f.write(f"label={label}\n")
        f.write(f"close={'true' if close else 'false'}\n")


def rebuild_leaderboard(issue_number):
    leaderboard = []
    for fname in sorted(os.listdir("results")):
        if not fname.endswith(".json"):
            continue
        r = load(f"results/{fname}", {})
        readings = r.get("readings", {})
        if not readings or not r.get("alias"):
            continue
        total_earned = sum(v["earned"] for v in readings.values())
        total_possible = sum(v["possible"] for v in readings.values())
        pct = round((total_earned / total_possible) * 100, 1) if total_possible else 0
        leaderboard.append({
            "alias": r["alias"],
            "readings_completed": len(readings),
            "avg_pct": pct,
        })
    leaderboard.sort(key=lambda x: (-x["avg_pct"], -x["readings_completed"]))
    save("leaderboard.json", {"last_updated_issue": issue_number, "students": leaderboard})


def main():
    issue_body = os.environ["ISSUE_BODY"]
    issue_number = os.environ["ISSUE_NUMBER"]
    issue_author = os.environ["ISSUE_AUTHOR"]

    try:
        payload = extract_json(issue_body)
        reading_id = payload["readingId"]
        score = payload["score"]
        submitted_persona = payload.get("persona") or {"name": "Anonymous", "emoji": "❓"}
    except Exception as e:
        write_outputs(
            f"This submission couldn't be auto-graded ({e}). "
            "An instructor will take a look. No need to resubmit yet.",
            "needs-review", False,
        )
        return

    results_path = f"results/{issue_author}.json"
    record = load(results_path, {"github_username": issue_author, "alias": None, "readings": {}})

    # Alias locks on the FIRST submission and is never overwritten by a later
    # one. That's what keeps one student's leaderboard entries from
    # fragmenting if they reroll their persona client-side between readings.
    alias_locked_this_time = False
    if not record.get("alias"):
        record["alias"] = submitted_persona
        alias_locked_this_time = True

    existing = record["readings"].get(reading_id)
    attempt_count = (existing.get("submission_count", 1) if existing else 0) + 1

    if existing and existing.get("submission_count", 1) >= MAX_ATTEMPTS_PER_READING:
        write_outputs(
            f"You've already used both submission attempts for this reading. "
            f"Your recorded score stays at **{existing['earned']} / {existing['possible']} "
            f"points ({existing['pct']}%)**. Reach out to an instructor if you think this "
            "needs a second look.",
            "attempt-limit-reached", True,
        )
        save(results_path, record)  # persist alias lock even if the score doesn't change
        return

    improved = existing is None or score["pct"] > existing["pct"]
    if improved:
        record["readings"][reading_id] = {
            "earned": score["earned"], "possible": score["possible"],
            "pct": score["pct"], "issue_number": issue_number,
            "submission_count": attempt_count,
        }
    else:
        record["readings"][reading_id]["submission_count"] = attempt_count
    save(results_path, record)

    # Per-reading snapshot too, so "how did everyone do on THIS reading" is a
    # single folder listing instead of opening every student's file.
    save(f"results/by-reading/{reading_id}/{issue_author}.json", {
        "github_username": issue_author,
        **record["readings"][reading_id],
    })

    rebuild_leaderboard(issue_number)

    alias = record["alias"]
    avg_pct = round(
        sum(v["pct"] for v in record["readings"].values()) / len(record["readings"]), 1
    )
    lines = [f"Recorded: **{score['earned']} / {score['possible']} points ({score['pct']}%)** on this reading."]
    if not improved and existing is not None:
        lines[0] += " Your earlier attempt already scored as well or better, so that's the one kept."
    if attempt_count >= MAX_ATTEMPTS_PER_READING:
        lines.append("That was your second and final submission attempt for this reading.")
    if alias_locked_this_time:
        lines.append(
            f"Your reading persona is now locked in as **{alias['emoji']} {alias['name']}**. "
            "That's what shows on the leaderboard from here on, no matter what you reroll to "
            "client-side on a future reading."
        )
    lines.append(
        f"You've completed **{len(record['readings'])}** reading(s) so far, averaging **{avg_pct}%**."
    )
    write_outputs("\n\n".join(lines), "graded", True)


if __name__ == "__main__":
    main()
