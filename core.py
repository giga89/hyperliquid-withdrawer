"""
Hyperliquid Direct DeFi Withdrawer - Core Module
Direct non-custodial interaction with Hyperliquid L1 and Arbitrum Bridge.
Bypasses web frontend geo-blocking by communicating directly with Hyperliquid validator/API endpoints.
"""

import os
import sys

# Comprehensive sys.path injection to ensure all site/dist-packages are available
possible_paths = [
    "/usr/lib/python3/dist-packages",
    "/usr/local/lib/python3/dist-packages",
    f"/usr/local/lib/python{sys.version_info.major}.{sys.version_info.minor}/dist-packages",
    os.path.expanduser(f"~/.local/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"),
    os.path.expanduser("~/.local/lib/python3/site-packages"),
]
for p in possible_paths:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.append(p)

import logging
from typing import Dict, Any, List, Optional
from eth_account import Account
from eth_account.signers.local import LocalAccount
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# Suppress excessive debug logs from web libraries
logging.basicConfig(level=logging.WARNING)


def clean_private_key(pk: str) -> str:
    """Sanitize and format private key string."""
    pk = pk.strip()
    if pk.startswith("0x") or pk.startswith("0X"):
        pk = pk[2:]
    return "0x" + pk


def is_valid_eth_address(address: str) -> bool:
    """Validate 42-char hex Ethereum/Arbitrum address."""
    if not address or not isinstance(address, str):
        return False
    addr = address.strip()
    if not addr.startswith("0x") or len(addr) != 42:
        return False
    try:
        int(addr[2:], 16)
        return True
    except ValueError:
        return False


class HyperliquidClient:
    """
    Client for interacting directly with Hyperliquid Mainnet.
    Supports both read-only operations (with just an address)
    and signed exchange actions (with a private key).
    """

    def __init__(self, private_key: Optional[str] = None, account_address: Optional[str] = None):
        self.base_url = constants.MAINNET_API_URL
        # Fast initialization bypassing heavy metadata download
        self._fast_meta = {"universe": []}
        self._fast_spot_meta = {"tokens": [], "universe": []}
        self.info = Info(
            self.base_url,
            skip_ws=True,
            meta=self._fast_meta,
            spot_meta=self._fast_spot_meta,
            perp_dexs=None,
        )
        self._full_meta_loaded = False
        self.wallet: Optional[LocalAccount] = None
        self.address: Optional[str] = None
        self.exchange: Optional[Exchange] = None

        if private_key:
            pk = clean_private_key(private_key)
            self.wallet = Account.from_key(pk)
            self.address = self.wallet.address
            self.exchange = Exchange(
                wallet=self.wallet,
                base_url=self.base_url,
                meta=self._fast_meta,
                spot_meta=self._fast_spot_meta,
                account_address=account_address or self.address,
            )
        elif account_address:
            self.address = account_address.strip()

    def _ensure_full_meta(self):
        """Lazy-load full market metadata only when needed (e.g. for order cancellation/market close)."""
        if not self._full_meta_loaded:
            full_meta = self.info.meta()
            self.info.set_perp_meta(full_meta, 0)
            if self.exchange:
                self.exchange.info.set_perp_meta(full_meta, 0)
            self._full_meta_loaded = True

    def get_account_summary(self, target_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch complete account overview:
        - Perp margin & withdrawable USDC
        - Open perp positions
        - Spot balances
        - Open orders
        - Staking summary
        """
        addr = target_address or self.address
        if not addr:
            raise ValueError("No address provided for account summary.")

        # 1. Fetch Perpetual Clearinghouse State
        perp_state = self.info.user_state(addr)
        margin_summary = perp_state.get("marginSummary", {})
        withdrawable = float(perp_state.get("withdrawable", "0"))
        asset_positions = perp_state.get("assetPositions", [])

        # Process open positions
        positions: List[Dict[str, Any]] = []
        for pos_data in asset_positions:
            pos = pos_data.get("position", {})
            szi = float(pos.get("szi", 0))
            if szi != 0:
                positions.append({
                    "coin": pos.get("coin"),
                    "size": szi,
                    "entry_px": float(pos.get("entryPx", 0)),
                    "position_value": float(pos.get("positionValue", 0)),
                    "unrealized_pnl": float(pos.get("unrealizedPnl", 0)),
                    "return_on_equity": float(pos.get("returnOnEquity", 0)),
                    "liquidation_px": float(pos.get("liquidationPx") or 0),
                    "leverage": pos.get("leverage", {}),
                    "margin_used": float(pos.get("marginUsed", 0)),
                })

        # 2. Fetch Spot Balances
        spot_state = self.info.spot_user_state(addr)
        raw_spot_balances = spot_state.get("balances", [])
        spot_balances: List[Dict[str, Any]] = []
        spot_usdc = 0.0

        for bal in raw_spot_balances:
            coin = bal.get("coin")
            total = float(bal.get("total", 0))
            hold = float(bal.get("hold", 0))
            available = max(0.0, total - hold)
            if total > 0 or hold > 0:
                spot_balances.append({
                    "coin": coin,
                    "token": bal.get("token"),
                    "total": total,
                    "hold": hold,
                    "available": available,
                    "entry_ntl": float(bal.get("entryNtl", 0)),
                })
            if coin == "USDC":
                spot_usdc = available

        # 3. Fetch Open Orders
        try:
            raw_orders = self.info.frontend_open_orders(addr)
        except Exception:
            raw_orders = self.info.open_orders(addr)

        open_orders: List[Dict[str, Any]] = []
        for ord_item in raw_orders:
            open_orders.append({
                "oid": ord_item.get("oid"),
                "coin": ord_item.get("coin"),
                "side": "BUY" if ord_item.get("side") == "B" else "SELL",
                "limit_px": float(ord_item.get("limitPx", 0)),
                "sz": float(ord_item.get("sz", 0)),
                "timestamp": ord_item.get("timestamp"),
                "order_type": ord_item.get("orderType", "Limit"),
            })

        # 4. Fetch Staking Summary
        try:
            staking_data = self.info.user_staking_summary(addr)
        except Exception:
            staking_data = {}

        account_value = float(margin_summary.get("accountValue", 0))
        total_margin_used = float(margin_summary.get("totalMarginUsed", 0))

        return {
            "address": addr,
            "perp": {
                "account_value": account_value,
                "withdrawable_usdc": withdrawable,
                "total_margin_used": total_margin_used,
                "total_raw_usd": float(margin_summary.get("totalRawUsd", 0)),
                "positions": positions,
            },
            "spot": {
                "usdc_available": spot_usdc,
                "balances": spot_balances,
            },
            "open_orders": open_orders,
            "staking": {
                "delegated": float(staking_data.get("delegated", 0)),
                "undelegated": float(staking_data.get("undelegated", 0)),
                "total_pending_withdrawal": float(staking_data.get("totalPendingWithdrawal", 0)),
            },
            "total_withdrawable_usdc": withdrawable + spot_usdc,
        }

    def _ensure_exchange(self):
        if not self.exchange or not self.wallet:
            raise PermissionError("Private key required for signed actions. Read-only client cannot execute transactions.")

    def cancel_all_orders(self) -> Dict[str, Any]:
        """Cancel all open orders to unlock margin and balances."""
        self._ensure_exchange()
        orders = self.info.open_orders(self.address)
        if not orders:
            return {"status": "ok", "cancelled_count": 0, "message": "No open orders found."}

        self._ensure_full_meta()
        cancel_requests = [{"coin": o["coin"], "oid": o["oid"]} for o in orders]
        res = self.exchange.bulk_cancel(cancel_requests)
        return {
            "status": "ok",
            "cancelled_count": len(cancel_requests),
            "response": res,
        }

    def close_all_positions(self, slippage: float = 0.05) -> List[Dict[str, Any]]:
        """
        Close all open perpetual positions at market price to liberate margin.
        slippage: tolerance (default 5%)
        """
        self._ensure_exchange()
        self._ensure_full_meta()
        summary = self.get_account_summary(self.address)
        positions = summary["perp"]["positions"]
        results = []

        for pos in positions:
            coin = pos["coin"]
            res = self.exchange.market_close(coin=coin, slippage=slippage)
            results.append({"coin": coin, "size": pos["size"], "response": res})

        return results

    def transfer_spot_usdc_to_perp(self, amount: Optional[float] = None) -> Dict[str, Any]:
        """
        Transfer USDC from Spot to Perpetual account.
        Withdrawals to Arbitrum bridge pull from the Perpetual balance.
        If amount is None, transfers all available Spot USDC.
        """
        self._ensure_exchange()
        summary = self.get_account_summary(self.address)
        avail = summary["spot"]["usdc_available"]

        if avail <= 0:
            return {"status": "err", "message": "No available Spot USDC to transfer."}

        if amount is None or amount <= 0 or amount > avail:
            amount = avail

        # usd_class_transfer(amount, to_perp=True)
        res = self.exchange.usd_class_transfer(amount=amount, to_perp=True)
        if isinstance(res, dict) and res.get("status") == "err":
            err_msg = res.get("response", "Unknown error from Hyperliquid")
            return {
                "status": "err",
                "message": f"{err_msg}",
                "response": res,
            }

        return {
            "status": "ok",
            "transferred_amount": amount,
            "response": res,
        }

    def transfer_perp_usdc_to_spot(self, amount: float) -> Dict[str, Any]:
        """Transfer USDC from Perp to Spot account."""
        self._ensure_exchange()
        if amount <= 0:
            return {"status": "err", "message": "Amount must be greater than 0."}
        res = self.exchange.usd_class_transfer(amount=amount, to_perp=False)
        if isinstance(res, dict) and res.get("status") == "err":
            err_msg = res.get("response", "Unknown error from Hyperliquid")
            return {
                "status": "err",
                "message": f"{err_msg}",
                "response": res,
            }
        return {
            "status": "ok",
            "transferred_amount": amount,
            "response": res,
        }

    def withdraw_to_arbitrum(self, amount: float, destination_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Withdraw USDC to an Arbitrum One address via Hyperliquid Bridge.
        Hyperliquid deducts a $1 fee on the bridge withdrawal.
        Destination defaults to user's wallet address if not specified.
        Takes ~5 minutes to settle on Arbitrum.
        """
        self._ensure_exchange()
        dest = destination_address or self.address
        if not is_valid_eth_address(dest):
            return {"status": "err", "message": f"Invalid Arbitrum destination address: {dest}"}

        # Check total available balance (Perp + Spot)
        summary = self.get_account_summary(self.address)
        perp_withdrawable = float(summary.get("perp", {}).get("withdrawable_usdc", 0.0))
        spot_avail = float(summary.get("spot", {}).get("usdc_available", 0.0))
        total_avail = float(summary.get("total_withdrawable_usdc", perp_withdrawable + spot_avail))

        if amount > total_avail:
            return {
                "status": "err",
                "message": (
                    f"Requested amount ({amount:.2f} USDC) exceeds total available balance "
                    f"({total_avail:.2f} USDC)."
                ),
            }

        if amount <= 1.0:
            return {
                "status": "err",
                "message": f"Withdrawal amount must be greater than the bridge fee (1.0 USDC). Requested: {amount}",
            }

        # If Perp balance is insufficient but Spot balance exists, attempt transfer first
        if amount > perp_withdrawable and spot_avail > 0:
            try:
                self.transfer_spot_usdc_to_perp(min(spot_avail, amount - perp_withdrawable))
            except Exception:
                pass

        # Round to 6 decimals (standard USDC precision)
        withdraw_amount = round(amount, 6)

        # Call withdraw_from_bridge
        res = self.exchange.withdraw_from_bridge(amount=withdraw_amount, destination=dest)
        if isinstance(res, dict) and res.get("status") == "err":
            err_msg = res.get("response", "Unknown error from Hyperliquid bridge")
            return {
                "status": "err",
                "message": f"{err_msg}",
                "response": res,
            }

        return {
            "status": "ok",
            "amount": withdraw_amount,
            "destination": dest,
            "bridge": "Arbitrum One",
            "estimated_time": "3 - 5 minutes",
            "fee": "1.00 USDC",
            "response": res,
        }

    def transfer_spot_token(self, token: str, amount: float, destination_address: str) -> Dict[str, Any]:
        """
        Send a spot token (like HYPE, PURR, etc.) on Hyperliquid L1
        to another 0x address.
        """
        self._ensure_exchange()
        if not is_valid_eth_address(destination_address):
            return {"status": "err", "message": f"Invalid destination address: {destination_address}"}
        if amount <= 0:
            return {"status": "err", "message": "Amount must be greater than 0."}

        res = self.exchange.spot_transfer(amount=amount, destination=destination_address, token=token)
        return {
            "status": "ok",
            "token": token,
            "amount": amount,
            "destination": destination_address,
            "response": res,
        }
