import os
import sys
import unittest
from unittest.mock import patch

# Ensure root directory and local site-packages are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
user_site = os.path.expanduser(f"~/.local/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
if os.path.exists(user_site) and user_site not in sys.path:
    sys.path.insert(0, user_site)

from web_app import app


class TestWebAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_index_page(self):
        res = self.app.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Hyperliquid Direct DeFi Withdrawer", res.data)

    def test_summary_invalid_address(self):
        res = self.app.get("/api/summary?address=invalid")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["status"], "err")

    @patch("web_app.HyperliquidClient")
    def test_summary_valid_address(self, mock_client_cls):
        mock_instance = mock_client_cls.return_value
        mock_instance.get_account_summary.return_value = {
            "address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
            "perp": {"account_value": 100.0, "withdrawable_usdc": 100.0, "total_margin_used": 0.0, "positions": []},
            "spot": {"usdc_available": 50.0, "balances": []},
            "open_orders": [],
            "total_withdrawable_usdc": 150.0,
        }

        res = self.app.get("/api/summary?address=0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["data"]["total_withdrawable_usdc"], 150.0)

    def test_withdraw_missing_fields(self):
        res = self.app.post("/api/withdraw", json={})
        self.assertEqual(res.status_code, 400)

    @patch("web_app.HyperliquidClient")
    def test_withdraw_api_success(self, mock_client_cls):
        mock_instance = mock_client_cls.return_value
        mock_instance.withdraw_to_arbitrum.return_value = {
            "status": "ok",
            "amount": 25.0,
            "destination": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
            "bridge": "Arbitrum One",
        }

        res = self.app.post("/api/withdraw", json={
            "private_key": "0x" + "1" * 64,
            "destination": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
            "amount": 25.0
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["amount"], 25.0)


if __name__ == "__main__":
    unittest.main()
