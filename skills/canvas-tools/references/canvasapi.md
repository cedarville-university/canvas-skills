# CanvasAPI Reference (Broad Coverage)

This reference summarizes common `canvasapi` capabilities and patterns across
Canvas objects. It is intentionally practical and example-driven rather than
exhaustive. For very large datasets, rely on iterators and avoid `list()` unless
you need eager materialization for formatting.

## General Pattern

1. Start from `Canvas(base_url, token)`.
2. Fetch a top-level object (account, course, user).
3. Call methods on that object (list, get, create, update).
4. For write actions, confirm before calling the method.

## Initialize Client

```python
from canvasapi import Canvas

canvas = Canvas(base_url, token)
```

## List Courses

```python
for course in canvas.get_courses():
    print(course.id, course.name)
```

## List Courses By Term

```python
courses = canvas.get_courses(enrollment_term_id=term_id)
for course in courses:
    print(course.id, course.name)
```

## Fetch Course By ID

```python
course = canvas.get_course(course_id)
```

## Update Course Settings

```python
course = canvas.get_course(course_id)
course.update(course={"name": "New Name", "course_code": "NEW-101"})
```

## List Assignments In A Course

```python
for assignment in course.get_assignments():
    print(assignment.id, assignment.name, assignment.due_at)
```

## List Assignments With Filters

```python
for assignment in course.get_assignments(bucket="upcoming"):
    print(assignment.id, assignment.name)
```

## Filter Assignments By Due Date (Client-Side)

```python
from datetime import datetime

for assignment in course.get_assignments():
    if assignment.due_at:
        due = datetime.fromisoformat(assignment.due_at.replace("Z", "+00:00"))
        if start <= due <= end:
            print(assignment.id, assignment.name, assignment.due_at)
```

## Submissions (Assignment)

```python
assignment = course.get_assignment(assignment_id)
for submission in assignment.get_submissions():
    print(submission.id, submission.user_id, submission.score)
```

## Submissions (Course)

```python
for submission in course.get_submissions():
    print(submission.id, submission.assignment_id, submission.user_id)
```

## Grade A Submission

```python
assignment = course.get_assignment(assignment_id)
assignment.grade_student(
    user_id,
    submission={"posted_grade": "95", "comment": {"text_comment": "Nice work"}},
)
```

## Users In A Course

```python
for user in course.get_users(enrollment_type=["student"]):
    print(user.id, user.name)
```

## Enrollments

```python
for enrollment in course.get_enrollments():
    print(enrollment.id, enrollment.user_id, enrollment.type)
```

## Create Enrollment

```python
course = canvas.get_course(course_id)
course.enroll_user(user_id, enrollment_type="StudentEnrollment")
```

## Sections

```python
for section in course.get_sections():
    print(section.id, section.name)
```

## Groups And Group Categories

```python
for category in course.get_group_categories():
    print(category.id, category.name)
for group in course.get_groups():
    print(group.id, group.name)
```

## Files

```python
for file in course.get_files():
    print(file.id, file.display_name, file.size)
```

## Upload A File (Course)

```python
course = canvas.get_course(course_id)
with open("syllabus.pdf", "rb") as fh:
    course.upload(fh, "syllabus.pdf")
```

## Modules

```python
for module in course.get_modules():
    print(module.id, module.name)
```

## Module Items

```python
module = course.get_module(module_id)
for item in module.get_module_items():
    print(item.id, item.title, item.type)
```

## Pages

```python
for page in course.get_pages():
    print(page.page_id, page.title)
```

## Create Or Update Page

```python
course = canvas.get_course(course_id)
course.create_page(
    wiki_page={"title": "Welcome", "body": "<p>Hello</p>", "published": True}
)
```

## Announcements

```python
for topic in course.get_discussion_topics(only_announcements=True):
    print(topic.id, topic.title)
```

## Create Announcement

```python
course.create_discussion_topic(
    title="Reminder",
    message="Assignment due Friday.",
    is_announcement=True,
)
```

## Discussions

```python
for topic in course.get_discussion_topics():
    print(topic.id, topic.title)
```

## Quizzes

```python
for quiz in course.get_quizzes():
    print(quiz.id, quiz.title)
```

## Quiz Submissions

```python
quiz = course.get_quiz(quiz_id)
for submission in quiz.get_submissions():
    print(submission.id, submission.user_id, submission.score)
```

## Rubrics

```python
for rubric in course.get_rubrics():
    print(rubric.id, rubric.title)
```

## Outcomes

```python
for outcome in course.get_outcomes():
    print(outcome.id, outcome.title)
```

## Calendar Events

```python
for event in course.get_calendar_events():
    print(event.id, event.title, event.start_at)
```

## Course Analytics (If Enabled)

```python
for summary in course.get_analytics():
    print(summary)
```

## External Tools (LTI)

```python
for tool in course.get_external_tools():
    print(tool.id, tool.name)
```

## Account-Level Objects

```python
account = canvas.get_account(account_id)
for course in account.get_courses():
    print(course.id, course.name)
for user in account.get_users():
    print(user.id, user.name)
```

## Terms

```python
account = canvas.get_account(account_id)
for term in account.get_enrollment_terms():
    print(term.id, term.name)
```

## Publish Course

```python
course.publish()
```

## Pagination Notes

- `canvasapi` returns paginated iterators; always iterate the full iterator.
- Avoid calling `list()` on large datasets unless required for output formatting.
