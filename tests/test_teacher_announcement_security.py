import io
import ast
import os
from pathlib import Path
import re
import unittest
import uuid
import zipfile

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


SOURCE_PATH = Path(__file__).resolve().parents[1] / "routes" / "teacher.py"
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")
STUDENT_SOURCE = (
    Path(__file__).resolve().parents[1] / "routes" / "student_portal.py"
).read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
WANTED = {
    "CLASS_ANNOUNCEMENT_EXTENSIONS",
    "CLASS_ANNOUNCEMENT_MAX_FILE_SIZE",
    "_normalize_grade",
    "_parse_class_announcement_attachment",
    "_validate_class_announcement_file",
    "_announcement_target_matches",
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
_announcement_target_matches = NAMESPACE["_announcement_target_matches"]
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
        self.assertIn("WHERE a.branch_id = %s", SOURCE)
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


if __name__ == "__main__":
    unittest.main()
