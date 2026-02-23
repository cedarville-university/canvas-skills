# CAG Course Build Workflow (Generalized)

Use this workflow for any course build generated from a CAG document.

## 1) Collect Inputs

- Target Canvas `course_id`
- Build date range (`start_date`, `end_date`)
- Scheduling defaults (`default_due_day`, `default_discussion_due_day`, `default_last_day`)
- `build_type` (`1` existing assignments, `2` full build)
- Template names (`overview_page_template`, `discussion_template`, `assignment_template`, `newquiz_template`, `classicquiz_template`)
- Clean CAG source `.docx`

## 2) Clean And Normalize The CAG

- Keep only approved course objective section(s).
- Normalize module titles to a consistent capitalization style.
- Normalize assessment titles to a stable naming convention.
- Keep learner-facing resources in module resources.
- Move prompts/import/setup notes into an assessment-details section.
- Apply detailed assessment/resources rules from
  `references/cag-assessment-resource-handling.md`.

## 3) Run CAG Build Phase

- Follow `references/cag-build-request.md` for:
- parser usage (`extract_cag_to_build_request.py`)
- key options and schema validation
- post-processing and assignment-ID reconciliation
- preflight, build, verification, recovery, and artifact archive
