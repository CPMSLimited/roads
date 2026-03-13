# Project Status Report

Date: 2026-03-08
Scope: CPMS FERMA Django project state based on current repository contents.

## Executive summary
The project is operational as a Django monolith with significant feature coverage across inventory, motorability, condition, library, and engineering-admin workflows. Production deployment on DigitalOcean is functioning with Nginx/Gunicorn. Current technical posture is workable but would benefit from cleanup and hardening in configuration, dependencies, and module organization.

## Delivered capabilities (observed)
- Multi-page FERMA workflow platform with unified navigation.
- Road inventory with route-level details and segment characteristics presentation.
- Road motorability with KPI panels, map/table view, and defect-aware investigation table.
- Road condition draft defect creation flow.
- Engineering admin workflow chain:
  - root cause analysis
  - physical inspection
  - solution design
  - approvals
- Library module with multiple content sections and records display.
- Segment/sub-segment refresh services backed by Google API and Celery queue options.
- Route details synchronization utility from template source.

## Recent implemented changes (highlights)
- Route model enhancements (`details`, optional `start_point`/`end_point`).
- Segment model enhancements:
  - `settlement_type`
  - `carriages`
  - `lanes`
  - `pavement_type`
  - `junctions`
  - `culverts`
  - `bridges`
- Road inventory side tables wired to Segment model fields.
- Segment summary derivation improvements:
  - first/last segment start/end point derivation
  - formatted coordinate output
  - fallback chain for point names
- Engineering-admin priority UI removal.
- Motorability side card rewritten to show active defect status per segment.
- Production static serving issue diagnosed and resolved (stale zero-byte CSS response until process restart).

## Known gaps and risks

## 1) Dependency reproducibility risk
`requirements.txt` appears incomplete for a full deploy/build (core framework packages likely installed outside pinned file). This creates environment drift risk.

## 2) Settings ambiguity risk
Both split settings package (`roads/settings/`) and legacy `roads/settings.py` exist. This can confuse operators and new contributors.

## 3) Large view module complexity
`website/views.py` is very large and hosts many responsibilities. This increases regression probability and slows onboarding.

## 4) Endpoint hardening
Some API endpoints use permissive access decorators (`AllowAny`) and should be reviewed for production security posture.

## 5) Static serving operational risk
Production static delivery depends on correct `collectstatic` + service restart sequencing.

## Recommended next priorities
1. Standardize dependency management (complete lockfile/pinned requirements).
2. Archive or remove legacy `roads/settings.py` after confirming no runtime usage.
3. Refactor `website/views.py` into feature modules (inventory, motorability, condition, engineering-admin).
4. Add automated tests for key workflows and JSON endpoints.
5. Harden API permissions and document role expectations.
6. Add CI checks (lint, migrations check, tests, collectstatic smoke).

## Suggested KPI for engineering progress
- test coverage for `website/views.py` critical paths
- deployment lead time and rollback time
- post-deploy incident count
- endpoint error-rate (5xx) trend

## Overall status
- Delivery maturity: medium
- Operational maturity: medium
- Documentation maturity: improved with current docs set, but should be maintained as code evolves
