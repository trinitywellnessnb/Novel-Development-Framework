"""Offline, explicit-manifest Pandoc builds. Nothing here publishes or approves text.

Only a new directory below ``.writing-support`` may receive build outputs.
Pandoc receives a JSON document assembled from individually verified inputs;
raw HTML/TeX and remote or undeclared image resources cannot be followed.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import zipfile
import xml.etree.ElementTree as ET

from .core import VERSION, source_path, output_path, verify_evidence, git_info, ensure_derived



class ExportError(ValueError):
    """An invalid manifest, stale input, or failed export."""


def _run(command, *, data=None, cwd=None, env=None):
    try:
        return subprocess.run(command, input=data, capture_output=True, text=True,
                              cwd=cwd, timeout=120, check=False, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExportError(f"Dependency invocation failed: {type(exc).__name__}") from exc


def _epubcheck_command():
    executable = shutil.which("epubcheck")
    if executable:
        return [executable]
    jar = os.environ.get("EPUBCHECK_JAR")
    java = shutil.which("java")
    if jar and java and Path(jar).is_file():
        return [java, "-jar", str(Path(jar).resolve())]
    return None


def dependency_status() -> dict:
    """Return local executable versions without installing or contacting services."""
    pandoc = shutil.which("pandoc")
    check = _epubcheck_command()
    java = shutil.which("java")
    def version(command):
        if not command:
            return None
        result = _run(command + ["--version"])
        return (result.stdout or result.stderr).splitlines()[0] if result.returncode == 0 else "version unavailable"
    return {"pandoc": {"available": bool(pandoc), "version": version([pandoc]) if pandoc else None},
            "epubcheck": {"available": bool(check), "version": version(check)},
            "java": {"available": bool(java), "version": version([java]) if java else None},
            "setup": "Install Pandoc using your environment package manager; install official EPUBCheck with Java and set EPUBCHECK_JAR to its jar, or provide epubcheck on PATH."}


def _path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or not PurePosixPath(relative).parts or PurePosixPath(relative).parts[0] in {".writing-support", ".git", "_inbox", "_private"}:
        raise ExportError("Excluded or invalid source boundary")
    try:
        return source_path(root, relative)
    except ValueError as exc:
        raise ExportError(str(exc)) from exc


def _bytes(root: Path, record: dict) -> bytes:
    if not isinstance(record, dict) or not {"path", "sha256"} <= record.keys():
        raise ExportError("Each input requires path and sha256")
    data = _path(root, record["path"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != record["sha256"]:
        raise ExportError(f"Stale source hash: {record['path']}")
    if len(data) > 16 * 1024 * 1024:
        raise ExportError("Input exceeds the 16 MiB per-file limit")
    return data


def _approval(root: Path, source: dict, preview: bool):
    approval = source.get("approval", {})
    if preview:
        return
    if not isinstance(approval, dict) or approval.get("status") != "approved":
        raise ExportError("Non-preview build requires explicit approved source status; use preview for unapproved drafts")
    evidence = approval.get("evidence")
    if not isinstance(evidence, dict):
        raise ExportError("Approved source requires anchored approval evidence")
    try:
        verify_evidence(root, evidence)
    except (ValueError, OSError) as exc:
        raise ExportError("Invalid approval quotation or evidence span: " + str(exc)) from exc


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _plain(value):
    if isinstance(value, list):
        blocks = {"Para", "Plain", "Header", "HorizontalRule", "Div", "Figure", "BlockQuote", "CodeBlock", "Table", "LineBlock", "BulletList", "OrderedList"}
        separator = " " if any(isinstance(v, dict) and v.get("t") in blocks for v in value) else ""
        return separator.join(_plain(v) for v in value)
    if not isinstance(value, dict):
        return ""
    kind, content = value.get("t"), value.get("c")
    if kind == "Str":
        return content
    if kind in {"Space", "SoftBreak", "LineBreak"}:
        return " "
    if kind in {"Code", "Math"}:
        return content[-1]
    if kind == "Figure":
        return _plain(content[1]) + " " + _plain(content[2])
    if kind == "Image":
        return _plain(content[1])
    if kind == "Link":
        return _plain(content[1])
    if kind == "Quoted":
        # Pandoc preserves curly quotation marks as quote nodes when reading EPUB.
        marks = ('“', '”') if content[0]["t"] == "DoubleQuote" else ('‘', '’')
        return marks[0] + _plain(content[1]) + marks[1]
    return _plain(content)


def _fingerprint(document: dict) -> dict:
    """Documented comparison: collapse whitespace; retain ordered words/punctuation.

    Ignore format-generated identifiers, metadata/title pages and image paths.
    Independently retain heading levels/titles and italic text. DOCX horizontal
    rules may become styled paragraphs, so scene-break preservation is also
    inspected in the archive XML by the integration tests.
    """
    blocks = document["blocks"]
    body = " ".join(_plain(node) for node in blocks)
    return {"text": " ".join(body.split()),
            "headings": [(n["c"][0], " ".join(_plain(n["c"][2]).split()))
                         for n in _walk(blocks) if n.get("t") == "Header"],
            "paragraphs": [text for n in _walk(blocks) if n.get("t") in {"Para", "Plain"}
                           for text in [" ".join(_plain(n).split())] if text],
            "italics": [" ".join(_plain(n["c"]).split()) for n in _walk(blocks) if n.get("t") == "Emph"],
            "images": sum(n.get("t") == "Image" for n in _walk(blocks)),
            "scene_breaks": sum(n.get("t") == "HorizontalRule" for n in _walk(blocks))}


def validate_epub(path: Path) -> dict:
    """Run real EPUBCheck when available, retaining its actual stdout/stderr."""
    path = Path(path).resolve()
    if path.suffix.lower() != ".epub" or not path.is_file():
        raise ExportError("EPUB validation requires an existing .epub file")
    command = _epubcheck_command()
    if not command:
        return {"status": "SKIPPED", "reason": "EPUBCheck unavailable; install it or set EPUBCHECK_JAR. EPUB conformance has not been validated."}
    result = _run(command + [str(path)])
    return {"status": "PASSED" if result.returncode == 0 else "FAILED",
            "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
            "version": dependency_status()["epubcheck"]["version"]}


def _archive_check(path: Path, format_: str, expected: dict, asset_hashes=()):
    try:
        with zipfile.ZipFile(path) as archive:
            if archive.testzip():
                raise ExportError("Export archive CRC check failed")
            embedded_hashes = {hashlib.sha256(archive.read(name)).hexdigest()
                               for name in archive.namelist()
                               if name.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))}
            if not set(asset_hashes).issubset(embedded_hashes):
                raise ExportError("Export image bytes changed or an image is missing")
            if format_ == "docx":
                xml = ET.fromstring(archive.read("word/document.xml"))
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                actual_breaks = len(xml.findall(".//w:pBdr/w:bottom", ns)) + len(xml.findall(".//{urn:schemas-microsoft-com:vml}rect[@{urn:schemas-microsoft-com:office:office}hr]"))
                if actual_breaks < expected["scene_breaks"]:
                    raise ExportError("DOCX scene-break count changed")
            else:
                if archive.read("mimetype") != b"application/epub+zip":
                    raise ExportError("Invalid EPUB mimetype")
                ET.fromstring(archive.read("META-INF/container.xml"))
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        raise ExportError("Export is not a parseable package") from exc


def export_book(root: Path, manifest: dict, output: Path, preview: bool = False) -> dict:
    """Build an ordered review copy and/or EPUB in a new local output directory.

    ``manifest`` requires ``book``, metadata (title/author/language), ordered
    ``sources`` (path/sha256/role/approval), optional explicit assets and formats.
    This validates evidence bytes, not the authenticity or scope of approval.
    """
    root = Path(root).resolve()
    try:
        output = output_path(root, str(output))
    except ValueError as exc:
        raise ExportError(str(exc)) from exc
    if output.exists():
        raise ExportError("Build directory already exists; use a new name to preserve prior outputs")
    if not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int or manifest.get("schema_version") != 1:
        raise ExportError("Export manifest schema_version must be 1")
    metadata = manifest.get("metadata", {})
    if not isinstance(metadata, dict) or not isinstance(manifest.get("book"), str) or not manifest.get("book") or not all(isinstance(metadata.get(k), str) and metadata[k].strip()
                                           for k in ("title", "author", "language")):
        raise ExportError("Manifest needs book and metadata title, author, language")
    series = manifest.get("series")
    if series is not None:
        if (not isinstance(series, dict) or set(series) - {"name", "position"} or
                not isinstance(series.get("name"), str) or not series["name"].strip()):
            raise ExportError("Series requires a nonempty name and optional numeric position")
        position = series.get("position")
        if position is not None and (type(position) not in (int, float) or not math.isfinite(position) or position <= 0):
            raise ExportError("Series position must be a positive finite number")
    formats = manifest.get("formats", ["docx", "epub"])
    if not isinstance(formats, list) or not formats or any(not isinstance(f, str) or f not in {"docx", "epub"} for f in formats) or len(set(formats)) != len(formats):
        raise ExportError("Formats must be unique docx and/or epub")
    sources, assets = manifest.get("sources"), manifest.get("assets", [])
    if not isinstance(sources, list) or not sources or not isinstance(assets, list):
        raise ExportError("Manifest needs a nonempty ordered sources list and optional assets list")
    paths = [s.get("path") for s in sources + assets if isinstance(s, dict)]
    if len(paths) != len(sources + assets) or any(not isinstance(p, str) for p in paths) or len(set(paths)) != len(paths):
        raise ExportError("Manifest paths must be distinct")
    documents, provenance, asset_data, selected_texts = [], [], {}, []
    referenced_assets = set()
    for asset in assets:
        if PurePosixPath(asset.get("path", "")).suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif"}:
            raise ExportError("Image assets support PNG, JPEG and GIF only")
        asset_data[asset["path"]] = _bytes(root, asset)
        _approval(root, asset, preview)
    for source in sources:
        data = _bytes(root, source)
        if source.get("role") not in {"frontmatter", "chapter", "backmatter"}:
            raise ExportError("Source role must be frontmatter, chapter or backmatter")
        _approval(root, source, preview)
        if PurePosixPath(source["path"]).suffix.lower() not in {".md", ".txt"}:
            raise ExportError("Manuscript sources support UTF-8 Markdown or text")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ExportError("Manuscript source must be UTF-8") from exc
        selected_texts.append((source, text))
    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise ExportError("Pandoc unavailable; install Pandoc through your environment setup")
    for source, text in selected_texts:
        # Disable YAML metadata and raw directives: manuscript text is data.
        result = _run([pandoc, "--from=markdown-smart-raw_html-raw_tex-yaml_metadata_block", "--to=json"], data=text)
        if result.returncode:
            raise ExportError(f"Pandoc could not parse source: {source['path']}")
        document = json.loads(result.stdout)
        for node in _walk(document["blocks"]):
            if node.get("t") in {"RawBlock", "RawInline"}:
                raise ExportError("Raw output directives are unsupported; manuscript text is data")
            if node.get("t") == "Image":
                target = node["c"][2][0]
                image = str(PurePosixPath(source["path"]).parent / target)
                # Resolve lexical normalization solely to compare declared paths.
                resolved = os.path.normpath(image).replace(os.sep, "/")
                if ":" in target or resolved not in asset_data:
                    raise ExportError("Image must reference an explicitly hashed local manifest asset")
                referenced_assets.add(resolved)
                node["c"][2][0] = str(Path("assets") / (str(paths.index(resolved)) + Path(resolved).suffix))
        documents.append(document)
        provenance.append({**{k: source[k] for k in ("path", "sha256", "role", "approval") if k in source},
                           "line_start": 1, "line_end": len(text.splitlines()),
                           "source_class": "manuscript", "authority": "draft" if preview else "approved-manuscript",
                           "source_revision": git_info(root, source["path"])["source_revision"]})
    document = copy.deepcopy(documents[0])
    document["blocks"] = [b for doc in documents for b in doc["blocks"]]
    # Metadata is explicitly provided by the manifest, never inherited from prose.
    document["meta"] = {key: {"t": "MetaString", "c": value}
                        for key, value in metadata.items() if key in {"title", "author", "language", "rights", "date", "identifier"} and isinstance(value, str)}
    document["meta"]["lang"] = document["meta"].pop("language")
    if series is not None:
        document["meta"]["belongs-to-collection"] = {"t": "MetaString", "c": series["name"]}
        document["meta"]["collection-type"] = {"t": "MetaString", "c": "series"}
        if series.get("position") is not None:
            document["meta"]["group-position"] = {"t": "MetaString", "c": str(series["position"])}
    manifest_hash = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    document["meta"].setdefault("identifier", {"t": "MetaString", "c": "urn:sha256:" + manifest_hash})
    epoch = manifest.get("build_epoch", 0)
    if type(epoch) is not int or epoch < 0:
        raise ExportError("build_epoch must be a nonnegative integer Unix timestamp")
    build_environment = dict(os.environ, SOURCE_DATE_EPOCH=str(epoch))
    if preview:
        document["meta"]["title"]["c"] += " — UNAPPROVED DRAFT PREVIEW"
    settings = manifest.get("formatting", {})
    if not isinstance(settings, dict) or set(settings) - {"toc", "toc_depth", "split_level", "reference_doc"}:
        raise ExportError("Formatting supports toc, toc_depth, split_level and reference_doc")
    if type(settings.get("toc", False)) is not bool or any(type(settings.get(k, 1)) is not int or not 1 <= settings.get(k, 1) <= 6 for k in ("toc_depth", "split_level")):
        raise ExportError("Formatting depths must be integers 1–6; toc must be boolean")
    cover = manifest.get("cover")
    if cover is not None and (not isinstance(cover, str) or cover not in asset_data):
        raise ExportError("Cover must name a declared, hashed image asset")
    reference_doc = settings.get("reference_doc")
    reference_data = None
    if reference_doc is not None:
        if not isinstance(reference_doc, dict) or Path(reference_doc.get("path", "")).suffix.lower() != ".docx":
            raise ExportError("reference_doc must name a hashed DOCX formatting reference")
        reference_data = _bytes(root, reference_doc)
        _approval(root, reference_doc, preview)
    expected = _fingerprint(document)
    ensure_derived(root)
    output.mkdir(parents=True)
    if asset_data:
        (output / "assets").mkdir()
    for name, data in asset_data.items():
        (output / "assets" / (str(paths.index(name)) + Path(name).suffix)).write_bytes(data)
    if reference_data is not None:
        (output / "reference.docx").write_bytes(reference_data)
    (output / "input.json").write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    results = []
    for format_ in formats:
        dest = output / ("draft-preview" if preview else "manuscript")
        dest = dest.with_suffix("." + format_)
        command = [pandoc, "--from=json", "--to=" + ("epub3" if format_ == "epub" else "docx"), "--standalone", "--fail-if-warnings", "--output=" + str(dest)]
        if settings.get("toc"):
            command += ["--toc", "--toc-depth=" + str(settings.get("toc_depth", 3))]
        if format_ == "docx" and reference_data is not None:
            command += ["--reference-doc=" + str(output / "reference.docx")]
        if format_ == "epub" and cover is not None:
            command += ["--epub-cover-image=" + str(Path("assets") / (str(paths.index(cover)) + Path(cover).suffix))]
        if format_ == "epub":
            command += ["--split-level=" + str(settings.get("split_level", 1)), "--epub-title-page=false"]
        result = _run(command, data=json.dumps(document), cwd=output, env=build_environment)
        if result.returncode:
            (output / "pandoc-error.log").write_text(result.stderr, encoding="utf-8")
            raise ExportError("Pandoc export failed; inspect local pandoc-error.log in the build directory")
        used_assets = referenced_assets | ({cover} if format_ == "epub" and cover else set())
        _archive_check(dest, format_, expected, [hashlib.sha256(asset_data[name]).hexdigest() for name in used_assets])
        readback = _run([pandoc, "--from=" + format_, "--to=json", str(dest)])
        if readback.returncode:
            raise ExportError("Export could not be parsed for content verification")
        actual = _fingerprint(json.loads(readback.stdout))
        # EPUB may have a generated table of contents in a separate nav document;
        # Pandoc excludes it on readback. DOCX title metadata remains metadata.
        comparison_expected = dict(expected)
        if format_ == "epub" and cover is not None:
            # Pandoc readback includes one generated, empty-alt cover image.
            comparison_expected["images"] += 1
        comparison = {key: comparison_expected[key] == actual[key] for key in ("text", "paragraphs", "headings", "italics", "images")}
        if format_ == "epub":
            comparison["scene_breaks"] = expected["scene_breaks"] == actual["scene_breaks"]
        if not all(comparison.values()):
            raise ExportError("Export content verification failed: " + ", ".join(k for k, v in comparison.items() if not v))
        results.append({"path": str(dest.relative_to(root)), "format": format_, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                        "content_comparison": comparison, "asset_bytes_preserved": True,
                        "conformance": validate_epub(dest) if format_ == "epub" else {"status": "PARSED"}})
    report = {"schema_version": 1, "tool_version": VERSION, "status": "BUILT_PREVIEW" if preview else "BUILT",
              "book": manifest["book"], "repository": git_info(root), "manifest": manifest, "manifest_sha256": manifest_hash, "build_epoch": epoch, "identifier": document["meta"]["identifier"]["c"],
              "sources": provenance, "assets": assets, "metadata": metadata, "formatting": settings, "series": series,
              "dependencies": dependency_status(), "outputs": results,
              "normalization": "Account for one generated EPUB cover image when selected. Collapse whitespace only; compare ordered text/punctuation, paragraph sequence (ignoring empty generated anchors), headings, italics, image count; verify DOCX scene-break borders and package structure. SOURCE_DATE_EPOCH fixes build timestamps; manifest-derived EPUB identifier is stable. Binary reproducibility is checked only for the exercised Pandoc version.",
              "limitations": ["Approval citations are byte-validated; author intent and scope require human review.", "Conformance does not establish visual quality, retailer acceptance, or publication authorization.", "The cover property applies to EPUB; include a cover image in an explicit frontmatter source for DOCX."]}
    (output / "build.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
