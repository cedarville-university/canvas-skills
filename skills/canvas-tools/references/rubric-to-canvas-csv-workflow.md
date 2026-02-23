# Rubric To Canvas CSV Workflow

Use this workflow to convert rubric text into a Canvas LMS rubric import CSV.

## Template

- Start from `resources/rubric_import_template.csv`.
- Keep the same header and column order.
- Do not rename columns.

## Output Pattern

- Create one CSV per rubric for safer import and rollback.
- Recommended naming: `<rubric_name> Rubric.csv`.
- Example filenames: `Downturn Plan Debate Rubric.csv`, `Downturn Plan Memo Rubric.csv`.

## Required Columns

- `Rubric Name`
- `Criteria Name`
- `Criteria Description`
- `Criteria Enable Range` (use `false` unless range scoring is intentionally enabled)
- Rating fields in ordered triplets: `Rating Name`, `Rating Description`, `Rating Points`.
- Up to four rating triplets per criterion row.

## Conversion Rules

1. One criterion per CSV row.
2. Keep rubric and criterion names learner-facing and stable.
3. Put full performance-band language in `Rating Description`.
4. Keep points numeric (`0`, `1`, `2.5`, `4.5`, etc.).
5. For score ranges in source text (for example `4-5`), map to one numeric point value; default to midpoint (for example `4.5`) unless the instructor specifies otherwise.
6. Include a `No Marks` row level with `0` points for each criterion when possible.
7. If a criterion has fewer than four ratings, leave extra rating columns blank.
8. Escape commas and quotes correctly by using valid CSV quoting.

## Quality Checks Before Import

- Validate row count equals number of rubric criteria.
- Validate each row has the same number of columns as header.
- Validate total maximum points equals assignment rubric target.
- Verify wording fidelity to source rubric (no dropped constraints).
- Verify criteria order matches intended grading flow.

## Import Notes

- Import in Canvas as a rubric CSV.
- Review imported rubric in Canvas UI for criteria order, point values, and rating descriptions.
- If importing multiple rubrics, import one file at a time and verify each before continuing.

## Common Pitfalls

- Using non-numeric point values in `Rating Points`.
- Accidentally shifting columns because of unescaped commas in descriptions.
- Merging two rubrics into one CSV when assignment-level separation is preferred.
- Omitting `No Marks` when course grading policy expects a zero-level option.
