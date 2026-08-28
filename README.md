# YouTube Library Scraper (`yt-library`)

> A standalone, high-performance CLI tool for **Android Termux** and **PC / Desktop Terminal** (Windows PowerShell, macOS, Linux) to extract, normalize, deduplicate, and merge YouTube metadata from **Watch Later**, **Liked Videos**, and **All User Playlists** (3,000+ videos) into clean, versioned JSON datasets (`videos.json` & `playlists.json`) **without downloading any video or audio files**.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![Target: Termux | PC](https://img.shields.io/badge/target-Android%20Termux%20%7C%20PC%20Terminal-orange.svg)]()
[![Repository](https://img.shields.io/badge/GitHub-Zoro--15%2Fyt.libr-181717?logo=github)](https://github.com/Zoro-15/yt.libr)

---

## 1. Architecture & Design Principles

This tool is intentionally designed as an **independent extraction utility**, strictly decoupled from any future personal video library website or database.

```text
       YouTube Account (Watch Later, Liked, & Playlists)
                         │
                         ▼
        Android (Termux) / PC (Windows/Mac/Linux)
                         │
              yt-library (Python + yt-dlp)
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   Watch Later      Liked Videos    Custom Playlists
  (data/raw/wl)    (data/raw/liked)  (data/raw/playlists/)
        │                │                │
        └────────────────┼────────────────┘
                         ▼
             1. Metadata Normalization
                         │
                         ▼
             2. Canonical Deduplication (by YouTube video_id)
                         │
                         ▼
             3. Multi-Source Merging & Playlist Position Indexing
                         │
                         ▼
             4. Versioned JSON Outputs:
                - data/processed/videos.json
                - data/processed/playlists.json
                         │
                         ▼
         [ Future Personal Video Library Website ]
```

### Strict Separation of Concerns
- **The Scraper owns:** YouTube metadata extraction (`video_id`, `url`, `title`, `channel`, `thumbnail`, `duration_seconds`, `upload_date`, `description`, `sources`, `source_positions`, `playlists`).
- **The Scraper DOES NOT own:** User personal metadata (`category`, `tags`, `watched`, `backlog`, `favourite`, `notes`, `collections`).
- **The Future Website:** Imports `videos.json` and `playlists.json` to manage personal tags and categories independently without needing to re-scrape YouTube.

---

## 2. Security & Privacy Rules

> [!CAUTION]
> **NEVER** give your Google password to any script.
> **NEVER** commit or upload `cookies.txt` or session files anywhere.

This tool deals with authenticated YouTube data (private playlists: `:ytwatchlater`, `:ytliked`, and user created/saved playlists).

- **No Passwords**: The script never asks for or stores usernames or passwords.
- **Session Cookies**: Uses standard Netscape `cookies.txt` format or direct PC browser session extraction.
- **Privacy Protection**: `.gitignore` strictly ignores `cookies*.txt`, `.env`, raw private data, checkpoints, and logs.
- **Safe Output**: Generated JSON files contain only public video metadata and source identifiers.

---

## 3. 📱 Setup Guide for Android (Termux) Users

### Step 1: Install Termux & Setup Repository

**If you already cloned the repository (`~/yt.libr` exists):**
```bash
cd ~/yt.libr
git pull origin main
chmod +x scripts/install.sh
./scripts/install.sh
```

**For a fresh installation on a new phone / Termux:**
```bash
# 1. Update Termux packages
pkg update -y && pkg upgrade -y

# 2. Install Git and Python
pkg install -y git python ffmpeg

# 3. Setup Android Storage permissions (allows copying cookies from Downloads)
termux-setup-storage

# 4. Clone this repository
git clone https://github.com/Zoro-15/yt.libr.git
cd yt.libr

# 5. Run the automated installer
chmod +x scripts/install.sh
./scripts/install.sh
```

### Step 2: Export YouTube Cookies on Android
Termux cannot read browser cookies directly due to Android app sandboxing. You need a `cookies.txt` file:
1. Install **Kiwi Browser** or **Firefox Nightly** on your phone (browsers that support Chrome/Firefox extensions).
2. Install the open-source extension **"Get cookies.txt LOCALLY"** from the Chrome Web Store / Firefox Add-ons.
3. In that browser, open [youtube.com](https://www.youtube.com), log into your Google account, and make sure your **Watch Later**, **Liked Videos**, and playlists are visible.
4. Click the extension icon and press **Export** (it downloads `cookies.txt` into your phone's `Downloads` folder).
5. In Termux, copy the cookie file into the project folder:
   ```bash
   cp ~/storage/shared/Download/cookies.txt ~/yt.libr/cookies.txt
   chmod 600 ~/yt.libr/cookies.txt
   ```

### Step 3: Run Diagnostic & Auth Test
```bash
yt-library doctor
yt-library auth test
```

---

## 4. 💻 Setup Guide for PC Users (Windows / macOS / Linux)

### Step 1: Clone & Install Dependencies
```bash
# Clone the repository
git clone https://github.com/Zoro-15/yt.libr.git
cd yt.libr

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### Step 2: Run Diagnostics with Your Browser Session
On PC, you can either place `cookies.txt` in the root folder **OR** extract directly from your installed browser (`chrome`, `firefox`, `edge`, `brave`, `opera`):

```powershell
# Windows PowerShell:
py -m scraper doctor --cookies-from-browser chrome
py -m scraper auth test --cookies-from-browser chrome

# macOS / Linux Terminal:
yt-library doctor --cookies-from-browser chrome
yt-library auth test --cookies-from-browser chrome
```

---

## 5. 🎯 All Commands for All Scenarios

### ⚡ Scenario 1: Instant Offline Merge (No Internet / No Re-download)
*Use this when your raw videos are already downloaded on disk in `data/raw/` and you want to generate the final `videos.json` and `playlists.json` in 2 seconds.*

```bash
# Android Termux:
yt-library merge

# Windows PowerShell:
py -m scraper merge

# macOS / Linux:
yt-library merge
```

---

### 🌐 Scenario 2: Full Smart Scrape (Watch Later + Liked + Playlists)
*Extracts Watch Later, Liked Videos, and all user playlists. Uses smart disk-caching (automatically skips sources and playlists that are already downloaded).*

```bash
# Android Termux:
yt-library scrape all

# Windows PC (using Chrome session):
py -m scraper scrape all --cookies-from-browser chrome

# Windows PC (using cookies.txt):
py -m scraper scrape all
```

---

### 🔄 Scenario 3: Force Re-Scrape Everything from Scratch (`--force`)
*Bypasses local disk cache and forces re-downloading fresh metadata for all sources and playlists from YouTube.*

```bash
# Android Termux:
yt-library scrape all --force

# Windows PC:
py -m scraper scrape all --force --cookies-from-browser chrome
```

---

### 🧪 Scenario 4: Test Preview Scrape (Limit 20 Videos)
*Quick test to verify that extraction and cookies work properly with a small batch.*

```bash
# Android Termux:
yt-library scrape all --limit 20

# Windows PC:
py -m scraper scrape all --limit 20 --cookies-from-browser chrome
```

---

### 🕒 Scenario 5: Scrape Watch Later Only
*Extracts only the Watch Later playlist to `data/raw/watch_later.json`.*

```bash
# Android Termux:
yt-library scrape watch-later

# Windows PC:
py -m scraper scrape watch-later --cookies-from-browser chrome

# With limit:
yt-library scrape watch-later --limit 50
```

---

### 👍 Scenario 6: Scrape Liked Videos Only
*Extracts only Liked Videos to `data/raw/liked.json`.*

```bash
# Android Termux:
yt-library scrape liked

# Windows PC:
py -m scraper scrape liked --cookies-from-browser chrome

# With limit:
yt-library scrape liked --limit 50
```

---

### 📑 Scenario 7: Scrape All User Playlists Only
*Discovers and extracts all user-created and saved playlists and their embedded videos.*

```bash
# Android Termux:
yt-library scrape playlists

# Windows PC:
py -m scraper scrape playlists --cookies-from-browser chrome

# Limit to first 10 playlists and 25 videos per playlist:
yt-library scrape playlists --playlist-limit 10 --limit 25
```

---

### 🎯 Scenario 8: Scrape a Single Specific Playlist by ID or URL
*Extracts one specific playlist to `data/raw/playlists/<playlist_id>.json`.*

```bash
# Using Playlist ID (e.g. PLguWwLNVYKWecsPXNs4Tfi2NDvVPSC3bZ):
yt-library scrape playlist PLguWwLNVYKWecsPXNs4Tfi2NDvVPSC3bZ

# Using Full YouTube Playlist URL:
yt-library scrape playlist "https://www.youtube.com/playlist?list=PLguWwLNVYKWecsPXNs4Tfi2NDvVPSC3bZ"

# Windows PC:
py -m scraper scrape playlist PLguWwLNVYKWecsPXNs4Tfi2NDvVPSC3bZ --cookies-from-browser chrome
```

---

### 🔍 Scenario 9: Discover & List All User Playlists
*Lists all playlists in your YouTube feed with their IDs, video counts, and URLs without downloading entries.*

```bash
# Android Termux:
yt-library list playlists

# Windows PC:
py -m scraper list playlists --cookies-from-browser chrome
```

---

### 🛡️ Scenario 10: Dry Run (Simulate Extraction without Saving)
*Tests extraction from YouTube and displays progress without saving any files to disk.*

```bash
# Android Termux:
yt-library scrape all --dry-run

# Windows PC:
py -m scraper scrape all --dry-run --cookies-from-browser chrome
```

---

### ✅ Scenario 11: Validate Dataset Schema & Integrity
*Validates `data/processed/videos.json` and `data/processed/playlists.json` against Schema Version 1 rules, unique IDs, canonical URLs, and forbidden personal fields.*

```bash
# Android Termux:
yt-library validate

# Windows PC:
py -m scraper validate
```

---

### 📊 Scenario 12: View Library Statistics & Analytics
*Displays complete breakdown of total unique videos, Watch Later vs. Liked vs. Playlists counts, overlap counts, and total playback duration.*

```bash
# Android Termux:
yt-library stats

# Windows PC:
py -m scraper stats
```

---

### 🔋 Scenario 13: Prevent Termux Sleep During Large Extractions (3,000+ Videos)
*Keeps CPU awake so Android battery optimization does not kill the scraping process.*

```bash
# 1. Acquire wake lock in Termux
termux-wake-lock

# 2. Run full extraction
yt-library scrape all

# 3. Release wake lock when done
termux-wake-unlock
```

---

## 6. CLI Command Summary Table

| Command | Purpose | Example |
| :--- | :--- | :--- |
| `doctor` | Diagnostics for Python, yt-dlp, storage, and cookies | `yt-library doctor` |
| `auth test` | Test access to private Watch Later & Liked playlists | `yt-library auth test` |
| `list playlists` | Discover and list all user playlists from feed | `yt-library list playlists` |
| `scrape all` | Scrape Watch Later, Liked, & Playlists with smart caching | `yt-library scrape all` |
| `scrape all --force` | Force re-download all sources and playlists | `yt-library scrape all --force` |
| `scrape watch-later` | Scrape Watch Later playlist | `yt-library scrape watch-later --limit 100` |
| `scrape liked` | Scrape Liked Videos playlist | `yt-library scrape liked --limit 100` |
| `scrape playlists` | Scrape all user playlists | `yt-library scrape playlists` |
| `scrape playlist <ID>` | Scrape a specific playlist by ID or URL | `yt-library scrape playlist PL12345` |
| `merge` | Merge all downloaded raw data into final JSONs (2s) | `yt-library merge` |
| `validate` | Verify schema compliance and ID uniqueness | `yt-library validate` |
| `stats` | Display summary analytics and duration totals | `yt-library stats` |

### CLI Options & Flags
- `--force`: Force re-extraction even if data is already cached on disk.
- `--limit <N>`: Maximum number of videos to extract per source/playlist.
- `--playlist-limit <N>`: Maximum number of playlists to discover.
- `--no-playlists`: Skip user playlists during `scrape all`.
- `--dry-run`: Test extraction without writing files to disk.
- `--no-merge`: Skip automatic merge step after scraping.
- `--cookies <path>`: Custom path to `cookies.txt` (default: `./cookies.txt`).
- `--cookies-from-browser <browser>`: Extract session directly from PC browser (`chrome`, `firefox`, `edge`, `brave`).
- `--data-dir <path>`: Custom data directory (default: `./data`).
- `--config <path>`: Custom configuration JSON file.
- `--verbose` / `-v`: Verbose debugging output.

---

## 7. Output Data Structure Reference

### A. Processed Videos (`data/processed/videos.json`)

```json
{
  "schema_version": 1,
  "generated_at": "2026-08-28T09:30:00Z",
  "source": "youtube",
  "total_videos": 3201,
  "videos": [
    {
      "video_id": "dQw4w9WgXcQ",
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "title": "Rick Astley - Never Gonna Give You Up",
      "channel": {
        "name": "Rick Astley",
        "id": "UCuAXFkgsw1L7xaCfnd5JJOw"
      },
      "thumbnail": {
        "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
      },
      "duration_seconds": 212,
      "upload_date": "2009-10-25",
      "description": "The official video for Never Gonna Give You Up",
      "sources": [
        "liked",
        "playlist:PL1234567890",
        "watch_later"
      ],
      "source_positions": {
        "watch_later": 1,
        "liked": 42,
        "PL1234567890": 1
      },
      "playlists": [
        {
          "id": "PL1234567890",
          "title": "Favorite Music Videos",
          "position": 1
        }
      ]
    }
  ]
}
```

### B. Processed Playlists (`data/processed/playlists.json`)

```json
{
  "schema_version": 1,
  "generated_at": "2026-08-28T09:30:00Z",
  "source": "youtube",
  "total_playlists": 8,
  "playlists": [
    {
      "playlist_id": "PL1234567890",
      "title": "Favorite Music Videos",
      "url": "https://www.youtube.com/playlist?list=PL1234567890",
      "description": "A curated list of favorite music videos",
      "channel": {
        "name": "My Channel",
        "id": "UCmychannel"
      },
      "video_count": 25,
      "video_ids": [
        "dQw4w9WgXcQ",
        "fJ9rUzIMcZQ"
      ]
    }
  ]
}
```

---

## 8. Running Automated Unit Tests

Run the full unit test suite:
```bash
# On Android / Linux / macOS:
python3 -m unittest discover tests

# On Windows PC:
py -m unittest discover tests
```

---

## 9. Troubleshooting & FAQ Guide

| Problem | Cause | Solution |
| :--- | :--- | :--- |
| `Installing pip is forbidden` | Termux manages `pip` via `pkg` | Run `git pull origin main` and `./scripts/install.sh`. The installer handles Termux's environment automatically. |
| `This playlist type is unviewable (RD...)` | Dynamic YouTube Mix / Radio feed | Handled automatically! Dynamic mixes (`RD...`) are logged and skipped without halting the scraper. |
| `Cookie file not found` | `cookies.txt` is missing | Export `cookies.txt` into the project root folder or use `--cookies-from-browser chrome`. |
| `Private playlist / Sign in required` | Cookies expired or invalid | Log into YouTube in Kiwi/Firefox and export a fresh `cookies.txt`. |
| `Termux killed process` | Android OS battery optimization | Run `termux-wake-lock` before long scrapes, or disable battery optimization for Termux in Android Settings. |
| `UnicodeEncodeError` | Windows console cp1252 default | Handled automatically by `yt-library`, or run `chcp 65001` in PowerShell. |

---

## 10. Updating yt-dlp

YouTube regularly updates internal player endpoints. To keep extraction fast and reliable, update `yt-dlp` periodically:

```bash
# On Android Termux:
pip install -U yt-dlp --break-system-packages 2>/dev/null || pip install -U yt-dlp

# On PC:
pip install --upgrade yt-dlp
```

---

## 11. License

This project is licensed under the [MIT License](LICENSE).
