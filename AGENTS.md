# Agent Guidelines — Loop PC Builder

Welcome, coding agent. This repository (`Agam-Ramteke/loop-pc-builder`) maintains strict engineering and documentation standards. You **must** comply with the following 10 operating rules on every turn.

---

## 📜 Ten Inviolable Rules for Coding Agents

### 1. Read Architecture Documents First
Before modifying or recommending changes to any subsystem, inspect the corresponding documentation in `docs/`:
- **System Architecture:** `docs/Architecture/System-Overview.md` and `docs/Architecture/Technology-Stack.md`
- **Scraper Pipelines:** `docs/Scrapers/Scraper-Architecture.md`
- **Data Flow & Seeds:** `docs/Data-Pipeline/Data-Flow.md`
- **GPU Normalization:** `docs/GPU-Normalization/Canonicalization.md`
- **Compatibility Rules:** `docs/Compatibility-Engine/Compatibility-Rules.md`
- **APIs & Serving:** `docs/API/API-Architecture.md`
- **Frontend & UI:** `docs/Frontend/Frontend-Architecture.md`

### 2. Consult GitHub Issues for Task Requirements & Statuses
- **Authoritative Source:** GitHub Issues (#3–#20) and GitHub Projects are the single source of truth for task status, assignments, and acceptance criteria.
- **Reference Roadmap:** Consult `docs/Roadmap/Engineering-Roadmap.md` for sprint sequencing (W1–W4) and dependencies.
- Never invent new task IDs or duplicate existing issues.

### 3. Update Documentation When Implementation Changes
Whenever code or architecture changes:
- Update the relevant document in `docs/`.
- Provide exact file paths and clear diff explanations.
- Never leave outdated references in technical notes.

### 4. Record Significant Architectural Decisions in `docs/Decisions/`
When introducing structural changes, new database tables, major refactors, or new scraping strategies:
- Create a new Architecture Decision Record in `docs/Decisions/ADR-XXX-<title>.md`.
- Document Context, Problem, Decision, and Consequences (Positive & Trade-offs).

### 5. Never Mark Tasks Complete Without Verification
- Never claim a task, scraper, or migration is finished without empirical proof.
- Verify through automated tests (`pytest`, `npm test`), database document counts, or execution logs.
- Treat source code and database state as evidence of *current* behavior, not necessarily intended behavior.

### 6. Never Introduce Duplicate Task Trackers
- Do not maintain secondary, conflicting to-do lists, progress trackers, or status tables in markdown files.
- Refer all task references directly to GitHub Issues (#3–#20).

### 7. Never Overwrite Existing Documentation Without Inspection
- Always read existing files before modifying them.
- Preserve local untracked technical notes (`docs/project_progress.md`, `docs/postgres_migration.md`) and historical context.
- Reconcile discrepancies instead of discarding previous work.

### 8. Never Commit Credentials, Secrets, or Sensitive Data
- Never commit `.env`, `.env.local`, API keys, MongoDB credentials, or database dumps.
- Ensure `.gitignore` exclusions remain intact.
- Keep machine-specific Obsidian state (`.obsidian/workspace*.json`, `.obsidian/cache/`) out of version control.

### 9. Preserve Working MongoDB API Until PostgreSQL Migration is Validated
- The Next.js frontend currently serves live catalog queries from MongoDB `PC_Parts` (`/api/components`).
- Do **not** alter the production read path until PostgreSQL staging tables and query benchmarks demonstrate complete parity and feature-flag safety ([GitHub Issue #14](https://github.com/Agam-Ramteke/loop-pc-builder/issues/14)).

### 10. Maintain Clear Links Between Docs, Issues, and Implementation
- Use standard Markdown and Obsidian wikilinks (`[[Page-Name]]`) within `docs/`.
- Include clickable links to source code files and direct GitHub issue links (`https://github.com/Agam-Ramteke/loop-pc-builder/issues/<number>`).
- Do not claim that local Obsidian changes are synchronized unless they are committed and pushed to the remote repository.
- Never automatically stage, commit, or push Git changes without explicit user confirmation.

