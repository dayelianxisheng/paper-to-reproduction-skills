# Linked Repository Contract

## Canonical identity

- Local path: `/home/zq/resource/code/emb_ai/mobile_robot/clone/VLN-paper`
- SSH remote: `git@github.com:dayelianxisheng/VLN-paper.git`
- Repository slug: `dayelianxisheng/VLN-paper`

Accept the equivalent HTTPS remote only for identification. Keep SSH as the configured canonical remote when the user asks to associate the repository.

## Root resolution

1. Run `git rev-parse --show-toplevel` from the current directory.
2. Inspect `git remote get-url origin`.
3. Normalize either remote form to the slug:
   - `git@github.com:dayelianxisheng/VLN-paper.git`
   - `https://github.com/dayelianxisheng/VLN-paper.git`
4. Use the current root when the slug matches.
5. Otherwise test the canonical local path and verify it before writing.
6. Stop and explain the mismatch if neither location is verified.

Do not select a repository solely because its folder is named `VLN-paper`.

## Managed layout

```text
VLN-paper/
├── notes/
│   └── <NN>_<learning-path>.md
└── demos/
    └── <stage>_<mechanism>/
        ├── README.md
        ├── source files
        └── outputs/
```

Keep `notes/` flat by default. Use a short numbered filename that matches the user's learning path, such as `01_action_to_topology.md`. Use lowercase kebab-case for demo directory suffixes.

## Initialization

Run:

```bash
python <skill-root>/scripts/init_workspace.py --repo <repo-root>
```

The initializer must create only missing directories. It must never seed, overwrite, rename, or delete note content.

## Update discipline

- Read the relevant path note before modifying it.
- Preserve user-authored sections and unrelated changes.
- Keep each note useful to the user as a standalone learning and review document.
- Integrate paper evidence and mechanism lineage into the relevant explanation instead of generating agent-oriented files.
- Do not create empty headings, status tables, YAML frontmatter, indexes, or placeholders in `notes/`.
- Add material only after it has been taught, agreed, or explicitly requested.
- Keep raw PDFs, large model weights, datasets, and generated caches outside Git unless the repository explicitly defines a storage policy.
- Inspect `git status --short` before and after edits.
- Do not stage, commit, push, pull, or modify remotes unless the user explicitly requests that operation.
