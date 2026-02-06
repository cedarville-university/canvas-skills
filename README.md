# Canvas Skills

Codex skill for working with Canvas LMS using the `canvasapi` Python library.

## Install

Clone this repo and copy the skill into your Codex skills folder:

```bash
cp -R skills/canvas-tools ~/.codex/skills/
```

If your Codex home is different, replace `~/.codex` with your `CODEX_HOME`.


## Install With Skill Installer

If you want to install directly from GitHub using the Codex skill installer:

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py   --repo <owner>/<repo>   --path skills/canvas-tools
```

Replace `<owner>/<repo>` with your GitHub repo (for example `yourname/canvas-skills`).
After installation, restart Codex to pick up the new skill.

## Setup

Create a `.env` file in your working folder (for example, `~/user/documents/.env`) 

```
CANVAS_BASE_URL=https://your.canvas.instance
CANVAS_API_TOKEN=your_token
```

## Usage

The skill is defined in:

- `skills/canvas-tools/SKILL.md`

Reference examples are in:

- `skills/canvas-tools/references/canvasapi.md`

## Safety

Write actions (publishing, grading, updates) require explicit confirmation.

## License

MIT
