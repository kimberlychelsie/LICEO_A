import unittest
from pathlib import Path

from routes.librarian import _filter_release_queue_rows


ROOT = Path(__file__).resolve().parents[1]
ROUTE = (ROOT / "routes" / "librarian.py").read_text(encoding="utf-8")
TEMPLATE = (ROOT / "templates" / "librarian_releases.html").read_text(encoding="utf-8")


class LibrarianReleaseFilterTest(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {
                "status": "PAID",
                "full_name": "Ana Cruz",
                "username": "ana",
                "grade_level": "Grade 1",
                "reserved_books": "Math (x1)",
            },
            {
                "status": "CANCELLED",
                "full_name": "Ben Santos",
                "username": "ben",
                "grade_level": "Grade 2",
                "reserved_books": "Science (x1)",
            },
        ]

    def test_status_filter_finds_matches_before_pagination(self):
        result = _filter_release_queue_rows(self.rows, status="cancelled")
        self.assertEqual(["Ben Santos"], [row["full_name"] for row in result])

    def test_search_covers_student_grade_and_book(self):
        self.assertEqual(1, len(_filter_release_queue_rows(self.rows, search="science")))
        self.assertEqual(1, len(_filter_release_queue_rows(self.rows, search="grade 1")))

    def test_route_filters_then_slices_and_clamps_page(self):
        filter_pos = ROUTE.index("filtered_reservations = _filter_release_queue_rows")
        slice_pos = ROUTE.index("reservation_rows = filtered_reservations[")
        self.assertLess(filter_pos, slice_pos)
        self.assertIn("page = min(page, max(1, total_queue_pages))", ROUTE)

    def test_template_preserves_filters_in_pagination(self):
        self.assertIn('name="queue_status"', TEMPLATE)
        self.assertIn('name="queue_search"', TEMPLATE)
        self.assertGreaterEqual(TEMPLATE.count("queue_status=queue_status or None"), 2)
        self.assertGreaterEqual(TEMPLATE.count("queue_search=queue_search or None"), 2)


if __name__ == "__main__":
    unittest.main()
