---
name: portfolio-wizard-workflow
description: Guides development in the Portfolio Navigator Wizard repo: verify changes before integration, no Redis deletes without approval, progress bars for long operations, recommendation-tab style for new UI, no unsolicited docs, and structured failure analysis. Use when working on backend, frontend tabs/pages, Redis, scripts, or debugging in this project.
---

# Portfolio Wizard Workflow

## Verification before integration

All new or changed systems (backend endpoint, frontend flow, script, Redis usage) must be independently tested and verified before being treated as part of the overall system. Do not commit or consider a feature done until verification is complete: feature works as specified, no regressions, error handling and UI/UX behave as expected.

## Redis and cleanup

- Never delete or remove data from Redis without explicit user approval. Any script or change that would delete or bulk-remove Redis content must be proposed and approved first.
- After achieving their purpose, delete or remove debug files and test files. Do not leave temporary test artifacts in the repo.

## Progress and UX consistency

- When creating scripts or flows that process many items or run for a long time, include a progress bar (or equivalent progress indicator) so the user can follow the process.
- For new tabs or pages in the wizard, match the style used in the recommendation tab. Confirm with the user before implementing a new tab or page so the design is approved first.

## No unsolicited docs

Do not create txt or markdown files unless the user requests them. This includes READMEs, notes, and ad-hoc documentation.

## Failure analysis

When something fails, analyze: frontend console and Network tab, backend logs, API responses, DB/cache/background jobs, and auth/CORS config. Provide a short summary of why it failed and where the issue likely is.

## Example scenario

**New "Export history" tab:** User asks for a tab that lists past portfolio exports and allows re-downloading PDFs.

- Confirm with the user that the design/UX follows the recommendation tab style before building.
- Implement with a progress indicator when loading the list of exports.
- Independently test the new tab (run app, trigger export, open tab, verify list and re-download) before considering it integrated.
- Do not propose deleting Redis keys for this feature unless the user asks; if clearing cache is needed, ask for approval first.
- Remove any temporary test/debug files created during the work.
- If something breaks, analyze console, network, backend logs, API, and CORS and summarize the failure.

Apply this skill whenever working in this repo on features that touch Redis, new UI (tabs/pages), long-running or batch operations, or verification/debug workflows.
