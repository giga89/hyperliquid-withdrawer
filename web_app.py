#!/usr/bin/env python3
"""
Hyperliquid Direct DeFi Rescue Web GUI
Local Web graphical user interface running on http://127.0.0.1:5000
Bypasses Cloudflare/GUI geoblocking by routing calls directly through the local Python backend to L1 nodes.
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

import argparse
from flask import Flask, request, jsonify, render_template_string
from core import HyperliquidClient, is_valid_eth_address

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hyperliquid DeFi Rescue - Direct Withdrawer</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #0b0f19;
            --bg-card: rgba(18, 24, 38, 0.85);
            --bg-card-hover: rgba(26, 34, 52, 0.9);
            --border: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(56, 189, 248, 0.25);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-cyan: #38bdf8;
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            --radius-md: 12px;
            --radius-lg: 16px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: radial-gradient(circle at top right, #131b2e, #0b0f19 60%);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 2rem 1rem;
            line-height: 1.5;
        }

        .container {
            max-width: 1080px;
            margin: 0 auto;
        }

        header {
            margin-bottom: 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 1rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border);
        }

        .brand-logo {
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }

        .badge-live {
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-emerald);
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            border: 1px solid rgba(16, 185, 129, 0.3);
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }

        .badge-live::before {
            content: "";
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent-emerald);
            box-shadow: 0 0 8px var(--accent-emerald);
        }

        h1 {
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, #ffffff, var(--accent-cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtitle {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 0.2rem;
        }

        .alert-banner {
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: var(--radius-md);
            padding: 1rem 1.25rem;
            margin-bottom: 2rem;
            display: flex;
            align-items: flex-start;
            gap: 0.8rem;
        }

        .alert-banner svg {
            color: var(--accent-amber);
            flex-shrink: 0;
            margin-top: 0.15rem;
        }

        .alert-banner div p {
            font-size: 0.9rem;
            color: #fef3c7;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(12px);
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.25rem;
        }

        .card-title {
            font-size: 1.15rem;
            font-weight: 600;
            color: #fff;
        }

        .form-row {
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
        }

        .form-input {
            flex: 1;
            min-width: 280px;
            background: rgba(10, 15, 26, 0.8);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 0.8rem 1rem;
            color: var(--text-primary);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            transition: all 0.2s;
        }

        .form-input:focus {
            outline: none;
            border-color: var(--accent-cyan);
            box-shadow: 0 0 16px rgba(56, 189, 248, 0.2);
        }

        .btn {
            background: linear-gradient(135deg, #0284c7, #0369a1);
            color: #fff;
            border: none;
            border-radius: var(--radius-md);
            padding: 0.8rem 1.5rem;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn:hover {
            opacity: 0.92;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3);
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        .btn-emerald {
            background: linear-gradient(135deg, #059669, #047857);
        }
        .btn-emerald:hover {
            box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3);
        }

        .btn-amber {
            background: linear-gradient(135deg, #d97706, #b45309);
        }

        .btn-rose {
            background: linear-gradient(135deg, #e11d48, #be123c);
        }

        .grid-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }

        .stat-box {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 1.25rem;
            position: relative;
            overflow: hidden;
        }

        .stat-label {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            margin-bottom: 0.4rem;
        }

        .stat-val {
            font-size: 1.6rem;
            font-weight: 700;
            color: #fff;
            font-family: 'JetBrains Mono', monospace;
        }

        .stat-val.highlight {
            color: var(--accent-emerald);
        }

        .stat-desc {
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 0.3rem;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.88rem;
            margin-top: 0.5rem;
        }

        th {
            text-align: left;
            padding: 0.75rem 1rem;
            color: var(--text-secondary);
            font-weight: 500;
            border-bottom: 1px solid var(--border);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        td {
            padding: 0.85rem 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            font-family: 'JetBrains Mono', monospace;
        }

        tr:last-child td {
            border-bottom: none;
        }

        .quick-actions {
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
            margin-top: 1.25rem;
        }

        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(6px);
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
            z-index: 999;
            visibility: hidden;
            opacity: 0;
            transition: all 0.25s;
        }

        .modal-overlay.open {
            visibility: visible;
            opacity: 1;
        }

        .modal-box {
            background: #111827;
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            max-width: 520px;
            width: 100%;
            padding: 2rem;
            box-shadow: 0 20px 48px rgba(0, 0, 0, 0.5);
        }

        .modal-title {
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: #fff;
        }

        .form-group {
            margin-bottom: 1.2rem;
        }

        .form-label {
            display: block;
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-bottom: 0.35rem;
            font-weight: 500;
        }

        .status-msg {
            padding: 1rem;
            border-radius: var(--radius-md);
            margin-top: 1rem;
            font-size: 0.9rem;
            display: none;
        }

        .status-msg.success {
            display: block;
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #6ee7b7;
        }

        .status-msg.error {
            display: block;
            background: rgba(244, 63, 94, 0.15);
            border: 1px solid rgba(244, 63, 94, 0.3);
            color: #fca5a5;
        }

        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand-logo">
                <div>
                    <h1>Hyperliquid Direct DeFi Withdrawer</h1>
                    <div class="subtitle">Bypass GUI geofencing and withdraw funds directly to Arbitrum One</div>
                </div>
            </div>
            <div class="badge-live">Connected to Hyperliquid L1 RPC</div>
        </header>

        <div class="alert-banner">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
            <div>
                <p><strong>Why does the "Restricted Jurisdiction" message appear?</strong> The official web frontend (<span style="font-family: monospace;">app.hyperliquid.xyz</span>) applies Cloudflare geolocation filters for derivatives trading compliance. However, your funds reside directly on-chain on Hyperliquid Layer 1 and the Arbitrum One bridge smart contracts. This local application communicates directly with decentralized L1 validator nodes with zero third-party intermediaries or frontend restrictions.</p>
            </div>
        </div>

        <!-- Read-Only Account Inspection -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">1. Inspect Account (Read-Only)</div>
            </div>
            <div class="form-row">
                <input type="text" id="targetAddress" class="form-input" placeholder="Ethereum address 0x... (no private key needed)">
                <button class="btn" id="btnCheck" onclick="fetchSummary()">
                    <span id="btnCheckText">Inspect Balances</span>
                </button>
            </div>
        </div>

        <!-- Account Overview Card -->
        <div id="resultsCard" class="card" style="display: none;">
            <div class="card-header">
                <div>
                    <div class="card-title">Account State & Available Liquidity</div>
                    <div class="subtitle" id="activeAccountDisplay"></div>
                </div>
            </div>

            <div class="grid-stats">
                <div class="stat-box">
                    <div class="stat-label">Withdrawable to Bridge (Perp)</div>
                    <div class="stat-val highlight" id="valWithdrawable">0.00 USDC</div>
                    <div class="stat-desc">Immediately withdrawable to Arbitrum</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Spot USDC Available</div>
                    <div class="stat-val" id="valSpotUsdc">0.00 USDC</div>
                    <div class="stat-desc">Transferable to Perp to enable withdrawal</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Total Perp Value</div>
                    <div class="stat-val" id="valPerpValue">$0.00</div>
                    <div class="stat-desc">Account margin + unrealized PnL</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Locked Margin</div>
                    <div class="stat-val" id="valMarginUsed">$0.00</div>
                    <div class="stat-desc">Committed in open perpetual positions</div>
                </div>
            </div>

            <!-- Open Positions -->
            <div id="positionsSection" style="margin-top: 1.5rem; display: none;">
                <div style="font-weight: 600; margin-bottom: 0.5rem; color: #f43f5e;">Open Perpetual Positions (Locked Margin):</div>
                <table id="positionsTable">
                    <thead>
                        <tr>
                            <th>Asset</th>
                            <th>Size</th>
                            <th>Entry Price</th>
                            <th>PnL</th>
                            <th>Margin Used</th>
                        </tr>
                    </thead>
                    <tbody id="positionsBody"></tbody>
                </table>
            </div>

            <!-- Open Orders -->
            <div id="ordersSection" style="margin-top: 1.5rem; display: none;">
                <div style="font-weight: 600; margin-bottom: 0.5rem; color: #f59e0b;">Open Orders:</div>
                <table id="ordersTable">
                    <thead>
                        <tr>
                            <th>OID</th>
                            <th>Asset</th>
                            <th>Side</th>
                            <th>Size</th>
                            <th>Limit Price</th>
                        </tr>
                    </thead>
                    <tbody id="ordersBody"></tbody>
                </table>
            </div>

            <!-- Other Spot Tokens -->
            <div id="spotTokensSection" style="margin-top: 1.5rem; display: none;">
                <div style="font-weight: 600; margin-bottom: 0.5rem; color: #38bdf8;">Other Spot Tokens (Hyperliquid L1):</div>
                <table id="spotTokensTable">
                    <thead>
                        <tr>
                            <th>Token</th>
                            <th>Available</th>
                            <th>In Orders (Hold)</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody id="spotTokensBody"></tbody>
                </table>
            </div>

            <!-- Quick Action Buttons -->
            <div class="quick-actions">
                <button class="btn btn-emerald" onclick="openWithdrawModal()">
                    💸 Withdraw USDC to Arbitrum One
                </button>
                <button class="btn btn-amber" id="btnSpotToPerp" onclick="openSpotToPerpModal()" style="display: none;">
                    🔄 Move Spot USDC to Perp
                </button>
            </div>
        </div>

        <div id="statusMessage" class="status-msg"></div>
    </div>

    <!-- Modal: Withdrawal -->
    <div class="modal-overlay" id="withdrawModal">
        <div class="modal-box">
            <div class="modal-title">Withdraw USDC to Arbitrum One</div>
            <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1.25rem;">
                The withdrawal is submitted directly to Hyperliquid's official bridge on Arbitrum One. Estimated arrival: 3-5 minutes. Bridge network fee: 1.00 USDC.
            </p>

            <div class="form-group">
                <label class="form-label">Sender Wallet Private Key:</label>
                <input type="password" id="withdrawKey" class="form-input" style="width: 100%;" placeholder="0x... (in-memory only, never saved to disk)" autocomplete="off">
            </div>
            <div class="form-group">
                <label class="form-label">Destination Arbitrum One Address:</label>
                <input type="text" id="withdrawDest" class="form-input" style="width: 100%;" placeholder="0x...">
            </div>
            <div class="form-group">
                <label class="form-label">USDC Amount:</label>
                <div style="display: flex; gap: 0.5rem;">
                    <input type="number" id="withdrawAmount" class="form-input" style="flex: 1;" placeholder="e.g. 100.00" step="any">
                    <button class="btn" type="button" onclick="setMaxWithdraw()">MAX</button>
                </div>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;" id="maxWithdrawableHint"></div>
            </div>

            <div style="display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem;">
                <button class="btn" style="background: transparent; border: 1px solid var(--border);" onclick="closeModals()">Cancel</button>
                <button class="btn btn-emerald" id="btnExecuteWithdraw" onclick="executeWithdraw()">Confirm & Send Withdrawal</button>
            </div>
        </div>
    </div>

    <!-- Modal: Spot -> Perp -->
    <div class="modal-overlay" id="spotToPerpModal">
        <div class="modal-box">
            <div class="modal-title">Transfer USDC from Spot to Perp</div>
            <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1.25rem;">
                Bridge withdrawals to Arbitrum One are executed from your Perpetual balance. Move USDC from your Spot wallet to Perpetual to make it withdrawable.
            </p>
            <div class="form-group">
                <label class="form-label">Private Key:</label>
                <input type="password" id="s2pKey" class="form-input" style="width: 100%;" placeholder="0x... (in-memory only)" autocomplete="off">
            </div>
            <div class="form-group">
                <label class="form-label">USDC Amount to Transfer:</label>
                <input type="number" id="s2pAmount" class="form-input" style="width: 100%;" placeholder="MAX">
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem;">
                <button class="btn" style="background: transparent; border: 1px solid var(--border);" onclick="closeModals()">Cancel</button>
                <button class="btn btn-amber" onclick="executeSpotToPerp()">Transfer to Perp</button>
            </div>
        </div>
    </div>

    <script>
        let currentSummary = null;

        async function fetchSummary() {
            const addr = document.getElementById('targetAddress').value.trim();
            if (!addr) {
                alert('Please enter a valid 0x Ethereum address');
                return;
            }

            const btn = document.getElementById('btnCheck');
            const btnText = document.getElementById('btnCheckText');
            btn.disabled = true;
            btnText.innerHTML = '<span class="spinner"></span> Loading...';

            try {
                const res = await fetch(`/api/summary?address=${encodeURIComponent(addr)}`);
                const data = await res.json();

                if (data.status !== 'ok') {
                    showStatus(data.message || 'Error fetching account data', 'error');
                    return;
                }

                currentSummary = data.data;
                renderSummary(currentSummary);
                document.getElementById('resultsCard').style.display = 'block';
                hideStatus();
            } catch (err) {
                showStatus('Network connection error: ' + err.message, 'error');
            } finally {
                btn.disabled = false;
                btnText.innerText = 'Inspect Balances';
            }
        }

        function renderSummary(s) {
            document.getElementById('activeAccountDisplay').innerText = s.address;
            document.getElementById('valWithdrawable').innerText = `${s.perp.withdrawable_usdc.toFixed(2)} USDC`;
            document.getElementById('valSpotUsdc').innerText = `${s.spot.usdc_available.toFixed(2)} USDC`;
            document.getElementById('valPerpValue').innerText = `$${s.perp.account_value.toFixed(2)}`;
            document.getElementById('valMarginUsed').innerText = `$${s.perp.total_margin_used.toFixed(2)}`;

            // Positions
            const posSec = document.getElementById('positionsSection');
            const posBody = document.getElementById('positionsBody');
            posBody.innerHTML = '';
            if (s.perp.positions && s.perp.positions.length > 0) {
                posSec.style.display = 'block';
                s.perp.positions.forEach(p => {
                    const pnlColor = p.unrealized_pnl >= 0 ? '#10b981' : '#f43f5e';
                    posBody.innerHTML += `
                        <tr>
                            <td style="font-weight: 600;">${p.coin}</td>
                            <td>${p.size}</td>
                            <td>$${p.entry_px.toFixed(2)}</td>
                            <td style="color: ${pnlColor};">${p.unrealized_pnl >= 0 ? '+' : ''}$${p.unrealized_pnl.toFixed(2)}</td>
                            <td>$${p.margin_used.toFixed(2)}</td>
                        </tr>
                    `;
                });
            } else {
                posSec.style.display = 'none';
            }

            // Orders
            const ordSec = document.getElementById('ordersSection');
            const ordBody = document.getElementById('ordersBody');
            ordBody.innerHTML = '';
            if (s.open_orders && s.open_orders.length > 0) {
                ordSec.style.display = 'block';
                s.open_orders.forEach(o => {
                    ordBody.innerHTML += `
                        <tr>
                            <td>${o.oid}</td>
                            <td style="font-weight: 600;">${o.coin}</td>
                            <td style="color: ${o.side === 'BUY' ? '#10b981' : '#f43f5e'}">${o.side}</td>
                            <td>${o.sz}</td>
                            <td>$${o.limit_px.toFixed(2)}</td>
                        </tr>
                    `;
                });
            } else {
                ordSec.style.display = 'none';
            }

            // Spot tokens
            const spotSec = document.getElementById('spotTokensSection');
            const spotBody = document.getElementById('spotTokensBody');
            spotBody.innerHTML = '';
            const otherTokens = s.spot.balances.filter(b => b.coin !== 'USDC');
            if (otherTokens.length > 0) {
                spotSec.style.display = 'block';
                otherTokens.forEach(t => {
                    spotBody.innerHTML += `
                        <tr>
                            <td style="font-weight: 600;">${t.coin}</td>
                            <td>${t.available.toFixed(4)}</td>
                            <td>${t.hold.toFixed(4)}</td>
                            <td>${t.total.toFixed(4)}</td>
                        </tr>
                    `;
                });
            } else {
                spotSec.style.display = 'none';
            }

            // Spot to perp button
            const btnS2P = document.getElementById('btnSpotToPerp');
            btnS2P.style.display = s.spot.usdc_available > 0 ? 'inline-flex' : 'none';
        }

        function openWithdrawModal() {
            if (!currentSummary) return;
            document.getElementById('withdrawDest').value = currentSummary.address;
            document.getElementById('withdrawAmount').value = currentSummary.perp.withdrawable_usdc.toFixed(2);
            document.getElementById('maxWithdrawableHint').innerText = `Max withdrawable: ${currentSummary.perp.withdrawable_usdc.toFixed(2)} USDC`;
            document.getElementById('withdrawModal').classList.add('open');
        }

        function setMaxWithdraw() {
            if (!currentSummary) return;
            document.getElementById('withdrawAmount').value = currentSummary.perp.withdrawable_usdc;
        }

        function openSpotToPerpModal() {
            if (!currentSummary) return;
            document.getElementById('s2pAmount').value = currentSummary.spot.usdc_available.toFixed(2);
            document.getElementById('spotToPerpModal').classList.add('open');
        }

        function closeModals() {
            document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('open'));
        }

        async function executeWithdraw() {
            const pk = document.getElementById('withdrawKey').value.trim();
            const dest = document.getElementById('withdrawDest').value.trim();
            const amount = parseFloat(document.getElementById('withdrawAmount').value);

            if (!pk) { alert('Please enter your private key'); return; }
            if (!dest) { alert('Please enter a destination address'); return; }
            if (isNaN(amount) || amount <= 1.0) { alert('Amount must be greater than 1.0 USDC (bridge network fee)'); return; }

            const btn = document.getElementById('btnExecuteWithdraw');
            btn.disabled = true;
            btn.innerText = 'Signing & Submitting...';

            try {
                const res = await fetch('/api/withdraw', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ private_key: pk, destination: dest, amount: amount })
                });
                const data = await res.json();
                closeModals();

                if (data.status === 'ok') {
                    showStatus(`Withdrawal of ${data.amount} USDC successfully submitted to Arbitrum bridge for ${data.destination}! Estimated arrival time: 3-5 minutes.`, 'success');
                    fetchSummary();
                } else {
                    showStatus('Withdrawal error: ' + data.message, 'error');
                }
            } catch (err) {
                showStatus('Network error: ' + err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.innerText = 'Confirm & Send Withdrawal';
            }
        }

        async function executeSpotToPerp() {
            const pk = document.getElementById('s2pKey').value.trim();
            const amount = parseFloat(document.getElementById('s2pAmount').value);
            if (!pk) { alert('Please enter your private key'); return; }

            try {
                const res = await fetch('/api/spot-to-perp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ private_key: pk, amount: amount })
                });
                const data = await res.json();
                closeModals();
                if (data.status === 'ok') {
                    showStatus(`Successfully transferred ${data.transferred_amount} USDC from Spot to Perp!`, 'success');
                    fetchSummary();
                } else {
                    showStatus('Error: ' + data.message, 'error');
                }
            } catch (err) {
                showStatus('Network error: ' + err.message, 'error');
            }
        }

        function showStatus(msg, type) {
            const el = document.getElementById('statusMessage');
            el.className = 'status-msg ' + type;
            el.innerText = msg;
            el.style.display = 'block';
            el.scrollIntoView({ behavior: 'smooth' });
        }

        function hideStatus() {
            document.getElementById('statusMessage').style.display = 'none';
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/summary", methods=["GET"])
def api_summary():
    address = request.args.get("address", "").strip()
    if not is_valid_eth_address(address):
        return jsonify({"status": "err", "message": "Invalid 0x Ethereum address"}), 400
    try:
        client = HyperliquidClient(account_address=address)
        summary = client.get_account_summary()
        return jsonify({"status": "ok", "data": summary})
    except Exception as e:
        return jsonify({"status": "err", "message": str(e)}), 500


@app.route("/api/withdraw", methods=["POST"])
def api_withdraw():
    data = request.json or {}
    pk = data.get("private_key", "").strip()
    dest = data.get("destination", "").strip()
    amount = data.get("amount")

    if not pk or not dest or amount is None:
        return jsonify({"status": "err", "message": "Missing required fields (private_key, destination, amount)"}), 400

    try:
        amount = float(amount)
        client = HyperliquidClient(private_key=pk)
        res = client.withdraw_to_arbitrum(amount=amount, destination_address=dest)
        if res.get("status") == "ok":
            return jsonify(res)
        return jsonify(res), 400
    except Exception as e:
        return jsonify({"status": "err", "message": str(e)}), 500


@app.route("/api/spot-to-perp", methods=["POST"])
def api_spot_to_perp():
    data = request.json or {}
    pk = data.get("private_key", "").strip()
    amount = data.get("amount")

    if not pk:
        return jsonify({"status": "err", "message": "Missing private key"}), 400

    try:
        amount_val = float(amount) if amount is not None else None
        client = HyperliquidClient(private_key=pk)
        res = client.transfer_spot_usdc_to_perp(amount=amount_val)
        if res.get("status") == "ok":
            return jsonify(res)
        return jsonify(res), 400
    except Exception as e:
        return jsonify({"status": "err", "message": str(e)}), 500


def main():
    parser = argparse.ArgumentParser(description="Hyperliquid Web GUI")
    parser.add_argument("--port", type=int, default=5000, help="Port for local server (default: 5000)")
    parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    args = parser.parse_args()

    print(f"\n[+] Local Web server running on http://{args.host}:{args.port}")
    print("[+] Open your browser to access the recovery dashboard.")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
