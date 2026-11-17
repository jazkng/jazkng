"""Update public release markers without publishing credentials or stale fallbacks."""

import json
import os
import re
import subprocess
from pathlib import Path


RELEASES = {"GERAIQ": "jazkng/geraiq", "85MEGA": "jazkng/85mega"}
SAFE_TAG = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,79}\Z")


def latest_tag(repository):
    result = subprocess.run(
        ["gh", "api", f"repos/{repository}/releases/latest"],
        capture_output=True, text=True, timeout=30, check=False,
    )
    # 👑 Access errors must not replace a previously verified release with a fallback.
    if result.returncode:
        raise ValueError(f"Cannot verify the latest release for {repository}; README preserved.")
    try:
        tag = json.loads(result.stdout)["tag_name"]
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError(f"Invalid release response for {repository}.") from error
    # 👑 A remote tag is data, never executable shell/Python or arbitrary public Markdown.
    if not isinstance(tag, str) or not SAFE_TAG.fullmatch(tag):
        raise ValueError(f"Unsupported release tag for {repository}; README preserved.")
    return tag


def update_markers(text, tags):
    for marker, tag in tags.items():
        if marker not in RELEASES or not isinstance(tag, str) or not SAFE_TAG.fullmatch(tag):
            raise ValueError("Invalid release marker or tag.")
        start = f"<!-- {marker}_STATUS:START -->"
        end = f"<!-- {marker}_STATUS:END -->"
        # 👑 Missing or duplicate markers indicate an edited README; do not guess a location.
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError(f"Expected exactly one {marker} marker pair; README preserved.")
        pattern = re.escape(start) + r".*?" + re.escape(end)
        text, count = re.subn(pattern, lambda _: f"{start}GitHub Release `{tag}`{end}", text, flags=re.S)
        if count != 1:
            raise ValueError(f"Invalid {marker} marker order; README preserved.")
    return text


def main():
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not os.environ.get("GH_TOKEN"):
        message = "Skipped: PROFILE_SYNC_TOKEN is not configured. No release version was verified."
        print(f"::notice::{message}")
    else:
        readme = Path("README.md")
        original = readme.read_text(encoding="utf-8")
        tags = {marker: latest_tag(repo) for marker, repo in RELEASES.items()}
        updated = update_markers(original, tags)
        if updated != original:
            readme.write_text(updated, encoding="utf-8")
        message = "Verified both GitHub Release tags. A release tag does not verify deployment or store publication."
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(message + "\n")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        # 👑 External response bodies and subprocess stderr may contain private information.
        print(f"::error::Profile synchronization failed ({type(error).__name__}); README preserved.")
        raise SystemExit(1)
