#!/usr/bin/env python3
"""Sync the separate Norma Go module from the public Go module proxy.

The default build path checks for a newer stable Norma release and updates the
nested ./norma module plus the root go.mod requirement. Set NORMA_AUTO_SYNC=0
for reproducible/offline builds, or NORMA_VERSION=vX.Y.Z to pin a version.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

MODULE = "github.com/Autumn-27/norma"
PROXY_MODULE = "github.com/!autumn-27/norma"
PROXY_BASE = f"https://proxy.golang.org/{PROXY_MODULE}/@v"
ROOT = Path(__file__).resolve().parents[1]
NORMA = ROOT / "norma"
VERSION_FILE = NORMA / "VERSION"
VERSION_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def http_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "artex-robot-norma-sync"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def stable_versions() -> list[str]:
    versions = []
    for raw in http_bytes(f"{PROXY_BASE}/list").decode("utf-8").splitlines():
        raw = raw.strip()
        if VERSION_RE.fullmatch(raw):
            versions.append(raw)
    return sorted(versions, key=lambda v: tuple(int(x) for x in VERSION_RE.fullmatch(v).groups()))


def current_version() -> str:
    if not VERSION_FILE.exists():
        return ""
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def latest_or_pinned() -> str:
    pinned = os.environ.get("NORMA_VERSION", "").strip()
    if pinned:
        if not VERSION_RE.fullmatch(pinned):
            raise ValueError(f"NORMA_VERSION 不是稳定三段版本：{pinned}")
        return pinned
    versions = stable_versions()
    if not versions:
        raise RuntimeError("Go Module Proxy 没有返回稳定 Norma 版本")
    return versions[-1]


def safe_extract(data: bytes, target: Path, expected_root: str) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        prefix = expected_root + "/"
        for name in names:
            if not name.startswith(prefix) or ".." in Path(name).parts:
                raise RuntimeError(f"Norma archive contains an unsafe path: {name}")
        archive.extractall(target)


def update_root_go_mod(version: str) -> None:
    path = ROOT / "go.mod"
    text = path.read_text(encoding="utf-8")
    pattern = r"(github\.com/Autumn-27/norma\s+)v\d+\.\d+\.\d+"
    updated, count = re.subn(pattern, rf"\g<1>{version}", text, count=1)
    if count != 1:
        raise RuntimeError("go.mod does not contain the Norma requirement")
    path.write_text(updated, encoding="utf-8", newline="\n")


def sync(version: str) -> bool:
    current = current_version()
    if current == version:
        print(f"Norma {version} already present; no sync needed.")
        return False

    archive_url = f"{PROXY_BASE}/{version}.zip"
    info_url = f"{PROXY_BASE}/{version}.info"
    archive = http_bytes(archive_url)
    info = json.loads(http_bytes(info_url).decode("utf-8"))
    expected_root = f"github.com/Autumn-27/norma@{version}"

    with tempfile.TemporaryDirectory(prefix="artex-norma-") as temp_name:
        temp = Path(temp_name)
        safe_extract(archive, temp, expected_root)
        extracted = temp / expected_root
        if not (extracted / "go.mod").exists():
            raise RuntimeError("Norma archive has no go.mod")
        source = {
            "module": MODULE,
            "version": version,
            "source": archive_url,
            "origin_commit": info.get("Origin", {}).get("Hash", ""),
            "archive_sha256": hashlib.sha256(archive).hexdigest(),
        }
        (extracted / "VERSION").write_text(version + "\n", encoding="utf-8", newline="\n")
        (extracted / "SOURCE.json").write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        next_dir = ROOT / "norma.next"
        if next_dir.exists():
            shutil.rmtree(next_dir)
        shutil.copytree(extracted, next_dir)
        if NORMA.exists():
            shutil.rmtree(NORMA)
        next_dir.rename(NORMA)

    update_root_go_mod(version)
    print(f"Synced Norma {current or '(missing)'} -> {version} ({source['origin_commit']}).")
    print(f"Archive SHA-256: {source['archive_sha256']}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true", help="select the latest stable proxy version")
    parser.add_argument("--check", action="store_true", help="check whether a newer stable version exists")
    args = parser.parse_args()
    try:
        target = latest_or_pinned() if args.auto or args.check or os.environ.get("NORMA_VERSION") else current_version()
        if not target:
            target = latest_or_pinned()
        current = current_version()
        if args.check:
            if current == target:
                print(f"Norma is current: {current}")
                return 0
            print(f"Norma update available: {current or '(missing)'} -> {target}")
            return 1
        if current == target:
            print(f"Norma {current} already present; no sync needed.")
            return 0
        sync(target)
        return 0
    except (OSError, urllib.error.URLError, ValueError, RuntimeError) as error:
        if os.environ.get("NORMA_AUTO_SYNC", "1") != "0" and current_version():
            print(f"Warning: Norma auto-sync skipped: {error}", file=sys.stderr)
            return 0
        print(f"Norma sync failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
