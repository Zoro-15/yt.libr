# YouTube Library Scraper (`yt-library`)

> A standalone, security-first CLI tool for **Android Termux** and **PC / Desktop Terminal** to extract, normalize, deduplicate, and merge YouTube metadata from **Watch Later** and **Liked Videos** (3,000+ videos) into a clean, versioned `videos.json` **without downloading any video or audio files**.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![Target: Termux | PC](https://img.shields.io/badge/target-Android%20Termux%20%7C%20PC%20Terminal-orange.svg)]()
[![Repository](https://img.shields.io/badge/GitHub-Zoro--15%2Fyt.libr-181717?logo=github)](https://github.com/Zoro-15/yt.libr)

---

## 1. Project Overview & Architecture

This tool is intentionally designed as an **independent extraction utility**, strictly decoupled from any future personal video library website or database.

```text
       YouTube Account (Watch Later / Liked)
                         │
                         ▼
        Android (Termux) / PC (Windows/Mac/Linux)
                         │
              yt-library (Python + yt-dlp)
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
   Watch Later                       Liked Videos
  (data/raw/watch_later.json)       (data/raw/liked.json)
        │                                 │
        └────────────────┬────────────────┘
                         ▼
             1. Metadata Normalization
                         │
                         ▼
             2. Canonical Deduplication (by YouTube video_id)
                         │
                         ▼
             3. Multi-Source Merging & Position Indexing
                         │
                         ▼
             4. Versioned JSON (data/processed/videos.json)
                         │
                         ▼
         [ Future Personal Video Library Website ]
```

### Strict Separation of Concerns
- **The Scraper owns:** YouTube metadata extraction (`video_id`, `url`, `title`, `channel`, `thumbnail`, `duration_seconds`, `upload_date`, `description`, `sources`, `source_positions`).
- **The Scraper DOES NOT own:** User personal metadata (`category`, `tags`, `watched`, `backlog`, `favourite`, `notes`, `collections`).
- **The Future Website:** Imports `videos.json` and manages personal tags and categories independently without needing to re-scrape YouTube.

---

## 2. Security & Privacy Rules

> [!CAUTION]
> **NEVER** give your Google password to any script.
> **NEVER** commit or upload `cookies.txt` or session files anywhere.

This tool deals with authenticated YouTube data (private playlists: `:ytwatchlater` and `:ytliked`).

- **No Passwords**: The script never asks for or stores usernames or passwords.
- **Session Cookies**: Uses standard Netscape `cookies.txt` format or direct PC browser session extraction.
- **Privacy Protection**: `.gitignore` strictly ignores `cookies*.txt`, `.env`, raw private data, and logs.
- **Safe Output**: Generated JSON files contain only public video metadata and source identifiers.

---

## 3. 📱 Step-by-Step Guide for Android (Termux) Users

Follow these exact steps on your Android device:

### Step 1: Install Termux & Clone Repository
Open Termux and run:
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
3. In that browser, open [youtube.com](https://www.youtube.com), log into your Google account, and make sure your **Watch Later** and **Liked Videos** are visible.
4. Click the extension icon and press **Export** (it downloads `cookies.txt` into your phone's `Downloads` folder).
5. In Termux, copy the cookie file into the project folder:
   ```bash
   cp ~/storage/shared/Download/cookies.txt ~/yt.libr/cookies.txt
   chmod 600 ~/yt.libr/cookies.txt
   ```

### Step 3: Run Diagnostic Check
```bash
yt-library doctor
```
*(Verify that Python, yt-dlp, storage, and cookies all show green checkmarks).*

### Step 4: Test Authentication
```bash
yt-library auth test
```

### Step 5: Test Scrape with Small Batch (20 Videos)
```bash
yt-library scrape all --limit 20
```

### Step 6: Full Scrape (3,000+ Videos)
```bash
# Run the full extraction (with automatic normalization & merge)
yt-library scrape all
```

### Step 7: Validate & View Statistics
```bash
# Validate schema and unique IDs
yt-library validate

# View total unique videos and overlap counts
yt-library stats
```

The output file will be ready at: `data/processed/videos.json`!

---

## 4. 💻 Step-by-Step Guide for PC Users (Windows / macOS / Linux)

You can run this directly in your terminal, PowerShell, or Antigravity Terminal:

### Step 1: Clone & Setup
```bash
# Clone the repository
git clone https://github.com/Zoro-15/yt.libr.git
cd yt.libr

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### Step 2: Run Diagnostics
On PC, you can either place `cookies.txt` in the root folder **OR** extract directly from your installed browser (`chrome`, `firefox`, `edge`, `brave`, `opera`):

```bash
# On Windows PowerShell:
py -m scraper doctor --cookies-from-browser chrome

# On macOS / Linux:
yt-library doctor --cookies-from-browser chrome
```

### Step 3: Test Authentication
```bash
# Windows:
py -m scraper auth test --cookies-from-browser chrome

# macOS / Linux:
yt-library auth test --cookies-from-browser chrome
```

### Step 4: Test Scrape (20 Videos)
```bash
# Windows:
py -m scraper scrape all --limit 20 --cookies-from-browser chrome

# macOS / Linux:
yt-library scrape all --limit 20 --cookies-from-browser chrome
```

### Step 5: Full Extraction & Merge
```bash
# Windows:
py -m scraper scrape all --cookies-from-browser chrome

# macOS / Linux:
yt-library scrape all --cookies-from-browser chrome
```

### Step 6: Validate and View Statistics
```bash
# Windows:
py -m scraper validate
py -m scraper stats

# macOS / Linux:
yt-library validate
yt-library stats
```

---

## 5. CLI Command Reference

| Command | Description | Example |
| :--- | :--- | :--- |
| `doctor` | Checks environment, dependencies, storage, and cookies | `yt-library doctor` |
| `auth test` | Tests authenticated access to private playlists | `yt-library auth test` |
| `scrape watch-later` | Extracts metadata from Watch Later to `data/raw/watch_later.json` | `yt-library scrape watch-later --limit 50` |
| `scrape liked` | Extracts metadata from Liked Videos to `data/raw/liked.json` | `yt-library scrape liked --limit 50` |
| `scrape all` | Extracts both playlists and automatically normalizes & merges | `yt-library scrape all` |
| `merge` | Reads raw JSON files and generates `data/processed/videos.json` | `yt-library merge` |
| `validate` | Validates `videos.json` against Schema Version 1 rules | `yt-library validate` |
| `stats` | Displays breakdown of unique, overlap, and missing metadata | `yt-library stats` |

### CLI Options & Flags
- `--cookies <path>`: Custom path to `cookies.txt` (default: `./cookies.txt`).
- `--cookies-from-browser <browser>`: Extract session directly from PC browser (`chrome`, `firefox`, `edge`, `brave`).
- `--data-dir <path>`: Custom data output directory (default: `./data`).
- `--config <path>`: Custom JSON configuration file.
- `--dry-run`: Test extraction without writing files to disk.
- `--no-merge`: (For `scrape all`) Skip automatic merge after scraping.
- `--verbose` / `-v`: Verbose debug logging.

---

## 6. Output Data Structure (`videos.json`)

Output location: `data/processed/videos.json` (Schema Version 1)

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
        "watch_later"
      ],
      "source_positions": {
        "watch_later": 1,
        "liked": 42
      }
    }
  ]
}
```

---

## 7. Running Automated Tests

Run the full unit test suite:
```bash
python -m unittest discover tests
# On Windows:
py -m unittest discover tests
```

---

## 8. Updating yt-dlp

Because YouTube frequently updates internal player endpoints, update `yt-dlp` if extraction encounters issues:

```bash
# On PC:
pip install --upgrade yt-dlp

# On Android Termux:
pip install -U yt-dlp
```

---

## 9. Troubleshooting Guide

| Problem | Cause | Solution |
| :--- | :--- | :--- |
| `Cookie file not found` | `cookies.txt` is missing | Export `cookies.txt` into project directory or use `--cookies-from-browser chrome`. |
| `Private playlist / Sign in` | Cookies expired or invalid | Log in to YouTube again and re-export `cookies.txt`. |
| `Termux killed process` | Android battery optimization | Disable battery optimization for Termux in Android Settings, or run `termux-wake-lock`. Partial checkpoints are saved in `data/checkpoints/`. |
| `UnicodeEncodeError` | Windows console cp1252 | Handled automatically by `yt-library`, or run `chcp 65001` in PowerShell. |
| `yt-dlp not installed` | Missing dependency | Run `pip install -r requirements.txt`. |

---

## 10. License

This project is licensed under the [MIT License](LICENSE).
