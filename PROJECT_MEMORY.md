# Profile repository memory

| ID | Date | Category | Status | Fact / decision | Source | Next action |
|---|---|---|---|---|---|---|
| PROFILE-001 | 2026-11-18 | Release synchronization | pending | Replace silent Alpha/Active fallbacks with verified GitHub Release tags. Missing PROFILE_SYNC_TOKEN explicitly skips; access errors preserve the README and fail. Tags are validated as data; release tags do not prove app deployment or store publication. | scripts/sync_profile.py; tests/test_sync_profile.py; GitHub maintenance request. | Verify PR checks, then verify the workflow result; the owner manages private token configuration. |
