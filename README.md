# AI Agent Skills for Internal Business Apps

[日本語版](README.ja.md)

Public, reusable skills for building internal business applications with generative AI. Use them with coding agents such as Claude Code and Codex to set up a new web app, turn requirements into screen and API designs, document data flows, and verify changes before release.

Start with [bootstrap-ai-harness](skills/bootstrap-ai-harness/SKILL.md) for a new app, or install individual skills for your existing workflow. The bootstrap skill supports a stack based on Nuxt, Vue, Vuetify, Python APIs, AWS CDK, and Playwright. Each skill's `SKILL.md` explains its requirements and how to use it.

## Language

The skills are written in Japanese, and the documents they produce (designs, diagrams, issues, and reviews) are in Japanese as well. They are built for development practices common in Japanese enterprise projects, such as Excel-based design documents and the Nablarch development standards. Agents can still read and run them in other languages, but expect Japanese terminology and output. A Japanese version of this README is available at [README.ja.md](README.ja.md).

## Available skills

| Skill | What it does |
| --- | --- |
| [a5er-editor](skills/a5er-editor/SKILL.md) | Read, edit, and generate A5:SQL Mk-2 ER diagrams (`.a5er`), including tables, columns, keys, indexes, logical names, and relationships. |
| [ai-development-assessment](skills/ai-development-assessment/SKILL.md) | Assess a project's AI-assisted development practices against a rubric and export the results to Excel. |
| [bootstrap-ai-harness](skills/bootstrap-ai-harness/SKILL.md) | Set up project documentation, agent instructions, and skills for a new web app. |
| [create-github-issue](skills/create-github-issue/SKILL.md) | Create GitHub issues from repository templates, prepare working branches, and document progress and handoffs. |
| [dev-document-writing](skills/dev-document-writing/SKILL.md) | Define what belongs in standards, specifications, designs, procedures, and other project documents, including README and AGENTS.md files. |
| [data-flow-volume](skills/data-flow-volume/SKILL.md) | Turn design inputs into an Excel summary of data flows, estimated record counts, update frequencies, and retention periods. |
| [design-doc-revision](skills/design-doc-revision/SKILL.md) | Revise shared design documents, prepare change summaries and review materials, and apply reviewed changes to the authoritative copy. |
| [feature-er-diagram-drawio](skills/feature-er-diagram-drawio/SKILL.md) | Create, update, and validate feature-level draw.io ER diagrams for the tables used by a process. |
| [genai-knowledge-comic](skills/genai-knowledge-comic/SKILL.md) | Explain generative AI use cases, adoption, and the risks of non-adoption in a multi-page comic. Requires the separate `baoyu-comic` skill to generate the comic. |
| [generate-screen-design-rules](skills/generate-screen-design-rules/SKILL.md) | Create project-specific UI design rules using design principles and reference material. |
| [nablarch-basic-design-excel](skills/nablarch-basic-design-excel/SKILL.md) | Create and update Nablarch-style backend design documents and unit test specifications in Excel. |
| [nablarch-frontend-design-excel](skills/nablarch-frontend-design-excel/SKILL.md) | Create and update Nablarch-style screen designs and unit test specifications for single-page applications in Excel. |
| [pre-push-check](skills/pre-push-check/SKILL.md) | Run tests, AI review, and standards checks for the areas you changed before pushing. |
| [process-flow-diagram](skills/process-flow-diagram/SKILL.md) | Create, update, and validate draw.io diagrams showing how screens, backend processes, tables, and files relate. |
| [prompt-8-plus-1](skills/prompt-8-plus-1/SKILL.md) | Design, refine, and review reusable prompts using the 8+1 formula. |

## Install with the skills CLI

From your target project, run the following with Node.js and npm available. The CLI lets you choose skills and agents interactively.

```bash
npx skills add wss-m-nagata/public-skills

# Install one skill
npx skills add wss-m-nagata/public-skills --skill prompt-8-plus-1

# Install one skill for Claude Code or Codex
npx skills add wss-m-nagata/public-skills --skill prompt-8-plus-1 --agent claude-code
npx skills add wss-m-nagata/public-skills --skill prompt-8-plus-1 --agent codex
```

These commands install the version available on GitHub. Check the installed `SKILL.md` for runtime requirements and external dependencies.

## Install with gh-skill

Use the [gh-skill](https://github.com/github/gh-skill) extension for GitHub CLI.

```bash
# Choose skills interactively
gh skill install wss-m-nagata/public-skills

# Install one skill
gh skill install wss-m-nagata/public-skills ai-development-assessment

# Pin a version
gh skill install wss-m-nagata/public-skills ai-development-assessment --pin v1.0.0

# Install all skills
gh skill install wss-m-nagata/public-skills --all
```

Use `--agent` to select the agent and `--scope` to choose the installation scope (`project` or `user`).

```bash
gh skill install wss-m-nagata/public-skills ai-development-assessment --agent claude-code --scope project
```

## Update installed skills

```bash
# Preview available updates
gh skill update --dry-run

# Choose skills to update interactively
gh skill update

# Update one skill
gh skill update ai-development-assessment

# Update all installed skills without prompting
gh skill update --all
```

Skills pinned with `--pin` are excluded from regular updates.

## Repository layout

```text
skills/<skill-name>/
├── SKILL.md      # Skill name, description, and instructions
├── scripts/      # Helper scripts
├── references/   # Supporting reference material
└── assets/       # Templates and other resources
```

## Publishing

Skills are published with `gh skill publish`.

## License

The skills in this repository are released under the [MIT License](LICENSE). Each skill directory includes a license so it accompanies an individual installation.

Some skills include third-party material from sources such as IBM Carbon Design System, Japan's Digital Agency Design System, and the Nablarch development standards. Those materials follow their respective licenses. See the relevant skill's `THIRD_PARTY_NOTICES.md` for details.
