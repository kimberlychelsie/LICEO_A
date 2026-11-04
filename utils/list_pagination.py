GRADE_REVIEW_PER_PAGE = 5


def paginate_sequence(items, page, per_page=GRADE_REVIEW_PER_PAGE):
    """Slice a list into a 1-based page. Returns (page_items, page, total_pages, total, per_page)."""
    rows = list(items or [])
    total = len(rows)
    if total == 0:
        return [], 1, 1, 0, per_page
    total_pages = max(1, (total + per_page - 1) // per_page)
    try:
        page = int(page or 1)
    except (TypeError, ValueError):
        page = 1
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    return rows[start:start + per_page], page, total_pages, total, per_page


def review_filter_query_args(args):
    """Keep grade-review filter query params, dropping the current page."""
    query = args.to_dict(flat=True) if hasattr(args, "to_dict") else dict(args or {})
    query.pop("page", None)
    return query
