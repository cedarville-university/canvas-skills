# CAG DOCX To Build Request JSON

Use `scripts/extract_cag_to_build_request.py` to convert a Course Alignment Grid
Word document into `buildRequest` JSON for Canvas course build tooling.

Modes:
- `--mode deterministic`: rule-based parser only.
- `--mode llm`: OpenAI extraction only.
- `--mode auto` (default): deterministic first, then OpenAI fallback on parse failure or low confidence.
- interactive prompting is enabled by default; use `--no-interactive` to disable.

## Input Expectations

- A `.docx` CAG with course metadata blocks and one alignment table.
- Table format must be 4 or 5 columns.
- Standard sections are expected:
  - `Textbook:`
  - `Course policy`
  - `Course Overview`
  - `Current Course Objectives`
  - `Course alignment grid`

## Mapping Rules

- Missing values stay present in JSON with empty values (`""` or `[]`).
- Bullet symbols and extra formatting are removed.
- Objectives have trailing parenthetical references and trailing numbering stripped.
- Module numbering is incremental:
  - `id`: 1..N
  - `number`: 1..N
  - `position`: starts at `4` and increments by `1`
- Assessment to assignment mapping:
  - if an assessment includes explicit id marker (`id:123`, `id=q7`, `(id:a2)`, `[id:q3]`), preserve that id in `assignments[].id`
  - generate `d#`, `q#`, `a#` ids only when no explicit id exists
  - contains `discussion` -> `type: "discussion"` with `d#`
  - contains `classic quiz` -> `type: "classic quiz"` with `q#`; remove `classic` from name
  - contains `quiz` -> `type: "quiz"` with `q#`
  - contains `exam` -> quiz behavior (`classic quiz` if explicitly classic) without renaming
  - otherwise -> `type: "assignment"` with `a#`
- Content mapping:
  - `(new_page)` or `#new_page` creates a page in `pages` (`p#`) and content link `#new_page`
  - `file:<id>` creates a file entry and Canvas file link in `content`
  - URLs are preserved as HTML links

## Command

```bash
python3 scripts/extract_cag_to_build_request.py \
  --input-docx /path/to/cag.docx \
  --output-json /tmp/build_request.json \
  --schema /path/to/courseInfo_buildRequest_schema.json \
  --course-id 12345 \
  --mode auto
```

With custom instruction file:

```bash
python3 scripts/extract_cag_to_build_request.py \
  --input-docx /path/to/cag.docx \
  --output-json /tmp/build_request.json \
  --schema /path/to/courseInfo_buildRequest_schema.json \
  --course-id 12345 \
  --mode llm \
  --instructions /path/to/custom-gpt-instruction.md
```

## Key Options

- `--course-id` sets build payload `course_id` and file-link course id.
- `--start-date` and `--end-date` override derived date-time defaults.
- `--default-due-day`, `--default-discussion-due-day`, `--default-last-day` set scheduling defaults.
- `--build-type` and template fields override request defaults.
- `--schema` validates output with `jsonschema`.
- `--llm-model` sets the OpenAI model for `llm/auto` fallback.
- `--api-key-env` selects the API-key environment variable (default `OPENAI_API_KEY`).
- `--interactive` / `--no-interactive` toggles prompting for missing fields like dates, textbooks, policy, and course id.

## Operational Build Workflow

Use this sequence after JSON generation.

### 1) Post-Process Build JSON

- Verify course metadata: code, name, description, credits, year, term, `start_at`, `end_at`, textbooks.
- Verify objectives list contains only intended objective items.
- Verify module names, objectives, assessments, and resources.
- Verify assessment type mapping (`discussion`, `assignment`, `quiz`, `classic quiz`).

### 2) Canvas Assignment ID Reconciliation

After generating JSON, reconcile assignment IDs against the target Canvas course:

1. Use the target `course_id`.
2. List existing assignments in that Canvas course.
3. Match by assignment name (`modules[].assignments[].name` to Canvas assignment names).
4. If found, replace `modules[].assignments[].id` with the Canvas assignment ID.
5. If not found, keep the existing CAG assignment ID.
6. Keep assignment `name` and `type` unchanged while reconciling IDs.
7. If one CAG assignment text represents multiple Canvas assignments, split into multiple assignment objects so each object has one Canvas ID.

### 3) Preflight Before Build

- Confirm server target (production vs beta) matches intent.
- Confirm templates exist in the target course.
- Confirm JSON has unique assignment IDs and valid types.
- Confirm required permissions and token scope.

### 4) Build

- Run builder (`builder_build` or `scripts/build_course_from_request.py`).
- Capture status, message, and course URL.

### 5) Verify Post-Build

- Verify modules created and ordered correctly.
- Verify assessments linked into expected modules.
- Verify critical items (tests/final/capstone/discussion templates).

### 6) Recover If Needed

- Run cleanup (`builder_cleanbuild`) if build output is incorrect.
- Fix source JSON or template/settings issues.
- Re-run build and verify again.

### 7) Archive Artifacts

- Cleaned CAG `.docx`/`.md`
- Final build JSON
- ID reconciliation notes
- Build/clean output logs

## LLM Requirements

- `openai` Python package installed.
- API key available in environment (`OPENAI_API_KEY` by default).
