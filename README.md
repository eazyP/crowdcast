# Crowdcast

A synthetic AI live-chat crowd for a stream that doesn't have one yet. Open `index.html` and it's already live: a scrolling feed of chat reactions, follow/sub-style alerts, and a slowly drifting viewer count, all generated from a large pool of hand-written message templates so it doesn't read like the same few lines on a loop.

No build step, no dependencies. It's a static HTML file, plus an optional OBS script for controlling it without leaving OBS.

## Running it standalone

Open `index.html` in any browser, or serve the folder with anything that serves static files:

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

## Using it in OBS

There are two ways to run this as a stream overlay:

### Option A — the OBS script (recommended)

1. In OBS: **Tools > Scripts** > the **+** button > select `obs_crowdcast.py`. OBS needs a Python install configured under the "Python Settings" tab first (Windows/Linux; macOS OBS ships its own).
2. In the script's properties panel:
   - Set **Crowdcast folder** to this folder (the one with `index.html`).
   - Click **Create Crowdcast source** to add a ready-sized Browser Source to your current scene.
   - Set the stream topic, streamer's name, chat pace, text size, theme, starting viewer count, and overlay mode.
   - Most fields apply immediately; use **Apply to browser source** to force it.
3. Toggle **Overlay mode** on to drop the panel background, border, and topbar so only the floating chat messages show — the state you actually want on stream.

The script runs a small local web server (`127.0.0.1`, port configurable) so it can pass your settings to the page as a URL, and points the browser source at it. It doesn't make any network connections of its own beyond that.

### Option B — a plain Browser Source, by hand

1. Add a **Browser Source** in OBS.
2. Point it at `index.html` (a local file, or wherever you're hosting it), optionally with settings baked into the URL:
   ```
   index.html?topic=Valorant&streamer=Dana&pace=hype&accent=auto&overlay=1
   ```
3. Size the source to fit your layout.
4. Open the settings gear on the page itself and turn on **Overlay Mode** if you didn't pass `overlay=1`.

## Settings

- **Stream topic** / **Streamer's name** — woven into the chat templates (`"{topic} chat rise up"`, `"{streamer} really cooked with that one"`).
- **Chat pace** — Chill, Normal, or Hype, controlling how often new messages land.
- **Text size** — tune legibility for whatever resolution you're capturing at.
- **Theme** — Amber, Sky, Orchid, or Mint, or **Auto**, which changes the accent across the day (morning → sky, day → amber, evening → orchid, night → mint) using the local clock, so a long-running stream isn't lit the same way at 2pm and 2am.
- **Starting viewer count** — the number the live counter drifts from.
- **Trigger hype moment** — manually fires a raid-style burst with a viewer count jump.

Opened directly in a browser, settings are saved to `localStorage` and persist between visits. Driven by the OBS script or a URL, the URL wins.

## License

MIT — see [LICENSE](LICENSE).
