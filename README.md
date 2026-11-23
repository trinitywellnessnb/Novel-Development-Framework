![Novel Development Framework: an illustrated writing desk, story map, and creative development connections](assets/novel-development-framework-banner.webp)

# Novel Development Framework (NDF)

**A free, open-source workspace for planning a novel, reconstructing an older manuscript, or keeping a series consistent. Use it on your own, with an editor, or with an AI assistant. The author decides what becomes canon, what gets rewritten, and what gets published.**

NDF gives the work behind the manuscript a home: original drafts and conversations, character and worldbuilding notes, scene plans, unresolved questions, approved decisions, and new revisions. A note can help explain how an idea developed without becoming a fact the next chapter has to follow.

The public repository is story-neutral. It contains Markdown and CSV templates, documented workflows, agent instructions, and optional local Python checks. It is not a writing app, an automatic chat importer, or a service that trains a model on your manuscript.

## Start with your project

| If you're… | Start here |
| --- | --- |
| Starting a novel | Write your [Vision](00_Project/Vision.md), [Author Intent](00_Project/Author_Intent.md), and [Voice Guide](00_Project/Voice_Guide.md). Use the [initialization interview](09_Tools/Templates/Project_Initialization.md) to identify the decisions you need next. |
| Rebuilding an old manuscript | Name the original version you want to inspect, keep it unchanged, and use the [manuscript workflow](docs/MANUSCRIPT_WORKFLOW.md) and [rewrite protocol](docs/REWRITE_PROTOCOL.md) to map gaps and contradictions before rewriting. |
| Managing a series | Keep shared canon in one place, give each book its own folder, and use the [series and continuity guide](docs/SERIES_AND_CONTINUITY.md) to track event order, dependencies, and when each book can reveal a fact. |

For unpublished work, create a **separate private repository** from the template if enabled, or download a ZIP and work locally. Use a public fork only to contribute to the framework. See the [privacy guide](docs/PRIVACY.md) before uploading a manuscript, interview, or chat export.

## How the workflow works

1. **Preserve the source.** Authorize inspection of a named manuscript, conversation export, or other source. After approval to preserve it, keep the original unchanged and record its provenance and any gaps. An inbox file is not permission to open it. See [conversation preservation](docs/CONVERSATION_INGESTION.md) and the [manuscript workflow](docs/MANUSCRIPT_WORKFLOW.md).
2. **Turn evidence into decisions.** Interview the author, stage individual claims with source anchors, and queue contradictions or uncertainties for review. Keep observations, AI suggestions, and author decisions distinct. Only explicitly approved story facts enter [canon](docs/CANON_APPROVAL_PROCESS.md). A deliberate mystery may stay unresolved.
3. **Plan the prose.** Use the outline, [Scene Registry](04_Story/Scene_Registry.csv), and [Plot Threads](04_Story/Plot_Threads.md) to track what each scene changes and what it sets up or pays off. Before major drafting, prepare a [Writing Context Brief](09_Tools/Templates/Writing_Context_Brief.md) with the exact branch and commit, relevant canon and continuity, the voice and viewpoint, what must stay unrevealed, and the proposed scope. Wait for the author to approve that scope.
4. **Draft in the author's voice.** Use the [author-voice guide](docs/Author_Voice_Drafting.md) to make choices before writing. Work from short, authorized samples for that book and viewpoint when available. Decide what the viewpoint character wants, what they know, and what they'd notice under pressure. If you lack samples, use the author's stated preferences and label any inferred choices as provisional.
5. **Review, then polish.** Check the reader's experience, character behavior, and continuity against the brief and sources. The [source-bound review protocol](docs/REVIEW_PROTOCOL.md) separates confirmed conflicts, possible issues, intentional mysteries, and editorial options. Then use the [Humanizer prose pass](docs/Humanizer_Prose_Pass.md) to cut forced contrasts, mechanical rhythms, and explanatory endings while keeping the author's deliberate choices intact.
6. **Keep a trail.** Save distinct revisions, link author decisions to their evidence, and leave a [session handoff](09_Tools/Templates/Session_Handoff.md) with what changed and what's next. Approval to draft or revise is separate from permission to publish.

The [Constitution](00_Project/Constitution.md), [AGENTS.md](AGENTS.md), and [full workflow](docs/WORKFLOW.md) define these boundaries. The drafting guide and Humanizer are editorial aids. Neither requires model training, an external judging service, or a separate skill installation.

## Quick start

1. Follow [Getting Started](docs/GETTING_STARTED.md) to make your own workspace. You don't need Python, Git on the command line, or an AI account to edit the templates.
2. Start from the [project dashboard](00_Project/Dashboard.md). Copy the [blank book template](05_Books/BOOK_TEMPLATE/), or use the optional commands below. Add only the records you need for the next decision.
3. If you use an assistant, give it the actual authorized files and ask for a bounded task. For example:

```text
Read AGENTS.md, my Vision, Author Intent, and Voice Guide. Tell me the
branch and commit you inspected and what you could not access. Propose a
scene brief for review. Do not open the manuscript inbox, draft the scene,
or change canon.
```

## Optional local tools

The core scripts use Python 3.10+ and the standard library. These baseline checks run locally without model calls. The optional writing toolkit can invoke an already-configured native Codex CLI; DOCX/EPUB builds use Pandoc.

```bash
python scripts/create_book.py --id BOOK-001 --title "My Novel"
# After reviewing the preview, add --apply to create the book folder.
python scripts/validate_framework.py
python scripts/project_status.py
python -m unittest discover -s tests -v
```

The [tools guide](docs/TOOLS.md) also covers opt-in word counts, checksums for named sources, and review packets that verify exact source files, hashes, and line anchors. A passing check can catch a broken link, duplicate ID, missing approval field, or mismatched source excerpt. It cannot tell you whether a scene works, a claim is true, a capture is complete, or the author actually approved it.

## Writing support toolkit

The [source-aware writing toolkit](docs/WRITING_SUPPORT.md) adds executable context packets, continuity and character-state checks, chronology and revelation records, native Codex voice/dialogue/POV reviews, bounded revision proposals, chapter handoffs, simulated reader feedback, and manifest-driven DOCX/EPUB builds. Prepared packets and validated evidence remain distinct from performed literary reviews and author-approved changes.

Use [project setup](docs/PROJECT_SETUP.md) for an independent novel or series, and [framework updates](docs/FRAMEWORK_UPDATES.md) for versioned installation, conflict-aware upgrade proposals and rollback. Generated records stay local; project manuscripts, canon and author instructions remain project-owned. See [the implementation inventory](docs/WRITING_SUPPORT_INVENTORY.md) and [verification evidence](docs/WRITING_SUPPORT_VERIFICATION.md) for tested scope and limits.

## Where things live

| Location | What belongs there |
| --- | --- |
| `00_Project/` | Vision, intent, voice, decisions, open questions, and handoffs |
| `01_Artifacts/`, `_inbox/`, `archive/` | Source-linked artifacts, unprocessed intake, and unchanged preserved originals |
| `knowledge/`, `02_Canon/` | Staged claims and review queues, kept separate from approved canon |
| `03_Worldbuilding/`, `06_Research/`, `07_Artwork/` | Character and setting development, external research, and visual development |
| `04_Story/`, `05_Books/` | Outlines, timelines, scenes, plot threads, and per-book workspaces |
| `08_Publication/` | Release preparation and checklists, not permission to publish |
| `docs/`, `09_Tools/`, `scripts/`, `tests/` | Guides, [templates and checklists](09_Tools/README.md), optional utilities, and tests |

## Contributing and license

Keep public contributions free of private story material. See [CONTRIBUTING](CONTRIBUTING.md), the [roadmap](ROADMAP.md), and the [full documentation index](docs/README.md). The framework is available under the [MIT License](LICENSE). It does not require you to open-source your own fiction.
