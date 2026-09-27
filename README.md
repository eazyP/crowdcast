# Crowdcast

A synthetic AI live-chat crowd for a stream that doesn't have one yet. Open `index.html` and it's already live: a scrolling feed of chat reactions, follow/sub-style alerts, and a slowly drifting viewer count, all generated from a large pool of hand-written message templates so it doesn't read like the same few lines on a loop.

No build step, no dependencies, no server. It's a single static HTML file.

## Running it

Open `index.html` in any browser, or serve the folder with anything that serves static files:

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

## Using it as a stream overlay

1. In OBS (or your streaming software of choice), add a **Browser Source**.
2. Point it at `index.html` (a local file URL) or wherever you're hosting it.
3. Size the source to fit your layout.
4. Open the settings gear on the page and turn on **Overlay Mode** — this drops the panel background, border, and topbar chrome so only the floating chat messages show.

## Settings

- **Stream topic** / **Streamer's name** — get woven into the chat templates (`"{topic} chat rise up"`, `"{streamer} really cooked with that one"`).
- **Chat pace** — Chill, Normal, or Hype, controlling how often new messages land.
- **Text size** — tune legibility for whatever resolution you're capturing at.
- **Accent** — four color options for usernames, badges, and highlights.
- **Starting viewer count** — the number the live counter drifts from.
- **Trigger hype moment** — manually fires a raid-style burst with a viewer count jump.

Settings are saved to `localStorage` in your browser, so they persist between sessions on the same device.

## License

MIT — see [LICENSE](LICENSE).
