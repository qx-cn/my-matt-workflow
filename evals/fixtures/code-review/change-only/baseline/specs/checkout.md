# Checkout totals

- `checkout_total(items, coupon=None)` returns the item-price total.
- A negative quantity is invalid and must raise `ValueError`.
- Coupon `SAVE10` applies a ten-percent discount.
- Existing `legacy_discount` behavior is outside this change.
