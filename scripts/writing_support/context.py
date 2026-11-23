"""Budgeted, reproducible source selection. Selection never establishes story truth."""
from .core import VERSION, TASKS, build_index, digest, git_info, packet_identity, literal, validate_config, DEFAULT_AUTHORITY_ORDER

CONTEXT_FIELDS = ("purpose", "opening_state", "intended_outcome", "distance", "phase", "abilities",
                  "world_rules", "location", "condition", "injuries", "possessions", "relationships",
                  "commitments", "knowledge", "beliefs", "suspicions", "preceding_consequences",
                  "setups", "obligations", "protected_revelations")


def estimate(text):
    """Conservative character-based estimate, not a model tokenizer."""
    return (len(text) + 3) // 4


def prepare(root, config, request, synthetic=False):
    validate_config(config)
    if not isinstance(request, dict):
        raise ValueError("Request must be an object")
    task = request.get("task", "context")
    if task not in TASKS:
        raise ValueError("Unsupported task: " + task)
    book = request.get("book")
    if book not in config.get("books", {}):
        raise ValueError("Book is not configured; use its exact configured title")
    if not request.get("scene") or not request.get("viewpoint"):
        raise ValueError("Explicit scene and viewpoint required (use 'unknown' if unresolved)")
    budget = request.get("budget", config.get("context_budget", 8000))
    if type(budget) is not int or budget <= 0:
        raise ValueError("Context budget must be a positive integer")
    omissions, selected, gaps = [], [], []
    if task != "reader" and not config["books"][book].get("repository_id"):
        gaps.append("No registered book ID or manuscript manifest; title is a selector, not an invented ID")
    used = 0
    # Critical instructions first; stable config order resolves equal priorities.
    eligible = []
    for selection in config["sources"]:
        app = selection.get("applicability", {})
        reason = None
        if app.get("books") and book not in app["books"]:
            reason = "different book"
        elif app.get("scenes") and request["scene"] not in app["scenes"]:
            reason = "different scene"
        elif app.get("chapters") and request.get("chapter") not in app["chapters"]:
            reason = "different or unspecified chapter"
        elif app.get("viewpoints") and request["viewpoint"] not in app["viewpoints"]:
            reason = "different viewpoint"
        elif app.get("characters") and not set(app["characters"]) & set(request.get("characters", [request["viewpoint"]])):
            reason = "different or unspecified characters"
        elif app.get("times") and request.get("time") not in app["times"]:
            reason = "different or unspecified project time label"
        elif app.get("tasks") and task not in app["tasks"]:
            reason = "different task"
        elif app.get("phases") and request.get("constraints", {}).get("phase") not in app["phases"]:
            reason = "phase not established or different"
        if task == "reader" and reason is None:
            # Reader contexts are an allowlist of visible manuscript spans, never the author index.
            point = request.get("reader_point", {})
            order = request.get("reading_order", [])
            visible = app.get("reader_visible")
            if not visible or selection["source_class"] not in {"manuscript", "test"}:
                reason = "not explicitly reader-visible text"
            elif visible.get("book") not in order:
                reason = "book outside selected reading order"
            elif (visible.get("book") not in point or
                  type(visible.get("position")) is not int or
                  visible["position"] > point[visible["book"]]):
                reason = "after reader's selected stopping point"
        if reason:
            omissions.append({"path": selection["path"], "reason": reason})
            continue
        eligible.append(selection)
    index = build_index(root, {**config, "sources": eligible}, synthetic)
    order = config.get("authority_order", DEFAULT_AUTHORITY_ORDER)
    indexed = sorted(enumerate(index["sources"]), key=lambda pair: (
        not pair[1]["critical"],
        order.index(pair[1]["authority"]) if pair[1]["authority"] in order else len(order), pair[0]))
    for _, ref in indexed:
        cost = estimate(ref["excerpt"])
        if used + cost > budget and not ref["critical"]:
            omissions.append({"path": ref["path"], "reason": "estimated context budget"})
            if task == "reader":
                gaps.append("Reader-visible material omitted due to context budget; coverage incomplete")
            continue
        selected.append(ref)
        used += cost
    for missing in index["unavailable"]:
        omissions.append(missing)
        if missing["critical"]:
            gaps.append("Unavailable critical source: " + str(missing["path"]))
    if used > budget:
        gaps.append("Critical sources exceed estimated budget; retained intact. Increase budget or narrow explicitly")
    if not selected:
        raise ValueError("No eligible sources selected; configure explicit source/reader spans")
    facts = request.get("scene_context", {})
    # A structured context field is either a source-backed record or explicitly unknown.
    from .core import verify_evidence
    for key, record in facts.items():
        if key not in CONTEXT_FIELDS or not isinstance(record, dict) or not record.get("evidence"):
            raise ValueError("Scene context needs a supported field and cited evidence")
        for ref in record["evidence"]:
            verify_evidence(root, ref)
            if not any(ref["path"] == s["path"] and ref["sha256"] == s["sha256"] and
                       s["line_start"] <= ref["line_start"] <= ref["line_end"] <= s["line_end"] for s in selected):
                raise ValueError("Context evidence outside selected scope")
            matched = next(s for s in selected if s["path"] == ref["path"] and s["sha256"] == ref["sha256"])
            if ref["authority"] != matched["authority"]:
                raise ValueError("Context evidence cannot change authority")
    unknowns = [key for key in CONTEXT_FIELDS if key not in facts]
    required = request.get("required_context_fields", config.get("required_context_fields", []))
    if not isinstance(required, list) or any(key not in CONTEXT_FIELDS for key in required):
        raise ValueError("required_context_fields must list supported context fields")
    missing_required = [key for key in required if key in unknowns]
    if task != "reader" and missing_required:
        gaps.append("Required scene context fields remain unknown: " + ", ".join(missing_required))
    packet = {"schema_version": 1, "tool_version": VERSION, "status": "PREPARED", "task": task,
              "repository": git_info(root), "config_hash": digest(config), "book": book,
              "configuration": {"authority_order": order, "book_settings": config["books"][book]} if task != "reader" else "reader-only selection",
              "chapter": request.get("chapter"), "objective": request.get("objective", "Not specified"),
              "scene": request["scene"], "viewpoint": request["viewpoint"],
              "constraints": request.get("constraints", {}), "scene_context": facts,
              "unknowns": unknowns, "sources": selected, "omissions": omissions,
              "critical_gaps": gaps, "budget": {"limit": budget, "estimated_tokens": used,
                "method": "ceil(characters/4) for selected excerpts; instructions/result schema overhead excluded"},
              "reading_order": request.get("reading_order", []), "reader_point": request.get("reader_point", {}),
              "synthetic": synthetic, "coverage": "Only selected spans; no complete-series review"}
    if task == "reader":
        # Do not leak hidden filenames, source-selection rationale or author-only constraints.
        packet["omissions"] = [{"reason": "Reader-ineligible source omitted"} for _ in omissions]
        packet["critical_gaps"] = ["Reader packet incomplete: selected material unavailable or budget exceeded" for _ in gaps]
        packet["scene_context"] = {}
        packet["constraints"] = {}
        packet["unknowns"] = []
        packet["config_hash"] = "reader-only"
        packet["chapter"] = None
        packet["objective"] = "Simulated response to the reader-visible passages"
        packet["scene"] = "reader stopping point"
        packet["viewpoint"] = "reader"
        packet["repository"] = {"head": packet["repository"].get("head")}
        from .core import EVIDENCE_KEYS
        packet["sources"] = [{**{k: ref[k] for k in EVIDENCE_KEYS},
            "authority": "reader-visible", "source_class": "manuscript", "critical": ref["critical"]}
            for ref in selected]
        selected = packet["sources"]
        facts = {}
    if task != "reader":
        deps = {}
        for ref in index["sources"]:
            deps[ref["path"]] = ref["sha256"]
            if ref.get("authority_evidence"):
                approval = ref["authority_evidence"]
                deps[approval["path"]] = approval["sha256"]
        for item in index["unavailable"]:
            # Missing/invalid inputs remain a gap; selected hashes above are never replaced.
            from .core import source_path
            import hashlib
            try:
                raw = source_path(root, item["path"]).read_bytes()
                deps.setdefault(item["path"], hashlib.sha256(raw).hexdigest())
            except (OSError, ValueError):
                deps.setdefault(item["path"], None)
        packet["dependencies"] = [{"path": path, "sha256": sha} for path, sha in sorted(deps.items())]
    # Budget the serialized native input, including evidence metadata, task contract
    # and result schema. Critical facts are retained, with explicit overflow.
    import json
    packet["packet_id"] = "0" * 64
    def packet_cost():
        text = json.dumps(packet, ensure_ascii=False, sort_keys=True)
        if task != "context":
            from .reviews import task_instructions, result_template
            text += task_instructions(packet) + json.dumps(result_template(packet), ensure_ascii=False)
        return estimate(text)
    protected_paths = {ref["path"] for record in facts.values() for ref in record["evidence"]}
    while packet_cost() > budget and len(selected) > 1:
        removable = [ref for ref in selected if not ref["critical"] and ref["path"] not in protected_paths]
        if not removable:
            break
        ref = removable[-1]
        selected.remove(ref)
        packet["omissions"].append({"reason": "estimated full packet budget"} if task == "reader" else
                                 {"path": ref["path"], "reason": "estimated full packet budget"})
        if task == "reader":
            packet["critical_gaps"].append("Reader-visible material omitted due to context budget; coverage incomplete")
    packet["budget"]["estimated_tokens"] = sum(estimate(ref["excerpt"]) for ref in selected)
    packet["budget"]["method"] = "estimated ceil(characters/4): excerpts and full serialized packet + native instructions/result schema; not a tokenizer"
    if packet_cost() > budget:
        packet["critical_gaps"].append("Full packet exceeds context budget; minimum evidence/critical constraints retained. Narrow scope or increase budget")
    packet["budget"]["packet_estimated_tokens"] = packet_cost()
    for _ in range(3):
        packet["budget"]["packet_estimated_tokens"] = packet_cost()
    packet["packet_id"] = packet_identity(packet)
    return packet


def render_brief(packet):
    out = ["# Writing Context Brief — PREPARED", "", "Derived evidence, not canon or prose authorization.",
           "", f"Book: {packet['book']} | Scene: {packet['scene']} | Viewpoint: {packet['viewpoint']}",
           f"Task: {packet['task']} | Packet: {packet['packet_id']}",
           f"Repository: {packet['repository']}", "", packet["coverage"], "",
           f"Budget: {packet['budget']}", "", "## Current task constraints (author inputs)",
           str(packet["constraints"]), "", "## Source-backed scene context"]
    for key, value in packet["scene_context"].items():
        out.append(f"- {key}: {value}")
    out += ["", "Unknown: " + ", ".join(packet["unknowns"]), "", "## Selected evidence"]
    for ref in packet["sources"]:
        out += ["", f"### {ref['path']}:{ref['line_start']}-{ref['line_end']}",
                f"Authority: {ref['authority']} | Class: {ref['source_class']} | SHA256: {ref['sha256']}",
                f"Reason: {ref.get('reason', 'reader-visible span')}", "", literal(ref["excerpt"])]
    out += ["", "## Important gaps", *["- " + gap for gap in packet["critical_gaps"]],
            "", "## Exclusions", *["- " + str(item) for item in packet["omissions"]], ""]
    return "\n".join(out)
