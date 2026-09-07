from decimal import Decimal


def checkout_total(items):
    return sum(
        (item["price"] * item["quantity"] for item in items),
        Decimal("0"),
    )
