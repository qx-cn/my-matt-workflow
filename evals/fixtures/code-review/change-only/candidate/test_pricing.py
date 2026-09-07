from decimal import Decimal
import unittest

from pricing import checkout_total


class CheckoutTotalTests(unittest.TestCase):
    def test_save10(self):
        items = [{"price": Decimal("20"), "quantity": 2}]
        self.assertEqual(Decimal("36.00"), checkout_total(items, "SAVE10"))


if __name__ == "__main__":
    unittest.main()
