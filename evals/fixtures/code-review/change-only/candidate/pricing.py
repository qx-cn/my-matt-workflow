from decimal import Decimal


def legacy_discount(total):
    if total > Decimal("100"):
        return total * Decimal("0.90")
    return total


def checkout_total(items, coupon=None):
    subtotal = sum(
        (item["price"] * item["quantity"] for item in items),
        Decimal("0"),
    )
    average_price = subtotal / len(items)
    if coupon == "SAVE10":
        subtotal -= subtotal * Decimal("0.10")
    return subtotal
