#!/usr/bin/env python3
"""
enhanced_t.py – Concurrent GitHub token checker with CLI, rich output, and flexible formatting.

Usage:
    python enhanced_t.py [OPTIONS]

Options:
    --tokens-file TEXT        Path to tokens file (default: tokens.txt)
    --api-url TEXT            GitHub API URL (default: https://api.github.com/user)
    --delay FLOAT             Delay between requests per worker (default: 1.0)
    -w, --workers INT         Number of concurrent workers (default: 2)
    --retries INT             Number of retries for failed requests (default: 2)
    --min-scopes TEXT         Comma-separated required scopes (e.g. "repo,read:org")
    --mask/--full-token       Mask tokens in output or show full (default: full-token)
    --output-format TEXT      text, json, csv (default: text)
    --output-file TEXT        Path to write JSON/CSV output
    --valid-output-file TEXT  Write valid tokens (one per line)
    --log-file TEXT           Path to write detailed logs
    -v, --verbose             Verbose console logging
    -h, --help                Show help message and exit
"""
import sys
import time
import json
import csv
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

import click
import requests
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from requests.adapters import HTTPAdapter, Retry

# Setup console and logger
def setup_logging(log_file: Optional[str], verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler(sys.stderr)]
    if log_file:
        fh = logging.FileHandler(log_file)
        handlers.append(fh)
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s", handlers=handlers)
    return logging.getLogger(__name__)

console = Console()


def make_session(retries: int) -> requests.Session:
    session = requests.Session()
    adapter = HTTPAdapter(
        max_retries=Retry(total=retries, backoff_factor=0.5,
                           status_forcelist=[429, 500, 502, 503, 504], raise_on_status=False)
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def check_token(session: requests.Session, api_url: str, token: str, delay: float,
                min_scopes: List[str], mask: bool) -> Dict:
    token = token.strip()
    display_token = token if not mask else f"{token[:6]}…"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    try:
        resp = session.get(api_url, headers=headers, timeout=10)
        # Rate-limit handling
        if resp.status_code == 403 and "X-RateLimit-Remaining" in resp.headers:
            remaining = int(resp.headers.get("X-RateLimit-Remaining", 0))
            reset = int(resp.headers.get("X-RateLimit-Reset", 0))
            if remaining == 0:
                wait = max(0, reset - int(time.time()))
                console.print(f"[yellow]Rate limit reached. Sleeping {wait}s...[/]")
                time.sleep(wait + 1)
                resp = session.get(api_url, headers=headers, timeout=10)
        time.sleep(delay)

        if resp.status_code == 200:
            data = resp.json()
            scopes = [s.strip() for s in resp.headers.get("X-OAuth-Scopes", "").split(',') if s.strip()]
            if min_scopes and not set(min_scopes).issubset(scopes):
                msg = f"Insufficient scopes: {','.join(scopes) or 'none'}"
                valid = False
            else:
                msg = None
                valid = True
            return {"token": display_token, "full_token": token, "valid": valid,
                    "login": data.get("login"), "id": data.get("id"),
                    "scopes": ",".join(scopes) or 'none', "message": msg}
        elif resp.status_code == 401:
            return {"token": display_token, "full_token": token, "valid": False,
                    "login": None, "id": None, "scopes": None,
                    "message": "Unauthorized / invalid"}
        else:
            return {"token": display_token, "full_token": token, "valid": False,
                    "login": None, "id": None, "scopes": None,
                    "message": f"HTTP {resp.status_code}: {resp.text[:80]}"}
    except Exception as e:
        return {"token": display_token, "full_token": token, "valid": False,
                "login": None, "id": None, "scopes": None,
                "message": f"Error: {e}"}

@click.command()
@click.option('--tokens-file', default='tokens.txt', type=click.Path(exists=True),
              help='File with one token per line.')
@click.option('--api-url', default='https://api.github.com/user', show_default=True,
              help='GitHub API URL to check tokens against.')
@click.option('--delay', default=1.0, show_default=True,
              help='Delay (s) between requests per worker.', type=float)
@click.option('-w', '--workers', default=2, show_default=True,
              help='Number of concurrent workers.', type=int)
@click.option('--retries', default=2, show_default=True,
              help='Retry count for HTTP errors.', type=int)
@click.option('--min-scopes', default=None,
              help='Comma-separated required scopes.')
@click.option('--mask/--full-token', default=False,
              help='Mask tokens in output or display full tokens.')
@click.option('--output-format', default='text', show_default=True,
              type=click.Choice(['text','json','csv']),
              help='Output format.')
@click.option('--output-file', default=None, type=click.Path(),
              help='Path to write JSON/CSV output.')
@click.option('--valid-output-file', default=None, type=click.Path(),
              help='File path to write valid tokens (one per line).')
@click.option('--log-file', default=None, type=click.Path(),
              help='Log file path for detailed logs.')
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose logging.')
def main(tokens_file, api_url, delay, workers, retries, min_scopes,
         mask, output_format, output_file, valid_output_file, log_file, verbose):
    logger = setup_logging(log_file, verbose)
    scopes = [s.strip() for s in min_scopes.split(',')] if min_scopes else []

    tokens = [t.strip() for t in Path(tokens_file).read_text().splitlines() if t.strip()]
    if not tokens:
        console.print(f"[red]Error:[/] {tokens_file} is empty.", style="bold red")
        sys.exit(1)
    console.print(f"[cyan]Checking {len(tokens)} tokens with {workers} workers...[/]")

    session = make_session(retries)
    results = []
    try:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(),
                      TimeElapsedColumn()) as progress:
            task = progress.add_task("Validating tokens", total=len(tokens))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(check_token, session, api_url, tok, delay, scopes, mask): tok for tok in tokens}
                for future in as_completed(futures):
                    res = future.result()
                    results.append(res)
                    progress.update(task, advance=1)
                    if verbose and res['valid']:
                        logger.info(f"Valid: {res['full_token']} -> user={res['login']}")
    except KeyboardInterrupt:
        console.print("[red]Interrupted. Exiting...[/]")
        sys.exit(1)

    valid = [r for r in results if r['valid']]
    invalid = [r for r in results if not r['valid']]

    # Write valid tokens separately if requested
    if valid_output_file and valid:
        Path(valid_output_file).write_text("\n".join(r['full_token'] for r in valid))
        console.print(f"[green]Wrote {len(valid)} valid tokens to {valid_output_file}[/]")

    # Display results
    if output_format == 'text':
        table = Table(show_header=True, header_style="bold green")
        table.add_column("Token", style="dim")
        table.add_column("User")
        table.add_column("ID", justify="right")
        table.add_column("Scopes")
        for r in valid:
            table.add_row(r['token'], r['login'], str(r['id']), r['scopes'])
        console.print(table)
        console.print(f"\nTotal: {len(results)}, Valid: {len(valid)}, Invalid: {len(invalid)}")
        if invalid:
            console.print(f"[yellow]Omitted {len(invalid)} invalid tokens.[/]")
    else:
        data = valid if output_format == 'csv' else results
        if output_file:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                if output_format == 'json':
                    json.dump(results, f, indent=2)
                else:
                    writer = csv.DictWriter(f, fieldnames=results[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
            console.print(f"[green]Wrote output to {output_file}[/]")
        else:
            if output_format == 'json':
                console.print_json(results)
            else:
                writer = csv.DictWriter(sys.stdout, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(data)

if __name__ == '__main__':
    main()
