# Lilliput v0.1 — The Living Little Town

A **real-time, persistent, 25-resident town simulation** that runs on a server, not on your phone. Watch the Lilliputians through a lightweight iPhone web app, look inside their dossiers, see where they work and live, and read what has happened while you've been away.

## What is in v0.1?

- Exactly **25 named Lilliputians** at founding. Every one has an age, a job, workplace, home, shift, traits, a biography, goal, personal journal, needs, savings, and relationships.
- **Real time, never accelerated**: a real day is a town day. The simulation updates resident behavior and needs every **15 real minutes**, including when the dashboard is closed. The app clock shows real local time.
- **Places**: town hall, bakery, trading square, school, clinic, workshop, farm, pond, inn, library, watch, park, and four home districts. Tap a place to see who is currently there.
- **Autonomy**: residents follow different shifts and days off, sleep, work, eat, spend personal time, socialize in shared locations, and maintain well-being, connections and journals. The core works with zero cloud calls and zero third-party Python dependencies.
- **Chronicle**: a timeline of selected activities, encounters, and milestones. Stored in a local SQLite database, with a rolling 30-day/6,000-entry limit.
- **iPhone-friendly interface**: a responsive town dashboard and resident registry; tap any person for their dossier. A web manifest, icons and optional HTTPS-only service-worker shell cache are included.
- **Optional local AI layer**: can ask an existing Ollama model to choose a resident's evening pastime and write an individualized inner thought. This is **optional enrichment**, not required for their basic day-to-day behavior.

This is a working **foundation**, not yet a full life simulator: no marriage, children, aging, death, construction, deep economic trade, direct conversation with citizens, or navigable animated map. AI thoughts are occasional, and standard routines remain simulation-driven. The journal is simulated narrative, **not** a literal record of a conscious entity.

## iPhone → Working Copy → GitHub → Proxmox

1. Unzip the provided project ZIP in **Working Copy** on your iPhone (or use the Files app to extract it, then copy the project folder into Working Copy). Make a new GitHub repo for Lilliput and commit/push these files. Do **not** commit a `.env` file or the `data/` directory; `.gitignore` excludes them.
2. On your Debian/Ubuntu **Proxmox VM or LXC**, install basic system tools:

   ```bash
   sudo apt update && sudo apt install -y git python3
   ```

3. Clone the repo into an accessible location (recommended: `/opt/lilliput`):

   ```bash
   sudo git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git /opt/lilliput
   cd /opt/lilliput
   ```

4. Run the service installer:

   ```bash
   sudo bash scripts/install-service.sh
   sudo systemctl status lilliput --no-pager
   ```

5. Open **`http://YOUR_VM_IP:8788`** in Safari on your iPhone while on your home network. In Safari choose **Share → Add to Home Screen → Open as Web App → Add**.

The default port is **8788** so it does not collide with TinyCiv's old **8787** port. This project is **not** the same as TinyCiv; it uses its own database. Make sure your VM has its own LAN IP and that the VM firewall permits TCP 8788 from your LAN.

**Important:** Apple lets you open an HTTP site as a Home Screen web app, but full browser service-worker functionality requires HTTPS (or localhost). So the basic Home Screen view works over LAN HTTP, while offline shell caching and other more advanced PWA features need HTTPS. The live town itself necessarily needs the server to be reachable.

### Verify / troubleshoot

```bash
sudo systemctl restart lilliput
sudo systemctl status lilliput --no-pager
sudo journalctl -u lilliput -n 60 --no-pager
curl http://127.0.0.1:8788/api/health
curl http://127.0.0.1:8788/api/world
```

A running instance answers `{"ok":true,"version":"0.1.0"}` on `/api/health`. The simulation data lives at `/var/lib/lilliput/lilliput.sqlite`, **outside the Git repo**. Back up that directory if you want to preserve their world.

For local testing without installing a service, run `python3 server.py` from the project directory. That uses `./data/lilliput.sqlite`. The installer copies that local database into `/var/lib/lilliput/` if the service database does not yet exist. Avoid running the same database simultaneously in two processes.

### Update without starting a new town

```bash
cd /opt/lilliput
sudo git pull
sudo systemctl restart lilliput
```

As long as you keep `/var/lib/lilliput/lilliput.sqlite`, the residents stay the same. This app intentionally has **no** endpoint that resets the town.

## Optional AI decisions with Ollama

The regular simulation works without AI, APIs, GPUs, internet, subscriptions, or token costs. If you later install and configure a local Ollama model on your network, the backend can occasionally ask it which leisure activity a resident prefers and for one brief inner thought. Each thought is associated with the resident's personality, goal, friends, recent diary, and needs.

1. Set up Ollama independently and pull a model suited to your server hardware.
2. Create an `.env` file in `/opt/lilliput` (copy `.env.example`) containing the two non-comment lines:

   ```ini
   OLLAMA_URL=http://127.0.0.1:11434
   OLLAMA_MODEL=YOUR_INSTALLED_MODEL
   AI_INTERVAL_SECONDS=600
   ```

   The Ollama URL must point to a reachable **local** Ollama API. If the model runs on a different VM, use that VM's IP and configure Ollama's listener carefully; do not expose the model API to the public internet.
3. `sudo systemctl restart lilliput` and check `journalctl -u lilliput -f`.

The AI worker only attempts decisions during the **5 PM–9:59 PM local time** window, choosing at most one pending resident per configured interval, and each resident receives at most one AI-inspired leisure decision per local day. AI failure does **not** stop or slow the normal village simulation. The worker times out on slow or inaccessible Ollama requests.

**Resource note:** Calling 25 language models repeatedly would be wasteful. This project runs **one rules-based simulation** for all 25 and makes occasional LLM calls for richer individual choices. With `OLLAMA_MODEL` omitted, AI calls are **fully disabled**.

## Technical notes

- Python 3.9+ standard library: `http.server`, `sqlite3`, `zoneinfo`, background threads.
- Standalone one-process web server; 15-minute wall-clock steps; downtime reconstruction for up to 7 days when the server restarts. Longer outages resume from the most recent seven days; the sim does not run days faster in normal operation.
- Time zone defaults to `America/New_York`, configurable via `LILLIPUT_TIMEZONE`. A real clock follows local daylight-saving rules.
- Read-only JSON endpoints: `/api/world`, `/api/people/ID`, `/api/chronicle`, `/api/health`.
- The interface has **no login/authentication**. Keep port 8788 on a trusted LAN or VPN, never forward it directly to the internet. Use Tailscale or a properly secured HTTPS reverse proxy for remote use.
- The server is intentionally simple. For exposure outside your private network or multi-user access, add access control, HTTPS, and a hardened production gateway.

Enjoy watching twenty-five tiny strangers make a home. 🌿
