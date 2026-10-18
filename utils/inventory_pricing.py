from decimal import Decimal, InvalidOperation


def is_valid_inventory_price(value):
    """Return True only for finite, strictly positive database prices."""
    try:
        price = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return False
    return price.is_finite() and price > 0


def require_valid_inventory_price(value, item_name="Item"):
    if not is_valid_inventory_price(value):
        raise ValueError(f"{item_name} does not have a valid configured price.")
    return Decimal(str(value))
