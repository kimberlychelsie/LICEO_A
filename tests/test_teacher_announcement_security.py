import io
import ast
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch
import uuid
import zipfile

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from db import get_teacher_announcement_year_mode


SOURCE_PATH = Path(__file__).resolve().parents[1] / "routes" / "teacher.py"
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")
STUDENT_SOURCE = (
    Path(__file__).resolve().parents[1] / "routes" / "student_portal.py"
).read_text(encoding="utf-8")
MIGRATION_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "add_teacher_announcements_year_id.sql"
).read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
WANTED = {
    "CLASS_ANNOUNCEMENTS_PER_PAGE",
    "CLASS_ANNOUNCEMENT_EXTENSIONS",
    "CLASS_ANNOUNCEMENT_MAX_FILE_SIZE",
    "_normalize_grade",
    "_parse_class_announcement_attachment",
    "_validate_class_announcement_file",
    "_announcement_target_matches",
    "_class_announcement_list_state",
}
NODES = [
    node
    for node in TREE.body
    if (
        isinstance(node, (ast.FunctionDef, ast.Assign))
        and (
            getattr(node, "name", None) in WANTED
            or any(
                isinstance(target, ast.Name) and target.id in WANTED
                for target in getattr(node, "targets", [])
            )
        )
    )
]
NAMESPACE = {
    "os": os,
    "re": re,
    "zipfile": zipfile,
    "uuid": uuid,
    "secure_filename": secure_filename,
}
exec(compile(ast.Module(body=NODES, type_ignores=[]), str(SOURCE_PATH), "exec"), NAMESPACE)

CLASS_ANNOUNCEMENT_MAX_FILE_SIZE = NAMESPACE["CLASS_ANNOUNCEMENT_MAX_FILE_SIZE"]
CLASS_ANNOUNCEMENTS_PER_PAGE = NAMESPACE["CLASS_ANNOUNCEMENTS_PER_PAGE"]
_announcement_target_matches = NAMESPACE["_announcement_target_matches"]
_class_announcement_list_state = NAMESPACE["_class_announcement_list_state"]
_parse_class_announcement_attachment = NAMESPACE["_parse_class_announcement_attachment"]
_validate_class_announcement_file = NAMESPACE["_validate_class_announcement_file"]


def upload(name, content):
    return FileStorage(stream=io.BytesIO(content), filename=name)


class TeacherAnnouncementUploadSecurityTest(unittest.TestCase):
    def test_valid_pdf_jpg_png_and_doc_are_accepted(self):
        samples = {
            "notice.pdf": b"%PDF-1.7\ncontent",
            "photo.jpg": b"\xff\xd8\xff\xe0content",
            "photo.png": b"\x89PNG\r\n\x1a\ncontent",
            "notice.doc": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1content",
        }
        for name, content in samples.items():
            with self.subTest(name=name):
                extension, error = _validate_class_announcement_file(
                    upload(name, content)
                )
                self.assertEqual(name.rsplit(".", 1)[-1], extension)
                self.assertIsNone(error)

    def test_valid_docx_is_accepted(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types />")
            archive.writestr("word/document.xml", "<document />")
        extension, error = _validate_class_announcement_file(
            upload("notice.docx", stream.getvalue())
        )
        self.assertEqual("docx", extension)
        self.assertIsNone(error)

    def test_unsupported_and_mismatched_files_are_rejected(self):
        for name, content in (
            ("payload.xml", b"<xml />"),
            ("fake.pdf", b"<script>alert(1)</script>"),
            ("fake.png", b"%PDF-1.7"),
            ("fake.docx", b"PK-not-a-real-office-file"),
        ):
            with self.subTest(name=name):
                extension, error = _validate_class_announcement_file(
                    upload(name, content)
                )
                self.assertIsNone(extension)
                self.assertTrue(error)

    def test_oversized_file_is_rejected(self):
        extension, error = _validate_class_announcement_file(
            upload("large.pdf", b"%PDF-" + b"x" * CLASS_ANNOUNCEMENT_MAX_FILE_SIZE)
        )
        self.assertIsNone(extension)
        self.assertIn("10 MB", error)


class TeacherAnnouncementTargetSecurityTest(unittest.TestCase):
    def test_section_target_matches_only_exact_section(self):
        self.assertTrue(_announcement_target_matches(12, "Grade 7", "Grade 7:12"))
        self.assertFalse(_announcement_target_matches(2, "Grade 7", "Grade 7:12"))

    def test_grade_wide_target_preserves_normalized_grade_matching(self):
        self.assertTrue(_announcement_target_matches(12, "Grade 7", "Grade 7"))
        self.assertTrue(_announcement_target_matches(12, "7", "Grade 7"))
        self.assertFalse(_announcement_target_matches(12, "Grade 8", "Grade 7"))

    def test_attachment_parser_preserves_existing_metadata_format(self):
        body, attachment = _parse_class_announcement_attachment(
            "Details\n\n[ATTACHMENT|/uploads/old_file.pdf|Old Notice.pdf]"
        )
        self.assertEqual("Details", body)
        self.assertEqual("/uploads/old_file.pdf", attachment["path"])
        self.assertEqual("Old Notice.pdf", attachment["name"])


class TeacherAnnouncementRouteSecurityTest(unittest.TestCase):
    def test_feed_enforces_branch_and_deterministic_order(self):
        self.assertIn('"a.branch_id = %s"', SOURCE)
        self.assertIn(
            "ORDER BY a.created_at DESC, a.announcement_id DESC",
            SOURCE,
        )

    def test_mutations_enforce_owner_and_branch(self):
        self.assertGreaterEqual(SOURCE.count("AND teacher_user_id = %s"), 3)
        self.assertGreaterEqual(SOURCE.count("AND branch_id = %s"), 3)

    def test_create_uses_assignment_authorization(self):
        create_start = SOURCE.index("def teacher_announce():")
        create_end = SOURCE.index("def teacher_announce_delete", create_start)
        create_source = SOURCE[create_start:create_end]
        self.assertIn("_class_announcement_section_map(", create_source)
        self.assertIn("You are not authorized to post to that section.", create_source)

    def test_student_feed_keeps_branch_and_target_filters(self):
        self.assertIn("WHERE a.branch_id = %(branch_id)s", STUDENT_SOURCE)
        self.assertIn("a.grade_level LIKE '%%:' || %(section_id)s", STUDENT_SOURCE)

    def test_attachment_route_rejects_unapproved_roles_and_unsafe_paths(self):
        self.assertIn('role not in {"teacher", "student"}', SOURCE)
        self.assertIn('not attachment["path"].startswith("/uploads/")', SOURCE)
        self.assertIn("file_path.startswith(upload_root + os.sep)", SOURCE)

    def test_list_uses_server_side_pagination_and_matching_search(self):
        route_start = SOURCE.index("def teacher_class_announcements():")
        route_end = SOURCE.index("def teacher_set_grade", route_start)
        route_source = SOURCE[route_start:route_end]
        self.assertEqual(10, CLASS_ANNOUNCEMENTS_PER_PAGE)
        self.assertIn("SELECT COUNT(*) AS total", route_source)
        self.assertIn("LIMIT %s OFFSET %s", route_source)
        self.assertIn("a.teacher_user_id = %s", route_source)
        self.assertIn("SPLIT_PART(COALESCE(a.body, ''), '[ATTACHMENT|', 1)", route_source)
        self.assertIn('where_clauses.append("a.year_id = %s")', route_source)
        self.assertIn("WHERE {where_sql}", route_source)

    def test_list_state_validates_filters_and_return_values(self):
        state = _class_announcement_list_state({
            "view": "invalid",
            "search": "x" * 250,
            "section_id": "-4",
            "page": "bad",
        })
        self.assertEqual("all", state["view"])
        self.assertEqual(200, len(state["search"]))
        self.assertIsNone(state["section_id"])
        self.assertEqual(1, state["page"])

        return_state = _class_announcement_list_state({
            "return_view": "mine",
            "return_search": "notice",
            "return_section_id": "12",
            "return_page": "4",
        })
        self.assertEqual(
            {"view": "mine", "search": "notice", "section_id": 12, "page": 4},
            return_state,
        )

    def test_create_supports_legacy_and_year_aware_inserts(self):
        create_start = SOURCE.index("def teacher_announce():")
        create_end = SOURCE.index("def teacher_announce_delete", create_start)
        create_source = SOURCE[create_start:create_end]
        self.assertIn('announcement_year_mode == "legacy"', create_source)
        self.assertIn(
            "(teacher_user_id, branch_id, grade_level, title, body, year_id)",
            create_source,
        )
        self.assertIn(
            "user_id, branch_id, grade_to_save, title, body or None, year_id",
            create_source,
        )

    def test_strict_mode_covers_dashboard_mutations_and_attachments(self):
        self.assertIn("recent_announcement_mode", SOURCE)
        self.assertIn('delete_year_sql = " AND year_id = %s"', SOURCE)
        self.assertIn('mutation_year_sql = " AND year_id = %s"', SOURCE)
        self.assertIn(
            'announcement.get("year_id") != active_year_id',
            SOURCE,
        )

    def test_student_feed_uses_active_enrollment_year_in_strict_mode(self):
        self.assertIn(
            'announcement_params["year_id"] = active_enrollment["year_id"]',
            STUDENT_SOURCE,
        )
        self.assertIn(
            'announcement_year_sql = " AND a.year_id = %(year_id)s"',
            STUDENT_SOURCE,
        )


class FakeSchemaCursor:
    def __init__(self, has_year_id):
        self.has_year_id = has_year_id
        self.queries = []

    def execute(self, query):
        self.queries.append(query)

    def fetchone(self):
        return {"has_year_id": self.has_year_id}


class TeacherAnnouncementYearCompatibilityTest(unittest.TestCase):
    def test_missing_column_uses_legacy_mode_without_year_query(self):
        cursor = FakeSchemaCursor(False)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual("legacy", get_teacher_announcement_year_mode(cursor))
        self.assertEqual(1, len(cursor.queries))
        self.assertIn("information_schema.columns", cursor.queries[0])

    def test_migrated_column_defaults_to_bridge_mode(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                "bridge",
                get_teacher_announcement_year_mode(FakeSchemaCursor(True)),
            )

    def test_strict_mode_requires_the_migrated_column(self):
        with patch.dict(
            os.environ,
            {"TEACHER_ANNOUNCEMENTS_STRICT_YEAR": "true"},
            clear=True,
        ):
            self.assertEqual(
                "strict",
                get_teacher_announcement_year_mode(FakeSchemaCursor(True)),
            )
            with self.assertRaises(RuntimeError):
                get_teacher_announcement_year_mode(FakeSchemaCursor(False))

    def test_migration_is_additive_nullable_and_does_not_backfill(self):
        self.assertIn(
            "ADD COLUMN IF NOT EXISTS year_id INTEGER",
            MIGRATION_SOURCE,
        )
        self.assertNotIn("year_id INTEGER NOT NULL", MIGRATION_SOURCE)
        self.assertIn("FOREIGN KEY (branch_id, year_id)", MIGRATION_SOURCE)
        self.assertIn("ON DELETE RESTRICT", MIGRATION_SOURCE)
        self.assertIn("NOT VALID", MIGRATION_SOURCE)
        self.assertIn(
            "CREATE INDEX IF NOT EXISTS idx_teacher_ann_branch_year_created",
            MIGRATION_SOURCE,
        )
        executable_sql = "\n".join(
            line for line in MIGRATION_SOURCE.splitlines()
            if not line.lstrip().startswith("--")
        )
        self.assertNotIn("UPDATE teacher_announcements", executable_sql)


class TeacherAnnouncementTemplateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "teacher_class_announcements.html"
        ).read_text(encoding="utf-8")

    def test_template_has_filters_pagination_and_shared_modals(self):
        self.assertIn(">All Section<", self.template)
        self.assertIn(">My Announcements<", self.template)
        self.assertIn('name="search"', self.template)
        self.assertIn('class="ca-pagination"', self.template)
        self.assertEqual(1, self.template.count('id="details-modal"'))
        self.assertEqual(1, self.template.count('id="edit-modal"'))
        self.assertEqual(1, self.template.count('id="delete-modal"'))

    def test_manage_actions_remain_owner_only_and_attachments_are_protected(self):
        self.assertIn("announcement.is_owner", self.template)
        self.assertIn("teacher.teacher_announcement_attachment", self.template)
        self.assertNotIn('href="{{ announcement.attachment.path', self.template)
        self.assertIn("resize: none", self.template)


if __name__ == "__main__":
    unittest.main()
