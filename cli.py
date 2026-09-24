#!/usr/bin/env python3
"""
Hyperliquid Direct DeFi Rescue & Withdrawer CLI
Command-line tool to inspect and withdraw funds from Hyperliquid L1 directly to Arbitrum One,
bypassing web frontend geoblocking and Cloudflare restrictions.
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

import re
import getpass
import argparse
from typing import Optional

# Load environment variables from .env (with standard library fallback if python-dotenv is missing)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    if os.path.exists(".env"):
        try:
            with open(".env", "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip().strip("'\""), v.strip().strip("'\""))
        except Exception:
            pass

# Import rich with pure standard-library fallback
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich import print as rprint
    console = Console()
except ImportError:
    class FallbackConsole:
        def print(self, *args, **kwargs):
            clean_args = []
            for a in args:
                if isinstance(a, str):
                    cleaned = re.sub(r"\[/?[a-zA-Z0-9_\s#]+\]", "", a)
                    clean_args.append(cleaned)
                else:
                    clean_args.append(str(a))
            print(*clean_args)

        def status(self, status_msg):
            class StatusContext:
                def __enter__(self):
                    cleaned = re.sub(r"\[/?[a-zA-Z0-9_\s#]+\]", "", str(status_msg))
                    print(f">> {cleaned}")
                    return self
                def __exit__(self, *exc):
                    pass
            return StatusContext()

    class FallbackPanel:
        def __init__(self, renderable, title=None, border_style=None):
            self.text = str(renderable)
            self.title = title
        def __str__(self):
            cleaned = re.sub(r"\[/?[a-zA-Z0-9_\s#]+\]", "", self.text)
            header = f"\n=== {self.title} ===" if self.title else "\n=========================================="
            return f"{header}\n{cleaned}\n=========================================="

    class FallbackTable:
        def __init__(self, title=None, header_style=None):
            self.title = title
            self.columns = []
            self.rows = []
        def add_column(self, name, *args, **kwargs):
            self.columns.append(name)
        def add_row(self, *row_items):
            clean_row = [re.sub(r"\[/?[a-zA-Z0-9_\s#]+\]", "", str(i)) for i in row_items]
            self.rows.append(clean_row)
        def __str__(self):
            lines = []
            if self.title:
                lines.append(f"\n--- {self.title} ---")
            if self.columns:
                lines.append(" | ".join(self.columns))
                lines.append("-" * max(40, len(" | ".join(self.columns))))
            for r in self.rows:
                lines.append(" | ".join(r))
            return "\n".join(lines)

    class FallbackPrompt:
        @staticmethod
        def ask(prompt_text, default=None, choices=None):
            cleaned = re.sub(r"\[/?[a-zA-Z0-9_\s#]+\]", "", str(prompt_text))
            suffix = f" [{default}]" if default else ""
            if choices:
                suffix += f" ({'/'.join(choices)})"
            val = input(f"{cleaned}{suffix}: ").strip()
            if not val and default is not None:
                return default
            return val

    class FallbackConfirm:
        @staticmethod
        def ask(prompt_text, default=True):
            cleaned = re.sub(r"\[/?[a-zA-Z0-9_\s#]+\]", "", str(prompt_text))
            suffix = " [Y/n]: " if default else " [y/N]: "
            res = input(f"{cleaned}{suffix}").strip().lower()
            if not res:
                return default
            return res in ["y", "yes"]

    def rprint(*args, **kwargs):
        clean_args = [re.sub(r"\[/?[a-zA-Z0-9_\s#]+\]", "", str(a)) if isinstance(a, str) else str(a) for a in args]
        print(*clean_args)

    Console = FallbackConsole
    Panel = FallbackPanel
    Table = FallbackTable
    Prompt = FallbackPrompt
    Confirm = FallbackConfirm
    console = FallbackConsole()

from core import HyperliquidClient, is_valid_eth_address

DONATION_ADDRESS = "0xD8BFC83AB8601540A2626260A0628198b9053AE7"


def print_banner():
    banner_text = (
        "[bold cyan]HYPERLIQUID DIRECT DEFI WITHDRAWER[/bold cyan]\n"
        "[dim]Bypasses web GUI geoblocking by connecting directly to L1 validator nodes and the Arbitrum Bridge.[/dim]"
    )
    console.print(Panel(banner_text, border_style="cyan"))


def get_private_key(args_key: Optional[str] = None) -> str:
    """Retrieve private key from CLI argument, environment variable, or masked prompt."""
    if args_key and args_key.strip():
        return args_key.strip()

    env_key = os.getenv("HL_PRIVATE_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    console.print("\n[yellow]Enter the Ethereum Private Key associated with your Hyperliquid account:[/yellow]")
    console.print("[dim](Input is masked for your security. Press Enter when done)[/dim]")
    pk = getpass.getpass("Private Key: ").strip()
    if not pk:
        console.print("[red]Error: No private key provided.[/red]")
        sys.exit(1)
    return pk


def display_account_overview(summary: dict):
    """Print complete summary tables of account state and balances."""
    addr = summary["address"]
    perp = summary["perp"]
    spot = summary["spot"]
    orders = summary["open_orders"]
    staking = summary["staking"]

    console.print(f"\n[bold green]Account:[/bold green] [cyan]{addr}[/cyan]\n")

    # Primary Balance Overview Table
    bal_table = Table(title="Account Overview & Liquidity", header_style="bold magenta")
    bal_table.add_column("Category", style="cyan")
    bal_table.add_column("Value", justify="right", style="bold green")
    bal_table.add_column("Notes / Action", style="dim")

    bal_table.add_row(
        "Perp Account Value",
        f"${perp['account_value']:,.2f}",
        "Total margin + unrealized PnL",
    )
    bal_table.add_row(
        "Perp Withdrawable (Bridge)",
        f"{perp['withdrawable_usdc']:,.2f} USDC",
        "[bold yellow]Ready to withdraw to Arbitrum One[/bold yellow]",
    )
    bal_table.add_row(
        "Perp Margin Used",
        f"${perp['total_margin_used']:,.2f}",
        "Margin locked in active perpetual positions",
    )
    bal_table.add_row(
        "Spot USDC Available",
        f"{spot['usdc_available']:,.2f} USDC",
        "Transferable to Perp to enable withdrawal",
    )
    bal_table.add_row(
        "[bold]Total Available USDC[/bold]",
        f"[bold]{summary['total_withdrawable_usdc']:,.2f} USDC[/bold]",
        "Sum of Perp Withdrawable + Spot USDC",
    )
    console.print(bal_table)

    # Open Positions Table (if any)
    positions = perp["positions"]
    if positions:
        pos_table = Table(title="Open Perpetual Positions (Locked Margin)", header_style="bold red")
        pos_table.add_column("Asset", style="bold")
        pos_table.add_column("Size", justify="right")
        pos_table.add_column("Entry Price", justify="right")
        pos_table.add_column("Position Value", justify="right")
        pos_table.add_column("Unrealized PnL", justify="right")
        pos_table.add_column("Margin Used", justify="right")

        for pos in positions:
            pnl = pos["unrealized_pnl"]
            pnl_str = f"[green]+${pnl:.2f}[/green]" if pnl >= 0 else f"[red]-${abs(pnl):.2f}[/red]"
            pos_table.add_row(
                pos["coin"],
                f"{pos['size']}",
                f"${pos['entry_px']:,.2f}",
                f"${pos['position_value']:,.2f}",
                pnl_str,
                f"${pos['margin_used']:,.2f}",
            )
        console.print("\n", pos_table)
        console.print("[dim yellow]* Tip: If you want to withdraw all capital, close these positions first.[/dim yellow]")
    else:
        console.print("\n[dim green]No open perpetual positions (all margin is free and withdrawable).[/dim green]")

    # Open Orders Table (if any)
    if orders:
        ord_table = Table(title="Open Orders (Locked Capital/Margin)", header_style="bold yellow")
        ord_table.add_column("OID", style="dim")
        ord_table.add_column("Asset", style="bold")
        ord_table.add_column("Type", style="cyan")
        ord_table.add_column("Side", justify="center")
        ord_table.add_column("Size", justify="right")
        ord_table.add_column("Limit Price", justify="right")

        for o in orders:
            side_str = f"[green]{o['side']}[/green]" if o["side"] == "BUY" else f"[red]{o['side']}[/red]"
            ord_table.add_row(
                str(o["oid"]),
                o["coin"],
                o["order_type"],
                side_str,
                f"{o['sz']}",
                f"${o['limit_px']:,.2f}",
            )
        console.print("\n", ord_table)
        console.print("[dim yellow]* Tip: Cancel open orders to free up locked capital/margin.[/dim yellow]")

    # Spot Tokens Table
    spot_tokens = [b for b in spot["balances"] if b["coin"] != "USDC" and (b["total"] > 0 or b["hold"] > 0)]
    if spot_tokens:
        spot_table = Table(title="Other Spot Tokens on Hyperliquid L1", header_style="bold blue")
        spot_table.add_column("Token", style="bold")
        spot_table.add_column("Available", justify="right")
        spot_table.add_column("In Orders (Hold)", justify="right")
        spot_table.add_column("Total", justify="right")

        for t in spot_tokens:
            spot_table.add_row(
                t["coin"],
                f"{t['available']:,.4f}",
                f"{t['hold']:,.4f}",
                f"{t['total']:,.4f}",
            )
        console.print("\n", spot_table)

    # Staking Information
    if staking["delegated"] > 0 or staking["total_pending_withdrawal"] > 0:
        console.print(
            f"\n[cyan]HYPE Staking:[/cyan] Delegated: [bold]{staking['delegated']}[/bold] | "
            f"Undelegating (pending withdrawal): [bold]{staking['total_pending_withdrawal']}[/bold]"
        )


def cmd_status(target_address: str):
    """Check account status in read-only mode using a public address."""
    if not is_valid_eth_address(target_address):
        console.print(f"[red]Invalid Ethereum address:[/red] {target_address}")
        return

    with console.status("[bold cyan]Querying Hyperliquid L1 nodes...[/bold cyan]"):
        client = HyperliquidClient(account_address=target_address)
        summary = client.get_account_summary()

    display_account_overview(summary)


def cmd_spot_to_perp(args):
    """Transfer USDC from Spot to Perpetual."""
    pk = get_private_key(args.key)
    client = HyperliquidClient(private_key=pk)

    with console.status("[cyan]Checking Spot USDC balance...[/cyan]"):
        summary = client.get_account_summary()

    avail = summary["spot"]["usdc_available"]
    console.print(f"\n[green]Available Spot USDC balance:[/green] [bold]{avail:.2f} USDC[/bold]")

    if avail <= 0:
        console.print("[yellow]No USDC found in Spot wallet to transfer.[/yellow]")
        return

    amount = avail
    if args.amount and args.amount.upper() != "MAX":
        try:
            amount = float(args.amount)
        except ValueError:
            console.print("[red]Invalid amount.[/red]")
            return

    if not Confirm.ask(f"Do you want to transfer [bold]{amount:.2f} USDC[/bold] from Spot to Perp?"):
        console.print("[dim]Operation cancelled.[/dim]")
        return

    with console.status("[bold cyan]Submitting internal transfer transaction...[/bold cyan]"):
        res = client.transfer_spot_usdc_to_perp(amount)

    if res.get("status") == "ok":
        console.print(f"[bold green]Operation completed successfully![/bold green] Transferred {res['transferred_amount']:.2f} USDC to Perp.")
    else:
        console.print(f"[red]Transfer error:[/red] {res.get('message')}")


def cmd_cancel_orders(args):
    """Cancel all open orders."""
    pk = get_private_key(args.key)
    client = HyperliquidClient(private_key=pk)

    with console.status("[cyan]Checking open orders...[/cyan]"):
        summary = client.get_account_summary()

    orders = summary["open_orders"]
    if not orders:
        console.print("[green]No open orders found to cancel.[/green]")
        return

    console.print(f"[yellow]Found {len(orders)} open orders.[/yellow]")
    if not Confirm.ask("Are you sure you want to cancel ALL open orders?"):
        console.print("[dim]Operation cancelled.[/dim]")
        return

    with console.status("[bold cyan]Cancelling orders on Hyperliquid L1...[/bold cyan]"):
        res = client.cancel_all_orders()

    console.print(f"[bold green]Successfully cancelled {res.get('cancelled_count')} orders![/bold green]")


def cmd_close_positions(args):
    """Close all open perpetual positions."""
    pk = get_private_key(args.key)
    client = HyperliquidClient(private_key=pk)

    with console.status("[cyan]Checking open positions...[/cyan]"):
        summary = client.get_account_summary()

    positions = summary["perp"]["positions"]
    if not positions:
        console.print("[green]No open positions found to close.[/green]")
        return

    console.print(f"[yellow]Found {len(positions)} open positions.[/yellow]")
    for p in positions:
        console.print(f" - {p['coin']}: size {p['size']}, margin ${p['margin_used']:.2f}")

    if not Confirm.ask("Are you sure you want to MARKET CLOSE all positions to free up margin?"):
        console.print("[dim]Operation cancelled.[/dim]")
        return

    with console.status("[bold cyan]Closing positions at market price...[/bold cyan]"):
        results = client.close_all_positions(slippage=0.05)

    for r in results:
        console.print(f"[green]Position {r['coin']} closed.[/green]")


def cmd_withdraw(args):
    """Execute withdrawal to Arbitrum One via the bridge."""
    pk = get_private_key(args.key)
    client = HyperliquidClient(private_key=pk)

    with console.status("[cyan]Fetching account state and withdrawable balance...[/cyan]"):
        summary = client.get_account_summary()

    withdrawable = summary["perp"]["withdrawable_usdc"]
    spot_usdc = summary["spot"]["usdc_available"]
    total_avail = summary["total_withdrawable_usdc"]

    console.print(f"\n[bold]Sender Account:[/bold] [cyan]{client.address}[/cyan]")
    console.print(f"[bold]Total Available USDC:[/bold] [bold green]{total_avail:.2f} USDC[/bold green] (Perp: {withdrawable:.2f}, Spot: {spot_usdc:.2f})")

    if total_avail <= 1.0:
        console.print(f"[red]Insufficient balance for withdrawal. Minimum withdrawal must exceed bridge fee (1.00 USDC). Total available: {total_avail:.2f} USDC[/red]")
        return

    # Destination address
    dest = args.dest
    if not dest:
        dest_input = Prompt.ask(
            "Destination Arbitrum One address",
            default=client.address,
        )
        dest = dest_input.strip()

    if not is_valid_eth_address(dest):
        console.print(f"[red]Invalid Ethereum/Arbitrum address:[/red] {dest}")
        return

    # Amount
    amount = total_avail
    if args.amount:
        if args.amount.upper() == "MAX":
            amount = total_avail
        else:
            try:
                amount = float(args.amount)
            except ValueError:
                console.print("[red]Invalid amount.[/red]")
                return
    else:
        amt_str = Prompt.ask("Amount of USDC to withdraw", default=f"{total_avail:.2f}")
        try:
            amount = float(amt_str)
        except ValueError:
            console.print("[red]Invalid amount.[/red]")
            return

    # Confirmation Panel
    confirm_panel = (
        f"[bold]Withdrawal Amount:[/bold] [bold green]{amount:.2f} USDC[/bold green]\n"
        f"[bold]Bridge Fee:[/bold] 1.00 USDC (deducted by Hyperliquid bridge)\n"
        f"[bold]You will receive on Arbitrum:[/bold] ~{max(0.0, amount - 1.0):.2f} USDC\n"
        f"[bold]Destination Address:[/bold] [bold cyan]{dest}[/bold cyan]\n"
        f"[bold]Destination Network:[/bold] Arbitrum One (L2)\n"
        f"[bold]Estimated Settlement Time:[/bold] 3 - 5 minutes\n"
    )
    console.print(Panel(confirm_panel, title="WITHDRAWAL CONFIRMATION", border_style="yellow"))

    if not Confirm.ask("[bold red]Proceed with signing and submitting withdrawal?[/bold red]"):
        console.print("[dim]Withdrawal cancelled.[/dim]")
        return

    with console.status("[bold cyan]Computing EIP-712 cryptographic signature and submitting to bridge...[/bold cyan]"):
        res = client.withdraw_to_arbitrum(amount=amount, destination_address=dest)

    if res.get("status") == "ok":
        success_msg = (
            f"[bold green]WITHDRAWAL SUBMITTED TO BRIDGE SUCCESSFULLY![/bold green]\n\n"
            f"Amount: [bold]{res['amount']:.2f} USDC[/bold]\n"
            f"Destination: [cyan]{res['destination']}[/cyan]\n"
            f"Network: Arbitrum One\n"
            f"Hyperliquid validators are processing the transfer to Arbitrum.\n"
            f"Funds will arrive in your wallet on Arbitrum One within ~3-5 minutes.\n\n"
            f"[dim]💖 Found this tool helpful? Tips/Donations: [cyan]{DONATION_ADDRESS}[/cyan][/dim]"
        )
        console.print(Panel(success_msg, border_style="green"))
    else:
        console.print(f"[bold red]Withdrawal error:[/bold red] {res.get('message')}")


def interactive_wizard():
    """Step-by-step guided recovery wizard for inspecting and withdrawing funds."""
    print_banner()
    console.print("\n[bold]Welcome to the Hyperliquid DeFi Rescue Wizard.[/bold]")
    console.print("This tool will guide you step-by-step through inspecting and withdrawing your assets.\n")

    pk = get_private_key()
    client = HyperliquidClient(private_key=pk)

    with console.status("[cyan]Reading account data from Hyperliquid L1 nodes...[/cyan]"):
        summary = client.get_account_summary()

    display_account_overview(summary)

    # Step 1: Check Open Orders
    if summary["open_orders"]:
        console.print("\n[yellow]Notice: You have open orders locking up capital/margin.[/yellow]")
        if Confirm.ask("Do you want to cancel all open orders to unlock capital?"):
            with console.status("[cyan]Cancelling orders...[/cyan]"):
                c_res = client.cancel_all_orders()
            console.print(f"[green]Cancelled {c_res.get('cancelled_count')} orders.[/green]")
            summary = client.get_account_summary()

    # Step 2: Check Open Positions
    if summary["perp"]["positions"]:
        console.print("\n[yellow]Notice: You have open Perpetual positions with locked margin.[/yellow]")
        if Confirm.ask("Do you want to market-close all open positions to convert everything into withdrawable USDC?"):
            with console.status("[cyan]Closing positions at market price...[/cyan]"):
                client.close_all_positions()
            console.print("[green]Positions closed.[/green]")
            summary = client.get_account_summary()

    # Step 3: Check Spot USDC
    spot_usdc = summary["spot"]["usdc_available"]
    if spot_usdc > 0:
        console.print(f"\n[cyan]You have {spot_usdc:.2f} USDC in your Spot wallet.[/cyan]")
        if Confirm.ask(f"Do you want to transfer {spot_usdc:.2f} USDC from Spot to Perp now?"):
            with console.status("[cyan]Transferring Spot -> Perp...[/cyan]"):
                t_res = client.transfer_spot_usdc_to_perp(spot_usdc)
            if t_res.get("status") == "ok":
                console.print(f"[green]Transferred {t_res.get('transferred_amount'):.2f} USDC to Perp balance![/green]")
                summary = client.get_account_summary()
            else:
                console.print(f"[yellow]Spot -> Perp notice:[/yellow] {t_res.get('message')}")
                console.print("[dim]Proceeding with Arbitrum One withdrawal...[/dim]")

    # Step 4: Bridge Withdrawal to Arbitrum
    total_avail = summary["total_withdrawable_usdc"]
    console.print(f"\n[bold green]Total USDC available for withdrawal to Arbitrum:[/bold green] [bold]{total_avail:.2f} USDC[/bold]")

    if total_avail <= 1.0:
        console.print("[yellow]Insufficient withdrawable USDC (minimum > 1.00 USDC to cover bridge network fee).[/yellow]")
        return

    if not Confirm.ask("Do you want to proceed with withdrawing to Arbitrum One now?"):
        console.print("[dim]Process completed without withdrawal.[/dim]")
        return

    dest = Prompt.ask("Destination Arbitrum One address (default: your address)", default=client.address).strip()
    if not is_valid_eth_address(dest):
        console.print("[red]Invalid address.[/red]")
        return

    amt_str = Prompt.ask("Amount to withdraw (USDC)", default=f"{total_avail:.2f}").strip()
    try:
        amt = float(amt_str)
    except ValueError:
        console.print("[red]Invalid amount.[/red]")
        return

    # Confirmation
    confirm_panel = (
        f"[bold]Amount:[/bold] {amt:.2f} USDC\n"
        f"[bold]Bridge Fee:[/bold] 1.00 USDC\n"
        f"[bold]Destination:[/bold] [cyan]{dest}[/cyan] (Arbitrum One)\n"
    )
    console.print(Panel(confirm_panel, title="WITHDRAWAL CONFIRMATION", border_style="yellow"))

    if Confirm.ask("[bold red]Confirm sending withdrawal to the bridge?[/bold red]"):
        with console.status("[cyan]Cryptographic signing and submitting to Hyperliquid bridge...[/cyan]"):
            res = client.withdraw_to_arbitrum(amount=amt, destination_address=dest)

        if res.get("status") == "ok":
            console.print(Panel(
                f"[bold green]WITHDRAWAL SENT TO ARBITRUM BRIDGE![/bold green]\n\n"
                f"Funds sent to: [cyan]{dest}[/cyan]\n"
                f"Amount: [bold]{amt:.2f} USDC[/bold]\n"
                f"Hyperliquid validators will finalize the transfer on Arbitrum within 3-5 minutes.\n\n"
                f"[dim]💖 Found this tool helpful? Tips/Donations: [cyan]{DONATION_ADDRESS}[/cyan][/dim]",
                border_style="green"
            ))
        else:
            console.print(f"[red]Error:[/red] {res.get('message')}")


def main_menu():
    """Main interactive terminal menu."""
    while True:
        print_banner()
        console.print("\n[bold]Choose an action:[/bold]")
        console.print("  [bold cyan]1)[/bold cyan] [bold]View Account Balance & Status[/bold] (Read-only, requires only 0x address)")
        console.print("  [bold cyan]2)[/bold cyan] [bold green]Guided Withdrawal Wizard (Recommended)[/bold green] (Inspect -> Close/Cancel -> Transfer -> Withdraw)")
        console.print("  [bold cyan]3)[/bold cyan] [bold]Withdraw USDC to Arbitrum One[/bold]")
        console.print("  [bold cyan]4)[/bold cyan] [bold]Transfer USDC from Spot to Perp[/bold]")
        console.print("  [bold cyan]5)[/bold cyan] [bold]Close all open Perp positions[/bold]")
        console.print("  [bold cyan]6)[/bold cyan] [bold]Cancel all open orders[/bold]")
        console.print("  [bold cyan]7)[/bold cyan] [bold]Launch Local Web GUI[/bold] (Browser graphical interface)")
        console.print("  [bold cyan]0)[/bold cyan] [dim]Exit[/dim]")

        choice = Prompt.ask("\nSelection", choices=["1", "2", "3", "4", "5", "6", "7", "0"], default="1")

        if choice == "0":
            console.print("[dim]Goodbye![/dim]")
            sys.exit(0)
        elif choice == "1":
            addr = Prompt.ask("Enter Ethereum address (0x...): ").strip()
            cmd_status(addr)
            Prompt.ask("\nPress Enter to return to menu...")
        elif choice == "2":
            interactive_wizard()
            Prompt.ask("\nPress Enter to return to menu...")
        elif choice == "3":
            args = argparse.Namespace(key=None, amount=None, dest=None)
            cmd_withdraw(args)
            Prompt.ask("\nPress Enter to return to menu...")
        elif choice == "4":
            args = argparse.Namespace(key=None, amount=None)
            cmd_spot_to_perp(args)
            Prompt.ask("\nPress Enter to return to menu...")
        elif choice == "5":
            args = argparse.Namespace(key=None)
            cmd_close_positions(args)
            Prompt.ask("\nPress Enter to return to menu...")
        elif choice == "6":
            args = argparse.Namespace(key=None)
            cmd_cancel_orders(args)
            Prompt.ask("\nPress Enter to return to menu...")
        elif choice == "7":
            console.print("[bold green]Starting local Web server at http://127.0.0.1:5000 ...[/bold green]")
            import subprocess
            subprocess.run([sys.executable, "web_app.py"])


def main():
    parser = argparse.ArgumentParser(
        description="Hyperliquid Direct DeFi Rescue & Withdrawer - Bypass GUI blocks and withdraw funds to Arbitrum One"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Command: status
    parser_status = subparsers.add_parser("status", help="View account status (Read-only)")
    parser_status.add_argument("address", help="Ethereum address (0x...)")

    # Command: wizard
    subparsers.add_parser("wizard", help="Start step-by-step guided recovery wizard")

    # Command: withdraw
    parser_withdraw = subparsers.add_parser("withdraw", help="Withdraw USDC to Arbitrum One")
    parser_withdraw.add_argument("--key", help="Private key (optional, prompted interactively if omitted)")
    parser_withdraw.add_argument("--amount", help="USDC amount or 'MAX'")
    parser_withdraw.add_argument("--dest", help="Recipient Arbitrum One address")

    # Command: spot-to-perp
    parser_s2p = subparsers.add_parser("spot-to-perp", help="Transfer USDC from Spot to Perp")
    parser_s2p.add_argument("--key", help="Private key")
    parser_s2p.add_argument("--amount", help="USDC amount or 'MAX'")

    # Command: close-positions
    parser_close = subparsers.add_parser("close-positions", help="Close all open positions at market price")
    parser_close.add_argument("--key", help="Private key")

    # Command: cancel-orders
    parser_cancel = subparsers.add_parser("cancel-orders", help="Cancel all open orders")
    parser_cancel.add_argument("--key", help="Private key")

    # Command: web
    parser_web = subparsers.add_parser("web", help="Launch local Web graphical user interface")
    parser_web.add_argument("--port", type=int, default=5000, help="Port for local server (default: 5000)")

    args = parser.parse_args()

    if not args.command:
        main_menu()
    elif args.command == "status":
        cmd_status(args.address)
    elif args.command == "wizard":
        interactive_wizard()
    elif args.command == "withdraw":
        cmd_withdraw(args)
    elif args.command == "spot-to-perp":
        cmd_spot_to_perp(args)
    elif args.command == "close-positions":
        cmd_close_positions(args)
    elif args.command == "cancel-orders":
        cmd_cancel_orders(args)
    elif args.command == "web":
        import subprocess
        subprocess.run([sys.executable, "web_app.py", "--port", str(args.port)])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[dim]Operation cancelled by user.[/dim]")
        sys.exit(0)
