# Writing toolkit delivery and verification

This report records exercised behavior and remaining limits. Evidence validation does not establish literary accuracy, actual author consent, or canon approval.

## Repository and discovery

Started from clean `main` at `a71ff09dc755cebc79576c8ac16477c681c12833`; implementation branch: `feature/reusable-writing-toolkit`. Root AGENTS.md, Constitution, workflow and review rules govern; no nested AGENTS.md existed. Existing Python standard-library scripts, Markdown/CSV templates, canon approval and scene registry were preserved. Baseline: 32 tests passed and 82 Markdown documents passed structural validation. No existing package, release tags or framework update mechanism existed.

The final commit, draft PR, clean working-tree status and remote CI result are recorded in the delivery response and PR. No release is published and no PR is merged.

## Architecture and reuse

Core modules under `scripts/writing_support/` handle evidence, context, review contracts/results, state/event constraints, exports and initialization. `scripts/writing_toolkit.py` is the CLI. Project-owned JSON configuration registers exact source paths and authority; actual creative records remain independent. Derived packets/reports/proposals/exports stay in `.writing-support/`, with a local ignore marker. Unknown facts remain unknown. Approved labels need linked approval evidence; a hash verifies bytes, not the approving decision's meaning.

`framework.json` versions framework/toolkit 1.0.0, configuration schema 1 and Python >=3.10. `framework_manager.py` distributes only allowlisted engineering files under `.ndf/`. Local candidate bundles support opt-in version comparison, conflict detection, proposal, adoption, rollback and interruption recovery. Project-owned settings, canon, author instructions and extensions are never synchronized. No migrations currently exist: schema/major-version changes block adoption. Unknown project extensions require project-local tests before acceptance.

Authorized private reference PR #63 at commit `6850226a6b75623211368b056f6700c80df97753` was inspected outside the public checkout. All 56 toolkit tests passed independently before reuse. Its reported 157 total tests are not this branch's test count. Reused: eight generic toolkit engineering files, four test modules and explicitly synthetic fixtures. Added independently: project initialization, distribution/upgrades, missing templates, generic configuration/authority/budget refinements, privacy/freshness fixes and additional tests. Existing framework evidence validation and editorial guidance remain the foundation. MIT attribution is preserved; see [inventory](WRITING_SUPPORT_INVENTORY.md).

No private reference configuration, manuscript, canon, character record, author note, historical source, credential, full history or documentation was transferred. Vetted engineering removed a project-specific lens phrase. Fictional fixture names/content are explicitly synthetic. Introduced files, staged changes and public history were reviewed; derived results and runtime logs are ignored and excluded from commits. CI uses only synthetic sources and has read-only GitHub permissions.

## Feature delivery matrix

| Capability | Status and exercised behavior |
| --- | --- |
| Source indexing/provenance | Implemented/exercised: actual bytes, source Git revision, SHA-256, exact spans/quotes, class, approval link, applicability, account layer, supersession, scope |
| Authority hierarchy | Implemented/exercised: project order, custom approved labels, no modification-time authority or automatic canon promotion; semantic source conflicts remain author review |
| Context briefs | Implemented/exercised: structured + Markdown, task/book/chapter/scene/viewpoint/character/phase/time selectors, unknown fields and exclusions |
| Context budgets | Implemented/exercised: deterministic priorities, excerpt/full-packet character estimates, critical retention and explicit overflow; not model-token exact |
| Freshness | Implemented/exercised: sources, approval evidence, relevant omitted inputs, configuration and request bytes; reader bindings in private sidecar |
| Character states/phases | Implemented/exercised: optional dimensions, observed/inferred/unexplained changes, optional skills/abilities/phases and evidenced exceptions |
| Chapter handoffs | Implemented/exercised: seven source-cited state/consequence categories; derived status and stale-source rejection |
| Event graph | Implemented/exercised: strict/simultaneous/overlap/uncertain/unordered relations, cycle/date checks and incompatible clocks without invented conversion |
| Cross-book continuity | Implemented/exercised on synthetic records: shared event IDs, multiple depictions/account layers, reading order and reader revelation progression |
| Revelation checks | Implemented/exercised: earliest reader positions, prerequisite warnings and premature reveals; separate character knowledge |
| Continuity/causality | Implemented/exercised native assessment + deterministic declared-state/event checks; no automatic complete prose extraction |
| Review dispositions | Implemented/exercised: stable IDs, preserved decisions/history, meaningful evidence changes reopen findings; incomplete coverage stays incomplete |
| Voice review | Implemented/exercised native book/author-direction assessment; no generic readability optimization |
| Dialogue review | Implemented/exercised native assessment, including a correct zero-finding baseline and positive challenge |
| POV review | Implemented/exercised native assessment separating private knowledge from signaled inference |
| Local alternatives | Implemented/validated with explicit alternatives contract; prose suggestions require selected scope |
| Bounded revision | Implemented/exercised expansion and condensation with source identity, protected checks, factual proposals, separate diff and stale rejection; never applied |
| Reader packet restriction | Implemented/exercised selected visible spans and metadata allowlist; future/hidden sources excluded |
| Blinded beta reading | Blocked: this runtime cannot enforce inherited-context and retrieval isolation; simulated feedback explicitly NOT blinded |
| Simulated reader response | Implemented/exercised native assessment with cited observations and questions; not audience research |
| Manuscript manifests | Implemented/exercised explicit order, source/asset approval, front/back matter, author/series metadata, cover/reference DOCX and formatting |
| DOCX/EPUB | Implemented/exercised real Pandoc builds, round trips, order/paragraph/punctuation/italics/headings/scene-break/image-byte preservation |
| Export reproducibility | Implemented/exercised byte-identical repeated DOCX/EPUB builds under Pandoc 3.1.11.1; not cross-version guaranteed |
| EPUB conformance | Exercised official EPUBCheck 5.4.0: zero fatals/errors/warnings; unavailable validators remain SKIPPED |
| Visual validation | DOCX rendered with LibreOfficeDev 26.8 and representative page inspected; EPUB reader rendering timed out, remains unverified |
| PDF/print readiness | Existing publication guidance preserved; no existing automated PDF exporter to replace; no new print-ready claim |
| Project initialization | Implemented/exercised standalone/series, optional author/genre/POV/voice/clocks/worldbuilding/characters, custom book root, existing instructions preserved |
| Generic templates/skill | Implemented/exercised structure checks; existing equivalents reused, eleven missing templates added; one native skill routes ordinary language |
| Native CLI adapter | Implemented, probe blocked by HTTP 401 authentication here; successful actual model demonstrations used current-session native subagents |
| Installation/version/update detection | Implemented/exercised separate project, managed runtime completeness, installed version and candidate comparison |
| Upgrade conflict/adoption/rollback | Implemented/exercised local edits/extensions, stale plans, incompatibility, unchanged creative bytes, failed and interrupted transactions, serialized recovery |
| Update PR automation | Deliberately not implemented: local reviewable proposal is the single default; projects can open draft PRs through their existing authorized Git workflow |
| Windows operation locking | Implemented adapter, unverified on Windows; Linux advisory lock/concurrent recovery tested |

## Automated and manual verification

Final commands:

```bash
EPUBCHECK_JAR=/path/to/epubcheck-5.4.0/epubcheck.jar python -m unittest discover -s tests -v
python scripts/validate_framework.py
```

The actual local jar was installed outside the repository. Final local run: **147 tests passed, zero failures and zero skips**, in 25.189 seconds with Pandoc and official EPUBCheck available. Structural validation passed over **110 Markdown documents**. CI status is recorded in the delivery response/PR; local success is not a claim of remote CI success. Tests exercise real filesystem contents, Git ignore behavior, separate-project CLI installation and Pandoc round trips. External tools are optional at runtime; tests explicitly skip unavailable integrations instead of claiming conformance.

The 30 requested synthetic cases are covered across `test_writing_core.py`, `test_writing_generic.py`, `test_writing_reviews.py`, `test_writing_structure.py`, `test_writing_project.py`, `test_writing_export.py` and `test_framework_manager.py`, plus actual [native demonstrations](WRITING_SUPPORT_DEMONSTRATIONS.md). These cover attributes/objects/consistent details/development/capabilities, deception/unreliability, chronology/clocks/revelations, POV/inference, voice/dialogue, fabricated/missing/superseded/unapproved evidence, stale and protected revisions, reader restriction, exports, installation, updates, local modifications, conflicts, creative-file preservation and recovery. A deterministic test does not prove literary understanding; see observed model outcomes separately.

Independent review identified reader metadata leakage, unbound request freshness, existing-project ignore behavior, incomplete candidate runtimes and a concurrent recovery race. Each received a regression fix. Schema booleans were also rejected consistently in config/packet/result/export. No confirmed important defect remains outstanding. Runtime isolation, Windows locking, EPUB visual verification and arbitrary project compatibility retain the limits above.

## Working command reference

Run from a framework checkout; installed projects replace `python scripts/writing_toolkit.py` with `python .ndf/scripts/writing_toolkit.py --root .`. Use new output names on repeated runs.

```bash
# Initialize a new standalone (do not run into an already configured project).
python scripts/writing_toolkit.py --root /tmp/standalone init --title "New Novel" --author "Pen Name"
# Separate new series; options JSON supports further author-defined conventions.
python scripts/writing_toolkit.py --root /tmp/series init --title "Companion Series" --book BOOK-001="First Novel" --book BOOK-002="Companion Novel"
# Index sources and prepare the initializer's editable context request.
python scripts/writing_toolkit.py --root /tmp/standalone index
python scripts/writing_toolkit.py --root /tmp/standalone prepare --request 09_Tools/context-request.json
python scripts/writing_toolkit.py version
```

The following complete synthetic task inputs can be prepared without fictional setup. `demo` writes inputs only, never model answers:

```bash
python scripts/writing_toolkit.py demo
python scripts/writing_toolkit.py --config .writing-support/demo/config.json prepare --synthetic --request .writing-support/demo/continuity.request.json --out .writing-support/tasks/continuity.json
python scripts/writing_toolkit.py states --input .writing-support/demo/state.json
python scripts/writing_toolkit.py chronology --input .writing-support/demo/events.json
python scripts/writing_toolkit.py --config .writing-support/demo/config.json prepare --synthetic --request .writing-support/demo/voice.request.json --out .writing-support/tasks/voice.json
python scripts/writing_toolkit.py --config .writing-support/demo/config.json prepare --synthetic --request .writing-support/demo/dialogue.request.json --out .writing-support/tasks/dialogue.json
python scripts/writing_toolkit.py --config .writing-support/demo/config.json prepare --synthetic --request .writing-support/demo/pov.request.json --out .writing-support/tasks/pov.json
python scripts/writing_toolkit.py --config .writing-support/demo/config.json prepare --synthetic --request .writing-support/demo/revision.request.json --out .writing-support/tasks/revision.json
python scripts/writing_toolkit.py --config .writing-support/demo/config.json prepare --synthetic --request .writing-support/demo/handoff.request.json --out .writing-support/tasks/handoff.json
python scripts/writing_toolkit.py --config .writing-support/demo/config.json prepare --synthetic --request .writing-support/demo/reader.request.json --out .writing-support/tasks/reader.json
# Both DOCX and EPUB, explicitly a synthetic preview:
python scripts/writing_toolkit.py export --manifest tests/fixtures/writing_export/manifest.json --preview --out .writing-support/exports/example
```

The state fixture intentionally returns INVALID/exit1; chronology intentionally retains uncertainty. Preparing a review is not executing it: ask native Codex to read the adjacent task contract/packet and fill a result, then use `accept --packet ... --result ... --out ...`. The optional authenticated `native` adapter executes non-reader tasks. Reader execution must disclose effective isolation. These are the same workflow entry points for scene/character continuity, voice, dialogue, POV, revision, handoff and simulated beta review.

For installation, checking available candidate versions, preparing upgrade proposals, adoption and reversal, use the tested commands in [FRAMEWORK_UPDATES.md](FRAMEWORK_UPDATES.md). Detailed configuration, source registration, review dispositions, revisions, exports and troubleshooting are in [WRITING_SUPPORT.md](WRITING_SUPPORT.md) and [PROJECT_SETUP.md](PROJECT_SETUP.md).

No unresolved routine engineering choice requires author input. Each project still needs its own author decisions about creative sources, authority, voice, intended reading order, publication approval and publisher specifications.
