import unittest

from app import _is_phone_client


class PhoneClientTest(unittest.TestCase):
    def test_phones_and_tablets(self):
        iphone = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
        android = "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"
        self.assertTrue(_is_phone_client(iphone))
        self.assertTrue(_is_phone_client(android))
        self.assertTrue(_is_phone_client("Mozilla/5.0", "?1"))

    def test_desktop_is_not_a_phone(self):
        desktop = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        self.assertFalse(_is_phone_client(desktop))
        self.assertFalse(_is_phone_client(desktop, "?0"))
