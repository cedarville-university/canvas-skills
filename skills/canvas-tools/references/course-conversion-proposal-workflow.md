# Course Conversion Proposal Workflow

Use this workflow when you need to convert an existing Canvas course into a new module count (for example, 14 modules to 8 modules) before building or rebuilding the course.

## Purpose

- Produce a planning artifact first (`.md` and optional `.docx`) before making Canvas writes.
- Keep source traceability by preserving original assignment names and objective wording in the proposal.
- Balance student workload to a target range per module.

## Inputs

- Course export markdown or structured export (`course-<id>-export.md` / `.json`).
- Target module count and naming convention (for example, 8 modules).
- Workload target range (for example, 15-18 hours per module).
- Workload reference source (institutional or approved external calculator).

## Outputs

- Conversion proposal markdown (recommended naming: `course-<id>-<n>-module-conversion-proposal.md`).
- Optional Word export for review (`.docx`).
- Explicit assumptions and risk notes.

## Workflow

### 1) Inventory Current Course

- Extract module titles, chapter/content coverage, objectives, and assessments.
- Capture objective text and assignment titles exactly as currently named.
- Identify heavy assessments (papers, projects, cumulative exams, high-effort discussions).

### 2) Draft New Module Map

- Map old modules into new modules (for example, `M1-M2 -> New Module 1`).
- Keep a source-coverage column so each new module traces to original chapters/modules.
- Preserve original objective language in module objective cells; do not paraphrase unless requested.

### 3) Build Workload Model

- Define workload assumptions (reading rate, quiz time, discussion time, paper time, study overhead).
- Estimate hours per new module and compute overall average.
- Verify the average and each module are in target range; rebalance if out of range.

### 4) Place Assessments For Balance

- Keep original assignment titles in the proposal for cross-reference.
- Spread major writing tasks and milestone checkpoints across modules.
- Avoid stacking multiple high-effort assessments in the same module unless intentional.

### 5) Validate Alignment

- Check each new module's chapter range against chapter quiz placement.
- Confirm major assessments are placed where objective/content coverage supports them.
- Re-check modules late in term separately (drift often appears in last third of the map).

### 6) Format For Reviewer Clarity

- Use one summary table with these columns: new module title, source modules/chapters, module objectives, key assessments (original names), estimated hours.
- For table cells with many items, use HTML unordered lists (`<ul><li>...</li></ul>`).
- Add an implementation note: source names/objectives are references and can be renamed during implementation.

### 7) Finalize Artifacts

- Save markdown proposal.
- Export `.docx` from markdown (for example with `pandoc`).
- Keep both files synchronized after every revision.

## Recommended Validation Checklist

- Terminology is consistent (`module` vs `week`).
- Objective text is original where requested.
- Assignment titles are original where requested.
- Milestone schedule is exactly as requested.
- Chapter quiz alignment is correct across all modules.
- Estimated hours were updated after every assessment move.

## Example Decisions Applied In Recent Run

- Reduced a major project to four milestones due in Modules 1, 3, 5, and 7.
- Shifted a reflection paper earlier to rebalance load.
- Corrected chapter quiz alignment for later modules after source-chapter mismatch review.
