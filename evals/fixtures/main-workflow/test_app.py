import subprocess
import sys
import unittest

from app import greeting


class GreetingTests(unittest.TestCase):
    def test_greeting(self):
        self.assertEqual("Hello, Ada!", greeting("Ada"))

    def test_cli(self):
        result = subprocess.run(
            [sys.executable, "app.py", "Ada"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode)
        self.assertEqual("Hello, Ada!\n", result.stdout)


if __name__ == "__main__":
    unittest.main()
