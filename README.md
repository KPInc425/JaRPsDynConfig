# JaRPsDynConfig

The rate page the ARK servers read at startup via `?customdynamicconfigurl=` and
`-UseDynamicConfig`. GitHub Pages serves the `main` branch at
**http://ilgamingarksettings.servegame.com/**, so a commit to `main` is the deploy.

The game parses `Key=Value` lines out of the HTML body. Everything else on the page
is cosmetic.

## Why this exists

Rates used to be edited by hand in `index.html` for every event. On 2026-11-01 the
live "2x" page turned out to be four-ninths wrong: taming, harvest, XP and hexagons
were at 2x, while mating interval, baby mature, egg hatch, imprint cuddle and imprint
amount were still sitting at 4x levels from the previous event, because rolling a
number back meant remembering every place it had been changed.

Now there is one source of truth and one writer.

## Files

| File | What it is |
|---|---|
| `rates.base.json` | Our baseline rates, already higher than official. `mode` says whether an event bump multiplies the value or divides it (intervals divide, so the action gets faster). |
| `multiplier.json` | The official event bump. `1` = no event, `1.5`, `2`, `3`, `4` as official runs them. This is the only number that changes between events. |
| `scripts/render.mjs` | The only thing that writes `index.html`. |
| `index.html` | Generated. Do not hand-edit. |

## Changing rates for an official event

GitHub UI: **Actions -> Publish dynamic rates -> Run workflow**, set `multiplier` to
the official bump and `label` to something readable. It renders, verifies, and commits
`index.html` + `multiplier.json`, which is what deploys.

Locally, the same thing:

```bash
node scripts/render.mjs --multiplier 2   # render at the official 2x bump
node scripts/render.mjs --check          # fail if index.html is stale (CI gate)
node scripts/render.mjs --json           # print the computed numbers, write nothing
git add index.html multiplier.json && git commit -m "rates: official 2x" && git push
```

Edit `rates.base.json` only when the baseline itself changes, not for events.

## Verifying what a server is actually running

```bash
curl -s http://ilgamingarksettings.servegame.com/ | sed -e 's/<[^>]*>//g' | grep '='
```

Compare that to `node scripts/render.mjs --json`.

## Automating the official bump

`multiplier.json.source` records where the current value came from (`manual`,
`workflow_dispatch`, or a tracker). To drive it from the channel that tracks official
rates, a scheduled workflow needs two things:

1. The channel ID of the official-rate tracker.
2. A `DISCORD_BOT_TOKEN` repository secret with read access to that channel.

With those, the workflow can fetch the latest official multiplier, compare it to
`multiplier.json`, and only render and commit when it actually changed.
