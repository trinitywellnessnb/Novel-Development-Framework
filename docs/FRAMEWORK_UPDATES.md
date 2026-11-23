# Framework installation and controlled updates

The default distribution is a small local, manifest-managed directory. It requires Python 3.10+ and no package registry, hosted service, database, model account, or access to a private novel repository. `framework.json` identifies framework/toolkit version `1.0.0`, configuration schema `1`, and the exact engineering files distributed. This development version does not announce a release or establish compatibility with arbitrary existing projects.

Framework code, generic templates, documentation, and original synthetic demonstration fixtures install under a project's `.ndf/`. Your project configuration, manuscripts, canon, voice directions, and decisions stay outside `.ndf/`. Project extensions belong outside `.ndf/` too. Neither a GitHub fork nor a repository created from a template receives updates automatically.

## Make and install a distribution

Run from a trusted framework checkout after its tests pass. Choose a new, absent output directory each time:

```bash
python -m unittest discover -s tests -v
python scripts/validate_framework.py
python scripts/framework_manager.py bundle --out /tmp/ndf-1.0.0
mkdir -p /tmp/my-novel
python scripts/framework_manager.py install --distribution /tmp/ndf-1.0.0 --project /tmp/my-novel
python /tmp/my-novel/.ndf/scripts/framework_manager.py version --project /tmp/my-novel
python /tmp/my-novel/.ndf/scripts/writing_toolkit.py --root /tmp/my-novel --help
```

The [project setup guide](PROJECT_SETUP.md) covers initialization and project-local configuration. Always supply `--root` when running the installed toolkit: its code directory is separate from the project. A framework checkout can also run these tools directly without installation.

The bundle is an explicit allowlist, never a repository snapshot. It rejects private creative paths, source symlinks, invalid Python, and existing bundle outputs. Schema 1 requires the complete runtime module set, manager, and evidence validator; removing a required component cannot produce a compatible candidate. Installation rejects extra distribution files and does not overwrite an existing `.ndf/`. Hashes detect changes; they do not authenticate a publisher. Obtain executable framework code from a trusted checkout and inspect changes before adoption.

## Check and propose an upgrade

Update checks are opt-in and local. Obtain a newer trusted framework checkout, run its tests, and create a candidate bundle with its `bundle` command. Check installed versus available versions by passing that candidate. No private repository names, contents, logs, or generated reports are sent anywhere.

```bash
python scripts/framework_manager.py check --distribution /tmp/ndf-candidate --project /tmp/my-novel
python scripts/framework_manager.py plan --distribution /tmp/ndf-candidate --project /tmp/my-novel
```

`/tmp/ndf-candidate` must be the actual output directory of the newer checkout's `bundle` command. A same-version identical candidate reports `CURRENT`; a compatible newer candidate reports `READY`; conflicts report `BLOCKED` and a nonzero exit. Stable semantic versions compare numerically. Changed bytes under the same version, downgrades, major-version changes, and configuration-schema changes are blocked. No migrations are currently provided. The installed manifest records the schema interface expected by the toolkit; a project must also validate its own configuration and extensions against the candidate.

`plan` creates `.writing-support/framework-upgrade.json` exclusively; select a new `--out .writing-support/another-plan.json` for a later proposal. It records current/target versions, hashes, affected files, configuration changes, migrations, conflicts, project overrides, compatibility risks, actual validation results, and reversal instructions. Reports contain engineering paths and hashes. A local `.writing-support/.gitignore` containing `*` protects derived output without changing the project's existing root ignore rules. An incompatible local marker blocks output until explicitly resolved. Keep all `.writing-support/` data private, since other toolkit outputs can contain creative material. Git ignore rules do not remove already-tracked files or prevent deliberate force-adds.

Review the plan and the candidate's actual file diff. The plan is a local reviewable proposal. It does not open or merge a GitHub PR. You can commit a deliberately reviewed engineering update on your project's own feature branch and open a draft PR using your normal workflow; do not upload creative review packets as framework artifacts.

## Adopt after review

```bash
python scripts/framework_manager.py apply --plan /tmp/my-novel/.writing-support/framework-upgrade.json --project /tmp/my-novel
python scripts/framework_manager.py version --project /tmp/my-novel
```

The command revalidates both the installed tree and the exact candidate bytes against the plan immediately before adoption. Any local edit, added file or directory, missing file, candidate modification, or pending transaction blocks the operation. Expected Python `__pycache__/*.pyc` files are regenerable and excluded from modification checks. Custom source or assets inside `.ndf/` are never silently discarded. Move intentional extensions outside the managed installation and adapt configuration explicitly before preparing another plan.

Validation checks manifest schema, scope, exact hashes, and Python compilation without executing candidate code. It does **not** run arbitrary distribution hooks or project commands. The framework's synthetic upgrade tests exercise adoption, preservation, conflict handling, rollback and interrupted transactions. Run your project's applicable tests and literary checks before accepting an upgrade; structural compatibility alone cannot certify project behavior or story continuity. Candidate source-control diffs, test output, and this plan form the review record.

## Rollback and recovery

```bash
python scripts/framework_manager.py rollback --project /tmp/my-novel
python scripts/framework_manager.py recover --project /tmp/my-novel
```

Each successful upgrade retains its complete former installation under a unique `.ndf-backups/` directory. `rollback` validates the current installation and exact recorded backup fingerprint, stages the former tree, and adopts it through the same transaction mechanism. It preserves the outgoing tree as another backup. A modified current installation or damaged backup blocks rollback. A fresh installation has no predecessor to roll back to. Backups remain local until you deliberately archive or remove them; they contain engineering files, not project creative records.

Adoption stages a complete validated tree, acquires an OS advisory operation lock, writes an exclusive `.ndf-transaction.json` journal, renames the old tree to its unique backup, then renames the staged tree into place. Install, apply, rollback and recovery cannot run their swap/recovery steps concurrently. The `.ndf-operation.lock` file remains local; its operating-system lock is released automatically when the process exits. The Unix locking path is exercised here; the Windows standard-library lock adapter is implemented but requires Windows validation.

Ordinary operation failures attempt immediate recovery. A killed process or interruption may leave a journal: run `recover` before doing anything else. If the new complete tree was installed, recovery finishes the transaction; if the old tree was moved and the new tree is absent, recovery restores the verified former tree. Ambiguous or modified states fail without guessing; preserve the journal, staging tree, and backups for manual inspection. This protects against interrupted processes; it is not a guarantee against filesystem damage or concurrent manual writes during a rename.

The manager never writes project manuscripts, configuration, canon or approval records. Author decisions remain independent of framework installation. No command publishes a release, exports a book, promotes canon, merges a PR, or authorizes prose.
