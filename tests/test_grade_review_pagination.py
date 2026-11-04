import unittest
from types import SimpleNamespace

from utils.list_pagination import (
    GRADE_REVIEW_PER_PAGE,
    paginate_sequence,
    review_filter_query_args,
)


class GradeReviewPaginationTests(unittest.TestCase):
    def test_caps_each_page_at_five(self):
        rows = list(range(12))
        page1, page, total_pages, total, per_page = paginate_sequence(rows, 1)
        self.assertEqual(per_page, GRADE_REVIEW_PER_PAGE)
        self.assertEqual(per_page, 5)
        self.assertEqual(page1, [0, 1, 2, 3, 4])
        self.assertEqual(page, 1)
        self.assertEqual(total_pages, 3)
        self.assertEqual(total, 12)

        page2, page, total_pages, total, _ = paginate_sequence(rows, 2)
        self.assertEqual(page2, [5, 6, 7, 8, 9])
        self.assertEqual(page, 2)

        page3, page, _, _, _ = paginate_sequence(rows, 3)
        self.assertEqual(page3, [10, 11])
        self.assertEqual(page, 3)

    def test_clamps_out_of_range_pages(self):
        rows = list(range(6))
        page_items, page, total_pages, _, _ = paginate_sequence(rows, 99)
        self.assertEqual(page, 2)
        self.assertEqual(total_pages, 2)
        self.assertEqual(page_items, [5])

        page_items, page, _, _, _ = paginate_sequence(rows, 0)
        self.assertEqual(page, 1)
        self.assertEqual(page_items, [0, 1, 2, 3, 4])

    def test_empty_list_stays_on_page_one(self):
        page_items, page, total_pages, total, _ = paginate_sequence([], 4)
        self.assertEqual(page_items, [])
        self.assertEqual(page, 1)
        self.assertEqual(total_pages, 1)
        self.assertEqual(total, 0)

    def test_filter_args_drop_page_and_keep_filters(self):
        args = SimpleNamespace(to_dict=lambda flat=True: {
            "page": "2",
            "grade_level_id": "3",
            "period": "1st",
        })
        query = review_filter_query_args(args)
        self.assertNotIn("page", query)
        self.assertEqual(query["grade_level_id"], "3")
        self.assertEqual(query["period"], "1st")


if __name__ == "__main__":
    unittest.main()
