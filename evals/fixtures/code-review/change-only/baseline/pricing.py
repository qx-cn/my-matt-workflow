from decimal import Decimal


def legacy_discount(total):
    if total > Decimal("100"):
        return total * Decimal("0.90")
    return total


def checkout_total(items, coupon=None):
    return sum(
        (item["price"] * item["quantity"] for item in items),
        Decimal("0"),
    )
