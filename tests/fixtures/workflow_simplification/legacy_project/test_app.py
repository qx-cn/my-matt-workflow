import unittest
from app import greeting

class GreetingTests(unittest.TestCase):
    def test_trimmed_name(self):
        self.assertEqual("Hello, fixture", greeting(" fixture "))
