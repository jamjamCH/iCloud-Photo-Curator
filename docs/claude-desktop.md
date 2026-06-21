# Claude Desktop Setup (Step by Step)

This guide connects **iCloud Photo Curator** to Claude Desktop. No coding needed — just copy, paste, and follow along.

## What this does for you

You talk to Claude in plain language, for example *"Sort my last 10 iCloud photos into albums."* Claude looks at the actual photos, then suggests albums based on what it sees — food photos go to a **Food** album, a holiday photo taken in Paris is suggested for a **Paris** album, and so on.

- It **never deletes** photos.
- By default it only **suggests**; it changes your albums only after you explicitly approve.
- Your photos are not sent to any outside company — Claude (which you already use) does the looking.

## What you need first

| You need | How to get it |
| --- | --- |
| A computer | Windows, macOS, or Linux |
| Python 3.10 or newer | Download from [python.org](https://www.python.org/downloads/). On Windows, tick **"Add Python to PATH"** during install. |
| Claude Desktop | The desktop app from Anthropic |
| An Apple ID | The one your iCloud Photos are on |
| This project folder | On the GitHub page click **Code → Download ZIP**, then unzip it |

**Check Python is installed:** open a terminal (macOS/Linux: *Terminal*; Windows: *PowerShell*) and type `python --version`. If you see `Python 3.10` or higher, you are good. On macOS you may need to type `python3` instead of `python`.

## Step 1 — Put the folder in a simple location

Move the unzipped folder here:

| Platform | Folder |
| --- | --- |
| Windows | `C:\Users\<you>\plugins\icloud-photo-curator` |
| macOS | `~/plugins/icloud-photo-curator` |
| Linux | `~/plugins/icloud-photo-curator` |

If the unzipped folder is called `icloud-photo-curator-main`, rename it to `icloud-photo-curator`.

## Step 2 — Install and log in

Open a terminal **inside that folder** (right‑click the folder → *Open in Terminal*, or use `cd` to go there), then run:

**Windows (PowerShell):**
```powershell
python scripts\bootstrap.py
python scripts\try_curator.py login
```

**macOS / Linux:**
```bash
python3 scripts/bootstrap.py
python3 scripts/try_curator.py login
```

What happens:
- `bootstrap.py` creates a private workspace (a `.venv` folder) and installs everything needed. **Expected:** it ends with no red error.
- `login` asks for your Apple ID e‑mail and password, then usually an **Apple 2FA code** (the 6 digits that pop up on your iPhone/Mac). Type it in. Your password is saved in your operating system's secure keychain — **never** in a text file.
- **Expected result:** a short summary ending with `"logged_in": true`.

## Step 3 — Tell Claude Desktop about the server

Open Claude Desktop's config file (create it if it doesn't exist):

| Platform | Config file |
| --- | --- |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

Paste the block for your system and **replace `YOUR_NAME`** with your real username. Use full paths (Windows needs double backslashes).

**Windows:**
```json
{
  "mcpServers": {
    "icloud-photo-curator": {
      "command": "C:\\Users\\YOUR_NAME\\plugins\\icloud-photo-curator\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\YOUR_NAME\\plugins\\icloud-photo-curator\\scripts\\icloud_photo_curator_mcp.py"
      ],
      "env": {
        "ICLOUD_PHOTO_CURATOR_STATE_DIR": "C:\\Users\\YOUR_NAME\\.icloud-photo-curator"
      }
    }
  }
}
```

**macOS / Linux** (on Linux replace `/Users/YOUR_NAME` with `/home/YOUR_NAME`):
```json
{
  "mcpServers": {
    "icloud-photo-curator": {
      "command": "/Users/YOUR_NAME/plugins/icloud-photo-curator/.venv/bin/python",
      "args": [
        "/Users/YOUR_NAME/plugins/icloud-photo-curator/scripts/icloud_photo_curator_mcp.py"
      ],
      "env": {
        "ICLOUD_PHOTO_CURATOR_STATE_DIR": "/Users/YOUR_NAME/.icloud-photo-curator"
      }
    }
  }
}
```

## Step 4 — Restart and check

1. Fully quit and reopen Claude Desktop.
2. Open the connectors / developer view and confirm **icloud-photo-curator** shows as connected.
3. In a chat, ask Claude to run `setup_check`. **Expected:** a small report with `"vision_mode": "client_native_mcp_image"`.

## Step 5 — Try it

Type something like this to Claude:

> "Scan my iCloud albums and summarize them."

> "Prepare my next 10 photos for review and suggest albums."

Claude will ask whether you want to *only scan*, *scan and suggest*, or *apply approved changes*. Start with scan or suggest — nothing is changed in iCloud until you say so.

## Easier: one-click install (.mcpb, experimental)

Instead of editing the config by hand in Step 3, you can install a packaged extension. This is **experimental**: it still needs Python installed, and on first launch it downloads the dependencies into a private workspace (so the first start takes a moment and needs internet).

1. Get the `.mcpb` file — download it from the project's **Releases** page, or build it yourself from the project folder:
   - Windows: `python scripts\build_mcpb.py`
   - macOS / Linux: `python3 scripts/build_mcpb.py`

   It is written to `dist/icloud-photo-curator-<version>.mcpb`.
2. In Claude Desktop, open **Settings → Extensions** and drag the `.mcpb` file in (or double‑click it). Enter your Apple ID if prompted.
3. Still run the one‑time `login` (Step 2) once, so your password is stored in the OS keychain.

If anything misbehaves, use the manual config in Step 3 — that's the reliable path.

## Not connecting? Quick fixes

| Problem | Fix |
| --- | --- |
| Server not listed in Claude | Check the JSON paths are correct and that you restarted Claude completely. |
| `python` not found | Use `python3` (macOS/Linux), or reinstall Python with "Add to PATH" (Windows). |
| Asks for 2FA again later | Sessions expire — just run `python scripts/try_curator.py login` again. |
| "No iCloud session" error | Run the `login` step (Step 2) before asking Claude to scan. |

## Good to know

- **Vision:** the tools `prepare_batch_for_codex` and `get_photo_image` send the photo to Claude as an image, so Claude sorts by what's actually in the picture. No external vision service is used.
- **Location albums:** GPS is turned into a city/country **offline** (via `reverse_geocode`, installed automatically) so trips can be grouped by place.
- **Safety:** changing albums is an experimental, opt‑in feature. It stays in preview ("dry‑run") until you enable it and confirm. Photos are never deleted.
