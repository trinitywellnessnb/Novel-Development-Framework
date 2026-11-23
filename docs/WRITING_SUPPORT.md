# Source-aware writing toolkit

The toolkit prepares bounded evidence packets, checks explicit state and event records, validates results from an actual native Codex review, and builds manuscript copies. Python 3.10+ and the standard library run the core tools. Pandoc is required for DOCX/EPUB; EPUBCheck with Java is optional conformance validation. No hosted service, database, new model account, or model API key is required.

Read your project’s `AGENTS.md` and governing workflow first. Framework references: [AGENTS.md](https://github.com/trinitywellnessnb/Novel-Development-Framework/blob/main/AGENTS.md), [the workflow](https://github.com/trinitywellnessnb/Novel-Development-Framework/blob/main/docs/WORKFLOW.md), and [the review protocol](https://github.com/trinitywellnessnb/Novel-Development-Framework/blob/main/docs/REVIEW_PROTOCOL.md). The author controls canon, creative changes, and publication. A successful tool result establishes only the checks named in that result.

## Installation and first run

For a new independent project, use [project setup](PROJECT_SETUP.md). For an existing repository with another layout, install the managed toolkit and register its exact source paths; the review and export tools do not require numbered manuscript directories. [Framework updates](FRAMEWORK_UPDATES.md) documents the single supported distribution method, installation receipt, compatibility checks, upgrade proposals, conflicts, and rollback. Keep unrelated fictional universes in separate repositories.

From a framework checkout:

```bash
python scripts/writing_toolkit.py --help
python scripts/writing_toolkit.py doctor
python scripts/writing_toolkit.py index --out .writing-support/first-index.json
```

From an installed project, use `python .ndf/scripts/writing_toolkit.py --root .` in place of `python scripts/writing_toolkit.py`. Global `--root` and `--config` arguments precede the command. Relative input paths resolve against the project root. All generated writing records remain under `.writing-support/`; writers create a local `.gitignore` containing `*` there even when the project already has root ignore rules. Existing project rules remain unchanged. Git ignores do not hide previously tracked files; remove any accidentally tracked creative artifact from sharing through your project privacy workflow. Use a new output name for a new run so earlier evidence and decisions remain reviewable.

## Project configuration and source registration

The default configuration is `09_Tools/Writing_Support.json` in the project root. `schema_version: 1`, `books`, and an explicit `sources` list define the interface. Book selectors are project-defined strings; each can carry a stable `repository_id`. Neither chapter counts nor genres, character attributes, calendars, phases, or narrative structure are fixed.

A source selection names `path`, `source_class`, and `authority`, with optional `line_start`/`line_end` (1-based inclusive), `critical`, `reason`, `applicability`, and `supersedes`. Registration authorizes tool selection within the already-authorized task; it does not prove permission to inspect a manuscript. No recursive manuscript discovery occurs. Keep sources, decisions, and original bytes in the project repository.

For example, a project can register its current working chapter as:

```json
{
  "path": "drafts/chapter-a.md",
  "source_class": "manuscript",
  "authority": "draft",
  "applicability": {
    "books": ["BOOK-001"],
    "scenes": ["SCENE-A"],
    "reader_visible": {"book": "BOOK-001", "position": 1}
  },
  "reason": "Author-authorized scene review"
}
```

This is a schema illustration; create and authorize the named project file before registering it. `index` reads and hashes the actual file bytes, including uncommitted edits. Each selection retains the exact quote, span, hash, Git source revision when available, source class, applicability, and supersession metadata. Unknown authority stays unknown. Modification time never promotes authority.

Approved source labels require `authority_evidence`, a separate source selection quoting the applicable author decision. Byte validation checks that this evidence exists; a person must assess whether the decision actually approves the claim in scope. Set `authority_order` to an ordered list of project authority labels; set `approved_authorities` for additional custom labels that require approval evidence (all `approved-*` labels always do). `critical: true` retains a source even when the budget overflows. Within those groups, hierarchy order and stable configuration order determine selection. Use `account` for fact, belief, deception or interpretation labels, `applicability` for book/chapter/scene/character/phase/time restrictions, and `supersedes` for scoped replacement relationships. Configure hierarchy and source priorities in the project configuration. A hierarchy guides selection and interpretation; conflicting approved evidence must remain an explicit author decision. Character belief, narrator assertion, deception, interpretation, and objective fact remain separate record layers.

## Context and literary review

A request supplies `book`, `scene`, `viewpoint`, `task`, and task constraints. Optional chapter, objective, characters, project time label (`time` matched to `applicability.times`), development phase, reader position, context budget, and source-backed scene fields narrow the task. Unsupported or absent story facts remain unknown. Prepare JSON and a readable brief:

```bash
python scripts/writing_toolkit.py prepare --request 09_Tools/context-request.json --out .writing-support/context/scene-a.json
python scripts/writing_toolkit.py check --packet .writing-support/context/scene-a.json
```

Project initialization creates the request named above. Change its selectors to your actual registered scene and sources before a literary task. The brief lists the evidence boundary, unknowns, unavailable sources, exclusions, and budget method. `estimated_tokens` counts excerpts; `packet_estimated_tokens` estimates serialized packet metadata plus native instructions and result schema using characters/4. These are estimates, not a model tokenizer. Noncritical sources are removed from the end of the priority order to fit; minimum evidence and critical constraints are retained with explicit overflow. `required_context_fields` can require only the dimensions this task needs. Counts are estimated unless the result explicitly says otherwise. Critical constraints remain visible when they cannot fit. File-based preparation also binds the request bytes, so changing objectives or protected requirements invalidates the packet. Reader input bindings stay in a separate private sidecar, represented by an opaque identifier. Use neutral filenames for reader-visible source excerpts, since citation paths are visible to the reviewer. Prepare again after relevant source, request or configuration changes; `check` rejects stale packets.

Use distinct task values:

| Task | Assessment |
| --- | --- |
| `context` | Scene identity, instructions, applicable facts, character conditions, immediate history, voice, POV, protected revelations, conflicts, and gaps |
| `continuity` | Physical facts, objects, travel, knowledge, phase abilities, motivation, causality, setups/payoffs, and obligations |
| `voice` | Author/book/narrator/scene directions; diction, syntax, rhythm, imagery, distance, and emotional handling |
| `dialogue` | Speaker intention, vocabulary, syntax, subtext, knowledge, relationships, and development |
| `pov` | Applicable perspective rules; observation, inference, memory, belief, and unavailable private knowledge |
| `handoff` | Cited entry/exit state, actions, decisions, concealed/gained knowledge, obligations, and consequences |
| `revision` | A separate bounded prose proposal with protected facts, beats, voice, POV, and source version |
| `reader` | Simulated response using reader-visible material at the chosen reading point |

Preparation produces `PREPARED` evidence and, for review tasks, adjacent `.task.md` instructions and `.result-template.json`. It has not performed semantic analysis. Give those files to the current native Codex session or an authorized native subagent, which must actually read and evaluate the selected excerpts. The repository-local [skill](skills/writing-support/SKILL.md) routes ordinary-language requests through this workflow.

When an authenticated Codex CLI is already available, the optional adapter runs an ephemeral read-only task:

```bash
python scripts/writing_toolkit.py native --packet .writing-support/context/scene-a.json --out .writing-support/native/scene-a.json
```

The adapter does not provision accounts. An unavailable runtime is a blocked execution, not a completed review. Native execution of reader tasks is intentionally declined because the CLI adapter cannot establish effective retrieval isolation.

After an actual reviewer fills a copy of the result template, validate its identity, citations, coverage, and bounds:

```bash
python scripts/writing_toolkit.py accept --packet .writing-support/context/scene-a.json --result .writing-support/native/scene-a.json --out .writing-support/reviews/scene-a.json
```

`accept` means acceptance by the evidence validator, not author acceptance of findings or prose. `REVIEWED` means a submitted bounded assessment with checked evidence; `INCOMPLETE` means coverage or required checks are missing. Neither says the interpretation is true. Missing context and incomplete coverage prevent a comprehensive pass.

Each material finding has a stable ID, reviewed quotation, governing citations, category, explanation, narrative consequence, qualitative confidence/reason, smallest candidate repair, and author disposition. Categories separate established contradiction, unexplained transition, missing evidence, intentional/permitted difference, and optional craft. Unanswered mysteries are not automatically plot holes. Voice reviews do not impose numerical prose targets or a generic house style. Alternatives are produced only for a revision task or explicit `constraints.request_alternatives: true`.

To retain author review decisions on the next run, supply `--previous` with the prior validated report. The report preserves unchanged findings and their dispositions; changed evidence reopens the affected finding with a reason. Omitted findings remain in history instead of silently becoming resolved. Keep author decisions in project-owned decision records and cite them. An accepted finding does not authorize a manuscript edit or canon promotion.

## Character state and chronology

State and event tools validate declared records, not prose semantics. All populated factual records need source evidence arrays. The synthetic demonstration generates complete executable examples:

```bash
python scripts/writing_toolkit.py demo
python scripts/writing_toolkit.py states --input .writing-support/demo/state.json --out .writing-support/states/demo.json
python scripts/writing_toolkit.py chronology --input .writing-support/demo/events.json --out .writing-support/chronology/demo.json
```

The synthetic state command intentionally returns `INVALID` and exit status 1 for a premature capability and unexplained changes; it demonstrates detection. The event example can remain `INCOMPLETE` because uncertainty and unlocated events are deliberately preserved. Inspect their reports rather than treating every non-pass as a broken command.

State dimensions are optional project-defined values: location, injury, possessions, knowledge/beliefs, emotion, relationships, skills, commitments, or other needs. Explicit cited changes connect entry and exit states. Phase rules constrain capabilities only when configured; exceptions must be explicit. An explained development is distinct from a contradiction.

Event identities link depictions across books. Record world events, character knowledge, and reader revelations separately. Ordering supports strict, simultaneous, overlapping, and unknown/uncertain relationships without exact dates. Project-defined clocks remain separate unless an explicit compatible conversion is supplied. Cycles, incompatible explicit ordering, and premature configured revelations produce deterministic findings; uncertain dates and missing evidence remain visible. Differing beliefs or unreliable accounts are not automatically contradictory events.

## Controlled revisions and chapter handoffs

For revision requests, `constraints` must identify the exact `revision_source` path, hash and line range, a `revision_objective`, and `protected` requirements. Optional `length_target` values are advisory word-count checks. The result contains the exact original, proposed prose, substantive summary, added factual proposals, checks against every protected requirement, unresolved concerns, and a localized diff. A stale source or a different objective is rejected.

```bash
python scripts/writing_toolkit.py check --packet .writing-support/context/revision.json --result .writing-support/native/revision.json
```

This never applies a patch. Semantic preservation checks are reviewer assertions that need author review. A compression must preserve the required functions and beats; an expansion must earn its added action, staging, emotion, or subtext. The source manuscript stays untouched.

A `handoff` task extracts cited state and consequences into derived lists. Reuse a prior report through `--previous` for affected rechecks. Handoffs remain draft-derived when their sources are drafts; regenerate after source changes. They are not a second character or canon database.

## Simulated reader feedback

Reader requests require `reading_order` and `reader_point`, with each visible selection explicitly marked by `applicability.reader_visible`. Only manuscript/test spans at or before that point enter the packet. Author-only context, hidden canon, future text, and unrevealed companion material are excluded. Reader packet preparation is a selection boundary; it does not enforce the reviewer's runtime access.

A credible blinded review requires a fresh reviewer with no inherited hidden context and no retrieval access to hidden files. If the environment cannot enforce both, label the result simulated and **not blinded**. The validator records effective isolation as unverified even if the model claims a fresh session. Ask about understood events/motivations/relationships, useful mysteries, confusion, emotion, abrupt developments, anticipation, and reasons to stop. Cite reader-visible passages and supply optional non-leading human beta-reader questions. Model opinions are not audience research.

## Manuscript copies and exports

Pandoc builds DOCX and EPUB from an explicit ordered manifest. Paths and hashes, roles (`frontmatter`, `chapter`, `backmatter`), metadata, asset hashes, formats, formatting, and optional cover/reference DOCX are declared. Chapter order comes from the manifest, not filenames. Author approval evidence is mandatory for non-preview sources and assets. An export is a local build, not publication authorization.

A runnable synthetic example produces both formats:

```bash
python scripts/writing_toolkit.py export --manifest tests/fixtures/writing_export/manifest.json --preview --out .writing-support/exports/synthetic-a
python scripts/writing_toolkit.py export --manifest tests/fixtures/writing_export/manifest.json --preview --out .writing-support/exports/synthetic-b
python scripts/writing_toolkit.py epubcheck --input .writing-support/exports/synthetic-a/draft-preview.epub
```

For one format, set manifest `formats` to `["docx"]` or `["epub"]`. Draft previews have explicit unapproved labels. The build report records dependency versions, source provenance, metadata, structural checks, content round trips, and conformance status. Ordered text/punctuation, paragraph sequence, italics, headings, image count, and scene breaks are checked. Images must be explicitly declared local assets. Manuscript markup is data, not executable instructions or resource-loading permission.

Rebuild the identical manifest to a new directory to check reproducibility under the installed Pandoc version. `SOURCE_DATE_EPOCH` and a manifest-derived identifier stabilize generated metadata. Compare the recorded hashes; do not claim binary reproducibility across untested tool versions.

Install official EPUBCheck locally and set `EPUBCHECK_JAR` to its jar, or put `epubcheck` on `PATH`. `SKIPPED` means EPUB conformance has not been validated. `PASSED` requires successful execution. Structural validity does not establish visual quality, print readiness, retailer acceptance, or publishing permission. Review representative pages in Word/LibreOffice and EPUB in a reader when available. Specify and verify trim, margins, fonts, images, and printer requirements before any print-ready claim. The framework's existing publication workflows remain applicable; this toolkit does not add PDF generation.

## Troubleshooting and limits

| Result | Action |
| --- | --- |
| `HOLD: Missing source` or unavailable source | Correct the explicit path or record the authorized source as missing; do not invent content |
| Hash/span/quotation mismatch | Read the authorized current source and regenerate the packet or correct the citation |
| Approved authority lacks evidence | Register the actual approving decision; keep unapproved material labeled accurately |
| Critical sources exceed budget | Narrow the authorized scope or increase the budget; inspect exclusions |
| Output already exists | Choose a new run name and retain the earlier artifact |
| Review is `INCOMPLETE` | Inspect coverage, gaps, unresolved questions, and preservation checks |
| Native adapter fails | Use the current authorized Codex session with the generated task contract, or report runtime blockage |
| EPUBCheck skipped | Install it locally and rerun; do not call the EPUB validated |
| Upgrade conflict | Keep project modifications and review the generated plan; see the update guide |

Exact citations prevent fabricated or stale quotations, not unsupported interpretations of a real quotation. Deterministic record checks need manually authored or reviewed structured input. No general prose parser infers a complete event graph or character database. Author consent and semantic quality cannot be inferred from schema success. See [the inventory](WRITING_SUPPORT_INVENTORY.md) and [verification record](WRITING_SUPPORT_VERIFICATION.md) for exercised behavior and limits.
