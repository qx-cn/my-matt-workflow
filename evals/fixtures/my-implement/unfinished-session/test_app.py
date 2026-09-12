import unittest

from app import greeting


class GreetingTests(unittest.TestCase):
    def test_trimmed_name(self):
        self.assertEqual("Hello, Ada!", greeting(" Ada "))

    def test_blank_name_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "name must not be blank"):
            greeting("   ")


if __name__ == "__main__":
    unittest.main()
