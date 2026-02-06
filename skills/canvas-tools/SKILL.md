---
name: canvas-tools
description: Use when working with Canvas LMS via the Python `canvasapi` library for any Canvas operations (courses, assignments, submissions, enrollments, users, grading, files, analytics, etc.). Trigger on requests that ask to read or update Canvas data or perform Canvas actions. Do not use direct HTTP/REST calls; use `canvasapi` methods.
---

# Canvas Tools

## Overview

Use `canvasapi` to read and update Canvas data and perform Canvas actions using IDs provided by the user.

## Quick Start

1. Load `CANVAS_BASE_URL` and `CANVAS_API_TOKEN` from `.env` or environment.
2. Initialize the client with `Canvas(base_url, token)`.
3. Use `canvasapi` model methods for the requested Canvas objects.

## General Workflow For Any Canvas Task



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
- Save files to a user-specified output directory.

```python
course = canvas.get_course(course_id)
assignment = course.get_assignment(assignment_id)
submissions = assignment.get_submissions()
for submission in submissions:
    for attachment in submission.attachments or []:
        attachment.download("/path/to/output")
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
- `scripts/smoke_test.py` for a quick config check and sample course listing.
