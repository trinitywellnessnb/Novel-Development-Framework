# Implementation inventory and provenance

Discovery began on `main` at `a71ff09` with a clean working tree. The baseline had 32 passing Python unittest cases, structural validation of 82 Markdown files, and read-only GitHub Actions on Python 3.10/3.13. Root AGENTS.md was the sole applicable agent-instruction file. Existing utilities used Python 3.10+ standard library; no package/dependency manifest or tagged semantic release existed. The changelog used an unreleased baseline.

The framework already separated governance, preserved artifacts, staged claims, approved canon, development, story planning, per-book manuscripts, and publication preparation. Existing author intent, voice guide, character, scene, timeline, context, review, decision, and beta-feedback templates remain the editorial foundation. The implementation extends these contracts with executable tools instead of adding another canon index or agent stack.

| Capability | Existing framework | Reference engineering | Framework action |
| --- | --- | --- | --- |
| Source indexing | Named checksums; exact-source packet validator | Explicit spans, byte hashes, authority evidence | Reuse validator and generalize index/configuration |
| Context briefs | Writing Context Brief template; prose approval gate | Budgeted JSON/Markdown packets | Adapt source selection, freshness, budgets and unknowns |
| Character tracking | Character/relationship templates; continuity procedure | Explicit state change chains and phase rules | Generalize optional dimensions, capabilities and phases |
| Chronology | Timeline/scene/series records | Event graph, local clocks, depictions and reader reveals | Reuse with neutral relations and no universal calendar |
| Continuity analysis | Source-bound review categories | Native task contract and validated findings | Reuse evidence boundaries; retain author decisions |
| Narrative voice | Author Voice Drafting and Humanizer guidance | Dedicated native voice assessment | Integrate approved author/book/narrator directions |
| Dialogue | Voice/scene guidance | Dedicated dialogue contract | Reuse contextual assessment without verbal gimmicks |
| POV | Viewpoint and knowledge in scene briefs | Dedicated viewpoint contract | Reuse rules-based native review with citations |
| Revision proposals | Rewrite protocol and preserved revisions | Bounded proposals, exact original and localized diff | Reuse immutable source checks; no automatic application |
| Reader simulation | Beta-feedback template and reader review | Visible-span selection; honest isolation limits | Reuse packets and simulated feedback contract |
| Manuscript export | Publication checklists; no compiler | Ordered manifest, Pandoc DOCX/EPUB, round trips | Adapt reusable export profiles and actual conformance reporting |
| Framework distribution | Copy/template onboarding; no upgrade path | Repository-local tools only | Implement one versioned managed distribution/update mechanism |

## Reference review

The authorized private reference was PR #63 in Veiled Observers, exact commit `6850226a6b75623211368b056f6700c80df97753`. Its reported delivery was 157 total tests, including 56 toolkit tests. The 56 toolkit tests were independently executed successfully, including installed Pandoc integration, before adaptation. Other reported totals and earlier visual/model demonstrations are historical claims, not verification of this framework branch.

Reusable engineering was reviewed outside the public checkout. The adapted components are `scripts/writing_support/` (core, context, reviews, structure, exporter, synthetic demonstration), `scripts/writing_toolkit.py`, four toolkit test modules, and explicitly synthetic fixtures. The framework's existing `validate_review_packet.py` remains the evidence validator. Private project configuration, manuscript sources, lore, notes, actual character records, exports, generated review artifacts, and private documentation were excluded. Project-specific prompt language was removed. The distribution/update subsystem and project initialization were implemented for this framework.

The upstream engineering is MIT-licensed, copyright 2026 Trinity Wellness. Its [license notice](vendor/writing-support/LICENSE.txt) is preserved. Referencing the supplied repository and commit provides attribution; access to private creative material is neither required nor granted by this public framework.

## Ownership and authority

| Layer | Owner and treatment |
| --- | --- |
| Reusable tools, schemas, generic templates, workflow instructions | Framework-owned; versioned managed distribution |
| Configuration, author instructions, canon, manuscripts, characters, worldbuilding, decisions | Project-owned; upgrades preserve them |
| Custom project tools or deliberate framework modifications | Project extensions; detect changes and require review |
| Indexes, context packets, reviews, proposals, temporary exports | Derived local work; source-linked, never automatically canonical |

See [setup](PROJECT_SETUP.md), [toolkit operations](WRITING_SUPPORT.md), [updates](FRAMEWORK_UPDATES.md), and [the verification record](WRITING_SUPPORT_VERIFICATION.md) for current behavior and test evidence. Installation compatibility is bounded by tested schema/tool versions; a framework update does not validate the novel's creative truth.
