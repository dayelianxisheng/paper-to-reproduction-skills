---
name: clone-research-project
description: Clone a verified paper-code repository and pin its revision, submodules, and Git LFS assets. Use after the official project URL is known.
---

# Clone Research Project

## Workflow

1. Verify the repository is linked by the paper, authors, or official project
   page. Label third-party implementations clearly.
2. Confirm the destination directory is in scope and does not already contain
   unrelated files.
3. Clone non-interactively, then record the remote URL and exact commit.
4. Initialize submodules only when declared by the repository.
5. Check Git LFS pointers and release assets; fetch large files only when needed
   and authorized.
6. Report the local path, branch/commit, submodule state, and missing assets.

Do not install dependencies, download datasets or model weights, or run project
code. Hand the local repository to `$evaluate-research-project`.
