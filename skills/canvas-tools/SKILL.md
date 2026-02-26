---
name: canvas-tools
description: Use when working with Canvas LMS via the Python `canvasapi` library for any Canvas operations (courses, assignments, submissions, enrollments, users, grading, files, analytics, etc.). Trigger on requests that ask to read or update Canvas data or perform Canvas actions. Do not use direct HTTP/REST calls; use `canvasapi` methods.
---

# Canvas Tools

## Overview

Use `canvasapi` to read and update Canvas data and perform Canvas actions using IDs provided by the user.  
For Course Alignment Grid workflows, use the bundled parser script to convert CAG `.docx` files into build request JSON.

## Quick Start

1. Load `CANVAS_BASE_URL` and `CANVAS_API_TOKEN` from `.env` or environment.
2. Initialize the client with `Canvas(base_url, token)`.
3. Use `canvasapi` model methods for the requested Canvas objects.

## General Workflow For Any Canvas Task

1. Identify the Canvas object and action first (course, assignment, submission, enrollment, user, file).
2. Resolve required IDs before calling write operations.
3. Use `canvasapi` methods instead of direct HTTP calls.
4. Ask for explicit confirmation before write actions.
5. For any created or downloaded files, create and use a temp folder first.

## Temporary File Handling

- If a task creates or downloads files, create a temp folder and store all artifacts there.
- Prefer a deterministic path under `/tmp`, for example: `/tmp/canvas-tools/<course_id>/<assignment_id>/`.
- If IDs are not available, use a timestamped temp folder name.
- Report the temp folder path in the output so files are easy to find.
- Keep all intermediate files in that temp folder.

## Tasks

### List Courses

- Use `canvas.get_courses()` and iterate results.
- Return course `id` and `name` at minimum.

```python
from canvasapi import Canvas

canvas = Canvas(base_url, token)
for course in canvas.get_courses():
    print(course.id, course.name)
```

### List Courses By Term (If Term ID Provided)

- If the user provides a term ID, pass it via `enrollment_term_id`.
- Return course `id`, `name`, and `term` if available.

```python
courses = canvas.get_courses(enrollment_term_id=term_id)
for course in courses:
    print(course.id, course.name)
```

### List Assignments In Course

- Treat the numeric input as the Canvas course ID.
- Use `canvas.get_course(course_id).get_assignments()`.
- Include assignment `id`, `name`, and `due_at` when available.

```python
course = canvas.get_course(course_id)
for assignment in course.get_assignments():
    print(assignment.id, assignment.name, assignment.due_at)
```

### Filter Assignments By Due Date (If Requested)

- Use `get_assignments()` and filter client-side by `due_at`.
- If a date range is provided, show only assignments in that range.

```python
from datetime import datetime

course = canvas.get_course(course_id)
for assignment in course.get_assignments():
    if assignment.due_at:
        due = datetime.fromisoformat(assignment.due_at.replace("Z", "+00:00"))
        if start <= due <= end:
            print(assignment.id, assignment.name, assignment.due_at)
```

### Download Student Submissions

- Use course + assignment IDs to list submissions.
- For each submission, collect attachments and download them.
- Create a temp folder and save files there.

```python
from pathlib import Path

course = canvas.get_course(course_id)
assignment = course.get_assignment(assignment_id)
submissions = assignment.get_submissions()
output_dir = Path(f"/tmp/canvas-tools/{course_id}/{assignment_id}")
output_dir.mkdir(parents=True, exist_ok=True)
for submission in submissions:
    for attachment in submission.attachments or []:
        attachment.download(str(output_dir / attachment.filename))
```

### Submit Grades And Comments

- Grading is a write action. Ask for explicit confirmation before grading.
- Use `submission.edit` for score and comment.
- Require explicit values for score and comment text.

```python
course = canvas.get_course(course_id)
assignment = course.get_assignment(assignment_id)
submission = assignment.get_submission(user_id)
submission.edit(
    submission={"posted_grade": score},
    comment={"text_comment": comment}
)
```

### Publish Course

- Publishing is a write action. Ask for explicit confirmation before calling `course.publish()`.
- After confirmation, call `publish()` and report success.

```python
course = canvas.get_course(course_id)
course.publish()
```

### Manage Course Favorites (Dashboard Cards)

- Favorites are user-specific and must be set as the user (for example with `as_user_id` when an admin token can masquerade).
- Canvas has two dashboard behaviors:
- If a user has **no explicit favorites**, Canvas shows an auto-generated enrolled-course list.
- Once you add any favorite, Canvas switches to **explicit favorites mode** and dashboard cards come from that explicit list.
- **Important safety rule:** Never bulk-add a single favorite course without a pre-check. For users with no explicit favorites, this can unintentionally narrow dashboard cards to one course.

Safe patterns:
- Preferred for broad visibility: do not set favorites globally; ask users to star courses themselves.
- If you must add a required favorite and preserve visible cards:
- Read current favorites first (`get_favorite_courses`).
- If the user has no explicit favorites, promote currently returned courses into explicit favorites, then add the required course.
- If the user already has explicit favorites, add the required course only.

Rollback/repair patterns:
- Reset a user's explicit favorites to default auto-generated cards:
- `current_user.reset_favorite_courses(as_user_id=user_id)`
- Remove one course from favorites for a user:
- `DELETE /api/v1/users/self/favorites/courses/:id` (via `canvasapi.favorite.Favorite.remove(as_user_id=user_id)`)

```python
from canvasapi.favorite import Favorite

current_user = canvas.get_current_user()

# Add favorite course as a user (masquerade).
current_user.add_favorite_course(course_id, as_user_id=user_id)

# Reset user favorites to Canvas default generated list.
current_user.reset_favorite_courses(as_user_id=user_id)

# Remove one favorite course for a user.
fav = Favorite(current_user._requester, {"context_type": "Course", "context_id": course_id})
fav.remove(as_user_id=user_id)
```

### Parse CAG DOCX To Canvas Build Request JSON

- Use `scripts/extract_cag_to_build_request.py` when the user provides a CAG Word document and needs build payload JSON.
- Before extraction, apply normalization rules from:
- `references/cag-course-build-workflow.md`
- `references/cag-assessment-resource-handling.md`
- Use `--mode auto` (default) to parse with deterministic rules first, then fall back to OpenAI parsing for non-standard table layouts.
- Interactive prompting is enabled by default to fill missing values (for example `start_at`, `end_at`, `textbooks`, `course_policy`, and `course_id`) before output.
- Use `--no-interactive` when you need non-interactive batch output.
- The script reads course metadata, objectives, and the module table (4 or 5 columns).
- It maps assessments to assignment types (`quiz`, `classic quiz`, `discussion`, `assignment`), handles `(new_page)`, and supports `file:<id>` links.
- If an assessment item already includes an explicit assignment id marker (`id:123`, `id=q7`, `(id:a2)`, `[id:q3]`), the script preserves it instead of generating a new id.
- It outputs full `buildRequest` JSON with course data nested under `course`.
- Validate output with the provided schema when available.

```bash
python3 scripts/extract_cag_to_build_request.py \
  --input-docx /path/to/cag.docx \
  --output-json /tmp/build_request.json \
  --schema /path/to/courseInfo_buildRequest_schema.json \
  --course-id 12345 \
  --mode auto
```

- For custom extraction behavior, pass instruction markdown:

```bash
python3 scripts/extract_cag_to_build_request.py \
  --input-docx /path/to/cag.docx \
  --output-json /tmp/build_request.json \
  --schema /path/to/courseInfo_buildRequest_schema.json \
  --course-id 12345 \
  --mode llm \
  --instructions /path/to/custom-gpt-instruction.md
```

### Convert Rubric Text To Canvas Import CSV

- Use `references/rubric-to-canvas-csv-workflow.md` for the complete conversion procedure.
- Start from `resources/rubric_import_template.csv` and keep header order unchanged.
- Prefer one CSV per rubric for safer Canvas import and easier rollback.
- Keep points numeric and include `No Marks` (`0`) when course policy expects a zero-level option.
- After generating CSV, validate column count consistency and point totals before import.

## Pagination

`canvasapi` returns paginated iterators. Always iterate the result set rather than assuming one page.

## Auth And Config

- Prefer `.env` with `CANVAS_BASE_URL` and `CANVAS_API_TOKEN`.
- If `.env` is used, load it with `python-dotenv` when available.
- For OAuth-based auth, see `references/auth.md` and update only the token acquisition step.
- For local setup, see `references/setup.md` and `.env.example`.

## Output Expectations

- Be explicit about course IDs and names in results.
- For assignments, include assignment `id`, `name`, and `due_at` when available.
- For submission downloads, report destination path and file names.
- For grading, report user ID, score, and comment summary.
- For publish actions, include the course ID and confirm success.

## Safety

- Never call `publish()` without explicit user confirmation in the same session.
- Never submit grades or comments without explicit user confirmation in the same session.

## Resources

- `references/canvasapi.md` for common `canvasapi` usage patterns, pagination notes, and general workflows.
- `references/submissions.md` for submission download and grading patterns.
- `references/auth.md` for `.env` configuration and OAuth migration notes.
- `references/setup.md` for local `.env` setup instructions.
- `references/cag-build-request.md` for CAG-to-build JSON mapping rules.
- `references/cag-course-build-workflow.md` for generalized end-to-end CAG cleanup/build workflow.
- `references/cag-assessment-resource-handling.md` for generalized assessment/resources column handling rules.
- `scripts/extract_cag_to_build_request.py` for deterministic CAG DOCX parsing.
