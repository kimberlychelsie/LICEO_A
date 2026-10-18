import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTE = (ROOT / "routes" / "student.py").read_text(encoding="utf-8")
TEMPLATE = (ROOT / "templates" / "student_reservation.html").read_text(
    encoding="utf-8"
)


class ReservationCatalogUxTest(unittest.TestCase):
    def test_category_values_are_validated_and_preserved(self):
        self.assertIn("{'ALL', 'BOOK', 'UNIFORM'}", ROUTE)
        self.assertIn("category=category_filter", ROUTE)
        self.assertIn('window.history.pushState({ category: selected }', TEMPLATE)
        self.assertIn('window.addEventListener("popstate"', TEMPLATE)
        self.assertIn('url.searchParams.set("category", selected)', TEMPLATE)

    def test_catalog_keeps_all_categories_available_for_history_navigation(self):
        self.assertNotIn('query += " AND category = %s"', ROUTE)
        self.assertIn('card.hidden = selected !== "ALL"', TEMPLATE)
        self.assertIn('.item-card-js[hidden]', TEMPLATE)
        self.assertIn('display: none !important', TEMPLATE)
        self.assertIn('data-category="{{ it.category|upper }}"', TEMPLATE)

    def test_item_and_size_availability_use_reserved_stock(self):
        self.assertIn("int(r['stock_total'] or 0) - int(r['reserved_qty'] or 0)", ROUTE)
        self.assertIn("int(s['stock_total'] or 0) - int(s['reserved_qty'] or 0)", ROUTE)
        self.assertIn("s_available = min(available, size_available)", ROUTE)
        self.assertIn('data-available="{{ s.available if s.available > 0 else 0 }}"', TEMPLATE)
        self.assertIn("Math.min(itemAvailable, sizeAvailable)", TEMPLATE)

    def test_stock_badges_and_disabled_controls_cover_all_states(self):
        self.assertIn("initial_available >= 6", TEMPLATE)
        self.assertIn("initial_available >= 1", TEMPLATE)
        self.assertIn("In Stock{% elif", TEMPLATE)
        self.assertIn("Low Stock{% else", TEMPLATE)
        self.assertIn("Out of Stock{% endif", TEMPLATE)
        self.assertIn("input.disabled = maxQuantity <= 0", TEMPLATE)
        self.assertIn("button.disabled = maxQuantity <= 0", TEMPLATE)
        self.assertIn("const maxQuantity = Math.min(3, available)", TEMPLATE)

    def test_cards_stretch_and_titles_are_clamped(self):
        self.assertIn("align-items: stretch", TEMPLATE)
        self.assertIn("height: 100%", TEMPLATE)
        self.assertIn("-webkit-line-clamp: 3", TEMPLATE)
        self.assertIn('class="product-card-title" tabindex="0"', TEMPLATE)
        self.assertIn('content: attr(data-full-title)', TEMPLATE)
        self.assertIn('.product-card-title:focus-visible::after', TEMPLATE)
        self.assertIn("margin-top: auto", TEMPLATE)

    def test_set_breakdown_uses_an_accessible_anchored_popover(self):
        self.assertIn('class="set-breakdown-toggle"', TEMPLATE)
        self.assertIn('aria-expanded="false"', TEMPLATE)
        self.assertIn('class="set-breakdown-list"', TEMPLATE)
        self.assertIn('data-placement="down" hidden', TEMPLATE)
        self.assertIn("list.dataset.placement = spaceBelow < panelHeight", TEMPLATE)
        self.assertIn("closeSetBreakdowns(box)", TEMPLATE)
        self.assertIn("event.key !== 'Escape'", TEMPLATE)


if __name__ == "__main__":
    unittest.main()
