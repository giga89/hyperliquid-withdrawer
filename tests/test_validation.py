import os
import sys
import unittest

# Ensure root directory and local site-packages are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
user_site = os.path.expanduser(f"~/.local/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
if os.path.exists(user_site) and user_site not in sys.path:
    sys.path.insert(0, user_site)

from core import clean_private_key, is_valid_eth_address


class TestValidation(unittest.TestCase):
    def test_clean_private_key_with_prefix(self):
        pk = "0x" + "a" * 64
        self.assertEqual(clean_private_key(pk), pk)

    def test_clean_private_key_uppercase_prefix(self):
        pk = "0X" + "a" * 64
        self.assertEqual(clean_private_key(pk), "0x" + "a" * 64)

    def test_clean_private_key_without_prefix(self):
        raw = "b" * 64
        self.assertEqual(clean_private_key(raw), "0x" + raw)

    def test_clean_private_key_with_whitespace(self):
        raw = "  0x" + "c" * 64 + "  \n"
        self.assertEqual(clean_private_key(raw), "0x" + "c" * 64)

    def test_is_valid_eth_address_valid(self):
        valid_addr = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        self.assertTrue(is_valid_eth_address(valid_addr))
        self.assertTrue(is_valid_eth_address(valid_addr.lower()))

    def test_is_valid_eth_address_invalid_prefix(self):
        self.assertFalse(is_valid_eth_address("1xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"))

    def test_is_valid_eth_address_invalid_length(self):
        self.assertFalse(is_valid_eth_address("0x1234"))
        self.assertFalse(is_valid_eth_address("0x" + "a" * 41))

    def test_is_valid_eth_address_invalid_chars(self):
        self.assertFalse(is_valid_eth_address("0xZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"))

    def test_is_valid_eth_address_empty_and_none(self):
        self.assertFalse(is_valid_eth_address(""))
        self.assertFalse(is_valid_eth_address(None))
        self.assertFalse(is_valid_eth_address(12345))


if __name__ == "__main__":
    unittest.main()
