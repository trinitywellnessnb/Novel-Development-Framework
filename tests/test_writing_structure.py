"""Synthetic structure tests; these names and facts are not story material."""
import copy
import unittest

from scripts.writing_support.structure import check_events, compare_states, render_events, render_states

EVIDENCE = [{"path": "tests/fixtures/synthetic.md", "sha256": "0" * 64, "line_start": 1, "line_end": 1, "excerpt": "TEST MATERIAL"}]


def event(identifier, position=1, account="world_fact", clock="garden", start=None):
    result = {"id": identifier, "title": "TEST MATERIAL " + identifier, "participants": ["Mira"],
              "depictions": [{"book": "TEST-A", "scene": "TEST-S" + str(position), "position": position,
                              "account": account, "character_knowledge": {"Mira": {"belief": "door is locked"}},
                              "reader_reveals": [], "evidence": EVIDENCE}], "evidence": EVIDENCE}
    if start is not None:
        result["local_time"] = {"clock": clock, "start": start}
    return result


def constraint(first, second, kind="before"):
    return {"first": first, "second": second, "type": kind, "evidence": EVIDENCE}


class EventTests(unittest.TestCase):
    def test_partial_order_and_unknown_clocks(self):
        result = check_events({"events": [event("E1", start=2), event("E2", 2, clock="cave", start=1)],
                               "constraints": [constraint("E1", "E2")], "reading_order": ["TEST-A"]})
        self.assertFalse(result["errors"])
        self.assertIn("incompatible_clocks", [w["code"] for w in result["warnings"]])
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertIn("garden", render_events(result))

    def test_strict_cycle_and_missing_event(self):
        result = check_events({"events": [event("E1"), event("E2", 2), event("E3", 3)],
                               "constraints": [constraint("E1", "E2"), constraint("E2", "E3"),
                                               constraint("E3", "E1"), constraint("E3", "MISSING")]})
        self.assertEqual(result["status"], "INVALID")
        self.assertIn("strict_order_cycle", [e["code"] for e in result["errors"]])
        self.assertIn("missing_event", [e["code"] for e in result["errors"]])

    def test_explicit_dates_and_simultaneous_conflict(self):
        events = [event("E1", start="2031-01-02"), event("E2", 2, start="2031-01-01")]
        result = check_events({"events": events, "constraints": [constraint("E1", "E2")]})
        self.assertIn("incompatible_dates", [e["code"] for e in result["errors"]])
        result = check_events({"events": [event("E1"), event("E2", 2), event("E3", 3)],
                               "constraints": [constraint("E1", "E2"), constraint("E2", "E3"), constraint("E1", "E3", "simultaneous")]})
        self.assertIn("incompatible_order", [e["code"] for e in result["errors"]])

    def test_overlap_ranges_and_unknown_relation(self):
        a, b = event("E1", start=1), event("E2", 2, start=5)
        a["local_time"]["end"] = 2
        result = check_events({"events": [a, b], "constraints": [constraint("E1", "E2", "overlaps")]})
        self.assertIn("incompatible_dates", [e["code"] for e in result["errors"]])
        result = check_events({"events": [a, b], "constraints": [constraint("E1", "E2", "unknown")]})
        self.assertFalse(result["errors"])
        self.assertIn("unknown_order", [w["code"] for w in result["warnings"]])

    def test_belief_deception_and_intentional_mystery_are_not_contradictions(self):
        events = [event("E1", account="belief"), event("E2", 2, account="impersonation"), event("E3", 3, account="withheld")]
        result = check_events({"events": events, "reading_order": ["TEST-A"]})
        self.assertFalse(result["errors"])
        self.assertEqual(result["events"][0]["depictions"][0]["character_knowledge"]["Mira"]["belief"], "door is locked")
        self.assertIn("impersonation", render_events(result))

    def test_premature_reveal_and_missing_reveal_dependency(self):
        e = event("E1")
        e["depictions"][0]["reader_reveals"] = ["SECRET"]
        result = check_events({"events": [e], "reveals": [{"id": "SECRET", "earliest": [{"book": "TEST-A", "position": 5}],
                               "prerequisites": ["MISSING"], "evidence": EVIDENCE}]})
        codes = [e["code"] for e in result["errors"]]
        self.assertIn("premature_reveal", codes)
        self.assertIn("missing_event", codes)

    def test_reading_order_not_character_knowledge(self):
        e = event("E1")
        e["depictions"].append({"book": "TEST-B", "scene": "TEST-B1", "position": 1, "account": "lie",
                               "character_knowledge": {}, "reader_reveals": ["SECRET"], "evidence": EVIDENCE})
        result = check_events({"events": [e], "reveals": [{"id": "SECRET", "earliest": [{"book": "TEST-B", "position": 1}], "evidence": EVIDENCE}],
                               "reading_order": ["TEST-A", "TEST-B"]})
        self.assertFalse(result["errors"])
        self.assertEqual(result["reader_progression"][0]["known_reveals"], [])
        self.assertEqual(result["reader_progression"][1]["known_reveals"], ["SECRET"])
        self.assertEqual(result["events"][0]["depictions"][0]["character_knowledge"]["Mira"]["belief"], "door is locked")

    def test_transitive_simultaneity_and_dated_order(self):
        result = check_events({"events": [event("E1"), event("E2", 2), event("E3", 3)],
                               "constraints": [constraint("E1", "E2", "simultaneous"), constraint("E2", "E3"), constraint("E3", "E1", "simultaneous")]})
        self.assertIn("strict_order_cycle", [e["code"] for e in result["errors"]])
        result = check_events({"events": [event("E1", start=5), event("E2", 2), event("E3", 3, start=1)],
                               "constraints": [constraint("E1", "E2"), constraint("E2", "E3")]})
        self.assertIn("incompatible_dates", [e["code"] for e in result["errors"]])

    def test_missing_evidence_and_invalid_shapes(self):
        e = event("E1")
        del e["evidence"]
        self.assertEqual(check_events({"events": [e]})["status"], "INCOMPLETE")
        self.assertEqual(check_events({"events": "bad"})["status"], "INVALID")
        self.assertEqual(check_events({"events": [event("E1"), event("E1")]})["status"], "INVALID")


class StateTests(unittest.TestCase):
    def state(self):
        return {"character": "Mira (TEST MATERIAL)", "scene": "TEST-S1", "phase": "seed",
                "entry": {"eye_color": "green", "possessions": ["scarf", "key"], "location": "garden"},
                "exit": {"eye_color": "green", "possessions": ["scarf"], "location": "cave"},
                "changes": [{"dimension": "possessions", "before": ["scarf", "key"], "after": ["scarf"],
                             "basis": "observed", "cause": "Mira hands over key", "evidence": EVIDENCE}],
                "phase_rules": [{"phase": "seed", "available_powers": ["glow"], "unavailable_powers": ["flight"], "evidence": EVIDENCE}],
                "powers_used": ["glow"], "evidence": EVIDENCE}

    def test_causal_changes_unknown_transition_and_consistent_control(self):
        result = compare_states(self.state())
        self.assertFalse(result["errors"])
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(result["unchanged"], ["eye_color"])
        self.assertIn("unexplained_transition", [w["code"] for w in result["warnings"]])
        self.assertIn("Mira hands over key", render_states(result))

    def test_ability_before_phase_and_unknown_ability(self):
        data = self.state()
        data["powers_used"] = ["flight", "invisibility"]
        result = compare_states(data)
        self.assertIn("phase_ability_conflict", [e["code"] for e in result["errors"]])
        self.assertIn("unknown_ability", [w["code"] for w in result["warnings"]])
        data["phase"] = "tree"
        data["phase_rules"].append({"phase": "tree", "available_powers": ["flight", "invisibility"], "evidence": EVIDENCE})
        self.assertNotIn("phase_ability_conflict", [e["code"] for e in compare_states(data)["errors"]])

    def test_impossible_transfer_and_state_mismatch(self):
        data = self.state()
        data["changes"][0]["before"] = ["scarf"]
        self.assertIn("state_change_mismatch", [e["code"] for e in compare_states(data)["errors"]])
        data["changes"][0]["before"] = ["scarf", "key"]
        data["changes"].append({"dimension": "eye_color", "before": "green", "after": "brown", "basis": "observed", "cause": "unknown", "evidence": EVIDENCE})
        self.assertIn("state_change_mismatch", [e["code"] for e in compare_states(data)["errors"]])

    def test_inferred_changes_remain_inferences_and_input_unchanged(self):
        data = self.state()
        data["changes"][0]["basis"] = "inferred"
        original = copy.deepcopy(data)
        result = compare_states(data)
        self.assertEqual(data, original)
        self.assertIn("inferred_change", [w["code"] for w in result["warnings"]])
        self.assertEqual(result["changes"][0]["basis"], "inferred")

    def test_missing_phase_rule_not_human_limitation(self):
        data = self.state()
        data["phase_rules"] = []
        result = compare_states(data)
        self.assertFalse(result["errors"])
        self.assertIn("unknown_phase", [w["code"] for w in result["warnings"]])


class GenericProjectTests(unittest.TestCase):
    def test_standalone_state_needs_no_phase_or_abilities(self):
        result = compare_states({"character": "Test Editor", "scene": "Kitchen",
                                 "entry": {"location": "kitchen"}, "exit": {"location": "kitchen"},
                                 "evidence": EVIDENCE})
        self.assertEqual(result["status"], "CHECKED", result)

    def test_generic_skill_rules_and_evidenced_scene_exception(self):
        data = {"character": "Test Apprentice", "scene": "Lesson", "phase": "beginner",
                "entry": {}, "exit": {}, "skills_used": ["navigation"], "evidence": EVIDENCE,
                "phase_rules": [{"phase": "beginner", "unavailable_skills": ["navigation"], "evidence": EVIDENCE}]}
        self.assertIn("phase_ability_conflict", [e["code"] for e in compare_states(data)["errors"]])
        data["exceptions"] = [{"capability": "navigation", "scene": "Lesson", "phase": "beginner",
                               "reason": "Teacher provides explicit guided assistance", "evidence": EVIDENCE}]
        self.assertEqual(compare_states(data)["status"], "CHECKED")
        data["exceptions"][0]["scene"] = "Other scene"
        self.assertIn("phase_ability_conflict", [e["code"] for e in compare_states(data)["errors"]])
        data["exceptions"][0]["scene"] = "Lesson"
        data["exceptions"][0]["evidence"] = []
        self.assertIn("phase_ability_conflict", [e["code"] for e in compare_states(data)["errors"]])

    def test_uncertain_order_and_explicit_unordered_relation(self):
        for relation in ("uncertain", "unordered", "overlapping"):
            result = check_events({"events": [event("A"), event("B")],
                                   "constraints": [constraint("A", "B", relation)]})
            self.assertFalse(result["errors"], result)
        result = check_events({"events": [event("A"), event("B")],
                               "constraints": [constraint("A", "B", "unordered")]})
        self.assertEqual(result["status"], "CHECKED")


if __name__ == "__main__":
    unittest.main()
