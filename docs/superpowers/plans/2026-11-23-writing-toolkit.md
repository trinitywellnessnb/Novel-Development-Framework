# Reusable writing toolkit implementation plan

Goal: deliver the user-specified reusable, source-aware writing toolkit and controlled project updates.
Architecture: adapt vetted MIT reference engineering into the existing Python script architecture. Project configuration and creative files stay project-owned; generated files stay in ignored .writing-support; portable tools install into manifest-managed .ndf. No service or model account is required for deterministic commands.
Baseline: main a71ff09, clean fresh clone, 32 tests and framework validator pass. No nested AGENTS.md; root instructions and Constitution apply. No existing releases or package dependencies.

## Tasks and interfaces

- [x] Adapt scripts/writing_support/{core,context,reviews,demo}.py and scripts/writing_toolkit.py. Keep schema 1 and use version 1.0.0. Retain exact-byte evidence and existing validator. Add configurable authority order, explicit approval evidence, source freshness, protected outputs and project CLI. Test with tests/test_writing_core.py, test_writing_reviews.py and test_writing_generic.py; run unittest discovery.
- [x] Generalize structure.py/exporter.py with tests/test_writing_structure.py and test_writing_export.py. Optional phases/abilities, clock/revelation constraints, ordered approved exports, actual Pandoc integration, reproducible builds, optional EPUBCheck. Preserve existing tests.
- [x] Add project.py init_project(root,title,author,books,genre,options), generic config, missing templates and tests/test_writing_project.py. Preflight collisions and path safety before any write; keep optional project dimensions optional.
- [x] Add framework_manager.py with framework.json explicit ownership allowlist. Bundle, install, check/plan, apply and recover/rollback interfaces documented in FRAMEWORK_UPDATES.md. Test independent project install, changed managed files, incompatible schema/major versions, stale plans, preserved creative bytes and rollback. Never run distribution hooks.
- [x] Document tested commands, inventory and reusable Codex skill; preserve existing editorial systems and license. Execute actual synthetic native model tasks for all seven literary modes plus condensation. Record evidence rather than fabricate success. Independent review and targeted regression fixes follow full validation.

## Validation and review focus

Run python -m unittest discover -s tests -v and python scripts/validate_framework.py. Exercise exports and installation in temporary synthetic projects. Validate native model results through exact citations and stale-source rejection; distinguish semantics from schema validity. Review paths/symlinks, output collisions, author-only reader leaks, omitted source freshness, conflicting approved claims, project extensions and upgrade recovery. Audit all staged files/history for private reference material. No private source/config/docs are imported; only vetted generic code and explicitly synthetic fixtures.

## Execution decisions

User explicitly authorized proceeding after concise plan without repeat approval. Parallel subsystem agents implement disjoint paths; root integrates interfaces and independently reviews delivery. Distribution candidates are local explicit bundles: avoids publishing releases or requiring private repository access. Project-specific test execution is documented, not run as untrusted distribution hooks.

## Verification ledger

Original toolkit reuse: 56/56 tests independently passed. Generic safety regressions were observed failing before fixes (authority selection, custom approval evidence, omitted-source freshness, context relabeling, output overwrite, full packet budget, reader metadata, request freshness, derived ignore, installed demo lookup and applicability). Independent review confirmed the reader/request/privacy issues; all received regression fixes. Distribution review added complete-runtime checks and an operation lock against concurrent recovery. Native model demonstrations, EPUBCheck and DOCX visual inspection completed; EPUB visual reader check and Windows lock verification remain unperformed. Detailed evidence is in WRITING_SUPPORT_VERIFICATION.md. User-directed draft PR delivery replaces the skill’s integration-choice menu; no merge/release is authorized.
