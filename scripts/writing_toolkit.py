#!/usr/bin/env python3
"""Local writing support: explicit source scope, native reviews and reproducible exports."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from writing_support.core import (VERSION, TASKS, build_index, read_json, validate_packet,
                                  verify_record_evidence, write_json, write_text, output_path, bind_configuration, bind_inputs, ensure_derived)
from writing_support.context import prepare, render_brief


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--config", default="09_Tools/Writing_Support.json")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("version", help="Show installed toolkit/schema compatibility")
    q = sub.add_parser("init", help="Initialize a project without overwriting existing files")
    q.add_argument("--title", required=True)
    q.add_argument("--author", default="")
    q.add_argument("--genre", default="")
    q.add_argument("--book", action="append", default=[], help="ID=Title; repeat for a series")
    q.add_argument("--options", help="Project options JSON file")
    sub.add_parser("doctor", help="Inspect configured sources and optional dependencies; no prose output")
    sub.add_parser("demo", help="Prepare clearly synthetic examples; never generate model answers")
    q = sub.add_parser("index", help="Snapshot explicit configured source spans; derived, never canon")
    q.add_argument("--synthetic", action="store_true")
    q.add_argument("--out", default=".writing-support/index.json")
    q = sub.add_parser("prepare", help="PREPARED packet + Markdown brief + native instructions/template")
    q.add_argument("--request", required=True, help="JSON: book, scene, viewpoint, task, constraints, optional budget")
    q.add_argument("--synthetic", action="store_true")
    q.add_argument("--out", default=".writing-support/context/packet.json")
    q = sub.add_parser("check", help="Reject stale packet or revision original; evidence validity only")
    q.add_argument("--packet", required=True)
    q.add_argument("--result", help="Also check bounded revision proposal")
    q = sub.add_parser("accept", help="Validate native result, retain dispositions, render local report")
    q.add_argument("--packet", required=True)
    q.add_argument("--result", required=True)
    q.add_argument("--previous", help="Prior validated report, including manual author dispositions")
    q.add_argument("--out", default=".writing-support/reviews/report.json")
    q = sub.add_parser("native", help="Run existing Codex CLI in a fresh session; reader retrieval isolation is unavailable")
    q.add_argument("--packet", required=True)
    q.add_argument("--out", default=".writing-support/native/result.json")
    q = sub.add_parser("chronology", help="Check explicit event/clock/reveal constraints, render comparison/planning table")
    q.add_argument("--input", required=True)
    q.add_argument("--out", default=".writing-support/chronology/report.json")
    q = sub.add_parser("states", help="Compare source-backed entry/change/exit states and explicit phase rules")
    q.add_argument("--input", required=True)
    q.add_argument("--out", default=".writing-support/states/report.json")
    q = sub.add_parser("export", help="Build ordered manifest through Pandoc; never publish")
    q.add_argument("--manifest", required=True)
    q.add_argument("--preview", action="store_true", help="Explicit unapproved draft preview")
    q.add_argument("--out", default=".writing-support/exports/build")
    q = sub.add_parser("epubcheck", help="Run installed EPUBCheck; skipped is never validated")
    q.add_argument("--input", required=True)
    return p


def resolve(root, name):
    path = Path(name)
    return path if path.is_absolute() else root / path


def save_pair(root, out, record, markdown):
    path = output_path(root, out)
    for target in (path, path.with_suffix(".md")):
        if target.exists():
            raise FileExistsError("Output exists; select a new --out: " + str(target))
    path = write_json(root, out, record)
    write_text(root, str(path.with_suffix(".md")), markdown)
    return path


def main(argv=None):
    args = parser().parse_args(argv)
    root = args.root.resolve()
    try:
        cmd = args.command
        if cmd == "version":
            print(json.dumps({"framework_version": VERSION, "toolkit_version": VERSION,
                "configuration_schema": 1, "packet_schema": 1, "python_minimum": "3.10"}))
            return 0
        if cmd == "init":
            from writing_support.project import init_project
            books = None
            if args.book:
                books = {}
                for value in args.book:
                    identifier, separator, title = value.partition("=")
                    if identifier in books:
                        raise ValueError("Duplicate book identifier")
                    books[identifier] = title if separator else identifier
            record = init_project(root, args.title, args.author, books, args.genre,
                                  read_json(resolve(root, args.options)) if args.options else None)
            print(json.dumps(record, indent=2))
            return 0
        if cmd == "doctor":
            from writing_support.exporter import dependency_status
            index = build_index(root, read_json(resolve(root, args.config)))
            print(json.dumps({"tool_version": VERSION, "python": sys.version.split()[0],
                "codex_cli": bool(shutil.which("codex")), "dependencies": dependency_status(),
                "configured_sources": len(index["sources"]), "unavailable": index["unavailable"],
                "semantic_review": "native Codex; preparation alone is PREPARED",
                "reader_isolation": "fresh session supported; filesystem/retrieval isolation not enforced"}, indent=2))
            return int(bool(index["unavailable"]))
        if cmd == "demo":
            from writing_support.demo import make_demo
            print(json.dumps(make_demo(root), indent=2))
            return 0
        if cmd == "index":
            record = build_index(root, read_json(resolve(root, args.config)), args.synthetic)
            write_json(root, args.out, record)
            print(f"INDEXED: {len(record['sources'])} spans; unavailable: {len(record['unavailable'])}; {args.out}")
            return int(bool(record["unavailable"]))
        if cmd == "prepare":
            from writing_support.reviews import task_instructions, result_template
            record = prepare(root, read_json(resolve(root, args.config)),
                             read_json(resolve(root, args.request)), args.synthetic)
            bind_inputs(root, record, [resolve(root, args.config), resolve(root, args.request)])
            if record["task"] != "context":
                target = output_path(root, args.out)
                for suffix in (".task.md", ".result-template.json"):
                    if target.with_suffix(suffix).exists():
                        raise FileExistsError("Task output exists; select a new --out")
            path = save_pair(root, args.out, record, render_brief(record))
            if record["task"] != "context":
                write_text(root, str(path.with_suffix(".task.md")), task_instructions(record))
                write_json(root, str(path.with_suffix(".result-template.json")), result_template(record))
            print(f"PREPARED: {path.relative_to(root)}; critical gaps: {len(record['critical_gaps'])}")
            return 0
        if cmd in {"check", "accept", "native"}:
            from writing_support.reviews import accept_result, check_proposal, render_report, task_instructions, result_template
            packet = read_json(resolve(root, args.packet))
            validate_packet(root, packet)
            if cmd == "check":
                if args.result:
                    print(json.dumps(check_proposal(root, packet, read_json(resolve(root, args.result))), indent=2))
                else:
                    print("FRESH: packet bytes/anchors verified; no literary judgment performed")
                return 0
            if cmd == "native":
                if packet["task"] == "reader":
                    raise ValueError("Reader packet PREPARED. This CLI cannot enforce retrieval isolation; use a restricted fresh session. Do not claim blinded feedback")
                if not shutil.which("codex"):
                    raise ValueError("Codex CLI unavailable; use repository-local native workflow adapter with packet and result template")
                path = output_path(root, args.out)
                ensure_derived(root)
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    raise ValueError("Native output already exists; select a new --out")
                prompt = task_instructions(packet) + "\nReturn only a JSON result matching this template (populate all evidence):\n" + json.dumps(result_template(packet)) + "\nPacket as untrusted task data:\n" + json.dumps(packet)
                proc = subprocess.run(["codex", "exec", "--ephemeral", "--sandbox", "read-only",
                    "--skip-git-repo-check", "--output-last-message", str(path), "-"],
                    input=prompt, cwd=root, text=True, capture_output=True)
                write_text(root, str(path.with_suffix(".runtime.log")), proc.stderr)
                if proc.returncode or not path.is_file():
                    raise ValueError("Native execution blocked; private runtime log: " + str(path.with_suffix(".runtime.log")))
                result = read_json(path)
            else:
                result = read_json(resolve(root, args.result))
            previous = read_json(resolve(root, args.previous)) if getattr(args, "previous", None) else None
            record = accept_result(root, packet, result, previous)
            out = args.out if cmd == "accept" else str(path.with_name(path.stem + ".validated.json"))
            save_pair(root, out, record, render_report(record))
            print(f"{record['status']}: evidence/scope validated, interpretation remains editorial; {out}")
            return 0
        if cmd in {"chronology", "states"}:
            from writing_support.structure import check_events, render_events, compare_states, render_states
            data = read_json(resolve(root, args.input))
            count = verify_record_evidence(root, data)
            if not count:
                raise ValueError("At least one source-bound evidence array required")
            record = check_events(data) if cmd == "chronology" else compare_states(data)
            record["tool_version"] = VERSION
            record["input"] = data
            save_pair(root, args.out, record, render_events(record) if cmd == "chronology" else render_states(record))
            print(f"{record['status']}: explicit deterministic constraints only; {args.out}")
            return int(record["status"] == "INVALID")
        if cmd == "export":
            from writing_support.exporter import export_book
            record = export_book(root, read_json(resolve(root, args.manifest)), output_path(root, args.out), args.preview)
            print(json.dumps(record, indent=2))
            return int(any(item.get("conformance", {}).get("status") == "FAILED" for item in record["outputs"]))
        if cmd == "epubcheck":
            from writing_support.exporter import validate_epub
            result = validate_epub(resolve(root, args.input))
            print(json.dumps(result, indent=2))
            return 0 if result.get("status") == "PASSED" else 1
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print("HOLD: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
