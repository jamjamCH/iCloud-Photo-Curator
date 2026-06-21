# Codex Desktop Setup (Step by Step)

This guide installs **iCloud Photo Curator** as a local plugin in Codex Desktop. No coding needed — copy, paste, and follow along.

## What this does for you

You ask Codex in plain language, for example *"Sort my last 10 iCloud photos into albums."* Codex looks at the actual photos and suggests albums based on what it sees — food photos go to a **Food** album, a holiday photo taken in Paris is suggested for a **Paris** album, and so on.

- It **never deletes** photos.
- By default it only **suggests**; your albums change only after you explicitly approve.
- Your photos are not sent to any outside company — Codex (which you already use) does the looking.

## What you need first

| You need | How to get it |
| --- | --- |
| A computer | Windows, macOS, or Linux |
| Python 3.10 or newer | Download from [python.org](https://www.python.org/downloads/). On Windows, tick **"Add Python to PATH"** during install. |
| Codex Desktop | The Codex app |
| An Apple ID | The one your iCloud Photos are on |
| This project folder | On the GitHub page click **Code → Download ZIP**, then unzip it |

**Check Python is installed:** open a terminal (macOS/Linux: *Terminal*; Windows: *PowerShell*) and type `python --version`. If you see `Python 3.10` or higher, you are good. On macOS you may need `python3` instead of `python`.

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
python scripts\try_curator.py setup
python scripts\try_curator.py login
```

**macOS / Linux:**
```bash
python3 scripts/bootstrap.py
python3 scripts/try_curator.py setup
python3 scripts/try_curator.py login
```

What happens:
- `bootstrap.py` creates a private workspace (a `.venv` folder) and installs everything needed. **Expected:** ends with no red error.
- `setup` prints a quick health check (dependencies, config, geocoder).
- `login` asks for your Apple ID e‑mail and password, then usually an **Apple 2FA code** (the 6 digits on your iPhone/Mac). Your password is saved in your operating system's secure keychain — **never** in a text file. **Expected:** a summary ending with `"logged_in": true`.

## Step 3 — Add the plugin to Codex's marketplace file

Create or edit this file (it is a small list of local plugins Codex can install):

| Platform | Marketplace file |
| --- | --- |
| Windows | `C:\Users\<you>\.agents\plugins\marketplace.json` |
| macOS | `~/.agents/plugins/marketplace.json` |
| Linux | `~/.agents/plugins/marketplace.json` |

Paste this. The `path` points to the plugin folder you placed in Step 1 (relative to your home folder), so `./plugins/icloud-photo-curator` matches `~/plugins/icloud-photo-curator`:

```json
{
  "name": "local",
  "interface": {
    "displayName": "Local Plugins"
  },
  "plugins": [
    {
      "name": "icloud-photo-curator",
      "source": {
        "source": "local",
        "path": "./plugins/icloud-photo-curator"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_USE"
      },
      "category": "Productivity"
    }
  ]
}
```

If you already have a marketplace file, only add the one entry inside the existing `plugins` list (don't duplicate the outer braces).

## Step 4 — Activate in Codex

1. Fully quit and reopen Codex Desktop.
2. Open the plugin list.
3. Install or enable **iCloud Photo Curator**.
4. Start a new Codex session and ask it to run `setup_check`. **Expected:** a small report with `"vision_mode": "client_native_mcp_image"`.

## Step 5 — Try it

Type something like this to Codex:

> "Scan my iCloud albums and summarize them."

> "Prepare my next 10 photos for review and suggest albums."

Codex will ask whether you want to *only scan*, *scan and suggest*, or *apply approved changes*. Start with scan or suggest — nothing changes in iCloud until you say so.

## Not connecting? Quick fixes

| Problem | Fix |
| --- | --- |
| Plugin not in the list | Check the path in `marketplace.json` matches where you put the folder, then restart Codex. |
| `python` not found | Use `python3` (macOS/Linux), or reinstall Python with "Add to PATH" (Windows). |
| Asks for 2FA again later | Sessions expire — run `python scripts/try_curator.py login` again. |
| "No iCloud session" error | Run the `login` step (Step 2) before asking Codex to scan. |

## What the tools do

| Tool | What it's for |
| --- | --- |
| `setup_check` | Health check: config, keychain, session, dependencies, geocoder |
| `connect_icloud` | Open an iCloud session (uses your saved login) |
| `list_albums` | Read your existing album names |
| `prepare_batch_for_codex` | Send a batch of photos as images (+ metadata/location) so Codex can see and sort them |
| `get_photo_image` | Send one photo as an image for a precise look |
| `save_codex_proposal` | Save a suggestion locally (no iCloud change) |
| `review_proposals` | Show the suggestions you've saved |
| `write_capabilities` / `create_album` / `add_photo_to_album` / `apply_proposals` | Optional, opt‑in album changes (preview first, then confirm) |

## Good to know

- **Vision:** `prepare_batch_for_codex` and `get_photo_image` send the real photos to Codex as images, so it sorts by what's actually visible (food, documents, landscapes, …). No external vision service is used.
- **Location albums:** GPS is turned into a city/country **offline** (via `reverse_geocode`, installed automatically) for place‑based albums.
- **Safety:** album changes are experimental and opt‑in. They require `ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES=true` plus the exact confirmation phrases shown by `write_capabilities`. Photos are never deleted.
