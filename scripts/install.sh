#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# YouTube Library Scraper — Termux Installation Script
# ==============================================================================
set -e

echo "=================================================="
echo " YouTube Library Scraper — Termux Installer"
echo "=================================================="

# Check if running in Termux
if [ -d "/data/data/com.termux" ]; then
    echo "[+] Termux environment detected."
    
    echo "[+] Installing required system packages (python, ffmpeg, git)..."
    pkg install -y python ffmpeg git || true
    
    # Check if storage access is setup (avoid prompting if ~/storage already exists)
    if [ ! -d "$HOME/storage" ]; then
        echo "[!] Requesting Android storage access (for Downloads folder access)..."
        termux-setup-storage || true
    else
        echo "[+] Android storage directory already configured."
    fi
else
    echo "[*] Non-Termux environment detected (Standard Linux/Unix)."
fi

echo "[+] Installing Python dependencies from requirements.txt..."
# In modern Termux, pip is system-managed; we do not upgrade pip directly.
# We support both standard pip and PEP 668 (--break-system-packages) environments.
pip install --break-system-packages -r requirements.txt 2>/dev/null || pip install -r requirements.txt || python3 -m pip install -r requirements.txt

echo "[+] Installing yt-library CLI command locally..."
pip install --break-system-packages -e . 2>/dev/null || pip install -e . || python3 -m pip install -e .

echo "[+] Ensuring data directories exist..."
mkdir -p data/raw/playlists data/processed data/logs data/checkpoints

echo ""
echo "=================================================="
echo " Installation Complete!"
echo "=================================================="
echo " Next steps:"
echo " 1. Place your exported 'cookies.txt' in this directory"
echo " 2. Run diagnostics:         yt-library doctor"
echo " 3. Verify authentication:   yt-library auth test"
echo " 4. Discover playlists:      yt-library list playlists"
echo " 5. Run test scrape (20):    yt-library scrape all --limit 20"
echo "=================================================="
