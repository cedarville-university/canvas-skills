# CAG Assessment And Resource Handling Rules (Generalized)

Use these rules when normalizing CAG table content before generating build JSON.

## Assessments Column

1. Parse each assessment line into:
- `assessment_title` (normalized title used in JSON)
- `assessment_description` (source instructional sentence kept for traceability)

2. Classify assessment type by meaning:
- Discussion keywords -> `discussion`
- Test/quiz/exam keywords -> `quiz` (or `classic quiz` when explicitly required)
- Journal/reflection/paper/project keywords -> `assignment`

3. Split mixed assessment lines:
- If one line represents multiple deliverables, split into multiple assessment records.

4. Normalize titles to a stable convention:
- Use one approved pattern across modules.
- Keep titles short and consistent.
- Do not include prompt text, rubric notes, or setup instructions in titles.

5. Apply numbering policy explicitly:
- Add numeric suffixes only when the course convention requires them.
- Support exceptions (for example skipped modules or custom test numbering starts).

## Resources Column

1. Classify each resource line into one of:
- `module_resource` (learner-facing content)
- `assessment_detail` (prompt/import/rubric/setup note tied to an assessment)
- `build_note` (implementation/admin note)

2. Keep only learner-facing content in module resources:
- Readings, videos, links, files, tools, worksheets, instructions students need directly.

3. Move assessment details out of module resources:
- Discussion prompts/questions
- \"Needs to be created\" notes
- \"Imported from other course\" notes
- Rubric/setup reminders

4. Treat \"import from another course\" as assessment detail:
- Keep it for mapping and migration context.
- Do not keep it as learner-facing module resource.

5. Add standard baseline resources only when policy requires it:
- Example: a generic \"Read assigned chapters\" item.

6. If a line is ambiguous:
- Keep it and flag for human review instead of dropping it.

## Validation Gates

- Every assessment has a type, normalized title, and module mapping.
- Assessment details map to an existing assessment title.
- Assessment titles contain no prompt text.
- Module resources contain only learner-facing resources unless intentionally overridden.
