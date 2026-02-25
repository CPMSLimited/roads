# Ferma Platform Styleguide Intake

Source bundle: `Ferma Platform.zip` (imported under `website/static/website/styleguide/ferma_platform/`)

## Implemented now
- Reusable button components:
  - `.sg-btn-primary`
  - `.sg-btn-outline`
  - `.sg-btn-soft`
- Reusable nav-link treatment:
  - `.sg-nav-item`
- Reusable selector shell:
  - `.sg-select`
- Reusable color tokens:
  - `--sg-bg`, `--sg-text`, `--sg-muted`, `--sg-primary`, `--sg-soft`, `--sg-outline`, `--sg-accent`
- Loading asset integration hook:
  - `website/styleguide/ferma_platform/Loading animation.svg`
  - `.library-loading` class (currently present but hidden in library empty state)

## Applied to current page
- `website/templates/website/engineering_admin.html`
  - Sidebar links now use `.sg-nav-item`
  - Action buttons now use styleguide button classes
  - Loading animation asset is wired into markup for future use

## Saved for later (deferred)
- Full screen compositions from:
  - `Root cause.svg`
  - `Frame 2466.svg`
  - `Frame 2477.svg`
  - `Frame 2495.svg`
  - `Frame 2548.svg`
  - `Frame 2603.svg`
  - `Frame 2612.svg`
- Dedicated top-nav variants:
  - `Nav with links.svg`
  - `Nav link.svg`
- Advanced dropdown variants:
  - `roads dropdown.svg`
  - `selector 3.svg`
- Button specimen sheet:
  - `Button.svg`

## Component reuse recommendation
- Yes, these can be reused as components.
- Suggested componentization path:
  1. Convert sidebar nav row into include: `website/templates/website/includes/sg_nav_item.html`
  2. Convert KPI card into include: `website/templates/website/includes/sg_kpi_card.html`
  3. Use `.sg-btn-*` globally across admin/library pages.
  4. Introduce a page-level design-token wrapper class to avoid regressions in legacy pages.
