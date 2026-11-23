# Project initialization

Initialize a separate project with the toolkit installed or available from a framework checkout. The initializer creates project-owned configuration, author intent and voice records, a context request, a blank chapter heading, and an ordered export manifest. It creates no characters, canon, dates, worldbuilding, word-count targets, or series records unless requested. The starting chapter has no story prose. It can be exported as an explicitly unapproved preview to check the installation.

From a framework checkout:

```bash
python scripts/writing_toolkit.py --root /tmp/my-novel init --title "My Novel" --author "My Pen Name"
python scripts/writing_toolkit.py --root /tmp/my-novel index
python scripts/writing_toolkit.py --root /tmp/my-novel prepare --request 09_Tools/context-request.json
python scripts/writing_toolkit.py --root /tmp/my-novel export --manifest 05_Books/BOOK-001/export-manifest.json --preview
```

Use an empty destination or attach to an existing project whose toolkit configuration and generated chapter targets do not exist. Existing `00_Project/Author_Intent.md` and `00_Project/Voice_Guide.md` are preserved and registered unchanged. An absent root `AGENTS.md` receives project-owned author-control guidance and the installed workflow path; existing agent instructions are preserved. Every other output must be absent. All paths are checked before any writes. Symlinks and parent traversal are rejected. Initialization does not install the framework; see [Framework updates](FRAMEWORK_UPDATES.md) for installation into `.ndf/`.

For a series, repeat `--book ID=Title`. IDs can use letters, numbers, underscores and hyphens. No fixed book count is imposed:

```bash
python scripts/writing_toolkit.py --root /tmp/my-series init --title "My Series" --book FIRST="First Novel" --book SECOND="Second Novel" --options /tmp/project-options.json
```

The optional JSON file can contain:

```json
{
  "project_type": "companion novels",
  "pov": "alternating limited third person",
  "voice": "Author guidance remains to be supplied",
  "time_systems": [{"id": "local-calendar", "conversion": "unknown"}],
  "context_budget": 8000,
  "worldbuilding": false,
  "export_formats": ["docx", "epub"],
  "review_rules": {"manuscript_changes": "explicit author approval"},
  "book_root": "05_Books"
}
```

An options file is optional; create it with your own values before using `--options`. Optional `characters` stores project-defined starting records in configuration. Optional `authority_order` replaces the default ordering; it does not authorize canon promotion. Use `book_root` to choose a different initial manuscript directory. After initialization, explicitly register arbitrary existing source paths in `sources`; the runtime does not require manuscripts to stay under `05_Books/`. Shared canon and existing approval workflows keep their authoritative homes.

Every initialized source begins with `authority: unknown`. Populate instructions and authorize inspection of the named sources before adding source selections. Approved sources require `authority_evidence` pointing at exact approval records; file location and modification time do not establish approval. See [Writing support](WRITING_SUPPORT.md) for source selection, review and export commands.

Before export after editing a chapter, calculate its current hash with `python scripts/source_manifest.py /tmp/my-novel/05_Books/BOOK-001/Chapters/01.md` from the framework checkout and update the manifest's `sha256`. Keep chapter order explicit in `sources`. The preview flag accepts unapproved source text and labels the export accordingly. A publication build requires approval citations and still does not authorize publication.

If the destination already has `.gitignore`, initialization preserves it. Toolkit output writers create `.writing-support/.gitignore` with a `*` rule before writing private derived records. Keep derived packets, reports and exports out of commits; ignore rules do not untrack previously committed files. Keep unpublished creative work in its own private repository.
