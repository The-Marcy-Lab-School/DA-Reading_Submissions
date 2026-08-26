# DA Reading Submissions

Private, course-only repo. This is where the "Submit for credit" button on a
Data Analytics Fellowship interactive reading sends your work — it's not
public, and only people added as collaborators here (DA Cohort students and
instructors) can see it.

## How it works

1. On a reading, you optionally type your GitHub username (a readable label
   only — see "Identity" below) and click **Submit for credit**.
2. That opens a pre-filled GitHub Issue in this repo with your answers, your
   score, and your chosen reading persona (alias + emoji) as a JSON block.
3. You submit the issue yourself, logged into your own GitHub account. No
   token, no password, nothing pasted in — just the normal "create issue" flow.
4. Within a minute or two, a GitHub Action reads it, records your score, comments
   back on the issue with your result, and closes it automatically.

You do **not** need write access to this repo's code — **Read** access is
enough to open issues. If you can't see this repo at all, ask an instructor
to add you as a collaborator.

## Identity: why you can't fake this

Grading uses **who you actually are, logged into GitHub, when you open the
issue** (`github.event.issue.user.login` — GitHub sets this itself, it can't
be typed over). Any "GitHub username" field on the reading page is just a
human-readable label in the issue text — it has no effect on whose score gets
recorded.

## Your leaderboard persona

Each reading lets you pick a fun alias + emoji (a reroll-able generator, not
free text) that shows up on the public-within-this-repo leaderboard instead
of your real name — that part's just for fun/light anonymity among
classmates.

**Your alias locks in on your very first submission.** After that, you can
still reroll it for fun on the reading page itself, but it won't change what
shows on the leaderboard — that stays tied to your GitHub username
permanently, so your progress reads as one consistent identity across every
reading instead of fragmenting into several different-looking entries.

## What gets stored

- `results/<your-github-username>.json` — your full record: every reading
  you've submitted, your score on each (best attempt kept if you resubmit),
  and your locked alias. Visible to collaborators on this repo (instructors
  and classmates), not the public internet.
- `leaderboard.json` — alias + emoji, readings completed, and average score
  percentage across all your readings, for everyone. No real names or
  GitHub handles in this file.

Grading trusts the score your browser computed and submitted — this is
formative practice, not a proctored exam, so there's no server-side
re-grading of every answer. Please don't edit your own score in devtools;
it defeats the point of practicing before lecture.

## For instructors

- Add DA Cohort students as collaborators with **Read** role — that's enough
  for them to open issues here, and keeps write access to the grading
  workflow itself restricted to instructors/admins.
- `scripts/grade.py` is the whole grading logic — plain Python, no external
  services. `.github/workflows/grade-submission.yml` wires it to fire on
  every new issue.
- If a submission can't be parsed, it's labeled `needs-review` and left open
  instead of silently failing — check issues with that label periodically.
