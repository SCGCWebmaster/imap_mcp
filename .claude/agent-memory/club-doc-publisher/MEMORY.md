# Club Doc Publisher - Agent Memory

See `patterns.md` for detailed notes.

## Quick Reference

- Repo: `~/code/SCGC/scgc-monorepo`
- Committee minutes data dir: `scgc-data/private/committee-minutes/`
- Committee minutes view: `my-gliding-club/app/views/minutes.pug`
- Minutes filename convention: `cm<YYYYMM>.pdf` (e.g. `cm202602.pdf` for Feb 2026)
- Minutes link format: `a(href=docDir+'/cm<YYYYMM>.pdf' target='_blank') <Mon> <YYYY>`
- The `docDir` variable in minutes.pug = `BD + '/private/committee-minutes'`
- Committee year runs Sep-Sep; but recent months (Oct/Nov/Dec/etc after AGM) are listed under the PREVIOUS year's heading (e.g. Oct-Dec 2025 appear under "2024-2025 Committee")
- New entries go AFTER the last month entry in the top section, BEFORE the next `h3`
- The Write tool cannot copy binary PDFs — provide shell `cp` commands to the user for PDF placement
- The repo's current branch at session start was `docs-update/2026-02-committee-minutes`
