from decimal import Decimal


def checkout_total(items):
    subtotal = sum(
        (item["price"] * item["quantity"] for item in items),
        Decimal("0"),
    )
    average_price = subtotal / len(items)
    return subtotal
