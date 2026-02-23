#!/usr/bin/env python3
"""Build a Canvas course from a buildRequest JSON payload using canvasapi.

This script mirrors the behavior of the CUGrader builder `/api/builder/build` endpoint:
- validates payload fields
- resolves templates from the target Canvas course
- supports build_type 1 (map existing assignments by due week)
- supports build_type 2 (upsert/create assignments/discussions/quizzes)
- updates syllabus placeholders
- creates modules and module items
- writes build artifacts to disk
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from canvasapi import Canvas

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


DEFAULTS: dict[str, Any] = {
    "dry_run": False,
    "course_id": -1,
    "start_date": "2025-08-26 00:00:00",
    "end_date": "2025-12-15 23:59:59",
    "default_due_day": 6,
    "default_discussion_due_day": 3,
    "default_last_day": 4,
    "build_type": 2,
    "overview_page_template": "Module 1: Overview",
    "discussion_template": "Group Discussion: [Title Here]",
    "assignment_template": "Individual Assignment: [Title Here]",
    "newquiz_template": "New Quiz: [Title Here]",
    "classicquiz_template": "Classic Quiz: [Title Here]",
}


@dataclass
class BuildStats:
    assignments_created: int = 0
    assignments_updated: int = 0
    discussions_created: int = 0
    discussions_updated: int = 0
    new_quizzes_created: int = 0
    new_quizzes_updated: int = 0
    classic_quizzes_created: int = 0
    classic_quizzes_updated: int = 0
    modules_created: int = 0
    module_items_created: int = 0
    pages_created: int = 0
    syllabus_updated: bool = False


class BuildError(Exception):
    """Structured build error with an HTTP-like status code."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


def maybe_load_dotenv() -> None:
    if load_dotenv is None:
        return
    load_dotenv(override=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Canvas course from buildRequest JSON.")
    parser.add_argument("--input-json", required=True, help="Path to buildRequest JSON file")
    parser.add_argument(
        "--files-root",
        default="/tmp/canvas-tools/builder",
        help="Folder for build artifacts (default: /tmp/canvas-tools/builder)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force dry run (validates and loads templates only; no Canvas writes)",
    )
    parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="Required for non-dry-run execution because this script performs write actions",
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="Canvas base URL override. Defaults to CANVAS_BASE_URL from env.",
    )
    parser.add_argument(
        "--api-token",
        default="",
        help="Canvas API token override. Defaults to CANVAS_API_TOKEN from env.",
    )
    parser.add_argument(
        "--print-course-json",
        action="store_true",
        help="Print final built course JSON to stdout in addition to result metadata",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BuildError(f"Input file not found: {path}", status_code=400) from exc
    except json.JSONDecodeError as exc:
        raise BuildError(f"Invalid JSON in {path}: {exc}", status_code=400) from exc


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def first_match(items: list[Any], key: str, expected: Any) -> Any | None:
    for item in items:
        if getattr(item, key, None) == expected:
            return item
    return None


def normalize_course_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(DEFAULTS)
    data.update(payload)

    if data.get("course_id", -1) <= 0:
        raise BuildError("course_id must be a positive integer.", status_code=400)

    course = data.get("course")
    if not isinstance(course, dict):
        raise BuildError("course must be an object.", status_code=400)

    modules = course.get("modules")
    if not isinstance(modules, list):
        raise BuildError("course must include a 'modules' list.", status_code=400)

    if data.get("build_type") not in {1, 2}:
        raise BuildError(
            "build_type must be 1 (existing assignments) or 2 (full build).",
            status_code=400,
        )

    for module in modules:
        if not isinstance(module, dict):
            raise BuildError("Each module must be an object.", status_code=400)
        module.setdefault("name", "")
        module.setdefault("number", 0)
        module.setdefault("position", 0)
        module.setdefault("overview", "")
        module.setdefault("objectives", [])
        module.setdefault("assessments", [])
        module.setdefault("assignments", [])
        module.setdefault("content", [])
        module.setdefault("pages", [])
        module.setdefault("files", [])
        if not isinstance(module["assessments"], list):
            module["assessments"] = []
        if not isinstance(module["assignments"], list):
            module["assignments"] = []
        if not isinstance(module["content"], list):
            module["content"] = []
        if not isinstance(module["pages"], list):
            module["pages"] = []
        if not isinstance(module["files"], list):
            module["files"] = []

    return data


def ensure_canvas_client(args: argparse.Namespace) -> Canvas:
    base_url = args.base_url.strip() or os.getenv("CANVAS_BASE_URL", "").strip()
    token = args.api_token.strip() or os.getenv("CANVAS_API_TOKEN", "").strip()
    if not base_url:
        raise BuildError("Missing Canvas base URL. Set CANVAS_BASE_URL or pass --base-url.", 400)
    if not token:
        raise BuildError("Missing Canvas API token. Set CANVAS_API_TOKEN or pass --api-token.", 400)
    return Canvas(base_url, token)


def canvas_root_url(canvas: Canvas) -> str:
    requester = getattr(canvas, "_Canvas__requester", None)
    base = getattr(requester, "base_url", "") if requester else ""
    return str(base).split("/api/v1/")[0].rstrip("/")


def course_url(base_url: str, course_id: int) -> str:
    root = base_url.rstrip("/")
    return f"{root}/courses/{course_id}" if root else f"/courses/{course_id}"


def replace_section(pattern: str, replacement: str, text: str) -> str:
    return re.sub(pattern, replacement, text, flags=re.IGNORECASE)


def remove_sample_hint(text: str) -> str:
    return re.sub(r"(<p.*Please see the sample below.*</p>)", "", text, flags=re.IGNORECASE)


def get_overview_page_template(course: Any, title: str) -> str:
    for page in course.get_pages(search_term=title):
        if getattr(page, "title", "") != title:
            continue
        body = getattr(page, "body", "") or ""
        body = replace_section(
            r"<h2>.*Module Overview.*</strong></h2>([\s\S]*?)<hr",
            "<div id = 'objectives'>[objectives]</div>",
            body,
        )
        body = replace_section(
            r"<h2>.*Content.*</strong></h2>\n([\s\S]*?)<hr",
            "<p>Read and view the following:</p><div id = 'content'>[content]</div>",
            body,
        )
        body = replace_section(
            r"<h2>.*Assessments</strong></h2>\n([\s\S]*)",
            "<p>In order to successfully complete this module, you will complete the following activities and assignments:</p><div id = 'assessments'>[assessments]</div>",
            body,
        )
        body = body.replace('[change to "Module Objectives" if you have specific objectives for this module]', "")
        body = body.replace("Module Overview", "Module Objectives")
        return "[overview]" + body
    raise BuildError(f"Template page {title} not found in course {course.id}. Please create the page first.", 404)


def get_assignment_template(course: Any, name: str) -> str:
    for assignment in course.get_assignments(search_term=name):
        if getattr(assignment, "name", "") != name:
            continue
        template = getattr(assignment, "description", "") or ""
        if not template:
            raise BuildError(f"Template assignment {name} in course {course.id} is missing description.", 404)
        template = replace_section(
            r"<h2>.*Overview</strong></h2>([\s\S]*?)<hr",
            "<div id = 'overview'>[overview]</div>",
            template,
        )
        template = replace_section(
            r"<h2>.*Guidelines</strong></h2>([\s\S]*?)<hr",
            "<div id = 'guidelines'>[guidelines]</div>",
            template,
        )
        return remove_sample_hint(template)
    raise BuildError(
        f"Template assignment {name} not found in course {course.id}. Please create the assignment first.",
        404,
    )


def get_discussion_template(course: Any, title: str) -> str:
    for discussion in course.get_discussion_topics():
        if getattr(discussion, "title", "") != title:
            continue
        template = getattr(discussion, "message", "") or ""
        if not template:
            raise BuildError(f"Template discussion {title} in course {course.id} is missing message body.", 404)
        template = replace_section(
            r"<h2>.*Prompt</strong></h2>([\s\S]*?)<hr",
            "<div id = 'prompt'>[prompt]</div>",
            template,
        )
        template = replace_section(
            r"<h2>.*Guidelines</strong></h2>([\s\S]*?)<hr",
            "<div id = 'guidelines'>[guidelines]</div>",
            template,
        )
        return remove_sample_hint(template)
    raise BuildError(
        f"Template discussion {title} not found in course {course.id}. Please create the discussion first.",
        404,
    )


def get_quiz_template_content(quizzes: list[Any], name: str, fields: list[str], kind: str, course_id: int) -> str:
    for quiz in quizzes:
        if getattr(quiz, "title", "") != name:
            continue
        for field in fields:
            content = getattr(quiz, field, "") or ""
            if content:
                return content
        fields_msg = ", ".join(fields)
        raise BuildError(
            f"Template {kind} {name} in course {course_id} is missing content fields: {fields_msg}.",
            404,
        )
    raise BuildError(
        f"Template {kind} {name} not found in course {course_id}. Please create the {kind} first.",
        404,
    )


def get_new_quiz_template(course: Any, title: str) -> str:
    quizzes = list(course.get_new_quizzes())
    template = get_quiz_template_content(quizzes, title, ["instructions"], "quiz", course.id)
    return replace_section(
        r"<h2>.*Guidelines</strong></h2>([\s\S]*)",
        "<div id = 'guidelines'>[guidelines]</div>",
        template,
    )


def get_classic_quiz_template(course: Any, title: str) -> str:
    quizzes = list(course.get_quizzes())
    template = get_quiz_template_content(quizzes, title, ["description", "instructions"], "classic quiz", course.id)
    template = replace_section(
        r"<h2>.*Guidelines</strong></h2>([\s\S]*?)<hr",
        "<div id = 'guidelines'>[guidelines]</div>",
        template,
    )
    return remove_sample_hint(template)


def render_syllabus_template(raw_syllabus: str) -> str:
    if not raw_syllabus:
        return ""
    syllabus = raw_syllabus
    syllabus = replace_section(
        r"<h3.*>.*Instructor Information</h3>\n([\s\S]*?)<p",
        "<div id = 'instructors'>[instructors]</div>",
        syllabus,
    )
    syllabus = replace_section(
        r"<h3.*>.*Course Learning Outcomes</h3>([\s\S]*?)<p",
        "<div id = 'objectives'>[objectives]</div>",
        syllabus,
    )
    syllabus = replace_section(
        r"<h3.*>.*Required Textbooks.*</h3>\n([\s\S]*?)<p",
        "<div id = 'textbooks'>[textbooks]</div>",
        syllabus,
    )
    return syllabus


def update_syllabus(canvas: Canvas, course: Any, course_json: dict[str, Any]) -> None:
    course_with_syllabus = canvas.get_course(course.id, include=["syllabus_body"])
    syllabus_template = render_syllabus_template(getattr(course_with_syllabus, "syllabus_body", "") or "")
    syllabus_body = syllabus_template
    syllabus_done = True

    if course_json.get("course_code"):
        syllabus_body = syllabus_body.replace("[Course Code]", str(course_json["course_code"]))
    else:
        syllabus_done = False

    if course_json.get("course_name"):
        syllabus_body = syllabus_body.replace("[Course Name]", str(course_json["course_name"]))
    else:
        syllabus_done = False

    if course_json.get("description"):
        syllabus_body = syllabus_body.replace("[Course Description]", str(course_json["description"]))
    else:
        syllabus_done = False

    if course_json.get("year"):
        syllabus_body = syllabus_body.replace("[Year]", str(course_json["year"]))
    else:
        syllabus_done = False

    if course_json.get("term"):
        syllabus_body = syllabus_body.replace("[Term]", str(course_json["term"]))
    else:
        syllabus_done = False

    if course_json.get("start_at"):
        syllabus_body = syllabus_body.replace("[StartDate]", str(course_json["start_at"]))
    else:
        syllabus_done = False

    if course_json.get("end_at"):
        syllabus_body = syllabus_body.replace("[EndDate]", str(course_json["end_at"]))
    else:
        syllabus_done = False

    if course_json.get("credits"):
        syllabus_body = syllabus_body.replace("[#]", str(course_json["credits"]))
    else:
        syllabus_done = False

    objectives = course_json.get("objectives", [])
    if objectives:
        objectives_html = "<ul>" + "".join(f"<li>{o}</li>" for o in objectives) + "</ul>"
        syllabus_body = syllabus_body.replace("[objectives]", objectives_html)
    else:
        syllabus_done = False

    textbooks = course_json.get("textbooks", [])
    if textbooks:
        textbooks_html = "<ul>" + "".join(f"<li>{t}</li>" for t in textbooks) + "</ul>"
        syllabus_body = syllabus_body.replace("[textbooks]", textbooks_html)
    else:
        syllabus_done = False

    instructors = course_json.get("instructor", [])
    if instructors:
        parts: list[str] = []
        for instructor in instructors:
            if not isinstance(instructor, dict):
                continue
            name = instructor.get("name") or "Instructor"
            email = instructor.get("email") or ""
            if email:
                parts.append(f"<li>{name} (<a href='mailto:{email}'>{email}</a>) [Office hours]</li>")
            else:
                parts.append(f"<li>{name} [Office hours]</li>")
        if parts:
            instructors_html = "<ul>" + "".join(parts) + "</ul>"
            syllabus_body = syllabus_body.replace("[instructors]", instructors_html)
        else:
            syllabus_done = False
    else:
        syllabus_done = False

    if course_json.get("course_policy"):
        syllabus_body = syllabus_body.replace("[Course Policies]", str(course_json["course_policy"]))
    else:
        syllabus_done = False

    if syllabus_done:
        syllabus_body = syllabus_body.replace(' style="color: #e03e2d;"', "")

    course.update(course={"syllabus_body": syllabus_body})


def get_next_sunday(date_value: datetime) -> datetime:
    days = (6 - date_value.weekday()) % 7
    return date_value + timedelta(days=days)


def get_module_due_date(start_at: str, module_number: int, weekday: int = 6) -> str:
    start_date = datetime.strptime(start_at, "%Y-%m-%d %H:%M:%S")
    first_due = datetime.strptime(f"{get_next_sunday(start_date).date()} 23:59:00", "%Y-%m-%d %H:%M:%S")
    due_date = first_due + timedelta(weeks=module_number) + timedelta(days=weekday - 6)
    eastern = ZoneInfo("America/New_York")
    utc = ZoneInfo("UTC")
    due_local = due_date.replace(tzinfo=eastern)
    return due_local.astimezone(utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def existing_assignments_by_week(course: Any, course_id: int) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for assignment in course.get_assignments():
        due_at = getattr(assignment, "due_at", None)
        if not due_at:
            continue
        if getattr(assignment, "workflow_state", "") != "published":
            continue
        due = datetime.strptime(due_at, "%Y-%m-%dT%H:%M:%SZ") - timedelta(hours=4)
        targets.append(
            {
                "name": assignment.name,
                "id": assignment.id,
                "due_at": due.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "week": 0,
                "link": f"/courses/{course_id}/assignments/{assignment.id}",
            }
        )

    if not targets:
        return []

    targets.sort(key=lambda item: datetime.strptime(item["due_at"], "%Y-%m-%dT%H:%M:%SZ"))
    first_week = datetime.strptime(targets[0]["due_at"], "%Y-%m-%dT%H:%M:%SZ").isocalendar().week
    for item in targets:
        week = datetime.strptime(item["due_at"], "%Y-%m-%dT%H:%M:%SZ").isocalendar().week
        item["week"] = week - first_week
    return targets


def fill_missing_fields(obj: Any, desired: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for key, value in desired.items():
        if is_empty_value(value):
            continue
        current = getattr(obj, key, None)
        if is_empty_value(current):
            updates[key] = value
    return updates


def find_existing_regular_assignment(existing_assignments: list[Any], assignment_id: Any) -> Any | None:
    if is_empty_value(assignment_id):
        return None
    target = str(assignment_id)
    for existing in existing_assignments:
        if str(getattr(existing, "id", "")) != target:
            continue
        submission_types = getattr(existing, "submission_types", []) or []
        if "discussion_topic" in submission_types:
            continue
        if getattr(existing, "quiz_id", None):
            continue
        return existing
    return None


def find_by_assignment_id(items: list[Any], assignment_id: Any) -> Any | None:
    if is_empty_value(assignment_id):
        return None
    target = str(assignment_id)
    for item in items:
        existing_assignment_id = getattr(item, "assignment_id", None)
        if not is_empty_value(existing_assignment_id) and str(existing_assignment_id) == target:
            return item
    return None


def safe_create_new_quiz(course: Any, payload: dict[str, Any]) -> Any:
    try:
        return course.create_new_quiz(**payload)
    except Exception:
        return course.create_new_quiz(quiz=payload)


def safe_update_new_quiz(new_quiz: Any, payload: dict[str, Any]) -> Any:
    try:
        return new_quiz.update(**payload)
    except Exception:
        return new_quiz.update(quiz=payload)


def ensure_assignment_group(course: Any, name: str = "New Assignments") -> Any:
    groups = list(course.get_assignment_groups())
    assignment_group = first_match(groups, "name", name)
    if assignment_group:
        return assignment_group

    try:
        return course.create_assignment_group(assignment_group={"name": name, "position": 1})
    except Exception:
        return course.create_assignment_group(name=name, position=1)


def upsert_module_assignments(
    course: Any,
    course_id: int,
    course_json: dict[str, Any],
    build: dict[str, Any],
    assignment_template: str,
    discussion_template: str,
    newquiz_template: str,
    classicquiz_template: str,
    stats: BuildStats,
) -> None:
    modules = course_json["modules"]
    existing_assignments = list(course.get_assignments())
    existing_discussions = list(course.get_discussion_topics())
    existing_new_quizzes = list(course.get_new_quizzes())
    existing_classic_quizzes = list(course.get_quizzes())

    assignment_group = ensure_assignment_group(course)

    for module in modules:
        module.setdefault("assessments", [])
        module.setdefault("assignments", [])
        module.setdefault("number", 0)

        module_due = get_module_due_date(
            build["start_date"],
            int(module["number"]) - 1,
            weekday=int(build["default_due_day"]),
        )
        module_disc_due = get_module_due_date(
            build["start_date"],
            int(module["number"]) - 1,
            weekday=int(build["default_discussion_due_day"]),
        )

        if int(module["number"]) == len(modules):
            module_due = get_module_due_date(
                build["start_date"],
                int(module["number"]) - 1,
                weekday=int(build["default_last_day"]),
            )

        for assignment in module["assignments"]:
            if not isinstance(assignment, dict):
                raise BuildError("Each module assignment must be an object.", 400)

            assignment_type = str(assignment.get("type", "")).strip().lower()
            assignment_name = str(assignment.get("name", "")).strip()
            if not assignment_name:
                raise BuildError(
                    f"Module {module.get('number')} has an assignment with empty name.",
                    400,
                )

            new_assignment_id: int | None = None
            new_assignment_name = assignment_name
            target_group_id = int(getattr(assignment_group, "id", 0))

            if assignment_type == "assignment":
                desired = {
                    "name": assignment_name,
                    "description": assignment_template,
                    "submission_types": ["online_upload"],
                    "points_possible": 100,
                    "grading_type": "points",
                    "workflow_state": "unpublished",
                    "assignment_group_id": assignment_group.id,
                    "due_at": module_due,
                }
                existing = find_existing_regular_assignment(existing_assignments, assignment.get("id"))
                if existing:
                    existing = course.get_assignment(existing.id)
                    updates = fill_missing_fields(existing, desired)
                    if updates:
                        existing = existing.edit(assignment=updates)
                        stats.assignments_updated += 1
                    target_group_id = getattr(existing, "assignment_group_id", target_group_id) or target_group_id
                    new_assignment_id = int(existing.id)
                    new_assignment_name = getattr(existing, "name", assignment_name)
                else:
                    created = course.create_assignment(desired)
                    existing_assignments.append(created)
                    stats.assignments_created += 1
                    new_assignment_id = int(created.id)
                    new_assignment_name = getattr(created, "name", assignment_name)

            elif assignment_type == "discussion":
                desired_discussion = {
                    "title": assignment_name,
                    "message": discussion_template,
                    "discussion_type": "threaded",
                    "published": False,
                    "workflow_state": "unpublished",
                }
                desired_discussion_assignment = {
                    "name": assignment_name,
                    "description": discussion_template,
                    "points_possible": 20,
                    "grading_type": "points",
                    "submission_types": ["discussion_topic"],
                    "assignment_group_id": assignment_group.id,
                    "due_at": module_disc_due,
                }

                existing_discussion = find_by_assignment_id(existing_discussions, assignment.get("id"))
                if existing_discussion:
                    existing_discussion = course.get_discussion_topic(existing_discussion.id)
                    updates = fill_missing_fields(existing_discussion, desired_discussion)
                    if updates:
                        existing_discussion = existing_discussion.update(**updates)
                        stats.discussions_updated += 1

                    discussion_assignment_id = getattr(existing_discussion, "assignment_id", None)
                    if discussion_assignment_id:
                        discussion_assignment = course.get_assignment(discussion_assignment_id)
                        assignment_updates = fill_missing_fields(discussion_assignment, desired_discussion_assignment)
                        if assignment_updates:
                            discussion_assignment = discussion_assignment.edit(assignment=assignment_updates)
                            stats.assignments_updated += 1
                        target_group_id = (
                            getattr(discussion_assignment, "assignment_group_id", target_group_id)
                            or target_group_id
                        )
                        new_assignment_id = int(discussion_assignment.id)
                        new_assignment_name = getattr(discussion_assignment, "name", assignment_name)

                if new_assignment_id is None:
                    created_discussion = course.create_discussion_topic(
                        title=assignment_name,
                        message=discussion_template,
                        discussion_type="threaded",
                        published=False,
                        workflow_state="unpublished",
                        assignment=desired_discussion_assignment,
                    )
                    existing_discussions.append(created_discussion)
                    stats.discussions_created += 1
                    discussion_assignment_id = getattr(created_discussion, "assignment_id", None)
                    if discussion_assignment_id:
                        discussion_assignment = course.get_assignment(discussion_assignment_id)
                        existing_assignments.append(discussion_assignment)
                        new_assignment_id = int(discussion_assignment.id)
                        new_assignment_name = getattr(discussion_assignment, "name", assignment_name)
                        target_group_id = (
                            getattr(discussion_assignment, "assignment_group_id", target_group_id)
                            or target_group_id
                        )

            elif assignment_type == "quiz":
                desired_quiz = {
                    "title": assignment_name,
                    "instructions": newquiz_template,
                    "grading_type": "percent",
                    "points_possible": 100,
                    "published": False,
                    "assignment_group_id": assignment_group.id,
                    "due_at": module_due,
                }

                existing_quiz = find_by_assignment_id(existing_new_quizzes, assignment.get("id"))
                if existing_quiz:
                    updates = fill_missing_fields(existing_quiz, desired_quiz)
                    if updates:
                        existing_quiz = safe_update_new_quiz(existing_quiz, updates)
                        stats.new_quizzes_updated += 1

                    quiz_assignment_id = getattr(existing_quiz, "assignment_id", None)
                    if quiz_assignment_id:
                        quiz_assignment = course.get_assignment(quiz_assignment_id)
                        assignment_updates = fill_missing_fields(
                            quiz_assignment,
                            {
                                "assignment_group_id": assignment_group.id,
                                "due_at": module_due,
                                "workflow_state": "unpublished",
                            },
                        )
                        if assignment_updates:
                            quiz_assignment = quiz_assignment.edit(assignment=assignment_updates)
                            stats.assignments_updated += 1
                        target_group_id = getattr(quiz_assignment, "assignment_group_id", target_group_id) or target_group_id
                        new_assignment_id = int(quiz_assignment.id)
                        new_assignment_name = getattr(quiz_assignment, "name", assignment_name)
                    else:
                        new_assignment_id = int(existing_quiz.id)
                        new_assignment_name = getattr(existing_quiz, "title", assignment_name)
                else:
                    created_quiz = safe_create_new_quiz(course, desired_quiz)
                    existing_new_quizzes.append(created_quiz)
                    stats.new_quizzes_created += 1
                    new_assignment_id = int(getattr(created_quiz, "assignment_id", 0) or created_quiz.id)
                    new_assignment_name = getattr(created_quiz, "title", assignment_name)

            elif assignment_type == "classic quiz":
                desired_classic = {
                    "title": assignment_name,
                    "quiz_type": "assignment",
                    "description": classicquiz_template,
                    "allowed_attempts": 1,
                    "show_one_question_at_a_time": True,
                    "points_possible": 100,
                    "published": False,
                    "assignment_group_id": assignment_group.id,
                    "due_at": module_due,
                }

                existing_classic = find_by_assignment_id(existing_classic_quizzes, assignment.get("id"))
                if existing_classic:
                    updates = fill_missing_fields(existing_classic, desired_classic)
                    if updates:
                        existing_classic = existing_classic.edit(quiz=updates)
                        stats.classic_quizzes_updated += 1

                    classic_assignment_id = getattr(existing_classic, "assignment_id", None)
                    if classic_assignment_id:
                        classic_assignment = course.get_assignment(classic_assignment_id)
                        assignment_updates = fill_missing_fields(
                            classic_assignment,
                            {
                                "assignment_group_id": assignment_group.id,
                                "due_at": module_due,
                                "workflow_state": "unpublished",
                            },
                        )
                        if assignment_updates:
                            classic_assignment = classic_assignment.edit(assignment=assignment_updates)
                            stats.assignments_updated += 1
                        target_group_id = (
                            getattr(classic_assignment, "assignment_group_id", target_group_id)
                            or target_group_id
                        )
                        new_assignment_id = int(classic_assignment.id)
                        new_assignment_name = getattr(classic_assignment, "name", assignment_name)
                    else:
                        new_assignment_id = int(existing_classic.id)
                        new_assignment_name = getattr(existing_classic, "title", assignment_name)
                else:
                    created_classic = course.create_quiz(desired_classic)
                    existing_classic_quizzes.append(created_classic)
                    stats.classic_quizzes_created += 1
                    new_assignment_id = int(getattr(created_classic, "assignment_id", 0) or created_classic.id)
                    new_assignment_name = getattr(created_classic, "title", assignment_name)

            else:
                raise BuildError(
                    f"Unsupported assignment type '{assignment_type}' in module {module.get('number')}",
                    400,
                )

            if not new_assignment_id:
                raise BuildError(
                    f"Failed to upsert assignment for module {module.get('number')}.",
                    500,
                )

            module["assessments"].append(
                {
                    "link": f"/courses/{course_id}/assignments/{new_assignment_id}",
                    "name": new_assignment_name,
                    "id": new_assignment_id,
                    "type": assignment_type,
                    "week": int(module["number"]) - 1,
                }
            )
            assignment["id"] = new_assignment_id
            assignment["week"] = int(module["number"]) - 1
            assignment["link"] = f"/courses/{course_id}/assignments/{new_assignment_id}"
            assignment["group_id"] = target_group_id


def create_module_overview_page(course: Any, module_obj: Any, module: dict[str, Any], page_template: str, stats: BuildStats) -> int:
    pages = module.get("pages", [])
    if pages:
        for page in pages:
            if not isinstance(page, dict):
                continue
            wiki_page = course.create_page(
                {
                    "title": page.get("title", "Untitled Page"),
                    "body": "[content placeholder]",
                    "editing_roles": "teachers",
                    "published": False,
                    "front_page": False,
                    "notify_of_update": False,
                }
            )
            page["id"] = int(wiki_page.page_id)
            page["url"] = wiki_page.url
            stats.pages_created += 1

    module_overview = f"<p>{module.get('overview', '')}</p>" if module.get("overview") else ""
    objectives_html = "<p>By the end of this module, you will be able to:</p><ul>"
    for objective in module.get("objectives", []):
        objectives_html += f"<li>{objective}</li>"
    objectives_html += "</ul>"

    content_html = "<ul>"
    for content in module.get("content", []):
        item = str(content)
        if "#new_page" in item:
            match = re.search(r"<a .*>(.*?)</a>", item)
            link_title = match.group(1) if match else ""
            link_page = next((p for p in pages if isinstance(p, dict) and p.get("title") == link_title), None)
            if link_page:
                item = item.replace("#new_page", f"/courses/{course.id}/pages/{link_page['url']}")
            elif link_title:
                item = item.replace("#new_page", f"#{link_title}")
        content_html += f"<li>{item}</li>"
    content_html += "</ul>"

    assessments_html = "<ul>"
    for assessment in module.get("assessments", []):
        assessments_html += f"<li><a href='{assessment['link']}'>{assessment['name']}</a></li>"
    assessments_html += "</ul>"

    page_content = (
        page_template.replace("[overview]", module_overview)
        .replace("[objectives]", objectives_html)
        .replace("[content]", content_html)
        .replace("[assessments]", assessments_html)
    )

    overview_page = course.create_page(
        {
            "title": f"Module {module.get('number')} Overview",
            "body": page_content,
            "editing_roles": "teachers",
            "published": True,
            "front_page": False,
            "notify_of_update": False,
        }
    )
    stats.pages_created += 1

    module_obj.create_module_item(
        {
            "title": overview_page.title,
            "type": "Page",
            "content_id": int(overview_page.page_id),
            "page_url": overview_page.url,
            "position": 1,
            "indent": 1,
        }
    )
    stats.module_items_created += 1

    return int(overview_page.page_id)


def create_modules(
    course: Any,
    modules: list[dict[str, Any]],
    page_template: str,
    stats: BuildStats,
) -> list[dict[str, Any]]:
    for module in modules:
        module_obj = course.create_module({"name": module.get("name", ""), "position": module.get("position", 0)})
        stats.modules_created += 1
        module["id"] = int(module_obj.id)

        position = 0
        for subheader in ["Discover", "Demonstrate"]:
            module_obj.create_module_item(
                {
                    "title": subheader,
                    "type": "SubHeader",
                    "indent": 0,
                    "position": position,
                    "published": True,
                }
            )
            stats.module_items_created += 1
            position += 1

        overview_page_id = create_module_overview_page(course, module_obj, module, page_template, stats)
        module["overview_page_id"] = overview_page_id

        for page in module.get("pages", []):
            if not isinstance(page, dict) or not page.get("id"):
                continue
            module_obj.create_module_item(
                {
                    "title": page.get("title", "Untitled Page"),
                    "type": "Page",
                    "content_id": int(page["id"]),
                    "page_url": page.get("url", ""),
                    "position": position,
                    "indent": 2,
                }
            )
            stats.module_items_created += 1
            position += 1

        for file_item in module.get("files", []):
            if not isinstance(file_item, dict) or not file_item.get("id"):
                continue
            module_obj.create_module_item(
                {
                    "title": file_item.get("name", f"File {file_item['id']}"),
                    "type": "File",
                    "content_id": int(file_item["id"]),
                    "position": position,
                    "indent": 2,
                }
            )
            stats.module_items_created += 1
            position += 1

        for assessment in module.get("assessments", []):
            if not isinstance(assessment, dict) or not assessment.get("id"):
                continue
            position += 1
            module_obj.create_module_item(
                {
                    "title": assessment.get("name", "Assessment"),
                    "type": "Assignment",
                    "content_id": int(assessment["id"]),
                    "position": position,
                    "indent": 1,
                }
            )
            stats.module_items_created += 1

    return modules


def resolve_templates(course: Any, build: dict[str, Any]) -> dict[str, str]:
    return {
        "page_template": get_overview_page_template(course, build["overview_page_template"]),
        "assignment_template": get_assignment_template(course, build["assignment_template"]),
        "discussion_template": get_discussion_template(course, build["discussion_template"]),
        "newquiz_template": get_new_quiz_template(course, build["newquiz_template"]),
        "classicquiz_template": get_classic_quiz_template(course, build["classicquiz_template"]),
    }


def run_build(build: dict[str, Any], args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    canvas = ensure_canvas_client(args)
    canvas_base = canvas_root_url(canvas)
    course_id = int(build["course_id"])
    course = canvas.get_course(course_id)

    dry_run = bool(args.dry_run or build.get("dry_run", False))
    if not dry_run and not args.confirm_write:
        raise BuildError("Non-dry-run build requires --confirm-write.", 400)

    files_root = Path(args.files_root).expanduser().resolve()
    files_root.mkdir(parents=True, exist_ok=True)
    course_json_file = files_root / f"{course_id}_modules_v4.json"
    course_built_file = files_root / f"{course_id}_built_v4.json"

    course_json = build["course"]
    write_json(course_json_file, course_json)

    templates = resolve_templates(course, build)
    if dry_run:
        result = {
            "status": "success",
            "message": "Dry run successful, templates loaded.",
            "course_url": course_url(canvas_base, course_id),
            "artifacts": {
                "modules_file": str(course_json_file),
                "built_file": str(course_built_file),
            },
            "dry_run": True,
        }
        return result, course_json

    stats = BuildStats()
    update_syllabus(canvas, course, course_json)
    stats.syllabus_updated = True

    build_type = int(build["build_type"])
    if build_type == 1:
        target_assignments = existing_assignments_by_week(course, course_id)
        for ta in target_assignments:
            for module in course_json["modules"]:
                if ta["week"] == int(module.get("number", 0)) - 1:
                    module.setdefault("assessments", []).append(ta)
    elif build_type == 2:
        upsert_module_assignments(
            course,
            course_id,
            course_json,
            build,
            templates["assignment_template"],
            templates["discussion_template"],
            templates["newquiz_template"],
            templates["classicquiz_template"],
            stats,
        )
        write_json(course_json_file, course_json)

    modules = create_modules(course, course_json["modules"], templates["page_template"], stats)
    course_json["modules"] = modules
    write_json(course_built_file, course_json)

    result = {
        "status": "success",
        "message": "Course built successfully",
        "course_url": course_url(canvas_base, course_id),
        "artifacts": {
            "modules_file": str(course_json_file),
            "built_file": str(course_built_file),
        },
        "dry_run": False,
        "stats": asdict(stats),
    }
    return result, course_json


def main() -> int:
    maybe_load_dotenv()
    args = parse_args()

    try:
        raw = read_json(Path(args.input_json))
        build = normalize_course_payload(raw)
        result, built_course_json = run_build(build, args)
    except BuildError as exc:
        error_payload = {
            "status": "error",
            "status_code": exc.status_code,
            "detail": str(exc),
        }
        print(json.dumps(error_payload, indent=2))
        return 1
    except Exception as exc:  # pragma: no cover
        error_payload = {
            "status": "error",
            "status_code": 500,
            "detail": f"Unexpected build failure: {exc}",
        }
        print(json.dumps(error_payload, indent=2))
        return 1

    print(json.dumps(result, indent=2))
    if args.print_course_json:
        print(json.dumps(built_course_json, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
