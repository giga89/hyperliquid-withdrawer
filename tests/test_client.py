import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure root directory and local site-packages are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
user_site = os.path.expanduser(f"~/.local/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
if os.path.exists(user_site) and user_site not in sys.path:
    sys.path.insert(0, user_site)

from core import HyperliquidClient


class TestHyperliquidClient(unittest.TestCase):
    def setUp(self):
        # Deterministic test private key (standard test key)
        self.test_pk = "0x" + "1" * 64
        self.test_addr = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

    def test_readonly_client_initialization(self):
        client = HyperliquidClient(account_address=self.test_addr)
        self.assertEqual(client.address, self.test_addr)
        self.assertIsNone(client.wallet)
        self.assertIsNone(client.exchange)

    def test_readonly_client_permission_errors(self):
        client = HyperliquidClient(account_address=self.test_addr)
        with self.assertRaises(PermissionError):
            client.withdraw_to_arbitrum(10.0, self.test_addr)
        with self.assertRaises(PermissionError):
            client.cancel_all_orders()
        with self.assertRaises(PermissionError):
            client.close_all_positions()
        with self.assertRaises(PermissionError):
            client.transfer_spot_usdc_to_perp(10.0)

    def test_signed_client_initialization(self):
        client = HyperliquidClient(private_key=self.test_pk)
        self.assertIsNotNone(client.wallet)
        self.assertIsNotNone(client.exchange)
        self.assertTrue(client.address.startswith("0x"))
        self.assertEqual(len(client.address), 42)

    @patch.object(HyperliquidClient, "get_account_summary")
    def test_withdraw_invalid_address(self, mock_summary):
        client = HyperliquidClient(private_key=self.test_pk)
        res = client.withdraw_to_arbitrum(10.0, "0xInvalid")
        self.assertEqual(res["status"], "err")
        self.assertIn("Invalid Arbitrum destination address", res["message"])

    @patch.object(HyperliquidClient, "get_account_summary")
    def test_withdraw_exceeds_balance(self, mock_summary):
        mock_summary.return_value = {
            "perp": {"withdrawable_usdc": 50.0},
            "spot": {"usdc_available": 0.0},
            "total_withdrawable_usdc": 50.0,
        }
        client = HyperliquidClient(private_key=self.test_pk)
        res = client.withdraw_to_arbitrum(100.0, self.test_addr)
        self.assertEqual(res["status"], "err")
        self.assertIn("exceeds total available balance", res["message"])

    @patch.object(HyperliquidClient, "get_account_summary")
    def test_withdraw_less_than_fee(self, mock_summary):
        mock_summary.return_value = {
            "perp": {"withdrawable_usdc": 50.0},
            "spot": {"usdc_available": 0.0},
            "total_withdrawable_usdc": 50.0,
        }
        client = HyperliquidClient(private_key=self.test_pk)
        res = client.withdraw_to_arbitrum(1.0, self.test_addr)
        self.assertEqual(res["status"], "err")
        self.assertIn("greater than the bridge fee", res["message"])

    @patch.object(HyperliquidClient, "get_account_summary")
    def test_withdraw_success(self, mock_summary):
        mock_summary.return_value = {
            "perp": {"withdrawable_usdc": 50.0},
            "spot": {"usdc_available": 0.0},
            "total_withdrawable_usdc": 50.0,
        }
        client = HyperliquidClient(private_key=self.test_pk)
        client.exchange.withdraw_from_bridge = MagicMock(return_value={"status": "ok", "response": {}})

        res = client.withdraw_to_arbitrum(25.5, self.test_addr)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["amount"], 25.5)
        self.assertEqual(res["destination"], self.test_addr)
        self.assertEqual(res["bridge"], "Arbitrum One")
        client.exchange.withdraw_from_bridge.assert_called_once_with(amount=25.5, destination=self.test_addr)

    @patch.object(HyperliquidClient, "get_account_summary")
    def test_transfer_spot_usdc_to_perp(self, mock_summary):
        mock_summary.return_value = {
            "spot": {"usdc_available": 42.0},
        }
        client = HyperliquidClient(private_key=self.test_pk)
        client.exchange.usd_class_transfer = MagicMock(return_value={"status": "ok"})

        # Test transfer MAX
        res = client.transfer_spot_usdc_to_perp(None)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["transferred_amount"], 42.0)
        client.exchange.usd_class_transfer.assert_called_once_with(amount=42.0, to_perp=True)

    @patch.object(HyperliquidClient, "get_account_summary")
    def test_transfer_spot_usdc_zero_available(self, mock_summary):
        mock_summary.return_value = {
            "spot": {"usdc_available": 0.0},
        }
        client = HyperliquidClient(private_key=self.test_pk)
        res = client.transfer_spot_usdc_to_perp(10.0)
        self.assertEqual(res["status"], "err")
        self.assertIn("No available Spot USDC", res["message"])


if __name__ == "__main__":
    unittest.main()
