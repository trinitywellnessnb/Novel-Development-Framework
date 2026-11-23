"""Deterministic, evidence-bearing event and state comparisons.

This module never extracts story facts or interprets prose. Callers supply explicit
records and validate their citations using the shared source foundation. CHECKED
means only that the declared constraints were checked, never literary approval.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
import math

ACCOUNTS = {"world_fact", "narrator_assertion", "belief", "guess", "lie", "disguise", "impersonation", "withheld"}
RELATIONS = {"before", "after", "overlaps", "simultaneous", "unknown", "uncertain", "unordered", "overlapping"}
BASES = {"observed", "inferred", "unexplained"}


def _issue(items, code, message, evidence=None):
    items.append({"code": code, "message": message, "evidence": deepcopy(evidence if isinstance(evidence, list) else [])})


def _status(errors, warnings):
    return "INVALID" if errors else "INCOMPLETE" if warnings else "CHECKED"


def _records(data, key, errors):
    value = data.get(key, [])
    if not isinstance(value, list) or any(not isinstance(v, dict) for v in value):
        _issue(errors, "invalid_schema", f"{key} must be a list of objects")
        return []
    return value


def _evidence(record, label, warnings):
    if not isinstance(record.get("evidence"), list) or not record["evidence"]:
        _issue(warnings, "missing_evidence", f"{label} has no supporting evidence; factual authority is unestablished")


def _strings(record, key, errors):
    value = record.get(key, [])
    if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
        _issue(errors, "invalid_schema", f"{key} must be a list of nonempty strings")
        return []
    return value


def _time(event, errors):
    value = event.get("local_time")
    if value is None:
        return None
    if not isinstance(value, dict) or not isinstance(value.get("clock"), str) or not value["clock"] or "start" not in value:
        _issue(errors, "invalid_schema", f"Event {event['id']} local_time requires clock and start")
        return None
    start, end = value["start"], value.get("end", value["start"])
    if isinstance(start, (int, float)) and not isinstance(start, bool) and isinstance(end, (int, float)) and not isinstance(end, bool):
        kind = "number"
        if not all(math.isfinite(v) for v in (start, end)):
            _issue(errors, "invalid_schema", f"Event {event['id']} has a nonfinite date")
            return None
    elif isinstance(start, str) and isinstance(end, str):
        try:
            start, end = date.fromisoformat(start).toordinal(), date.fromisoformat(end).toordinal()
        except ValueError:
            _issue(errors, "invalid_schema", f"Event {event['id']} dates must be ISO YYYY-MM-DD or finite numbers")
            return None
        kind = "day"
    else:
        _issue(errors, "invalid_schema", f"Event {event['id']} has incompatible start/end date types")
        return None
    if end < start:
        _issue(errors, "incompatible_dates", f"Event {event['id']} ends before it begins", event.get("evidence"))
    return value["clock"], kind, start, end


def check_events(data: dict) -> dict:
    """Check explicit partial ordering and book-specific reveal constraints.

    Event IDs connect depictions, not narrative certainty. ``account`` preserves
    belief/testimony/deception layers. Numeric times are comparable only within
    the same named clock; ISO dates have day precision. No clock conversion
    or duration/age inference is performed. ``reading_order`` controls only the
    displayed reader progression and never changes character knowledge.
    """
    errors, warnings = [], []
    if not isinstance(data, dict):
        return {"status": "INVALID", "errors": [{"code": "invalid_schema", "message": "Event map must be an object", "evidence": []}], "warnings": [], "events": [], "constraints": [], "reading_order": [], "reader_progression": []}
    events = deepcopy(_records(data, "events", errors))
    constraints = deepcopy(_records(data, "constraints", errors))
    reveals = deepcopy(_records(data, "reveals", errors))
    reading_order = _strings(data, "reading_order", errors)
    if len(set(reading_order)) != len(reading_order):
        _issue(errors, "invalid_schema", "reading_order must not contain duplicate books")
    if not events:
        _issue(warnings, "missing_events", "No events are configured; no story chronology was reviewed")
    indexed, times, graph = {}, {}, {}
    for event in events:
        identifier = event.get("id")
        if not isinstance(identifier, str) or not identifier:
            _issue(errors, "invalid_schema", "Every event requires a nonempty id")
            continue
        if identifier in indexed:
            _issue(errors, "duplicate_event", f"Duplicate event id {identifier}", event.get("evidence"))
            continue
        indexed[identifier], graph[identifier] = event, set()
        _evidence(event, f"Event {identifier}", warnings)
        times[identifier] = _time(event, errors)
        _strings(event, "participants", errors)
        for dependency in _strings(event, "dependencies", errors):
            # Dependencies carry planning links; only an explicit 'before'
            # constraint establishes strict chronological order.
            if dependency not in [e.get("id") for e in events]:
                _issue(errors, "missing_event", f"Event {identifier} references missing dependency {dependency}", event.get("evidence"))
        depictions = _records(event, "depictions", errors)
        if not depictions:
            _issue(warnings, "missing_depictions", f"Event {identifier} has no located book depiction")
        for depiction in depictions:
            if not all(isinstance(depiction.get(k), str) and depiction[k] for k in ("book", "scene")) or type(depiction.get("position")) is not int or depiction["position"] < 0:
                _issue(errors, "invalid_schema", f"Event {identifier} depiction requires book, scene and nonnegative integer position")
            if not isinstance(depiction.get("account"), str) or depiction["account"] not in ACCOUNTS:
                _issue(errors, "invalid_schema", f"Event {identifier} depiction requires explicit account layer")
            if not isinstance(depiction.get("character_knowledge", {}), dict):
                _issue(errors, "invalid_schema", f"Event {identifier} character_knowledge must be an object")
            _strings(depiction, "reader_reveals", errors)
            _evidence(depiction, f"Event {identifier} depiction", warnings)

    valid_constraints = []
    for relation in constraints:
        first, second, kind = relation.get("first"), relation.get("second"), relation.get("type")
        if kind == "overlapping":
            relation["type"] = kind = "overlaps"
        _evidence(relation, "Ordering constraint", warnings)
        if not isinstance(first, str) or not isinstance(second, str) or not isinstance(kind, str) or kind not in RELATIONS:
            _issue(errors, "invalid_schema", "Ordering constraint requires first, second and a supported type")
            continue
        if first not in indexed or second not in indexed:
            _issue(errors, "missing_event", f"Ordering constraint references missing event {first} or {second}", relation.get("evidence"))
            continue
        valid_constraints.append(relation)
        if kind == "before":
            graph[first].add(second)
        elif kind == "after":
            graph[second].add(first)
        elif kind in {"unknown", "uncertain"}:
            _issue(warnings, "unknown_order", f"Ordering of {first} and {second} remains unknown", relation.get("evidence"))

    # Simultaneity is an equivalence relation. Expand strict edges across
    # declared simultaneous groups so indirect conflicts cannot hide behind
    # different depictions of the same moment.
    parents = {identifier: identifier for identifier in graph}

    def representative(identifier):
        while parents[identifier] != identifier:
            identifier = parents[identifier]
        return identifier

    for relation in valid_constraints:
        if relation["type"] == "simultaneous":
            parents[representative(relation["first"])] = representative(relation["second"])
    groups = {}
    for identifier in graph:
        groups.setdefault(representative(identifier), set()).add(identifier)
    original_edges = [(a, b) for a, targets in graph.items() for b in targets]
    for first, second in original_edges:
        for a in groups[representative(first)]:
            graph[a].update(groups[representative(second)])
    for group in groups.values():
        ordered = sorted(group)
        for n, first in enumerate(ordered):
            for second in ordered[n + 1:]:
                a, b = times.get(first), times.get(second)
                if a is not None and b is not None and a[:2] == b[:2] and a[2] != b[2]:
                    _issue(errors, "incompatible_dates", f"Simultaneous events {first} and {second} have different explicit start dates", [ref for event in (indexed[first], indexed[second]) if isinstance(event.get("evidence"), list) for ref in event["evidence"]])
    reachable = {}
    for identifier in graph:
        seen, todo = set(), list(graph[identifier])
        while todo:
            item = todo.pop()
            if item not in seen:
                seen.add(item)
                todo.extend(graph[item])
        reachable[identifier] = seen
    cyclic = sorted(identifier for identifier, seen in reachable.items() if identifier in seen)
    if cyclic:
        _issue(errors, "strict_order_cycle", "Strict ordering cycle involves " + ", ".join(cyclic), [e for r in valid_constraints if isinstance(r.get("evidence"), list) for e in r["evidence"]])
    direct_pairs = {(r["first"], r["second"]) if r["type"] == "before" else (r["second"], r["first"]) for r in valid_constraints if r["type"] in {"before", "after"}}
    for first, following in reachable.items():
        for second in following:
            if first == second or (first, second) in direct_pairs:
                continue
            a, b = times.get(first), times.get(second)
            if a is not None and b is not None and a[:2] == b[:2] and (a[3] > b[2] or (a[1] == "number" and a[3] == b[2])):
                _issue(errors, "incompatible_dates", f"Transitive strict order {first} before {second} conflicts with explicit dates", [ref for event in (indexed[first], indexed[second]) if isinstance(event.get("evidence"), list) for ref in event["evidence"]])
    for relation in valid_constraints:
        first, second, kind = relation["first"], relation["second"], relation["type"]
        evidence = relation.get("evidence")
        if kind in {"overlaps", "simultaneous"} and (second in reachable[first] or first in reachable[second]):
            _issue(errors, "incompatible_order", f"{first} and {second} are {kind} but also strictly ordered", evidence)
        a, b = times.get(first), times.get(second)
        if kind in {"unknown", "uncertain", "unordered"} or a is None or b is None:
            continue
        if a[:2] != b[:2]:
            _issue(warnings, "incompatible_clocks", f"Cannot compare dates for {first} ({a[0]}) and {second} ({b[0]}); no approved conversion was applied", evidence)
            continue
        conflict = ((kind == "before" and (a[3] > b[2] or (a[1] == "number" and a[3] == b[2]))) or
                    (kind == "after" and (b[3] > a[2] or (a[1] == "number" and b[3] == a[2]))) or
                    (kind == "overlaps" and (a[3] < b[2] or b[3] < a[2])) or
                    (kind == "simultaneous" and a[2] != b[2]))
        if conflict:
            _issue(errors, "incompatible_dates", f"Explicit dates conflict with {first} {kind} {second} on clock {a[0]}", evidence)

    reveal_index = {}
    for reveal in reveals:
        identifier = reveal.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in reveal_index:
            _issue(errors, "invalid_schema", "Reveal IDs must be unique nonempty strings")
            continue
        reveal_index[identifier] = reveal
        _evidence(reveal, f"Reveal {identifier}", warnings)
        for window in _records(reveal, "earliest", errors):
            if not isinstance(window.get("book"), str) or type(window.get("position")) is not int or window["position"] < 0:
                _issue(errors, "invalid_schema", f"Reveal {identifier} earliest requires book and nonnegative integer position")
        for dependency in _strings(reveal, "prerequisites", errors):
            if dependency not in indexed:
                _issue(errors, "missing_event", f"Reveal {identifier} references missing prerequisite {dependency}", reveal.get("evidence"))
    progression = []
    for event in indexed.values():
        for depiction in _records(event, "depictions", []):
            for identifier in _strings(depiction, "reader_reveals", []):
                reveal = reveal_index.get(identifier)
                if reveal is None:
                    _issue(errors, "missing_reveal", f"Event {event['id']} references missing reveal {identifier}", depiction.get("evidence"))
                    continue
                windows = [w for w in _records(reveal, "earliest", []) if w.get("book") == depiction.get("book") and type(w.get("position")) is int]
                if not windows:
                    _issue(warnings, "unknown_reveal_ceiling", f"Reveal {identifier} has no approved earliest point for {depiction.get('book')}", reveal.get("evidence"))
                elif type(depiction.get("position")) is int and depiction["position"] < min(w["position"] for w in windows):
                    _issue(errors, "premature_reveal", f"Reveal {identifier} appears before its permitted point in {depiction.get('book')}:{depiction.get('scene')}", depiction.get("evidence"))
                for dependency in _strings(reveal, "prerequisites", []):
                    if dependency in indexed and type(depiction.get("position")) is int:
                        earlier = [d for d in _records(indexed[dependency], "depictions", []) if d.get("book") == depiction.get("book") and type(d.get("position")) is int and d["position"] <= depiction["position"]]
                        if not earlier:
                            _issue(warnings, "unseen_reveal_prerequisite", f"Reveal {identifier} prerequisite {dependency} is not shown by this point in {depiction.get('book')}; standalone support needs review", depiction.get("evidence"))
    known = set()
    for book in reading_order:
        depictions = [(e["id"], d) for e in indexed.values() for d in _records(e, "depictions", []) if d.get("book") == book and type(d.get("position")) is int]
        for identifier, depiction in sorted(depictions, key=lambda pair: (pair[1]["position"], pair[0])):
            known.update(_strings(depiction, "reader_reveals", []))
            progression.append({"book": book, "scene": depiction.get("scene"), "event": identifier, "known_reveals": sorted(known)})
    return {"status": _status(errors, warnings), "errors": errors, "warnings": warnings, "events": events,
            "constraints": constraints, "reveals": reveals, "reading_order": reading_order, "reader_progression": progression,
            "scope": "Only supplied event records and explicit constraints; no prose interpretation or universal clock"}


def compare_states(data: dict) -> dict:
    """Compare declared scene entry/exit state and phase-specific powers.

    Dimensions may hold structured knowledge/belief, relationship, possession or
    other state. Only explicit changes with evidence explain a transition. An
    inferred explanation remains a warning. Missing phase rules remain unknown,
    never ordinary-human defaults or permissions from eventual development.
    """
    errors, warnings = [], []
    if not isinstance(data, dict):
        return {"status": "INVALID", "errors": [{"code": "invalid_schema", "message": "State must be an object", "evidence": []}], "warnings": [], "changes": [], "unchanged": [], "carry_forward": []}
    entry, exit_state = data.get("entry", {}), data.get("exit", {})
    if not isinstance(entry, dict) or not isinstance(exit_state, dict):
        _issue(errors, "invalid_schema", "entry and exit must be state objects")
        entry, exit_state = {}, {}
    for key in ("character", "scene"):
        if not isinstance(data.get(key), str) or not data[key]:
            _issue(errors, "invalid_schema", f"State requires {key}")
    if "phase" in data and (not isinstance(data["phase"], str) or not data["phase"]):
        _issue(errors, "invalid_schema", "Optional phase must be nonempty text")
    _evidence(data, "Character state", warnings)
    changes = deepcopy(_records(data, "changes", errors))
    grouped = {}
    for change in changes:
        dimension = change.get("dimension")
        if not isinstance(dimension, str) or not dimension:
            _issue(errors, "invalid_schema", "Every state change requires a dimension")
            continue
        grouped.setdefault(dimension, []).append(change)
        if not isinstance(change.get("basis"), str) or change["basis"] not in BASES:
            _issue(errors, "invalid_schema", f"Change {dimension} requires observed, inferred or unexplained basis")
        _evidence(change, f"Change {dimension}", warnings)
        if not isinstance(change.get("cause"), str) or not change["cause"] or change.get("basis") == "unexplained":
            _issue(warnings, "unexplained_transition", f"Change {dimension} has no explicit causal explanation", change.get("evidence"))
        if change.get("basis") == "inferred":
            _issue(warnings, "inferred_change", f"Change {dimension} is an interpretation, not an observed fact", change.get("evidence"))
        if "before" not in change or "after" not in change:
            _issue(errors, "invalid_schema", f"Change {dimension} requires before and after values")
    unchanged = []
    for dimension in sorted(entry.keys() | exit_state.keys() | grouped.keys()):
        chain = grouped.get(dimension, [])
        if not chain:
            if dimension in entry and dimension in exit_state and entry[dimension] == exit_state[dimension]:
                unchanged.append(dimension)
            else:
                _issue(warnings, "unexplained_transition", f"Entry/exit {dimension} differs or is missing without a causal change")
            continue
        if dimension not in entry or dimension not in exit_state or chain[0].get("before") != entry.get(dimension) or chain[-1].get("after") != exit_state.get(dimension) or any(a.get("after") != b.get("before") for a, b in zip(chain, chain[1:])):
            _issue(errors, "state_change_mismatch", f"Change chain for {dimension} does not match entry/exit state", [e for c in chain for e in c.get("evidence", [])] if all(isinstance(c.get("evidence", []), list) for c in chain) else [])
    rules = _records(data, "phase_rules", errors)
    active = [r for r in rules if r.get("phase") == data.get("phase")]
    powers = sorted(set(value for key in ("abilities_used", "skills_used", "powers_used")
                        for value in _strings(data, key, errors)))
    if len(active) > 1:
        _issue(warnings, "conflicting_phase_rules", "Multiple phase rules apply; resolve their authority explicitly instead of selecting the newest")
    if not active and (powers or rules or data.get("phase")):
        _issue(warnings, "unknown_phase", f"No explicit phase rule for {data.get('phase')}; no capabilities inferred")
    available, unavailable = set(), set()
    for rule in active:
        _evidence(rule, "Phase rule", warnings)
        for key in ("available_abilities", "available_skills", "available_powers"):
            available.update(_strings(rule, key, errors))
        for key in ("unavailable_abilities", "unavailable_skills", "unavailable_powers"):
            unavailable.update(_strings(rule, key, errors))
    for power in sorted(available & unavailable):
        _issue(errors, "conflicting_phase_rules", f"Capability {power} is both available and unavailable in the supplied phase rules")
    exceptions = _records(data, "exceptions", errors)
    allowed_exceptions = set()
    for exception in exceptions:
        capability = exception.get("capability")
        if not isinstance(capability, str) or not capability or not isinstance(exception.get("reason"), str) or not exception["reason"]:
            _issue(errors, "invalid_schema", "Capability exceptions need capability and reason")
            continue
        _evidence(exception, "Capability exception", warnings)
        if (exception.get("scene") == data.get("scene") and
                exception.get("phase") == data.get("phase") and
                isinstance(exception.get("evidence"), list) and exception["evidence"]):
            allowed_exceptions.add(capability)
    for power in powers:
        if power in allowed_exceptions:
            continue
        if power in unavailable:
            _issue(errors, "phase_ability_conflict", f"Capability {power} is explicitly unavailable in phase {data.get('phase')}", [e for r in active for e in r.get("evidence", [])] if all(isinstance(r.get("evidence", []), list) for r in active) else [])
        elif power not in available:
            _issue(warnings, "unknown_ability", f"No supplied phase rule establishes power {power} at this point")
    return {"status": _status(errors, warnings), "errors": errors, "warnings": warnings,
            "character": data.get("character"), "scene": data.get("scene"), "phase": data.get("phase"),
            "entry": deepcopy(entry), "exit": deepcopy(exit_state), "changes": changes, "unchanged": unchanged,
            "carry_forward": deepcopy(data.get("carry_forward", [])),
            "exceptions": deepcopy(exceptions),
            "scope": "Only declared state and explicit phase rules; no psychological or prose inference"}


def _cell(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value if value is not None else "unknown").replace("|", "\\|").replace("\n", "<br>")


def _issues(result):
    lines = ["", "## Explicit constraint findings", ""]
    for level in ("errors", "warnings"):
        for finding in result.get(level, []):
            lines.append(f"- {level[:-1].upper()} `{finding['code']}`: {_cell(finding['message'])}; evidence: {_cell(finding.get('evidence', []))}")
    if not result.get("errors") and not result.get("warnings"):
        lines.append("No deterministic conflicts in supplied records. This is not a semantic continuity review.")
    return lines


def render_events(result: dict) -> str:
    """Render an event comparison and existing planning links without new arcs."""
    lines = ["# Event comparison (derived, not canon)", "", f"Status: {result['status']}", "", result.get("scope", ""), "",
             "| Event | Participants | Clock-local time | Experienced duration | Book / scene | Account layer | Character knowledge | Reader reveals | Evidence |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for event in result.get("events", []):
        for depiction in event.get("depictions", []) if isinstance(event.get("depictions", []), list) else []:
            if not isinstance(depiction, dict):
                continue
            cells = [event.get("id"), event.get("participants", []), event.get("local_time"), event.get("experienced_duration"),
                     f"{depiction.get('book')} / {depiction.get('scene')}", depiction.get("account"), depiction.get("character_knowledge", {}), depiction.get("reader_reveals", []), depiction.get("evidence", [])]
            lines.append("| " + " | ".join(_cell(c) for c in cells) + " |")
    lines.extend(["", "## Existing series-planning links", "", "| Event | Consequences | Arcs | Promises | Dependencies |", "| --- | --- | --- | --- | --- |"])
    for event in result.get("events", []):
        lines.append("| " + " | ".join(_cell(event.get(k, [])) for k in ("id", "consequences", "arcs", "promises", "dependencies")) + " |")
    lines.extend(["", "## Ordering constraints", ""])
    for relation in result.get("constraints", []):
        lines.append(f"- {_cell(relation.get('first'))} {_cell(relation.get('type'))} {_cell(relation.get('second'))}; evidence: {_cell(relation.get('evidence', []))}")
    lines.extend(["", "## Reader progression", "", "Configured reading order: " + _cell(result.get("reading_order", [])), ""])
    for point in result.get("reader_progression", []):
        lines.append(f"- {_cell(point['book'])} / {_cell(point['scene'])}: {_cell(point['known_reveals'])}")
    lines.extend(_issues(result))
    return "\n".join(lines) + "\n"


def render_states(result: dict) -> str:
    lines = ["# Character entry / exit comparison (derived, not canon)", "", f"Status: {result['status']}", "", result.get("scope", ""), "",
             f"Character: {_cell(result.get('character'))}; scene: {_cell(result.get('scene'))}; phase: {_cell(result.get('phase'))}", "",
             "| Dimension | Entry | Exit |", "| --- | --- | --- |"]
    for dimension in sorted(result.get("entry", {}).keys() | result.get("exit", {}).keys()):
        lines.append("| " + " | ".join(_cell(v) for v in (dimension, result["entry"].get(dimension), result["exit"].get(dimension))) + " |")
    lines.extend(["", "## Causal changes", ""])
    for change in result.get("changes", []):
        lines.append(f"- {_cell(change.get('dimension'))}: {_cell(change.get('cause'))} ({_cell(change.get('basis'))}); evidence: {_cell(change.get('evidence', []))}")
    lines.extend(["", "## Carry forward", "", _cell(result.get("carry_forward", []))])
    lines.extend(_issues(result))
    return "\n".join(lines) + "\n"
