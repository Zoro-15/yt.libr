"""
Command-Line Interface for YouTube Library Scraper.
Provides doctor diagnostics, auth testing, scraping, merging, validation, and statistics.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from scraper import __version__
from scraper.auth import test_authentication, validate_cookie_file
from scraper.config import ScraperConfig
from scraper.extract import run_merge_pipeline, scrape_source
from scraper.stats import compute_library_stats
from scraper.utils import (
    CHECK_MARK,
    CROSS_MARK,
    SEP_LINE,
    WARN_MARK,
    bold,
    check_directory_writable,
    check_python_version,
    check_ytdlp_installed,
    cyan,
    dim,
    green,
    is_termux,
    red,
    yellow,
)
from scraper.validate import validate_videos_json


def run_doctor(config: ScraperConfig) -> int:
    """Run environment, dependency, and configuration diagnostics."""
    print(bold("\n=================================================="))
    print(bold(" YouTube Library Scraper — Doctor Diagnostics"))
    print(bold("=================================================="))

    all_ok = True

    # 1. Environment
    termux_env = is_termux()
    env_name = "Android / Termux" if termux_env else f"Standard OS ({sys.platform})"
    print(f"Platform:              {green(env_name)}")

    # 2. Python
    py_ok, py_ver = check_python_version()
    if py_ok:
        print(f"Python Version:        {green(f'{py_ver} (>= 3.8)')}")
    else:
        print(f"Python Version:        {red(f'{py_ver} (Python 3.8+ required)')}")
        all_ok = False

    # 3. yt-dlp
    ytdlp_ok, ytdlp_ver = check_ytdlp_installed()
    if ytdlp_ok:
        print(f"yt-dlp:                {green(f'Installed ({ytdlp_ver})')}")
    else:
        print(f"yt-dlp:                {red('NOT INSTALLED')} (Run: pip install -r requirements.txt)")
        all_ok = False

    # 4. Storage & Output Directories
    data_ok, data_msg = check_directory_writable(config.data_dir)
    if data_ok:
        print(f"Storage / Output:      {green('Writable')} ({config.data_dir})")
    else:
        print(f"Storage / Output:      {red('ERROR')} ({data_msg})")
        all_ok = False

    # 5. Cookie Authentication / Browser
    if config.cookies_from_browser:
        print(f"Cookies Source:        {green(f'Browser ({config.cookies_from_browser})')}")
    else:
        cookie_res = validate_cookie_file(config.cookies_file)
        if cookie_res.exists:
            if cookie_res.is_netscape_format:
                if not cookie_res.missing_critical:
                    print(f"Cookies File:          {green('Found & Valid Netscape format')} ({config.cookies_file})")
                    print(f"Session Cookies:       {green(f'{len(cookie_res.found_cookies)} tokens detected')}")
                else:
                    print(f"Cookies File:          {yellow('Found with warnings')} ({config.cookies_file})")
                    print(f"                       {yellow(cookie_res.message)}")
            else:
                print(f"Cookies File:          {red('Invalid format')} ({config.cookies_file})")
                print(f"                       {red(cookie_res.message)}")
                all_ok = False
        else:
            print(f"Cookies File:          {yellow('NOT FOUND')} (Expected at: {config.cookies_file})")
            print(f"                       {dim('Required for private Watch Later & Liked Videos access on Termux.')}")
            print(f"                       {dim('On desktop/Antigravity terminal, you can also use --cookies-from-browser chrome')}")
            all_ok = False

    print(SEP_LINE)
    if all_ok:
        print(f"Overall Status:        {green(bold('READY TO SCRAPE'))}")
        print("\nRecommended next step:")
        print(cyan("  yt-library auth test") + " or " + cyan("py -m scraper auth test"))
        print(bold("==================================================\n"))
        return 0
    else:
        print(f"Overall Status:        {yellow(bold('ATTENTION NEEDED'))}")
        print("\nPlease address any red/yellow items above before scraping.")
        print(bold("==================================================\n"))
        return 1


def run_auth_test(config: ScraperConfig) -> int:
    """Test YouTube authentication against private playlists."""
    print(bold("\n--- Testing YouTube Authentication ---"))
    if config.cookies_from_browser:
        print(f"Using browser cookies from: {cyan(config.cookies_from_browser)}")
    else:
        print(f"Using cookies from: {cyan(str(config.cookies_file))}")
    print("Checking access to private Watch Later playlist...")

    success, message = test_authentication(config)
    if success:
        print(green(f"\n{CHECK_MARK} {message}"))
        print(green("You can now run test extractions with '--limit 20'."))
        return 0
    else:
        print(red(f"\n{CROSS_MARK} {message}"))
        return 1


def main(args: Optional[list] = None) -> int:
    # Common shared options for both root parser and subcommands
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--config", dest="config_path", help="Path to custom config.json")
    common_parser.add_argument("--cookies", dest="cookies_path", help="Path to custom cookies.txt")
    common_parser.add_argument(
        "--cookies-from-browser",
        dest="cookies_from_browser",
        help="Extract cookies directly from a desktop browser (chrome, firefox, edge, brave, etc.)",
    )
    common_parser.add_argument("--data-dir", dest="data_dir", help="Path to data output directory")
    common_parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    parser = argparse.ArgumentParser(
        prog="yt-library",
        description="Android Termux YouTube Library Scraper — extracts metadata from Watch Later and Liked Videos.",
        parents=[common_parser],
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: doctor
    subparsers.add_parser("doctor", parents=[common_parser], help="Check installation, environment, and cookie configuration")

    # Command: auth
    auth_parser = subparsers.add_parser("auth", parents=[common_parser], help="Authentication tools")
    auth_sub = auth_parser.add_subparsers(dest="auth_command", help="Auth subcommands")
    auth_sub.add_parser("test", parents=[common_parser], help="Verify private YouTube session access without downloading")

    # Command: scrape
    scrape_parser = subparsers.add_parser("scrape", parents=[common_parser], help="Extract metadata from YouTube")
    scrape_sub = scrape_parser.add_subparsers(dest="scrape_source", help="Extraction targets")

    # scrape watch-later
    wl_p = scrape_sub.add_parser("watch-later", parents=[common_parser], help="Scrape Watch Later playlist")
    wl_p.add_argument("--limit", type=int, default=None, help="Limit number of videos to extract")
    wl_p.add_argument("--dry-run", action="store_true", help="Extract without saving to disk")

    # scrape liked
    ll_p = scrape_sub.add_parser("liked", parents=[common_parser], help="Scrape Liked Videos playlist")
    ll_p.add_argument("--limit", type=int, default=None, help="Limit number of videos to extract")
    ll_p.add_argument("--dry-run", action="store_true", help="Extract without saving to disk")

    # scrape all
    all_p = scrape_sub.add_parser("all", parents=[common_parser], help="Scrape both Watch Later and Liked Videos")
    all_p.add_argument("--limit", type=int, default=None, help="Limit number of videos per source")
    all_p.add_argument("--dry-run", action="store_true", help="Extract without saving to disk")
    all_p.add_argument("--no-merge", action="store_true", help="Skip automatic merge after scraping")

    # Command: merge
    subparsers.add_parser("merge", parents=[common_parser], help="Merge raw watch_later.json and liked.json into videos.json")

    # Command: validate
    subparsers.add_parser("validate", parents=[common_parser], help="Validate videos.json schema and integrity")

    # Command: stats
    subparsers.add_parser("stats", parents=[common_parser], help="Show video library statistics and health report")


    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        return 0

    # Load configuration
    config = ScraperConfig.load(
        config_path=parsed_args.config_path,
        cookies_path_override=parsed_args.cookies_path,
        cookies_from_browser_override=parsed_args.cookies_from_browser,
        data_dir_override=parsed_args.data_dir,
    )


    if parsed_args.command == "doctor":
        return run_doctor(config)

    elif parsed_args.command == "auth":
        if parsed_args.auth_command == "test":
            return run_auth_test(config)
        else:
            auth_parser.print_help()
            return 0

    elif parsed_args.command == "scrape":
        if not parsed_args.scrape_source:
            scrape_parser.print_help()
            return 0

        target = parsed_args.scrape_source
        if target == "watch-later":
            scrape_source("watch_later", config, limit=parsed_args.limit, dry_run=parsed_args.dry_run)
            return 0
        elif target == "liked":
            scrape_source("liked", config, limit=parsed_args.limit, dry_run=parsed_args.dry_run)
            return 0
        elif target == "all":
            print(bold("=== Scraping All Sources (Watch Later & Liked Videos) ==="))
            scrape_source("watch_later", config, limit=parsed_args.limit, dry_run=parsed_args.dry_run)
            scrape_source("liked", config, limit=parsed_args.limit, dry_run=parsed_args.dry_run)

            if not parsed_args.dry_run and not parsed_args.no_merge:
                run_merge_pipeline(config)
            return 0

    elif parsed_args.command == "merge":
        run_merge_pipeline(config)
        return 0

    elif parsed_args.command == "validate":
        report = validate_videos_json(config.videos_processed_path)
        report.print_summary()
        return 0 if report.is_valid else 1

    elif parsed_args.command == "stats":
        stats = compute_library_stats(config.videos_processed_path)
        if stats:
            stats.print_report()
            return 0
        else:
            print(red(f"No processed library found at: {config.videos_processed_path}"))
            print("Run 'yt-library scrape all' or 'yt-library merge' first.")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
