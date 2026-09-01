# Contributing

## Integration changes

Firmware, documentation, tools, containers, and CI changes are made directly
in this repository.

## Linear history

The `main` branch must remain linear. Do not merge `main` into a feature branch
and do not create merge commits. Keep each commit buildable and use concise,
imperative commit subjects. Fold fixup, review, and debugging commits into the
commit they correct before merging.

Create a feature branch from the latest `main`:

```sh
git fetch origin
git switch --create my-change origin/main
```

Before requesting final review, replay the branch on the current remote tip:

```sh
git fetch origin
git rebase origin/main
git push --force-with-lease origin my-change
```

Resolve conflicts during the rebase and rerun the relevant tests. Use
`--force-with-lease`, never an unrestricted force push, when updating a rebased
feature branch.

Pull requests must be integrated with either **Rebase and merge** when the
individual commits are intentionally curated, or **Squash and merge** when the
pull request represents one logical change. Do not use **Create a merge
commit**. Repository settings should keep merge commits disabled and require a
branch to be up to date before it can merge.

## LLVM backend changes

1. Create a feature branch in the `llvm-project` submodule from
   `ppe42/llvm-21`.
2. Implement the change with LLVM CodeGen or MC regression tests.
3. Rebase the LLVM feature branch onto the latest `ppe42/llvm-21`, then
   integrate it with rebase or squash merge so that the downstream branch stays
   linear.
4. Update and commit the `llvm-project` gitlink in SBE Forge.
5. Run `./scripts/dev.sh` before submitting the integration change.

The parent commit and submodule commit should be reviewed together. A parent
commit must never reference an LLVM commit that has not been pushed to the
configured submodule remote. Never rewrite a toolchain commit that has already
been tagged or referenced by `toolchain.lock`; publish a new commit and release
instead.

## Updating upstream LLVM

Create a new downstream branch for a major LLVM release. For patch releases,
rebase the existing downstream branch onto the new upstream tag, run LLVM's
PowerPC tests and the SBE Forge integration suite, then advance the submodule
pointer. Tag known-good compiler revisions before changing the supported base.
