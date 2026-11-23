#!/usr/bin/env python3
"""Opt-in, local, versioned framework installation with reviewable upgrades.

Only engineering files in the fixed publication allowlist can be distributed.
Project creative records and project configuration are never synchronized.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import uuid

VERSION = "1.0.0"
SCHEMA = 1
MODULES = {"__init__", "context", "core", "demo", "exporter", "reviews", "structure", "project"}
REQUIRED_RUNTIME = {"scripts/writing_toolkit.py", "scripts/framework_manager.py", "scripts/validate_review_packet.py"}
REQUIRED_RUNTIME |= {"scripts/writing_support/" + name + ".py" for name in MODULES}
TEMPLATES = {"Character", "Session_Handoff", "Review_Report", "Project_Initialization",
    "Relationship", "Canon_Record", "Scene", "Location", "Creator_Interview", "Decision_Record",
    "Review_Packet", "Timeline_Event", "Research_Note", "Writing_Context_Brief", "Beta_Feedback",
    "Source_Manifest", "Plot_Thread", "Atomic_Claim", "Author_Intent", "Narrative_Voice_Guide",
    "Character_Development_Phases", "Worldbuilding_Rules", "Canon_Decisions", "Scene_Context_Brief",
    "Chapter_Outline", "Scene_Outline", "Character_State", "Chapter_Handoff", "Continuity_Review",
    "Voice_Review", "Dialogue_Review", "POV_Review", "Revision_Proposal", "Beta_Reader_Assessment",
    "Simulated_Beta_Assessment", "Manuscript_Export_Manifest"}
ALLOWED = {"scripts/writing_toolkit.py", "scripts/framework_manager.py", "scripts/validate_review_packet.py",
    "LICENSE", "docs/WRITING_SUPPORT.md", "docs/PROJECT_SETUP.md", "docs/FRAMEWORK_UPDATES.md",
    "docs/WRITING_SUPPORT_INVENTORY.md", "docs/WRITING_SUPPORT_VERIFICATION.md", "docs/WRITING_SUPPORT_DEMONSTRATIONS.md",
    "docs/skills/writing-support/SKILL.md", "docs/vendor/writing-support/LICENSE.txt"}
ALLOWED |= {"scripts/writing_support/" + name + ".py" for name in MODULES}
ALLOWED |= {"09_Tools/Templates/" + name + suffix for name in TEMPLATES for suffix in (".md", ".json")}
ALLOWED |= {"tests/fixtures/writing_support/" + name for name in (
    "README.md", "rules.md", "scene.md", "followup.md", "revision.md", "uncertain.md")}


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def _read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON field: " + key)
            result[key] = value
        return result
    return json.loads(_path(path).read_text(encoding="utf-8"), object_pairs_hook=unique)


def _relative(name):
    if not isinstance(name, str) or not name or "\\" in name or any(ord(c) < 32 for c in name):
        raise ValueError("Invalid relative path")
    path = PurePosixPath(name)
    if path.is_absolute() or path.as_posix() != name or any(p in {".", "..", ".git"} for p in name.split("/")):
        raise ValueError("Unsafe relative path: " + name)
    return name


def _path(path):
    """Reject symlinks in every component, including an existing ancestor."""
    path = Path(path).absolute()
    for item in [*reversed(path.parents), path]:
        if item.is_symlink():
            raise ValueError("Symlink path rejected: " + str(item))
    return path


def _version(value):
    if not isinstance(value, str) or not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", value):
        raise ValueError("Expected stable semantic version x.y.z")
    return tuple(map(int, value.split(".")))


def _manifest(value):
    expected = {"distribution_schema", "framework_version", "toolkit_version", "configuration_schema", "python_requires", "files"}
    if not isinstance(value, dict) or set(value) != expected or value["distribution_schema"] != SCHEMA:
        raise ValueError("Unsupported distribution manifest")
    _version(value["framework_version"])
    _version(value["toolkit_version"])
    if type(value["configuration_schema"]) is not int or value["configuration_schema"] < 1:
        raise ValueError("Invalid configuration schema")
    if value["python_requires"] != ">=3.10":
        raise ValueError("Unsupported Python constraint")
    files = value["files"]
    if not isinstance(files, dict) or not REQUIRED_RUNTIME <= set(files):
        raise ValueError("Distribution is missing required toolkit runtime components")
    for name, expected_hash in files.items():
        if _relative(name) not in ALLOWED or not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError("Not an allowed framework engineering file: " + str(name))
    return value


def _tree(root, installed=False):
    root = _path(root)
    manifest = _manifest(_read(root / "manifest.json"))
    expected = set(manifest["files"]) | {"manifest.json"}
    if installed:
        expected.add("install.json")
    expected_dirs = {str(parent) for name in expected for parent in PurePosixPath(name).parents if str(parent) != "."}
    actual = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("Symlink in managed tree")
        if path.is_file():
            name = path.relative_to(root).as_posix()
            # Python's regenerable bytecode is not a project extension.
            if installed and "__pycache__" in path.parts and path.suffix == ".pyc":
                continue
            actual.add(name)
        elif path.is_dir():
            name = path.relative_to(root).as_posix()
            is_cache = installed and path.name == "__pycache__" and path.parent.relative_to(root).as_posix() in expected_dirs
            if name not in expected_dirs and not is_cache:
                raise ValueError("Unmanaged directory in installation: " + name)
        else:
            raise ValueError("Unsupported filesystem entry")
    if actual != expected:
        raise ValueError("Unexpected or missing managed files: " + str(sorted(actual ^ expected)))
    checks = []
    for name, expected_hash in manifest["files"].items():
        raw = (root / name).read_bytes()
        if _hash(raw) != expected_hash:
            raise ValueError("Local modification or damaged distribution: " + name)
        if name.endswith(".py"):
            try:
                compile(raw, name, "exec")
            except (SyntaxError, ValueError) as exc:
                raise ValueError("Python compilation failed: " + name) from exc
    if installed:
        receipt = _read(root / "install.json")
        if not isinstance(receipt, dict) or set(receipt) != {"schema_version", "previous_backup", "previous_fingerprint"} or receipt["schema_version"] != 1:
            raise ValueError("Invalid installation receipt")
        previous, fingerprint = receipt["previous_backup"], receipt["previous_fingerprint"]
        if previous is None:
            if fingerprint is not None:
                raise ValueError("Invalid previous-installation receipt")
        elif not isinstance(previous, str) or not re.fullmatch(r"\.ndf-backups/[0-9a-f]{32}", previous) or not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise ValueError("Unsafe previous-installation receipt")
    checks.append({"check": "manifest scope and content hashes", "status": "PASSED"})
    checks.append({"check": "Python source compilation (no execution)", "status": "PASSED"})
    fingerprint = _hash(_json_bytes({name: _hash((root / name).read_bytes()) for name in sorted(actual)}))
    return {"manifest": manifest, "fingerprint": fingerprint, "validation": checks}


def bundle(source, out):
    source, out = _path(source), _path(out)
    if out.exists():
        raise ValueError("Bundle output already exists")
    cfg = _read(source / "framework.json")
    names = cfg["managed_files"]
    if not isinstance(names, list) or len(names) != len(set(names)):
        raise ValueError("Managed file list must be unique")
    manifest = {"distribution_schema": SCHEMA, "framework_version": cfg["framework_version"],
        "toolkit_version": cfg["toolkit_version"], "configuration_schema": cfg["configuration_schema"],
        "python_requires": cfg["python_requires"], "files": {}}
    data = {}
    for name in names:
        if _relative(name) not in ALLOWED:
            raise ValueError("File is outside framework publication allowlist: " + name)
        path = _path(source / name)
        raw = path.read_bytes()
        if name.endswith(".py"):
            try:
                compile(raw, name, "exec")
            except (SyntaxError, ValueError) as exc:
                raise ValueError("Python compilation failed: " + name) from exc
        data[name] = raw
        manifest["files"][name] = _hash(raw)
    _manifest(manifest)
    out.mkdir(parents=True)
    try:
        for name, raw in data.items():
            target = out / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        (out / "manifest.json").write_bytes(_json_bytes(manifest))
        return _tree(out)
    except Exception:
        shutil.rmtree(out)
        raise


def _project(project):
    project = _path(project)
    if not project.is_dir():
        raise ValueError("Project directory must already exist")
    for name in (".ndf", ".ndf-backups", ".ndf-transaction.json", ".ndf-operation.lock"):
        _path(project / name)
    return project


def version(project):
    project = _project(project)
    info = _tree(project / ".ndf", installed=True)
    return {key: info["manifest"][key] for key in ("framework_version", "toolkit_version", "configuration_schema", "python_requires")}


def _rename(source, destination):
    Path(source).rename(destination)


def _pending(project):
    if (project / ".ndf-transaction.json").exists():
        raise ValueError("Pending transaction: run recover before another operation")


def _stage(distribution, project, previous=None):
    stage = project / (".ndf-stage-" + uuid.uuid4().hex)
    shutil.copytree(distribution, stage)
    receipt = {"schema_version": 1, "previous_backup": previous[0] if previous else None,
               "previous_fingerprint": previous[1] if previous else None}
    (stage / "install.json").write_bytes(_json_bytes(receipt))
    return stage


@contextmanager
def _operation_lock(project):
    """OS advisory lock survives as a file, but releases on process exit."""
    path = _path(project / ".ndf-operation.lock")
    with path.open("a+b") as handle:
        try:
            if sys.platform == "win32":
                import msvcrt
                if path.stat().st_size == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError("Another framework operation is active; retry after it exits") from exc
        try:
            yield
        finally:
            if sys.platform == "win32":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _swap(project, stage, old_fingerprint):
    with _operation_lock(project):
        return _swap_locked(project, stage, old_fingerprint)


def _swap_locked(project, stage, old_fingerprint):
    """Journal before the first rename; interrupted transitions are recoverable."""
    backup_rel = ".ndf-backups/" + uuid.uuid4().hex if old_fingerprint else None
    # Stage receipt names its exact recovery source before calculating its fingerprint.
    receipt = _read(stage / "install.json")
    if old_fingerprint and receipt.get("previous_backup") == "pending":
        receipt["previous_backup"] = backup_rel
        (stage / "install.json").write_bytes(_json_bytes(receipt))
    target = _tree(stage, installed=True)
    journal = {"schema_version": 1, "stage": stage.name, "backup": backup_rel,
        "old_fingerprint": old_fingerprint, "new_fingerprint": target["fingerprint"]}
    journal_path = project / ".ndf-transaction.json"
    try:
        with journal_path.open("xb") as handle:
            handle.write(_json_bytes(journal))
    except FileExistsError as exc:
        shutil.rmtree(stage)
        raise ValueError("Concurrent transaction: recover first") from exc
    try:
        if old_fingerprint:
            if _tree(project / ".ndf", installed=True)["fingerprint"] != old_fingerprint:
                raise ValueError("Installation changed during transaction preparation")
            (project / ".ndf-backups").mkdir(exist_ok=True)
            _rename(project / ".ndf", project / backup_rel)
        elif (project / ".ndf").exists():
            raise ValueError("Installation appeared during transaction preparation")
        _rename(stage, project / ".ndf")
        journal_path.unlink()
    except Exception:
        _recover_locked(project)
        raise
    return {"status": "ADOPTED", "framework_version": target["manifest"]["framework_version"], "backup": backup_rel}


def install(distribution, project):
    distribution, project = _path(distribution), _project(project)
    _pending(project)
    _tree(distribution)
    if (project / ".ndf").exists():
        raise ValueError("Installation already exists; prepare an upgrade plan")
    stage = _stage(distribution, project)
    return _swap(project, stage, None)


def plan(distribution, project):
    distribution, project = _path(distribution), _project(project)
    _pending(project)
    target = _tree(distribution)
    # Baseline metadata is readable even if actual managed files have local changes.
    current_manifest = _manifest(_read(project / ".ndf/manifest.json"))
    conflicts = []
    current = None
    try:
        current = _tree(project / ".ndf", installed=True)
    except (ValueError, OSError) as exc:
        conflicts.append(str(exc))
    old, new = current_manifest["framework_version"], target["manifest"]["framework_version"]
    old_version, new_version = _version(old), _version(new)
    same = current_manifest == target["manifest"]
    if new_version[0] != old_version[0]:
        conflicts.append("Major-version compatibility is untested; manual migration required")
    if target["manifest"]["configuration_schema"] != current_manifest["configuration_schema"]:
        conflicts.append("Configuration schema migration is unavailable")
    if new_version < old_version or (new_version == old_version and not same):
        conflicts.append("Downgrade or changed content under unchanged version")
    affected = [{"path": name, "current_sha256": current_manifest["files"].get(name),
        "target_sha256": target["manifest"]["files"].get(name)}
        for name in sorted(set(current_manifest["files"]) | set(target["manifest"]["files"]))
        if current_manifest["files"].get(name) != target["manifest"]["files"].get(name)]
    result = {"schema_version": 1, "type": "framework-upgrade-proposal",
        "current_version": old, "target_version": new,
        "status": "BLOCKED" if conflicts else ("CURRENT" if same else "READY"),
        "distribution": str(distribution), "distribution_fingerprint": target["fingerprint"],
        "installed_fingerprint": current["fingerprint"] if current else None,
        "files_affected": affected, "configuration_changes": [], "schema_migrations": [],
        "conflicts": conflicts, "project_overrides": conflicts,
        "compatibility_risks": ["Same-major/schema compatibility is structural; project behavior still needs its own tests"],
        "validation_results": target["validation"] + (current["validation"] if current else []),
        "project_tests": "Not executed; no arbitrary project or distribution hooks are run",
        "reversal": "Run rollback --project PROJECT; old installation retained in .ndf-backups/",
        "protected": "Only .ndf/ is managed; creative records and project configuration are untouched"}
    result["plan_id"] = _hash(_json_bytes(result))
    return result


def apply(proposal, project):
    if not isinstance(proposal, dict) or proposal.get("plan_id") != _hash(_json_bytes({k: v for k, v in proposal.items() if k != "plan_id"})):
        raise ValueError("Upgrade plan was modified")
    if proposal.get("status") != "READY":
        raise ValueError("Upgrade plan is not ready")
    project = _project(project)
    refreshed = plan(proposal["distribution"], project)
    if refreshed != proposal:
        raise ValueError("Installation or candidate changed since planning; prepare again")
    stage = _stage(proposal["distribution"], project, ("pending", proposal["installed_fingerprint"]))
    return _swap(project, stage, proposal["installed_fingerprint"])


def rollback(project):
    project = _project(project)
    _pending(project)
    current = _tree(project / ".ndf", installed=True)
    receipt = _read(project / ".ndf/install.json")
    name = receipt.get("previous_backup")
    if not isinstance(name, str) or not re.fullmatch(r"\.ndf-backups/[0-9a-f]{32}", name):
        raise ValueError("No recorded previous installation")
    previous = _tree(project / name, installed=True)
    if previous["fingerprint"] != receipt.get("previous_fingerprint"):
        raise ValueError("Backup changed; rollback refused")
    stage = project / (".ndf-stage-" + uuid.uuid4().hex)
    shutil.copytree(project / name, stage)
    return _swap(project, stage, current["fingerprint"])


def recover(project):
    project = _project(project)
    with _operation_lock(project):
        return _recover_locked(project)


def _recover_locked(project):
    journal_path = project / ".ndf-transaction.json"
    if not journal_path.exists():
        return {"status": "NO_PENDING_TRANSACTION"}
    journal = _read(journal_path)
    stage_name, backup_name = journal.get("stage"), journal.get("backup")
    if journal.get("schema_version") != 1 or not isinstance(stage_name, str) or not re.fullmatch(r"\.ndf-stage-[0-9a-f]{32}", stage_name):
        raise ValueError("Unrecognized transaction journal; preserve it for manual recovery")
    if backup_name is not None and (not isinstance(backup_name, str) or not re.fullmatch(r"\.ndf-backups/[0-9a-f]{32}", backup_name)):
        raise ValueError("Unsafe backup in transaction journal")
    live, stage = project / ".ndf", _path(project / stage_name)
    backup = _path(project / backup_name) if backup_name else None
    old, new = journal.get("old_fingerprint"), journal.get("new_fingerprint")
    # Check staging before restoring or removing any tree.
    if stage.exists() and _tree(stage, installed=True)["fingerprint"] != new:
        raise ValueError("Staging tree changed; preserve for manual recovery")
    if live.exists():
        actual = _tree(live, installed=True)["fingerprint"]
        if actual == new:
            # The second rename completed; keeping the verified new tree is safe.
            journal_path.unlink()
            return {"status": "COMPLETED_PENDING_TRANSACTION"}
        if actual != old or (backup and backup.exists()):
            raise ValueError("Ambiguous recovery state; no files altered")
    elif backup and backup.exists():
        if _tree(backup, installed=True)["fingerprint"] != old:
            raise ValueError("Recovery backup changed; no files altered")
        _rename(backup, live)
    elif old is not None:
        raise ValueError("Recovery source unavailable; no files altered")
    if stage.exists():
        shutil.rmtree(stage)
    journal_path.unlink()
    return {"status": "RESTORED_PREVIOUS_INSTALLATION"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("bundle")
    p.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--out", type=Path, required=True)
    for command in ("install", "check", "plan"):
        p = sub.add_parser(command)
        p.add_argument("--distribution", type=Path, required=True)
        p.add_argument("--project", type=Path, required=True)
        if command == "plan":
            p.add_argument("--out", default=".writing-support/framework-upgrade.json")
    p = sub.add_parser("apply")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--project", type=Path, required=True)
    for command in ("version", "rollback", "recover"):
        p = sub.add_parser(command)
        p.add_argument("--project", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "bundle":
            result = bundle(args.source, args.out)
        elif args.command == "install":
            result = install(args.distribution, args.project)
        elif args.command in {"plan", "check"}:
            result = plan(args.distribution, args.project)
            if args.command == "plan":
                name = _relative(args.out)
                if not name.startswith(".writing-support/"):
                    raise ValueError("Plans must remain in .writing-support/")
                target = _path(_project(args.project) / name)
                target.parent.mkdir(parents=True, exist_ok=True)
                marker = _path(args.project / ".writing-support/.gitignore")
                if marker.exists():
                    if marker.read_bytes() != b"*\n":
                        raise ValueError("Derived output ignore marker was modified; preserve it and resolve before writing plans")
                else:
                    with marker.open("xb") as handle:
                        handle.write(b"*\n")
                with target.open("xb") as handle:
                    handle.write(_json_bytes(result))
        elif args.command == "apply":
            result = apply(_read(_path(args.plan)), args.project)
        else:
            result = {"version": version, "rollback": rollback, "recover": recover}[args.command](args.project)
        print(json.dumps(result, indent=2))
        return int(result.get("status") == "BLOCKED")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("HOLD: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
