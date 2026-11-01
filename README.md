# JaRPsDynConfig

The rate page the ARK servers read at startup via `?customdynamicconfigurl=` and
`-UseDynamicConfig`. GitHub Pages serves `main` at
**http://ilgamingarksettings.servegame.com/**, so a commit to `main` is the deploy.

The game parses `Key=Value` lines out of the HTML body. Everything else is cosmetic.

## How the numbers are made

```
final rate = rates.base.json (our baseline, already above official)
           x official.rates.json (the official event factor for that setting)
```

Per setting, not one global number, because ARK bumps categories differently: a
typical official post is 2x taming, 2x harvesting, 2x XP, 0.5x mating interval,
2x maturation, 2x hatching, 0.6x cuddle interval, 2x imprinting, 1x hexagon reward.
An interval factor below 1 shrinks our interval, which is the same as speeding it up.

## Why this exists

Rates used to be hand-edited in `index.html` for every event. On 2026-11-01 the live
"2x" page turned out to be wrong in five of nine settings: taming, harvest, XP and
hexagons were at 2x while mating interval, mature, hatch, cuddle and imprint were
still at 4x from the previous event, because rolling a number back meant remembering
every place it had changed.

## Files

| File | What it is |
|---|---|
| `rates.base.json` | Our baseline. Edit only when the baseline itself changes, never for an event. |
| `official.rates.json` | Official event factors, scraped from Discord. Written by the sync job, do not hand-edit. |
| `scripts/parse-official.py` | Reads the newest Official post from the rates channel and writes `official.rates.json`. |
| `scripts/render.mjs` | The only thing that writes `index.html`. |
| `index.html` | Generated. Do not hand-edit. |

## Publishing

Everything runs on the prod box (`steam@192.168.0.27`), because that is where the
Discord bot token and the GitHub SSH key already live:

```
/home/steam/rates-sync.sh --dry-run   # parse, render, show the diff, publish nothing
/home/steam/rates-sync.sh             # publish if the page or the factors changed
```

It pulls, scrapes the newest Official post, renders, and commits plus pushes only
when something actually changed. Log at `/home/steam/rates-sync.log`.

Checking by hand:

```
node scripts/render.mjs --check   # exit 1 if index.html is stale
node scripts/render.mjs --json    # the computed numbers
python3 scripts/parse-official.py # the parsed official factors
```

## Triggering it

Discord has no "new message in this channel" webhook, so there are only two ways to
react to a post:

- **Poll** — a cron on the prod box runs `rates-sync.sh` every few minutes. Simple,
  no extra moving parts, up to a few minutes late. This is what is installed.
- **Push** — a bot connected to the Discord gateway receives `MESSAGE_CREATE` the
  instant a post lands and calls the same script. Instant, but it means running a
  long-lived listener alongside the Controller Bot.

Either way the work is the same script, so switching is a one-line change.

## Source channel

`#official-ark-server-rates` (`1352482363518750720`) in KPInc425 Test Server. It
follows ARK's rate feed and posts one embed per server type; only the embed titled
"Official server rates updated at ..." is used, and a post is rejected unless all
nine settings parse.
