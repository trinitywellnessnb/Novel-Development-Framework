"""Generate synthetic runnable inputs, never fabricated model results."""
from pathlib import Path

from .context import CONTEXT_FIELDS, prepare
from .core import snapshot, write_json

FIXTURES = "tests/fixtures/writing_support/"
BOOK = "Test Lantern"
BASE = ".writing-support/demo/"


def _selection(filename, **extra):
    return {"path": FIXTURES + filename, "source_class": "test", "authority": "test-material",
            "critical": True, "reason": "explicit synthetic exercise selection", **extra}


def make_demo(root: Path) -> dict:
    """Write config, requests, packets and deterministic samples below demo/ only.

    Source fixtures are read-only. All evidence is rebuilt from actual current
    fixture bytes, including uncommitted edits. The return value maps names to
    repository-relative generated paths for CLI reporting and native exercises.
    """
    root = Path(root)
    prefix = FIXTURES
    if not (root / prefix / "rules.md").is_file():
        prefix = ".ndf/" + FIXTURES
    def selection(filename, **extra):
        return {**_selection(filename, **extra), "path": prefix + filename}
    tasks = ["continuity", "pov", "voice", "dialogue", "revision", "handoff", "reader"]
    config = {"schema_version": 1, "context_budget": 8000,
              "books": {BOOK: {"repository_id": "TEST-BOOK"}, "Test Glass": {"repository_id": "TEST-COMPANION"}},
              "sources": [
                  selection("rules.md", applicability={"tasks": [t for t in tasks if t != "reader"]}),
                  selection("scene.md", applicability={"tasks": ["continuity", "pov", "voice", "dialogue", "reader"],
                      "reader_visible": {"book": BOOK, "position": 1}}),
                  selection("followup.md", applicability={"tasks": ["continuity", "pov", "reader"],
                      "reader_visible": {"book": BOOK, "position": 2}}),
                  selection("revision.md", applicability={"tasks": ["revision", "handoff"]}),
              ]}
    paths = {}

    def save(name, value):
        rel = BASE + name + ".json"
        write_json(root, rel, value)
        paths[name] = rel

    def evidence(filename, needle):
        path = root / (prefix + filename)
        lines = path.read_text(encoding="utf-8").splitlines()
        matches = [i for i, line in enumerate(lines, 1) if needle in line]
        if len(matches) != 1:
            raise ValueError("Expected exactly one synthetic evidence span: " + needle)
        return snapshot(root, selection(filename, line_start=matches[0], line_end=matches[0]), synthetic=True)

    rules = snapshot(root, selection("rules.md"), synthetic=True)
    clean = snapshot(root, selection("revision.md", line_start=3, line_end=5), synthetic=True)
    save("config", config)
    for task in tasks:
        # Explicitly unknown dimensions are recorded, rather than invented for completeness.
        scene_context = {
            "phase": {"value": "apprentice", "evidence": [evidence("rules.md", "During the apprentice test phase")]},
            "distance": {"value": "close third through Mira", "evidence": [evidence("rules.md", "The courtyard scene uses close third-person")]},
        }
        request = {"task": task, "book": BOOK, "scene": "TEST-COURTYARD", "viewpoint": "Mira Vale",
                   "budget": 8000, "constraints": {"phase": "apprentice", "request_alternatives": False},
                   "scene_context": scene_context}
        if task == "revision":
            request["constraints"].update({
                "revision_objective": "Expand physical staging and the emotional cost of waiting without adding events or facts",
                "revision_source": {"path": clean["path"], "line_start": clean["line_start"],
                                    "line_end": clean["line_end"], "sha256": clean["sha256"]},
                "protected": ["Mira retains the red wool scarf", "The gate remains locked",
                              "Mira decides to wait for the bell", "No key transfer occurs",
                              "Close third-person viewpoint remains with apprentice Mira"],
                "length_target": {"min_words": 75, "max_words": 115}})
        if task == "handoff":
            request["constraints"]["review_scope"] = "Only the clean passage in revision.md; rules are governing context"
        if task == "reader":
            request["reading_order"] = [BOOK]
            request["reader_point"] = {BOOK: 1}
            request["scene_context"] = {}
        save(task + ".request", request)
        save(task + ".packet", prepare(root, config, request, synthetic=True))

    order_ev = evidence("rules.md", "The story-world event order")
    clock_ev = evidence("rules.md", "Clock cedar-realm")
    entry_ev = evidence("scene.md", "Mira stood beneath")
    bell_ev = evidence("followup.md", "The bell rang.")
    reveal_ev = evidence("followup.md", "Mira had known the visitor")
    phase_ev = evidence("rules.md", "During the apprentice test phase")
    eye_ev = evidence("rules.md", "Mira Vale has green eyes")
    key_ev = evidence("rules.md", "At courtyard entry")
    events = {"events": [
        {"id": "TEST-ENTER", "title": "Courtyard entry", "participants": ["Mira", "Tovan"],
         "depictions": [{"book": BOOK, "scene": "TEST-COURTYARD", "position": 1, "account": "world_fact",
                         "reader_reveals": [], "character_knowledge": {"Mira": ["visitor seems an inspector"]},
                         "evidence": [entry_ev]}], "arcs": ["apprentice restraint"],
         "promises": ["wait for the bell"], "evidence": [entry_ev]},
        {"id": "TEST-BELL", "title": "Bell signal", "participants": ["Mira", "Tovan"],
         "depictions": [{"book": BOOK, "scene": "TEST-TRANSFER", "position": 2, "account": "world_fact",
                         "reader_reveals": [], "character_knowledge": {"Mira": ["transfer now permitted"]},
                         "evidence": [bell_ev]}], "dependencies": ["TEST-ENTER"], "evidence": [bell_ev]},
        {"id": "TEST-TRANSFER", "title": "Key transfer and gate opening", "participants": ["Mira", "Tovan"],
         "depictions": [{"book": BOOK, "scene": "TEST-TRANSFER", "position": 2, "account": "world_fact",
                         "reader_reveals": ["TEST-COURIER"], "character_knowledge": {"Mira": ["visitor was Sella"]},
                         "evidence": [bell_ev, reveal_ev]}], "dependencies": ["TEST-BELL"],
         "consequences": ["Mira can pass the gate"], "evidence": [bell_ev]},
        {"id": "TEST-CEDAR", "title": "Cedar local history", "local_time": {"clock": "cedar-realm", "start": 100},
         "experienced_duration": {"character": "Mira", "value": None, "unit": "unknown"},
         "depictions": [], "evidence": [clock_ev]},
        {"id": "TEST-GLASS", "title": "Glass local history", "local_time": {"clock": "glass-realm", "start": 3},
         "experienced_duration": {"character": "Mira", "value": None, "unit": "unknown"},
         "depictions": [], "evidence": [clock_ev]},
    ], "constraints": [
        {"type": "before", "first": "TEST-ENTER", "second": "TEST-BELL", "evidence": [order_ev]},
        {"type": "before", "first": "TEST-BELL", "second": "TEST-TRANSFER", "evidence": [order_ev]},
        {"type": "unknown", "first": "TEST-CEDAR", "second": "TEST-GLASS", "evidence": [clock_ev]},
    ], "reveals": [{"id": "TEST-COURIER", "earliest": [{"book": BOOK, "position": 2}],
                     "prerequisites": ["TEST-BELL"], "evidence": [reveal_ev]}], "reading_order": [BOOK]}
    save("events", events)
    cycle = {**events, "constraints": events["constraints"] + [
        {"type": "before", "first": "TEST-TRANSFER", "second": "TEST-ENTER", "evidence": [order_ev]}]}
    save("events-cycle", cycle)
    premature = {**events, "reveals": [{"id": "TEST-COURIER", "earliest": [{"book": BOOK, "position": 3}],
                                      "prerequisites": ["TEST-BELL"], "evidence": [reveal_ev]}]}
    save("events-premature", premature)
    save("state", {"character": "Mira Vale", "scene": "TEST-COURTYARD", "phase": "apprentice",
                   "entry": {"eyes": "green", "scarf": "red wool", "key": "held by Tovan"},
                   "exit": {"eyes": "brown", "scarf": "red wool", "key": "used by Mira"},
                   "changes": [{"dimension": "eyes", "before": "green", "after": "brown", "basis": "unexplained",
                                "cause": "No identity change or permitted cause is established", "evidence": [eye_ev]},
                               {"dimension": "key", "before": "held by Tovan", "after": "used by Mira", "basis": "unexplained",
                                "cause": "No transfer before bell", "evidence": [key_ev]}],
                   "phase_rules": [{"phase": "apprentice", "available_powers": ["nearby heat-sense"],
                                    "unavailable_powers": ["mind-reading"], "evidence": [phase_ev]}],
                   "powers_used": ["nearby heat-sense", "mind-reading"],
                   "carry_forward": ["Scarf remains unchanged; key possession and eye color require review"],
                   "evidence": [eye_ev, key_ev, phase_ev]})
    return paths
