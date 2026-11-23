"""Synthetic contracts for native results, not tests of literary accuracy."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from scripts.writing_support import core, reviews


class NativeResultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir()
        self.scene = self.root / "docs" / "synthetic-scene.md"
        self.scene.write_text("SYNTHETIC TEST MATERIAL.\nMira kept the brass key.\nPerhaps Orren was afraid.\n", encoding="utf-8")
        self.rule_file = self.root / "docs" / "synthetic-rules.md"
        self.rule_file.write_text("SYNTHETIC TEST MATERIAL.\nOrren left the key with Mira.\n", encoding="utf-8")
        self.packet = self.packet_for("continuity")

    def packet_for(self, task):
        sources = [core.snapshot(self.root, {
            "path": "docs/synthetic-scene.md", "line_start": 2, "line_end": 3,
            "authority": "draft", "source_class": "manuscript",
        }), core.snapshot(self.root, {
            "path": "docs/synthetic-rules.md", "line_start": 2, "line_end": 2,
            "authority": "test-material", "source_class": "test",
        })]
        packet = {
            "schema_version": 1, "tool_version": core.VERSION, "status": "PREPARED",
            "task": task, "book": "SYNTHETIC", "scene": "TEST-SCENE",
            "viewpoint": "Mira close third", "constraints": {}, "sources": sources,
            "critical_gaps": [], "omissions": [],
        }
        packet["packet_id"] = core.packet_identity(packet)
        return packet

    def refresh_id(self, packet):
        packet["packet_id"] = core.packet_identity(packet)

    def result(self, packet=None):
        packet = packet or self.packet
        result = reviews.result_template(packet)
        result.update(status="REVIEWED", limitations=[], coverage=[ref["path"] for ref in packet["sources"]])
        return result

    def finding(self, packet=None):
        packet = packet or self.packet
        return {
            "issue_key": "synthetic-contract-issue", "category": "optional craft suggestion",
            "passage": deepcopy(packet["sources"][0]), "governing": [deepcopy(packet["sources"][1])],
            "explanation": "Synthetic schema fixture; no model judgment was performed.",
            "consequence": "This exercises evidence scope validation.",
            "confidence": {"level": "low", "reason": "Synthetic input only."},
            "candidate_repair": "Author review; no automatic correction.",
            "requires_canon_decision": False,
        }

    def test_result_evidence_and_render_keep_draft_authority(self):
        result = self.result()
        result["findings"] = [self.finding()]
        accepted = reviews.accept_result(self.root, self.packet, result)
        self.assertEqual("draft", accepted["findings"][0]["passage"]["authority"])
        self.assertIn("Perhaps Orren was afraid.", reviews.render_report(accepted))
        self.assertEqual("open", accepted["findings"][0]["disposition"])

    def test_fabricated_quote_rejected(self):
        result = self.result()
        finding = self.finding()
        finding["passage"]["excerpt"] = "Invented line that never existed."
        result["findings"] = [finding]
        with self.assertRaisesRegex(ValueError, "outside selected text"):
            reviews.accept_result(self.root, self.packet, result)

    def test_valid_source_outside_selected_span_rejected(self):
        result = self.result()
        finding = self.finding()
        finding["passage"].update(line_start=1, line_end=1, excerpt="SYNTHETIC TEST MATERIAL.")
        result["findings"] = [finding]
        with self.assertRaisesRegex(ValueError, "span is outside"):
            reviews.accept_result(self.root, self.packet, result)

    def test_citation_cannot_promote_draft_to_canon(self):
        result = self.result()
        finding = self.finding()
        finding["passage"]["authority"] = "approved-canon"
        result["findings"] = [finding]
        with self.assertRaisesRegex(ValueError, "cannot change source authority"):
            reviews.accept_result(self.root, self.packet, result)

    def test_contradiction_requires_governing_evidence(self):
        result = self.result()
        finding = self.finding()
        finding.update(category="established contradiction", governing=[])
        result["findings"] = [finding]
        with self.assertRaisesRegex(ValueError, "requires supporting"):
            reviews.accept_result(self.root, self.packet, result)

    def test_numerical_confidence_and_unknown_fields_rejected(self):
        result = self.result()
        result["findings"] = [self.finding()]
        result["findings"][0]["confidence"]["score"] = .9
        with self.assertRaisesRegex(ValueError, "Qualitative"):
            reviews.accept_result(self.root, self.packet, result)
        result = self.result()
        result["passed_all_plot_holes"] = True
        with self.assertRaisesRegex(ValueError, "unexpected fields"):
            reviews.accept_result(self.root, self.packet, result)

    def test_no_findings_with_missing_evidence_is_incomplete(self):
        result = self.result()
        result["coverage"] = result["coverage"][:1]
        self.assertEqual("INCOMPLETE", reviews.accept_result(self.root, self.packet, result)["status"])
        packet = deepcopy(self.packet)
        packet["critical_gaps"] = ["Opening state not established."]
        self.refresh_id(packet)
        self.assertEqual("INCOMPLETE", reviews.accept_result(self.root, packet, self.result(packet))["status"])

    def test_same_evidence_preserves_author_disposition_changed_bytes_reopen(self):
        result = self.result()
        result["findings"] = [self.finding()]
        previous = reviews.accept_result(self.root, self.packet, result)
        previous["findings"][0].update(disposition="intentionally-retained", author_review="Synthetic review record.")
        repeated = reviews.accept_result(self.root, self.packet, result, previous)
        self.assertEqual("intentionally-retained", repeated["findings"][0]["disposition"])
        self.scene.write_text("SYNTHETIC TEST MATERIAL.\nMira placed the brass key down.\nPerhaps Orren was afraid.\n", encoding="utf-8")
        new_packet = self.packet_for("continuity")
        new_result = self.result(new_packet)
        new_result["findings"] = [self.finding(new_packet)]
        reopened = reviews.accept_result(self.root, new_packet, new_result, previous)["findings"][0]
        self.assertEqual(previous["findings"][0]["finding_id"], reopened["finding_id"])
        self.assertEqual("open", reopened["disposition"])
        self.assertIn("changed", reopened["reopened_reason"])

    def test_omitted_findings_retain_adjudication_when_they_reappear(self):
        result = self.result()
        result["findings"] = [self.finding()]
        first = reviews.accept_result(self.root, self.packet, result)
        first["findings"][0].update(disposition="rejected", author_review="Synthetic author adjudication.")
        omitted = reviews.accept_result(self.root, self.packet, self.result(), first)
        self.assertEqual([], omitted["findings"])
        self.assertEqual("rejected", omitted["finding_history"][0]["disposition"])
        omitted_twice = reviews.accept_result(self.root, self.packet, self.result(), omitted)
        self.assertEqual(1, len(omitted_twice["finding_history"]))
        reappeared = reviews.accept_result(self.root, self.packet, result, omitted_twice)
        self.assertEqual("rejected", reappeared["findings"][0]["disposition"])
        self.assertEqual("Synthetic author adjudication.", reappeared["findings"][0]["author_review"])
        self.assertEqual([], reappeared["finding_history"])

    def test_changed_approval_evidence_reopens_adjudicated_issue(self):
        approval = self.root / "docs/approval.md"
        approval.write_text("TEST MATERIAL: approved for one test only.\n")
        ref = core.snapshot(self.root, {"path": "docs/approval.md", "source_class": "test", "authority": "test-material"})
        self.packet["sources"][1]["authority_evidence"] = ref
        self.refresh_id(self.packet)
        result = self.result()
        result["findings"] = [self.finding()]
        previous = reviews.accept_result(self.root, self.packet, result)
        previous["findings"][0]["disposition"] = "accepted"
        approval.write_text("TEST MATERIAL: approval withdrawn for this test.\n")
        new_packet = self.packet_for("continuity")
        new_packet["sources"][1]["authority_evidence"] = core.snapshot(self.root,
            {"path": "docs/approval.md", "source_class": "test", "authority": "test-material"})
        self.refresh_id(new_packet)
        new_result = self.result(new_packet)
        new_result["findings"] = [self.finding(new_packet)]
        reopened = reviews.accept_result(self.root, new_packet, new_result, previous)["findings"][0]
        self.assertEqual("open", reopened["disposition"])
        self.assertIn("reopened_reason", reopened)

    def test_handoff_preserves_manual_review_and_marks_changed_sources_for_review(self):
        packet = self.packet_for("handoff")
        result = self.result(packet)
        observation = {"text": "Observed: Mira has the key.", "evidence": [packet["sources"][0]]}
        result["handoff"]["entry_state"] = [observation]
        result["handoff"]["exit_state"] = [observation]
        first = reviews.accept_result(self.root, packet, result)
        first["author_review"] = {"status": "accepted", "by": "Synthetic test author", "note": "Keep the handoff."}
        repeated = reviews.accept_result(self.root, packet, result, first)
        self.assertEqual(first["author_review"], repeated["author_review"])
        self.scene.write_text("SYNTHETIC TEST MATERIAL.\nMira still kept the brass key.\nPerhaps Orren was afraid.\n", encoding="utf-8")
        changed = self.packet_for("handoff")
        changed_result = self.result(changed)
        changed_observation = {"text": "Observed: Mira still has the key.", "evidence": [changed["sources"][0]]}
        changed_result["handoff"]["entry_state"] = [changed_observation]
        changed_result["handoff"]["exit_state"] = [changed_observation]
        rechecked = reviews.accept_result(self.root, changed, changed_result, repeated)
        self.assertEqual("needs-review", rechecked["author_review"]["status"])
        self.assertEqual(first["author_review"], rechecked["author_review"]["prior_review"])
        self.assertEqual(packet["packet_id"], rechecked["author_review"]["reviewed_packet_id"])
        self.assertIn("changed", rechecked["author_review"]["reason"])

    def revision_pair(self):
        packet = self.packet_for("revision")
        original = deepcopy(packet["sources"][0])
        packet["constraints"] = {
            "revision_source": {key: original[key] for key in ("path", "line_start", "line_end", "sha256")},
            "revision_objective": "Compress the synthetic excerpt.",
            "protected": ["Mira retains the key", "Preserve uncertain inference"],
        }
        self.refresh_id(packet)
        result = self.result(packet)
        result["revision"] = {
            "original": original, "objective": packet["constraints"]["revision_objective"],
            "protected": [{"requirement": item, "evidence": [original]} for item in packet["constraints"]["protected"]],
            "proposed_text": "Mira kept the key. Perhaps Orren was afraid.",
            "summary": "Synthetic validation fixture removes the metal descriptor only.",
            "new_factual_proposals": [],
            "checks": [{"requirement": item, "result": "preserved", "reason": "Synthetic reviewer assertion.",
                        "evidence": [original]} for item in packet["constraints"]["protected"]],
        }
        return packet, result

    def test_proposal_keeps_source_bytes_and_stale_source_rejected(self):
        packet, result = self.revision_pair()
        before = self.scene.read_bytes()
        accepted = reviews.accept_result(self.root, packet, result)
        self.assertEqual(before, self.scene.read_bytes())
        self.assertTrue(accepted["revision"]["source_preserved"])
        self.assertIn("proposal", accepted["revision"]["patch"])
        self.scene.write_text("Changed source.\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            reviews.check_proposal(self.root, packet, result)

    def test_revision_must_identify_exact_passage_and_all_protected_checks(self):
        packet, result = self.revision_pair()
        result["revision"]["original"] = deepcopy(packet["sources"][1])
        with self.assertRaisesRegex(ValueError, "identified passage"):
            reviews.check_proposal(self.root, packet, result)
        packet, result = self.revision_pair()
        result["revision"]["checks"].pop()
        with self.assertRaisesRegex(ValueError, "lacks protected"):
            reviews.check_proposal(self.root, packet, result)

    def test_revision_original_cannot_be_a_substring_of_selected_lines(self):
        packet, result = self.revision_pair()
        result["revision"]["original"]["excerpt"] = "Mira kept the brass key."
        with self.assertRaisesRegex(ValueError, "entire identified passage"):
            reviews.check_proposal(self.root, packet, result)

    def test_explicit_revision_excerpt_can_select_exact_subline_passage(self):
        packet, result = self.revision_pair()
        selected = "Mira kept the brass key."
        packet["constraints"]["revision_source"]["excerpt"] = selected
        self.refresh_id(packet)
        result["packet_id"] = packet["packet_id"]
        result["revision"]["original"]["excerpt"] = selected
        accepted = reviews.check_proposal(self.root, packet, result)
        self.assertEqual(selected, accepted["original"]["excerpt"])
        result["revision"]["original"]["excerpt"] = "brass key."
        with self.assertRaisesRegex(ValueError, "entire identified passage"):
            reviews.check_proposal(self.root, packet, result)

    def test_uncertain_protected_check_remains_incomplete(self):
        packet, result = self.revision_pair()
        result["revision"]["checks"][0]["result"] = "uncertain"
        self.assertEqual("INCOMPLETE", reviews.accept_result(self.root, packet, result)["status"])

    def test_reader_claim_alone_cannot_establish_blinding(self):
        packet = self.packet_for("reader")
        result = self.result(packet)
        result["reader"] = {"isolation": "fresh-session", "questions": ["What do you expect Mira to do next?"]}
        accepted = reviews.accept_result(self.root, packet, result)
        self.assertEqual("unverified", accepted["reader"]["isolation"])
        self.assertIn("simulated", accepted["reader"]["feedback_type"])

    def test_handoff_is_source_bound_and_derived(self):
        packet = self.packet_for("handoff")
        result = self.result(packet)
        result["handoff"]["exit_state"] = [{"text": "Observed: Mira retains key; fear is an inference.",
                                              "evidence": [packet["sources"][0]]}]
        accepted = reviews.accept_result(self.root, packet, result)
        self.assertIn("not canon", accepted["authority"])
        self.assertEqual("draft", accepted["handoff"]["exit_state"][0]["evidence"][0]["authority"])

    def test_alternatives_require_explicit_task_constraint(self):
        packet = self.packet_for("pov")
        result = self.result(packet)
        result["alternatives"] = [{"text": "Perhaps Orren was afraid.", "evidence": [packet["sources"][0]]}]
        with self.assertRaisesRegex(ValueError, "unexpected fields"):
            reviews.accept_result(self.root, packet, result)
        packet["constraints"]["request_alternatives"] = True
        self.refresh_id(packet)
        result["packet_id"] = packet["packet_id"]
        self.assertEqual(1, len(reviews.accept_result(self.root, packet, result)["alternatives"]))


if __name__ == "__main__":
    unittest.main()
