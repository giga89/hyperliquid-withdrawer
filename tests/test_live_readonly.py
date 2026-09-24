import os
import sys
import unittest

# Ensure root directory and local site-packages are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
user_site = os.path.expanduser(f"~/.local/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
if os.path.exists(user_site) and user_site not in sys.path:
    sys.path.insert(0, user_site)

from core import HyperliquidClient


class TestLiveReadonlyConnectivity(unittest.TestCase):
    """
    Live test against official Hyperliquid API endpoints
    to verify that read-only calls work without geo-blocking.
    """

    def test_live_account_summary(self):
        vitalik_addr = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        client = HyperliquidClient(account_address=vitalik_addr)
        summary = client.get_account_summary()

        self.assertEqual(summary["address"], vitalik_addr)
        self.assertIn("perp", summary)
        self.assertIn("spot", summary)
        self.assertIn("withdrawable_usdc", summary["perp"])
        self.assertIn("usdc_available", summary["spot"])
        self.assertIsInstance(summary["open_orders"], list)
        self.assertIsInstance(summary["perp"]["positions"], list)
        self.assertIsInstance(summary["spot"]["balances"], list)


if __name__ == "__main__":
    unittest.main()
