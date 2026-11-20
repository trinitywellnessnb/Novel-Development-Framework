#!/usr/bin/env python3
"""Read-only verification of an explicitly authorized, source-bound review packet.

Checks identity and anchor existence, not a claim's meaning or author consent.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
PROTECTED = {"_inbox", "archive", "source-archive", "_private"}
MAX_SOURCE_BYTES = 4 * 1024 * 1024


class PacketError(ValueError):
    pass


def safe_relative(name):
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise PacketError("Source path must be a nonempty POSIX-relative path")
    p = PurePosixPath(name)
    if p.is_absolute() or p.as_posix() != name or any(part in (".", "..", ".git") for part in name.split("/")):
        raise PacketError("Unsafe or noncanonical source path: " + name)
    if any(ord(c) < 32 for c in name) or any(c in name for c in "*?[]"):
        raise PacketError("Unsupported source path characters: " + name)
    return p


def inspect_source(root, entry, allowed, allow_protected=False):
    if not isinstance(entry, dict) or set(entry) - {"path", "sha256", "line_start", "line_end", "excerpt", "authority"}:
        raise PacketError("Invalid source entry fields")
    name = entry.get("path")
    rel = safe_relative(name)
    if name not in allowed:
        raise PacketError("Source is outside authorized source scope: " + name)
    if (rel.parts[0] in PROTECTED or "Chapters" in rel.parts) and not allow_protected:
        raise PacketError("Protected source requires --allow-protected: " + name)
    target = root
    for part in rel.parts:
        target = target / part
        if target.is_symlink():
            raise PacketError("Symlink in source path: " + name)
    if not target.is_file():
        raise PacketError("Missing source file: " + name)
    if target.stat().st_size > MAX_SOURCE_BYTES:
        raise PacketError("Source exceeds text verification limit: " + name)
    expected = entry.get("sha256")
    if not isinstance(expected, str) or not SHA256.fullmatch(expected):
        raise PacketError("Source requires lowercase SHA-256: " + name)
    raw = target.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise PacketError("Source SHA-256 mismatch: " + name)
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise PacketError("Source is not UTF-8 text: " + name) from exc
    start, end = entry.get("line_start"), entry.get("line_end")
    if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
        raise PacketError("Missing or out-of-bounds line anchor: " + name)
    excerpt = entry.get("excerpt")
    if excerpt is not None and (not isinstance(excerpt, str) or excerpt not in "\n".join(lines[start - 1:end])):
        raise PacketError("Excerpt not present at stated anchor: " + name)
    if not isinstance(entry.get("authority"), str) or not entry["authority"].strip():
        raise PacketError("Missing source authority label: " + name)
    return name


def validate(root, packet, allow_protected=False):
    if not isinstance(packet, dict) or set(packet) != {"schema_version", "repository_revision", "purpose", "authorized_sources", "sources"}:
        raise PacketError("Review packet has unexpected or missing fields")
    if type(packet["schema_version"]) is not int or packet["schema_version"] != 1:
        raise PacketError("Unsupported review packet version")
    if not isinstance(packet["repository_revision"], str) or not re.fullmatch(r"[0-9a-f]{40}", packet["repository_revision"]):
        raise PacketError("Expected exact 40-character repository revision")
    if not isinstance(packet["purpose"], str) or not packet["purpose"].strip():
        raise PacketError("Review purpose is required")
    allowed = packet["authorized_sources"]
    sources = packet["sources"]
    if not isinstance(allowed, list) or not allowed or not all(isinstance(p, str) for p in allowed) or len(set(allowed)) != len(allowed):
        raise PacketError("authorized_sources must list unique exact paths")
    for name in allowed:
        safe_relative(name)
    if not isinstance(sources, list) or not sources:
        raise PacketError("sources must contain at least one entry")
    seen = set()
    for entry in sources:
        name = inspect_source(root, entry, allowed, allow_protected)
        anchor = (name, entry["line_start"], entry["line_end"])
        if anchor in seen:
            raise PacketError("Duplicate source anchor: " + name)
        seen.add(anchor)
    return len(sources)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--allow-protected", action="store_true", help="Explicitly permit inspection of named inbox, archive or chapter text")
    args = parser.parse_args(argv)
    try:
        with args.packet.open(encoding="utf-8") as handle:
            packet = json.load(handle)
        count = validate(args.root.resolve(), packet, args.allow_protected)
        print(f"PASS: verified {count} source anchor(s) against authorized exact paths and SHA-256")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print("HOLD: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
