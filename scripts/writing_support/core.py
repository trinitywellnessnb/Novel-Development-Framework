"""Shared explicit scope, byte provenance, evidence and generated-output boundaries."""
import hashlib
import json
from pathlib import Path
import subprocess
import re

try:
    from validate_review_packet import safe_relative, inspect_source
except ImportError:
    from scripts.validate_review_packet import safe_relative, inspect_source

VERSION = "1.0.0"
AUTHORITIES = {"approved-canon", "approved-direction", "approved-manuscript", "draft",
               "interpretation", "proposal", "superseded", "unknown", "test-material"}
CLASSES = {"canon", "direction", "manuscript", "development", "interpretation", "proposal",
           "historical", "governance", "planning", "test"}
EVIDENCE_KEYS = {"path", "sha256", "line_start", "line_end", "excerpt", "authority"}
DEFAULT_AUTHORITY_ORDER = ["approved-direction", "approved-canon", "approved-manuscript",
    "draft", "author-notes", "experimental", "interpretation", "proposal", "superseded", "unknown", "test-material"]

TASKS = {"context", "continuity", "voice", "dialogue", "pov", "handoff", "revision", "reader"}


def literal(text):
    """Render source content literally, preserving embedded fences and relative links as data."""
    size = max([2] + [len(match) for match in re.findall(r"`+", text)]) + 1
    fence = "`" * size
    return fence + "text\n" + text + "\n" + fence


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def source_path(root, name):
    rel = safe_relative(name)
    target = Path(root)
    for part in rel.parts:
        target /= part
        if target.is_symlink():
            raise ValueError("Symlink source rejected: " + name)
    if not target.is_file():
        raise ValueError("Missing source: " + name)
    return target


def output_path(root, name):
    """Every generated output is local and ignored, even for an absolute CLI path."""
    root = Path(root).resolve()
    path = Path(name)
    if path.is_absolute():
        try:
            name = path.relative_to(root).as_posix()
        except ValueError as exc:
            raise ValueError("Output must be inside .writing-support/") from exc
    rel = safe_relative(str(name))
    if rel.parts[0] != ".writing-support" or len(rel.parts) < 2:
        raise ValueError("Output must be inside .writing-support/")
    target = root
    for part in rel.parts:
        target /= part
        if target.is_symlink():
            raise ValueError("Symlink output rejected")
    return target


def ensure_derived(root):
    """Make local output ignore protection concrete without touching author rules."""
    marker = output_path(root, ".writing-support/.gitignore")
    marker.parent.mkdir(parents=True, exist_ok=True)
    if marker.exists():
        if marker.read_text(encoding="utf-8").strip() != "*":
            raise ValueError("Derived .gitignore needs a sole * rule; preserve artifacts and repair it explicitly")
    else:
        with marker.open("x", encoding="utf-8") as handle:
            handle.write("*\n")
    return marker.parent


def write_json(root, name, value):
    path = output_path(root, name)
    ensure_derived(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    return path


def write_text(root, name, value):
    path = output_path(root, name)
    ensure_derived(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(value)
    return path


def git_info(root, path=None):
    def run(args):
        proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
        return proc.stdout.strip() if proc.returncode == 0 else None
    return {"branch": run(["branch", "--show-current"]), "head": run(["rev-parse", "HEAD"]),
            "source_revision": run(["log", "-1", "--format=%H", "--", path]) if path else None}


def verify_evidence(root, ref):
    if not isinstance(ref, dict) or not EVIDENCE_KEYS <= ref.keys():
        raise ValueError("Evidence requires path/hash/line span/exact excerpt/authority")
    if not isinstance(ref["authority"], str) or not ref["authority"].strip():
        raise ValueError("Authority label required")
    if not isinstance(ref["excerpt"], str) or not ref["excerpt"].strip():
        raise ValueError("Evidence must quote a nonempty supporting passage")
    # Reuse the repository's bounded UTF-8/hash/span validator, preserving all its guards.
    inspect_source(Path(root), {k: ref[k] for k in EVIDENCE_KEYS}, [ref["path"]], True)


def snapshot(root, selection, synthetic=False, approved_authorities=()):
    if not isinstance(selection, dict) or "path" not in selection:
        raise ValueError("Source selection needs an exact path")
    name = selection["path"]
    rel = safe_relative(name)
    if rel.parts[0] in {".writing-support", ".git", "_inbox", "_private"}:
        raise ValueError("Excluded source boundary: " + name)
    if rel.parts[0] == "tests" and not synthetic:
        raise ValueError("Test sources require --synthetic")
    if selection.get("source_class", "unknown") not in CLASSES:
        raise ValueError("Explicit source_class required: " + name)
    raw = source_path(root, name).read_bytes()
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("Source exceeds 4 MiB: " + name)
    lines = raw.decode("utf-8").splitlines()
    start, end = selection.get("line_start", 1), selection.get("line_end", len(lines))
    if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
        raise ValueError("Invalid selected source span: " + name)
    ref = {"path": name, "sha256": hashlib.sha256(raw).hexdigest(), "line_start": start,
           "line_end": end, "excerpt": "\n".join(lines[start - 1:end]),
           "authority": selection.get("authority", "unknown"),
           "source_class": selection["source_class"], "revision": git_info(root, name)["source_revision"],
           "applicability": selection.get("applicability", {}),
           "supersedes": selection.get("supersedes", []),
           "extraction_confidence": selection.get("extraction_confidence", "not-extracted"),
           "reason": selection.get("reason", "explicit task selection"),
           "critical": selection.get("critical", False),
           "approval_status": "unapproved",
           "account": selection.get("account", "unspecified"),
           "review_scope": selection.get("review_scope", "selected span")}
    verify_evidence(root, ref)
    # Authority is a configured claim with evidence, never a directory/date heuristic.
    approval = selection.get("authority_evidence")
    if ref["authority"].startswith("approved-") or ref["authority"] in approved_authorities:
        if not approval:
            raise ValueError("Approved authority requires supporting authority_evidence: " + name)
        if not isinstance(approval, dict):
            raise ValueError("authority_evidence must be a source selection")
        authority_ref = snapshot(root, {**approval, "authority": "unknown"}, synthetic)
        ref["authority_evidence"] = authority_ref
        ref["approval_status"] = "approval-evidence-linked"
    return ref


def validate_config(config):
    """Validate the stable, dependency-free project interface before reading sources."""
    if not isinstance(config, dict) or type(config.get("schema_version")) is not int or config["schema_version"] != 1:
        raise ValueError("Configuration needs schema_version 1")
    if not isinstance(config.get("sources"), list):
        raise ValueError("Configuration needs explicit sources")
    if not isinstance(config.get("books", {}), dict):
        raise ValueError("books must map project identifiers to settings")
    for key in ("authority_order", "approved_authorities"):
        values = config.get(key, [])
        if (not isinstance(values, list) or not all(isinstance(v, str) and v.strip() for v in values)
                or len(values) != len(set(values))):
            raise ValueError(key + " must contain unique text labels")
    for item in config["sources"]:
        if not isinstance(item, dict) or "path" not in item:
            raise ValueError("Each source must be an object with an exact path")
        safe_relative(item["path"])
        if not isinstance(item.get("applicability", {}), dict):
            raise ValueError("Source applicability must be an object")
        for key in ("books", "scenes", "chapters", "viewpoints", "characters", "times", "tasks", "phases"):
            values = item.get("applicability", {}).get(key, [])
            if not isinstance(values, list) or any(type(v) not in (str, int) for v in values):
                raise ValueError("Applicability selectors must be lists: " + key)
        if type(item.get("critical", False)) is not bool:
            raise ValueError("Source critical flag must be boolean")
    return config


def build_index(root, config, synthetic=False):
    validate_config(config)
    result = {"schema_version": 1, "tool_version": VERSION, "type": "derived-index",
              "repository": git_info(root), "config_hash": digest(config), "sources": [], "unavailable": []}
    for item in config["sources"]:
        try:
            result["sources"].append(snapshot(root, item, synthetic, config.get("approved_authorities", [])))
        except (OSError, ValueError) as exc:
            result["unavailable"].append({"path": item.get("path"), "reason": str(exc),
                                          "critical": item.get("critical", False)})
    return result


def packet_identity(packet):
    return digest({k: v for k, v in packet.items() if k != "packet_id"})


def validate_packet(root, packet):
    if type(packet.get("schema_version")) is not int or packet.get("schema_version") != 1 or packet.get("tool_version") != VERSION:
        raise ValueError("Unsupported packet version")
    if packet.get("packet_id") != packet_identity(packet):
        raise ValueError("Packet changed: prepare again")
    if packet.get("status") != "PREPARED" or packet.get("task") not in TASKS:
        raise ValueError("Invalid prepared task packet")
    if not isinstance(packet.get("sources"), list) or not packet["sources"]:
        raise ValueError("Packet has no selected evidence")
    config_file = packet.get("configuration_file")
    if config_file:
        raw = source_path(root, config_file["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != config_file["sha256"]:
            raise ValueError("Configuration changed: prepare again")
    bindings = packet.get("input_bindings", [])
    if isinstance(bindings, dict):
        identifier = bindings.get("external")
        if not isinstance(identifier, str) or not re.fullmatch(r"[0-9a-f]{64}", identifier):
            raise ValueError("Invalid input binding identifier")
        bindings = read_json(output_path(root, ".writing-support/bindings/" + identifier + ".json"))
        if digest(bindings) != identifier:
            raise ValueError("Input bindings changed")
    for binding in bindings:
        raw = source_path(root, binding["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != binding["sha256"]:
            raise ValueError("Task input changed: " + binding["path"])
    for dep in packet.get("dependencies", []):
        try:
            raw = source_path(root, dep["path"]).read_bytes()
        except (OSError, ValueError):
            if dep["sha256"] is None:
                continue
            raise ValueError("Relevant source changed: " + dep["path"])
        if hashlib.sha256(raw).hexdigest() != dep["sha256"]:
            raise ValueError("Relevant source changed: " + dep["path"])
    for ref in packet["sources"]:
        verify_evidence(root, ref)
        if ref.get("authority_evidence"):
            verify_evidence(root, ref["authority_evidence"])


def bind_configuration(root, packet, path):
    """Bind file-based tasks to the configuration bytes as well as selected story bytes."""
    path = Path(path).resolve()
    name = path.relative_to(Path(root).resolve()).as_posix()
    raw = source_path(root, name).read_bytes()
    packet["configuration_file"] = {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}
    packet["packet_id"] = packet_identity(packet)
    return packet


def bind_inputs(root, packet, paths):
    """Bind task files; reader packets use an opaque private sidecar identifier."""
    bindings = []
    for path in paths:
        name = Path(path).absolute().relative_to(Path(root).resolve()).as_posix()
        raw = source_path(root, name).read_bytes()
        bindings.append({"path": name, "sha256": hashlib.sha256(raw).hexdigest()})
    if packet["task"] == "reader":
        identifier = digest(bindings)
        out = ".writing-support/bindings/" + identifier + ".json"
        target = output_path(root, out)
        if target.exists():
            if read_json(target) != bindings:
                raise ValueError("Input binding collision")
        else:
            write_json(root, out, bindings)
        packet["input_bindings"] = {"external": identifier}
    else:
        packet["input_bindings"] = bindings
    packet["packet_id"] = packet_identity(packet)
    return packet


def verify_record_evidence(root, value):
    """Validate every evidence array in a structured event/state record, recursively."""
    count = 0
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "evidence":
                if not isinstance(child, list) or not child:
                    raise ValueError("Populated evidence array required")
                for ref in child:
                    verify_evidence(root, ref)
                    count += 1
            else:
                count += verify_record_evidence(root, child)
    elif isinstance(value, list):
        for child in value:
            count += verify_record_evidence(root, child)
    return count
