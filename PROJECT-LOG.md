# PLM Kiosk — Project Log

Gallery welcome sign-in kiosk for Past Lives Makerspace. Runs on a Dell XPS 15 at the gallery entrance. Guests sign in, complete waivers, and indicate visit reason.

**Repo:** https://github.com/Past-Lives-Makerspace/plm-kiosk
**Local code (Mac):** `~/Code/plm-kiosk/`
**Deployed code (Dell):** `C:\Users\pc\kiosk\`

---

## Hardware — Dell XPS 15 9560

| Spec | Value |
|------|-------|
| Hostname | DESKTOP-OMOJRVE |
| CPU | Intel Core i7-7700HQ @ 2.80GHz |
| RAM | 8 GB |
| Storage | 256 GB NVMe (Toshiba) |
| OS | Windows 10 Home |
| Display | 15.6" touchscreen (kiosk mode via pywebview fullscreen) |
| Location | Past Lives Makerspace, 2808 SE 9th Ave, gallery entrance |

---

## Network & Remote Access

| Detail | Value |
|--------|-------|
| Tailscale IP | 100.76.241.47 |
| PLM WiFi IP | 10.0.16.118 (NOT routable from Mac subnet 10.0.10.x) |
| SSH | `ssh pc@100.76.241.47` (key-only, password auth disabled) |
| Windows user | pc |
| Flask server | http://localhost:5000 on the Dell |

**Important:** PLM WiFi segments subnets — Mac is on 10.0.10.x, Dell is on 10.0.16.x. Devices can't talk directly over local WiFi. Tailscale is **required** for all Mac-to-Dell communication.

---

## Stack

- **Backend:** Python/Flask on port 5000 (`kiosk.py`)
- **Frontend:** Single-page HTML/CSS/JS (`kiosk.html`)
- **Database:** SQLite (`kiosk.db`) + Google Sheets sync via service account
- **Display:** pywebview fullscreen wrapper (`launcher.pyw`) with IPC server on port 51988
- **Startup:** `start-kiosk.bat` in Windows Startup folder — auto-launches on boot (Windows auto-login, user: PC)

---

## Architecture

| File | Role |
|------|------|
| `kiosk.py` | Flask backend — sign-in API, Google Sheets sync, CSV export, SQLite DB, live refresh endpoint |
| `kiosk.html` | Single-page sign-in UI (multi-step: reason → info → waivers → interests → thank you) |
| `launcher.pyw` | pywebview fullscreen wrapper with IPC server on port 51988 (reload/ping/stop) |
| `start-kiosk.bat` | Launches kiosk.py then launcher.pyw with delay; lives in Startup folder |
| `launch-gui.vbs` | VBS helper for launching GUI |
| `service-account.json` | Google Sheets service account credentials (NOT in git) |
| `kiosk.db` | Runtime SQLite database (NOT in git) |
| `guest_log.csv` | CSV export of guest sign-ins (NOT in git) |
| `static/branding/` | PLM pixel art branding (logo, lantern, sign-in banner) |
| `static/icons/` | 42 pixel art guild tool icons (180x180 canvases, centered by visual center of mass) |
| `static/originals/` | Source ChatGPT sprite sheets (5 sheets) |

---

## Deploy Workflow

1. Edit code on Mac (`~/Code/plm-kiosk/`)
2. SCP to Dell: `scp ~/Code/plm-kiosk/kiosk.html pc@100.76.241.47:"C:\\Users\\pc\\kiosk\\kiosk.html"`
3. Trigger live refresh: `ssh pc@100.76.241.47 "curl -s -X POST http://localhost:5000/api/trigger-refresh"`

**Note:** GitHub raw CDN caches files — do NOT use `curl` from raw.githubusercontent.com for deploys. Always use `scp` directly.

For server-side changes (`kiosk.py`): need to kill python.exe on Dell and reboot, or kill + re-run via scheduled task. Cannot launch GUI apps over SSH — pywebview requires the interactive desktop session.

---

## Sign-In Flow

1. **Welcome** — Animated icon field background, tap to begin
2. **Reason** — 5 options: Touring, Taking a Class, Guest of Member, Event, Meeting
3. **Info** — Name, email, phone, guest-of (if guest), minor checkbox with guardian fields
4. **Waivers** — Varies by visit reason:
   - **Guest of Member:** Liability waiver only
   - **Taking a Class:** Liability waiver → Workshop waiver → Model release
   - **Touring / Event:** Liability waiver → Model release
   - **Meeting:** Skips all waivers
5. **Interests** — Membership interest, newsletter, "Invite me to the public events calendar"
6. **Thank you** — Sparkle animation, 3-second countdown, auto-reset

---

## Animated Background

- Rows of guild tool icons drift upward continuously (JS `requestAnimationFrame`)
- Each row is independent; when it exits the top, it recycles below with new icons
- Speed: 0.42 px/frame (~25px/sec at 60fps)
- Spacing: icon size 96px, row height 150px, horizontal gap 160px, stagger 80px
- No icon repeats within 2 rows (history ban + shuffled pool per row)

---

## Log

### 2026-04-02

- **Initial commit** — Full kiosk app: welcome screen with floating icon field, 5 visit reasons (Touring, Taking a Class, Guest of Member, Event, Meeting), guest info form, liability waiver, workshop waiver, model release, interests screen, thank-you with sparkle animation. Flask backend with SQLite + Google Sheets sync + CSV export.
- **Slowed floating icons** — Reduced icon drift speed from 1.5 → 0.42 px/frame through iterative tuning.
- **Guest of Member waiver simplification** — "Guest of Member" visitors now only see the liability waiver, skipping workshop waiver and model release. Other visit reasons unchanged.
