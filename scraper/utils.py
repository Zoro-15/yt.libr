"""
Utility functions for YouTube Library Scraper.
Provides terminal formatting, progress display, environment detection, and timestamps.
"""

from datetime import datetime, timezone
import importlib.util
import os
from pathlib import Path
import sys
from typing import Optional, Tuple


# ==============================================================================
# Terminal Encoding & Colors
# ==============================================================================
# Ensure UTF-8 output on Windows consoles without crashing cp1252
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def can_encode(text: str) -> bool:
    try:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        text.encode(encoding)
        return True
    except Exception:
        return False


# Symbols with safe ASCII fallbacks
CHECK_MARK = "✓" if can_encode("✓") else "[OK]"
WARN_MARK = "⚠" if can_encode("⚠") else "[!]"
CROSS_MARK = "✗" if can_encode("✗") else "[X]"
SEP_LINE = "─" * 50 if can_encode("─") else "-" * 50
BAR_FULL = "█" if can_encode("█") else "#"
BAR_EMPTY = "░" if can_encode("░") else "-"



class Style:
    RESET = "\033[0m" if _USE_COLOR else ""
    BOLD = "\033[1m" if _USE_COLOR else ""
    DIM = "\033[2m" if _USE_COLOR else ""
    RED = "\033[31m" if _USE_COLOR else ""
    GREEN = "\033[32m" if _USE_COLOR else ""
    YELLOW = "\033[33m" if _USE_COLOR else ""
    BLUE = "\033[34m" if _USE_COLOR else ""
    CYAN = "\033[36m" if _USE_COLOR else ""
    MAGENTA = "\033[35m" if _USE_COLOR else ""


def green(text: str) -> str:
    return f"{Style.GREEN}{text}{Style.RESET}"


def red(text: str) -> str:
    return f"{Style.RED}{text}{Style.RESET}"


def yellow(text: str) -> str:
    return f"{Style.YELLOW}{text}{Style.RESET}"


def cyan(text: str) -> str:
    return f"{Style.CYAN}{text}{Style.RESET}"


def bold(text: str) -> str:
    return f"{Style.BOLD}{text}{Style.RESET}"


def dim(text: str) -> str:
    return f"{Style.DIM}{text}{Style.RESET}"


# ==============================================================================
# Timestamps
# ==============================================================================
def iso_now() -> str:
    """Return current UTC time in ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ==============================================================================
# Progress Bar
# ==============================================================================
def render_progress_bar(
    current: int,
    total: Optional[int],
    width: int = 24,
    success: int = 0,
    unavailable: int = 0,
    failed: int = 0,
) -> str:
    """
    Renders a clean progress bar string suitable for mobile and desktop CLI.
    Example: [████████████░░░░░░] 60% (1,200/2,000) [✓ 1,180 | ⚠ 20 | ✗ 0]
    """
    if total and total > 0:
        pct = min(1.0, max(0.0, current / total))
        filled = int(width * pct)
        bar = BAR_FULL * filled + BAR_EMPTY * (width - filled)
        pct_text = f"{int(pct * 100):3d}%"
        counts_text = f"({current:,}/{total:,})"
    else:
        bar = BAR_FULL * width
        pct_text = "   "
        counts_text = f"({current:,} items)"

    stats_part = f"[{green(f'{CHECK_MARK} {success:,}')} | {yellow(f'{WARN_MARK} {unavailable:,}')} | {red(f'{CROSS_MARK} {failed:,}')}]"
    return f"[{cyan(bar)}] {pct_text} {counts_text} {stats_part}"



def print_progress(
    current: int,
    total: Optional[int],
    success: int = 0,
    unavailable: int = 0,
    failed: int = 0,
    end: str = "\r",
) -> None:
    """Print in-place progress update on stdout."""
    bar = render_progress_bar(
        current=current,
        total=total,
        success=success,
        unavailable=unavailable,
        failed=failed,
    )
    sys.stdout.write(f"\r{bar}")
    sys.stdout.flush()
    if end != "\r":
        sys.stdout.write(end)
        sys.stdout.flush()


# ==============================================================================
# Environment & Diagnostic Checks
# ==============================================================================
def is_termux() -> bool:
    """Detect if running inside Termux environment on Android."""
    if os.path.exists("/data/data/com.termux"):
        return True
    if "TERMUX_VERSION" in os.environ or "PREFIX" in os.environ and "com.termux" in os.environ["PREFIX"]:
        return True
    return False


def check_python_version() -> Tuple[bool, str]:
    """Check if Python is >= 3.8."""
    v = sys.version_info
    ver_str = f"{v.major}.{v.minor}.{v.micro}"
    if v.major > 3 or (v.major == 3 and v.minor >= 8):
        return True, ver_str
    return False, ver_str


def check_ytdlp_installed() -> Tuple[bool, str]:
    """Check if yt-dlp is installed and return its version."""
    try:
        import yt_dlp
        version = getattr(yt_dlp, "__version__", "Installed (unknown version)")
        return True, str(version)
    except ImportError:
        return False, "Not installed"


def check_directory_writable(path: Path) -> Tuple[bool, str]:
    """Check if a directory path is writable."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".write_test.tmp"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("ok")
        test_file.unlink()
        return True, f"Writable ({path})"
    except Exception as e:
        return False, f"Not writable ({path}): {e}"
