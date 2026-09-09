# Contributing

Bug reports, fixes, and new skills are all welcome.

## Reporting a problem

Open an issue with the skill name, what you asked for, what you got, and the shape of your input data. Never paste API keys, client data, or full exports into an issue. A few anonymized rows is plenty.

## Adding or changing a skill

Repo layout:

```
plugins/<plugin-name>/
├── .claude-plugin/plugin.json
├── README.md
└── skills/<skill-name>/
    ├── SKILL.md
    ├── references/
    └── scripts/
```

A few rules that keep these usable:

1. The `description` in SKILL.md frontmatter is what decides whether the skill fires. Write it as trigger conditions, not as a summary. List the phrasings a real person would use.
2. Keep SKILL.md focused on the procedure. Push detail into `references/` so it loads only when needed.
3. Scripts do the deterministic work. If a number can be computed, compute it, do not ask the model to eyeball it.
4. Outputs should be honest about their limits. If the data cannot support a claim, the skill should say so in the deliverable.
5. No credentials, client names, or absolute local paths anywhere in the tree.

If you add a plugin, add its entry to `.claude-plugin/marketplace.json` in the same PR.

## Testing

Install locally before opening a PR:

```
/plugin marketplace add ./marketing-skills
/plugin install <plugin-name>@marketing-skills
```

Run any smoke tests the skill ships with, then run the skill on a real export and check the deliverable opens cleanly.
