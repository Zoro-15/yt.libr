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
    
    echo "[+] Updating packages..."
    pkg update -y || true
    
    echo "[+] Installing required system packages (python, ffmpeg, git)..."
    pkg install -y python ffmpeg git
    
    # Check if storage access is setup
    if [ ! -d "$HOME/storage" ]; then
        echo "[!] Requesting Android storage access (needed if copying cookies from Downloads)..."
        termux-setup-storage || true
    fi
else
    echo "[*] Non-Termux environment detected (Standard Linux/Unix)."
fi

echo "[+] Upgrading pip..."
python3 -m pip install --upgrade pip

echo "[+] Installing Python dependencies from requirements.txt..."
python3 -m pip install -r requirements.txt

echo "[+] Installing yt-library CLI command locally..."
python3 -m pip install -e .

echo "[+] Ensuring data directories exist..."
mkdir -p data/raw data/processed data/logs

echo ""
echo "=================================================="
echo " Installation Complete!"
echo "=================================================="
echo " Next steps:"
echo " 1. Place your exported 'cookies.txt' in this directory"
echo " 2. Run diagnostics:         yt-library doctor"
echo " 3. Verify authentication:   yt-library auth test"
echo " 4. Run test scrape (20):    yt-library scrape all --limit 20"
echo "=================================================="
