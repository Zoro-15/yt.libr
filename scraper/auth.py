"""
Authentication and Cookie Management module.
Handles Netscape cookies.txt inspection and YouTube session testing.
CRITICAL SECURITY: Never prints, transmits, or exposes sensitive cookie contents.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import time
from typing import Dict, List, Optional, Tuple

from scraper.config import ScraperConfig
from scraper.utils import bold, green, red, yellow, cyan, dim


# Essential YouTube session cookie keys
ESSENTIAL_COOKIE_KEYS = {
    "LOGIN_INFO",
    "SID",
    "HSID",
    "SSID",
    "SAPISID",
    "__Secure-1PSID",
    "__Secure-3PSID",
}


@dataclass
class CookieInfo:
    domain: str
    name: str
    expires: Optional[int]
    is_expired: bool


@dataclass
class CookieValidationResult:
    exists: bool
    is_readable: bool
    is_netscape_format: bool
    found_cookies: List[str]
    missing_critical: List[str]
    expired_cookies: List[str]
    total_entries: int
    message: str


def validate_cookie_file(cookie_path: Path) -> CookieValidationResult:
    """
    Inspects a cookies.txt file for valid Netscape format and YouTube session tokens
    WITHOUT exposing or printing sensitive cookie values.
    """
    if not cookie_path.exists():
        return CookieValidationResult(
            exists=False,
            is_readable=False,
            is_netscape_format=False,
            found_cookies=[],
            missing_critical=list(ESSENTIAL_COOKIE_KEYS),
            expired_cookies=[],
            total_entries=0,
            message=f"Cookie file not found at: {cookie_path}",
        )

    if not cookie_path.is_file():
        return CookieValidationResult(
            exists=True,
            is_readable=False,
            is_netscape_format=False,
            found_cookies=[],
            missing_critical=list(ESSENTIAL_COOKIE_KEYS),
            expired_cookies=[],
            total_entries=0,
            message=f"Specified path is not a regular file: {cookie_path}",
        )

    found_names = set()
    expired_names = []
    total_valid_lines = 0
    now_ts = int(time.time())

    try:
        with open(cookie_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line_str = line.strip()
                if not line_str or line_str.startswith("#"):
                    continue

                parts = line_str.split("\t")
                if len(parts) >= 7:
                    total_valid_lines += 1
                    domain = parts[0].lower()
                    expires_str = parts[4]
                    name = parts[5]

                    if "youtube.com" in domain or "google.com" in domain:
                        found_names.add(name)
                        try:
                            exp_ts = int(expires_str)
                            if 0 < exp_ts < now_ts:
                                expired_names.append(name)
                        except ValueError:
                            pass
                elif len(parts) >= 6:
                    total_valid_lines += 1
    except Exception as e:
        return CookieValidationResult(
            exists=True,
            is_readable=False,
            is_netscape_format=False,
            found_cookies=[],
            missing_critical=list(ESSENTIAL_COOKIE_KEYS),
            expired_cookies=[],
            total_entries=0,
            message=f"Failed to read cookie file: {e}",
        )

    is_netscape = total_valid_lines > 0
    missing_critical = [k for k in ("LOGIN_INFO", "SID") if k not in found_names]

    if not is_netscape:
        msg = "File exists but does not appear to be in standard Netscape format (tab-separated)."
    elif missing_critical:
        msg = f"Cookie file found with {total_valid_lines} entries, but missing key session token(s): {', '.join(missing_critical)}"
    else:
        msg = f"Valid Netscape cookie file with {total_valid_lines} entries."

    return CookieValidationResult(
        exists=True,
        is_readable=True,
        is_netscape_format=is_netscape,
        found_cookies=sorted(list(found_names)),
        missing_critical=missing_critical,
        expired_cookies=expired_names,
        total_entries=total_valid_lines,
        message=msg,
    )


def test_authentication(config: ScraperConfig) -> Tuple[bool, str]:
    """
    Test authenticated YouTube session using yt-dlp by querying 1 item from
    Watch Later playlist without downloading any video.
    """
    try:
        import yt_dlp
    except ImportError:
        return False, "yt-dlp is not installed. Run 'pip install -r requirements.txt' or 'python -m pip install yt-dlp'."

    ydl_opts = {
        "skip_download": True,
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
        "playlist_items": "1",
        "ignoreerrors": True,
    }

    if config.cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (config.cookies_from_browser,)
    else:
        validation = validate_cookie_file(config.cookies_file)
        if not validation.exists:
            return False, f"Cookie file missing at '{config.cookies_file}'.\nPlease export cookies.txt from your browser (e.g. via Kiwi Browser or Firefox extension) and place it here, or use --cookies-from-browser on desktop."

        if not validation.is_netscape_format:
            return False, f"Cookie file at '{config.cookies_file}' is not in valid Netscape format.\nEnsure your extension exports in 'Netscape HTTP Cookie File' format."

        ydl_opts["cookiefile"] = str(config.cookies_file)

    test_url = "https://www.youtube.com/playlist?list=WL"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(test_url, download=False)
            if info is None:
                return False, "Extraction returned empty response. Your session cookies may have expired or Watch Later is inaccessible."

            entries = list(info.get("entries", []))
            title = info.get("title", "Watch later")
            
            return True, f"Authentication successful!\nSuccessfully accessed private playlist: '{title}' ({len(entries)} test item verified)."

    except Exception as e:
        err_msg = str(e)
        if "Private playlist" in err_msg or "Sign in" in err_msg:
            return False, f"Authentication rejected by YouTube: {err_msg}\nYour cookies may be expired or missing login session data."
        return False, f"Authentication test failed: {err_msg}"

