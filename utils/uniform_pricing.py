"""Uniform pre-order pricing: base price on smallest size, +step per next size."""

DEFAULT_SIZE_PRICE_STEP = 20

# Standard clothing size order (smallest → largest)
SIZE_ORDER = [
    "XXS", "XS", "S", "M", "L", "XL", "XXL", "2XL", "XXXL", "3XL", "4XL", "XXXXL", "5XL",
]


def size_rank(label: str) -> int:
    key = str(label or "").upper().strip()
    try:
        return SIZE_ORDER.index(key)
    except ValueError:
        return 99


def parse_size_list(size_label) -> list:
    """Parse comma-separated sizes and sort them smallest → largest."""
    if not size_label:
        return ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]
    if isinstance(size_label, (list, tuple)):
        raw = [str(s).strip() for s in size_label if str(s).strip()]
    else:
        raw = [s.strip() for s in str(size_label).split(",") if s.strip()]
    seen = set()
    unique = []
    for s in raw:
        key = s.upper()
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return sorted(unique, key=size_rank)


def size_step_index(selected_size: str, available_sizes) -> int:
    """0-based index of selected size within the item's ordered size list."""
    sizes = parse_size_list(available_sizes)
    sel = str(selected_size or "").strip().upper()
    for i, s in enumerate(sizes):
        if s.upper() == sel:
            return i
    return 0


def price_for_size(base_price, selected_size, available_sizes, step=DEFAULT_SIZE_PRICE_STEP) -> float:
    """
    Base price applies to the smallest configured size.
    Each next size in sequence adds `step` (default ₱20).
    Example: base 450, step 20 → XS=450, S=470, M=490, L=510
    """
    base = float(base_price or 0)
    try:
        step_val = float(step if step is not None else DEFAULT_SIZE_PRICE_STEP)
    except (TypeError, ValueError):
        step_val = float(DEFAULT_SIZE_PRICE_STEP)
    idx = size_step_index(selected_size, available_sizes)
    return round(base + (idx * step_val), 2)


def size_price_map(base_price, available_sizes, step=DEFAULT_SIZE_PRICE_STEP) -> dict:
    """Return {size_label: price} for all sizes on an item."""
    sizes = parse_size_list(available_sizes)
    return {s: price_for_size(base_price, s, sizes, step) for s in sizes}
