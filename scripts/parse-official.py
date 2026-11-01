#!/usr/bin/env python3
"""
Scrape the official ARK event rates from Discord and write official.rates.json.

Source: the #official-ark-server-rates channel, which follows ARK's rate feed. One
message can carry several embeds (Official, Arkpocalypse, Smalltribes, seasonal);
only the embed whose title starts with "Official" is used.

Discord offers no "new message in channel" webhook, so this is driven either by a
cron (see rates-sync.sh) or by a gateway listener that calls it on messageCreate.

Usage:
    python3 scripts/parse-official.py            # print the parsed rates as JSON
    python3 scripts/parse-official.py --write    # write official.rates.json
    python3 scripts/parse-official.py --check    # exit 1 if a newer official post exists
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

CHANNEL = "1352482363518750720"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(REPO_ROOT, "official.rates.json")

LABELS = {
    "taming": "TamingSpeedMultiplier",
    "harvesting": "HarvestAmountMultiplier",
    "xp": "XPMultiplier",
    "mating interval": "MatingIntervalMultiplier",
    "maturation": "BabyMatureSpeedMultiplier",
    "hatching": "EggHatchSpeedMultiplier",
    "cuddle interval": "BabyCuddleIntervalMultiplier",
    "imprinting": "BabyImprintAmountMultiplier",
    "hexagon reward": "HexagonRewardMultiplier",
}


def token():
    """Bot token, from the environment or the Controller Bot's env file."""
    if os.environ.get("DISCORD_TOKEN"):
        return os.environ["DISCORD_TOKEN"]
    env_paths = [
        os.path.expanduser("~/nodejs/discord-bot/.env"),
        "/home/steam/nodejs/discord-bot/.env",
    ]
    for path in env_paths:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if line.startswith("DISCORD_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("No DISCORD_TOKEN in the environment or the bot env file")


def fetch(limit=25):
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{CHANNEL}/messages?limit={limit}",
        headers={"Authorization": "Bot " + token(), "User-Agent": "DynConfigRates/1.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


def parse_embed(embed):
    """{setting: factor} for an Official embed, or None if this is not one."""
    title = (embed.get("title") or "").strip()
    if not title.lower().startswith("official"):
        return None
    found = {}
    for raw in (embed.get("description") or "").splitlines():
        line = raw.replace("**", "").strip()
        match = re.match(r"^([0-9]*\.?[0-9]+)\s*[x×]\s*(.+?)$", line, re.I)
        if not match:
            continue
        key = LABELS.get(match.group(2).strip().lower())
        if key:
            found[key] = float(match.group(1))
    # Only trust a complete post: a partial one would silently drop a setting.
    return found if len(found) == len(LABELS) else None


def latest_official(messages):
    """Newest message carrying an Official embed."""
    for msg in messages:  # Discord returns newest first
        for embed in msg.get("embeds", []):
            parsed = parse_embed(embed)
            if parsed:
                return {
                    "source": "discord",
                    "channel_id": CHANNEL,
                    "source_message_id": msg["id"],
                    "posted_at": msg["timestamp"],
                    "title": embed["title"],
                    "multipliers": parsed,
                }
    return None


def write_doc(doc, path):
    out = {
        "_comment": (
            "Official ARK event factors, scraped from the #official-ark-server-rates "
            "channel by scripts/parse-official.py. Final rate = rates.base.json base x "
            "these factors, per setting. Written by the sync job; do not hand-edit."
        ),
        **doc,
    }
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(out, handle, indent=2)
        handle.write("\n")


def main():
    args = sys.argv[1:]
    found = latest_official(fetch())
    if not found:
        print("No complete Official rates post in the last 25 messages", file=sys.stderr)
        return 2

    if "--write" in args:
        found["updated_at"] = subprocess.run(
            ["date", "-u", "+%Y-%m-%d"], capture_output=True, text=True
        ).stdout.strip()
        write_doc(found, TARGET)
        print(f"wrote official.rates.json from message {found['source_message_id']}")
        return 0

    if "--check" in args:
        try:
            with open(TARGET, encoding="utf-8") as handle:
                current = json.load(handle)
        except FileNotFoundError:
            print("official.rates.json is missing", file=sys.stderr)
            return 1
        if current.get("source_message_id") == found["source_message_id"]:
            print("official.rates.json is current")
            return 0
        print(f"newer official post available: {found['source_message_id']}", file=sys.stderr)
        return 1

    print(json.dumps(found, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
