# Submissions And Grading

## List Submissions For An Assignment

```python
course = canvas.get_course(course_id)
assignment = course.get_assignment(assignment_id)
submissions = assignment.get_submissions()
```

## Download Attachment Files

Each submission may include attachment objects. Use `attachment.download()` to save files.

```python
for submission in submissions:
    for attachment in submission.attachments or []:
        attachment.download("/path/to/output")
```

## Submit Grades And Comments

Use `submission.edit` with `posted_grade` and `text_comment`.

```python
submission = assignment.get_submission(user_id)
submission.edit(
    submission={"posted_grade": score},
    comment={"text_comment": comment}
)
```

## Notes

- Require explicit course ID, assignment ID, and user ID for grading actions.
- Confirm write actions before applying grades or comments.
- For bulk grading, iterate students and log each result.
