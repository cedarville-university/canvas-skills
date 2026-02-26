# canvas-tools

Codex skill for interacting with Canvas LMS using the `canvasapi` Python library.

## Install

```bash
cp -R /path/to/canvas-skills/skills/canvas-tools ~/.codex/skills/
```


## Install With Skill Installer

If you want to install directly from GitHub using the Codex skill installer:

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py   --repo <owner>/<repo>   --path skills/canvas-tools
```

Replace `<owner>/<repo>` with your GitHub repo (for example `yourname/canvas-skills`).
After installation, restart Codex to pick up the new skill.

## Setup

Create a `.env` file in the skill folder or export environment variables:

```
CANVAS_BASE_URL=https://your.canvas.instance
CANVAS_API_TOKEN=your_token
```

## Use

See `SKILL.md` for workflow rules and `references/canvasapi.md` for common examples.

## CAG Workflow References

- `references/cag-course-build-workflow.md` - generalized end-to-end CAG cleanup/build workflow.
- `references/cag-assessment-resource-handling.md` - generalized handling rules for assessment and resources columns.
- `references/course-conversion-proposal-workflow.md` - planning workflow for converting an existing course to a new module count with workload balancing.
- `references/rubric-to-canvas-csv-workflow.md` - dedicated workflow for converting rubric text into Canvas import-ready CSV files.

## Rubric CSV Template

- `resources/rubric_import_template.csv` - base template for Canvas rubric CSV imports.

## Safety

Write actions (publishing, grading, updates) require explicit confirmation.
For dashboard favorites, review `SKILL.md` before bulk updates: adding one
favorite for users with no explicit favorites can narrow visible dashboard cards.
