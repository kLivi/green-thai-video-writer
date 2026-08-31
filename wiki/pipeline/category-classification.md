# Category and pillar classification

> Sources: src/config/categories.json, 2026-03-16; scripts/wordpress_upload.py, 2026-08-09; progress.txt, 2026-06-19 entry
> Raw: [categories.json — content taxonomy](../../raw/pipeline/2026-03-16-categories-json-taxonomy.md); [wordpress_upload.py](../../raw/publishing/2026-08-09-wordpress-upload-script.md); [progress.txt — session log](../../raw/pipeline/2026-08-09-progress-txt-session-log.md)
> Updated: 2026-09-01

## Overview

Every article gets assigned a WordPress category via a two-level "silo" taxonomy: eight top-level pillars, each with 3-5 subcategories. `src/config/categories.json` is the source of truth for pillar names, their `pillar_phrases` (phrases Step 5 of the writing workflow must use naturally in the article body), and subcategory names. `scripts/wordpress_upload.py` maps those names to actual WordPress category IDs and can auto-derive a pillar/subcategory from an article's title when Step 3 doesn't already pick one.

## The eight pillars

`categories.json` defines: Solar Energy (`solar energy`, `solar power`), Wind Power (`wind energy`, `wind power`), Hydroelectric Power (`hydroelectric power`, `hydropower`), Bioenergy (`bioenergy`, `biogas`), Energy Storage & Grid Infrastructure (`energy storage`, `battery storage`), Electric Vehicles & Clean Transport (`electric vehicles`, `EV`), Green Buildings & Energy Efficiency (`green building`, `energy efficiency`), and Policy, Economics & Thailand Context (`energy policy`, `renewable energy policy`). Each carries 3-5 named subcategories — e.g. Solar Energy has "Solar Costs & Financing", "Installation, Permits & Grid Connection", "Climate, Performance & Maintenance", "Utility-Scale Solar & Innovation".

## Keyword-based derivation

`wordpress_upload.py` can derive a category from the article title alone via `derive_category(title)`: it lowercases and pads the title, matches it against a `_PILLAR_KEYWORDS` list to pick a pillar (falling back to "Policy, Economics & Thailand Context" — the "safest fallback" — if nothing matches), then matches against `_SUBCATEGORY_KEYWORDS` (a list of `(keyword, subcategory_name, parent_pillar)` triples, filtered to the chosen pillar) for the subcategory. The keyword list is granular — e.g. under Solar Energy, `"solar cost"`, `"solar financ"`, `"solar loan"`, `"solar roi"`, and `"payback"` all resolve to "Solar Costs & Financing"; `"mea"` and `"pea"` (Thailand's two electricity utilities) resolve to "Installation, Permits & Grid Connection". Under Policy, Economics & Thailand Context, `"boi"` maps to "Incentives, Subsidies & Tax Breaks" and `"pdp"`/`"aedp"` map to "National Energy Goals & Plans".

`resolve_silo_categories(pillar, subcategory)` then converts the resolved names to WordPress category IDs via `SILO_CATEGORY_IDS`, a `dict[str, dict[str, int]]` keyed by pillar name with a `_pillar` id plus one id per subcategory (e.g. Solar Energy's `_pillar` id is 68). If the pillar isn't found, it returns an empty list; if the subcategory name doesn't match a key under that pillar, only the pillar id is used and a warning is printed. `SILO_CATEGORY_IDS` is explicitly kept in sync by hand with the equivalent table in the sibling `claude-blog` repo's `wordpress_upload.py`.

## The "Sustainable Building Materials" gap (2026-06-19)

A materials/techniques video (concrete, cement, mass timber, hempcrete, bamboo construction) had no matching subcategory under Green Buildings & Energy Efficiency, so it was published pillar-only — which orphaned an earlier internal-linking post (post 941). The fix added `"Sustainable Building Materials": 116` to the Green Buildings block in `SILO_CATEGORY_IDS`, plus six new `_SUBCATEGORY_KEYWORDS` entries (`building material`, `concrete`, `cement`, `mass timber`, `hempcrete`, `bamboo construct`) so a materials video self-classifies into category id 116 going forward.

## See Also

- [/get-video pipeline](get-video-workflow.md)
