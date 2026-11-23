---
ID: TEMPLATE
Status: Template
Canonical: false
Scope: unknown
Source: unknown
---
# Manuscript export manifest

The initializer creates an executable `export-manifest.json` per book with the current hash of its initial chapter. Use that generated JSON as the starting manifest rather than inventing hashes.

## Identity and metadata

Set `schema_version: 1`, `book`, and `metadata` containing `title`, `author`, and `language`. Optional metadata includes rights, date and identifier. `formats` is an explicit list containing `docx`, `epub`, or both.

## Ordered sources

Each `sources` item contains `path`, current `sha256`, `role` (`frontmatter`, `chapter`, or `backmatter`) and `approval`. Order comes from this list. Approved builds require `approval.status: approved` and `approval.evidence` with exact path, SHA-256, line span, quotation and authority. Use the explicit preview command for unapproved drafts.

## Assets and profiles

Register images in `assets` with path and hash; `cover` names one registered image. Optional `formatting` supports a hashed `reference_doc`, table of contents, depth and EPUB split level. Set an integer `build_epoch` for reproducible timestamps. Do not treat a build as print-ready without checking the author's publishing profile.

## Verification and publication authorization

Record content round-trip checks and actual EPUBCheck status. Check formatting visually where supported. A successfully built or validated file does not authorize publication.
