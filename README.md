# 🛡️ Hyperliquid Direct DeFi Withdrawer

[![CI Tests](https://github.com/hyperliquid-dex/hyperliquid-withdrawer/actions/workflows/ci.yml/badge.svg)](https://github.com/)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Non-Custodial](https://img.shields.io/badge/Architecture-Non--Custodial-green.svg)](#security--privacy-guarantees)
[![Tests Passing](https://img.shields.io/badge/Tests-30%2F30%20Passing-brightgreen.svg)](#-automated-testing-suite)

A secure, open-source, **non-custodial** tool to **inspect and withdraw your funds directly from Hyperliquid L1 to Arbitrum One**, completely bypassing the official web frontend's geo-blocking, Cloudflare IP restrictions, or jurisdictional blocks.

---

## 📌 Why Does "Restricted Jurisdiction" Happen?

When attempting to access the official Hyperliquid web app (`app.hyperliquid.xyz`), you might encounter:

> *"You are accessing our products and services from a restricted jurisdiction. We do not allow access from certain jurisdictions including locations subject to sanctions restrictions and other jurisdictions where our services are ineligible for use..."*

### Are Your Funds Locked? **NO.**

- **The Block is Only on the Website**: Hyperliquid's commercial web interface employs Cloudflare geolocation filtering to comply with regional derivatives trading restrictions.
- **DeFi Non-Custodial Reality**: Hyperliquid is a decentralized Layer 1 appchain paired with an official smart contract bridge on **Arbitrum One**.
- **No Protocol-Level Block**: The underlying validator nodes (`api.hyperliquid.xyz`) and Arbitrum bridge smart contracts **do not enforce frontend geoblocks**.
- **Cryptographic Ownership**: As long as you control the private key of your Ethereum wallet, you can construct and submit signed transactions (**EIP-712 standard**) directly to the validator network to withdraw your assets at any time.

This repository provides both an interactive terminal wizard and a clean local browser GUI that speak directly to the Hyperliquid L1 nodes and Arbitrum bridge.

---

## 🔒 Security & Privacy Guarantees

In accordance with open-source community standards, this tool is built under a strict zero-retention security policy:

1. **Zero Key Storage**: Private keys are **NEVER saved to disk**, never appended to `.env` files, never written to log files, and never stored in browser `localStorage` or session cookies.
2. **Ephemeral In-Memory Handling**: Keys are entered via masked standard terminal inputs (`getpass`) or in-memory Web UI fields. Once the local EIP-712 signature is computed, the memory reference is discarded.
3. **Local EIP-712 Signing**: All signatures are generated **locally on your machine** using standard Ethereum cryptography (`eth_account`). Your private key is **NEVER** transmitted over the network—only the resulting signature and message payload are sent to Hyperliquid's official API.
4. **Direct RPC Communication**: The tool connects solely to Hyperliquid's official validator endpoints (`https://api.hyperliquid.xyz`). No intermediate servers, proxies, analytics, or telemetry are used.
5. **Auditable & Transparent**: 100% open-source Python with full automated test coverage.

---

## 📁 Repository Structure

```text
hyperliquid-withdrawer/
├── core.py                   # High-performance client (L1 nodes, metadata, signing & bridge)
├── cli.py                    # Terminal CLI (Interactive Wizard, Read-only Status, Direct commands)
├── web_app.py                # Standalone local Web GUI dashboard (http://127.0.0.1:5000)
├── requirements.txt          # Python dependencies
├── .env.example              # Configuration template (optional defaults)
├── .gitignore                # Git ignore rules (prevents accidental key or cache commits)
├── LICENSE                   # MIT Open-Source License
├── AGENTS.md                 # Agent guidelines and verification rules
├── .github/workflows/ci.yml  # Multi-version CI automated test workflow
└── tests/                    # Comprehensive 30-test automated suite
    ├── test_validation.py    # Address validation & key sanitization tests
    ├── test_client.py        # Business logic, permissions, and mock bridge tests
    ├── test_web_api.py       # Local Flask backend endpoint tests
    ├── test_live_readonly.py # Live connectivity test to Hyperliquid L1 nodes
    └── test_compilation_and_imports.py # Script compilation & subprocess import smoke tests
```

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/hyperliquid-withdrawer.git
cd hyperliquid-withdrawer
```

### 2. Set Up a Virtual Environment (Recommended)
```bash
python3 -m venv venv
source venv/bin/activate
```
*(On Windows: `venv\Scripts\activate`)*

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🚀 Usage Guide

You can use this tool in four ways depending on your preference:

### Option 1: Interactive Guided Wizard (Recommended)

The easiest and safest way to recover your assets. Run:

```bash
python3 cli.py wizard
```
*(or run `python3 cli.py` to open the main menu).*

**The Wizard automatically handles the full withdrawal pipeline:**
1. **Prompts for Private Key**: Securely masked input via `getpass`.
2. **Account Audit**: Displays your Perpetual balance, Spot balance, open positions, active orders, and staking status.
3. **Cancel Open Orders**: If active orders are locking up your margin, it prompts you to cancel them.
4. **Market-Close Positions**: If active Perpetual positions are locking up margin, it offers to close them at market price to free up capital.
5. **Spot-to-Perp Transfer**: Arbitrum bridge withdrawals are settled from the Perpetual account. If you hold USDC in Spot, it transfers it to Perpetual (`usdClassTransfer`).
6. **Bridge Withdrawal**: Asks for your recipient Arbitrum One address (defaults to your own address) and submits the withdrawal (`withdraw3`) directly to the Hyperliquid Bridge.

---

### Option 2: Read-Only Balance Check (Zero Risk, No Key Required)

If you just want to verify your balances, open positions, or orders without providing a private key:

```bash
python3 cli.py status 0xYourEthereumAddress
```

**Example Output:**
```text
Account: 0xbe022927399F866BD840144220c32A0389B143BC

                               Account Overview & Liquidity                                
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Category                  ┃     Value ┃ Notes / Action                                  ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Perp Account Value        │     $9.80 │ Total margin + unrealized PnL                   │
│ Perp Withdrawable (Bridge)│ 9.80 USDC │ Ready to withdraw to Arbitrum One               │
│ Perp Margin Used          │     $0.00 │ Margin locked in active perpetual positions     │
│ Spot USDC Available       │ 0.00 USDC │ Transferable to Perp to enable withdrawal       │
│ Total Available USDC      │ 9.80 USDC │ Sum of Perp Withdrawable + Spot USDC            │
└───────────────────────────┴───────────┴─────────────────────────────────────────────────┘
```

---

### Option 3: Local Web GUI Dashboard

If you prefer a visual web interface in your browser:

```bash
python3 web_app.py
```
*(or `python3 cli.py web`)*

Open your browser to: **`http://127.0.0.1:5000`**

- **Dark-Mode Modern UI**: Fast, responsive interface.
- **Inspect Any Address**: Check balances with zero credentials.
- **One-Click Withdrawals**: Modal dialogs to withdraw USDC to Arbitrum One or move Spot USDC to Perp.
- **100% Local**: All signing logic executes strictly on your local machine.

---

### Option 4: Direct CLI Commands (Automation / Scripting)

For advanced users or headless scripts:

- **Withdraw all available USDC to an Arbitrum address:**
  ```bash
  python3 cli.py withdraw --amount MAX --dest 0xYourArbitrumAddress
  ```

- **Transfer USDC from Spot to Perpetual:**
  ```bash
  python3 cli.py spot-to-perp --amount MAX
  ```

- **Market-close all open perpetual positions:**
  ```bash
  python3 cli.py close-positions
  ```

- **Cancel all pending orders:**
  ```bash
  python3 cli.py cancel-orders
  ```

---

## ⏱️ Bridge Settlement & Verification

- **Destination Network**: **Arbitrum One** (Layer 2).
- **Token Received**: **Native USDC** (`0xaf88d065e77c8cC2239327C5EDb3A432268e5831`).
- **Bridge Network Fee**: **1.00 USDC** (fixed fee deducted by Hyperliquid validator bridge).
- **Estimated Settlement Time**: **3 to 5 minutes**. Hyperliquid validators collect withdrawal requests, sign the bridge release, and execute the transfer on Arbitrum One.
- **Tracking Arrival**: You can monitor your incoming funds by searching your address on [Arbiscan](https://arbiscan.io).

---

## 🧪 Automated Testing Suite

This repository includes a comprehensive 30-test suite covering validation, client security permissions, mock transactions, Flask web endpoints, and live L1 RPC connectivity.

### Run with Pytest:
```bash
pytest -v
```

### Run with Python Standard Library Unittest:
```bash
python3 -m unittest discover -s tests -v
```

### What the Tests Verify:
1. **`tests/test_validation.py`**:
   - Sanitization of private key hex prefixes (`0x`, `0X`, whitespace trimming).
   - Strict validation of Ethereum/Arbitrum addresses (checksum, 42-char length, hex character validation).
2. **`tests/test_client.py`**:
   - Verifies that read-only client instances strictly reject any attempt to sign transactions (`PermissionError`).
   - Verifies proper derivation of Ethereum addresses from private keys.
   - Verifies withdrawal guardrails: rejecting invalid recipient addresses, blocking withdrawals exceeding available balance, and enforcing minimum bridge fee requirements.
   - Verifies Spot-to-Perp balance transfers and error handling.
3. **`tests/test_web_api.py`**:
   - Tests Flask web template rendering and REST API routes (`/api/summary`, `/api/withdraw`, `/api/spot-to-perp`).
   - Verifies input validation and error responses.
4. **`tests/test_live_readonly.py`**:
   - Performs a live read-only query against production Hyperliquid L1 nodes to confirm connectivity without geo-blocking.
5. **`tests/test_compilation_and_imports.py`**:
   - Syntax-compiles every `.py` file across the workspace.
   - Verifies clean subprocess imports.
   - Verifies graceful pure-Python fallback operation when terminal styling libraries (`rich`) are not installed.

---

## 💡 Frequently Asked Questions (FAQ)

### Q: Where do I get my Ethereum Private Key?
- **MetaMask**: Click the three dots next to your account name -> *Account Details* -> *Show Private Key* -> Enter your MetaMask password.
- **Rabby Wallet**: Click *Manage Wallets* -> select your active account -> *Export Private Key*.
*Never share your private key with anyone. This tool only uses it in local memory to compute the EIP-712 signature.*

### Q: What is "Action disabled when unified account is active"?
Hyperliquid accounts created or upgraded to Unified Account mode share collateral seamlessly between Spot and Perp. When Unified Account mode is enabled, internal transfers (`usdClassTransfer`) are disabled because your balances are already unified. The tool automatically detects this and proceeds directly to bridge withdrawal.

### Q: Can I withdraw to an exchange deposit address?
**We strongly recommend withdrawing to your own non-custodial wallet (e.g. MetaMask, Rabby, Trezor, Ledger) on Arbitrum One.** Centralized exchanges may take longer to credit bridge transactions or require specific deposit memo routing. Once the USDC is in your personal Arbitrum wallet, you can deposit to any exchange normally.

---

## 📜 License

This project is licensed under the [MIT License](LICENSE) - see the `LICENSE` file for details.

---

## ⚠️ Disclaimer

This software is an independent, non-custodial open-source utility provided "as is" under the MIT License, without warranty of any kind. This project is not officially affiliated with or endorsed by Hyperliquid or the Hyperliquid Foundation. Always inspect transactions and verify recipient addresses before submitting on-chain operations.
