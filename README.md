# Practice Orbit · Meta catalog feed

Builds the product feed behind Practice Orbit's state-targeted Facebook/Instagram
listing ads. Every 4 hours a GitHub Action:

1. pulls all listings from Practice Orbit,
2. keeps only listings that are **live** (not sold, not under contract) **and have an asking price**,
3. renders a branded 1080×1080 card for each (state/region background image, key numbers),
4. writes `docs/feed.csv` and publishes `docs/` with GitHub Pages.

Meta Commerce Manager reads the feed on a schedule, so new listings appear in the ads and
sold or unpriced ones drop out with no manual work.

## One-time setup

1. Create a repo under the **practiceorbit** GitHub account (e.g. `practice-orbit-meta-feed`) and push these files to `main`.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
3. **Actions tab → Build Meta feed → Run workflow** to build immediately.
4. Open `https://practiceorbit.github.io/<repo>/` to see every card and the feed URL
   (`https://practiceorbit.github.io/<repo>/feed.csv`).

A public repo is free. A private repo needs a paid GitHub plan for Pages, and the feed and
card images are public either way (Meta has to be able to fetch them).

## Feed columns

| Column | Value |
|---|---|
| `id` | Practice Orbit listing code, e.g. `P-JPJ7TR` |
| `price` | Asking price |
| `link` | Listing page with UTM tags (`utm_source=facebook&utm_medium=paid_social&utm_campaign=state_listing_catalog`) |
| `image_link` | Generated card image |
| `custom_label_0` | State abbreviation (`AZ`, `CA`, …) — **use this for product sets** |
| `custom_label_1` | Region (`CA-BAY`, `CA-LA`, `CA-OC`, `CA-SD`, `CA-IE`, `CA-NORTH`, or the state) |
| `custom_label_2` | Specialty |
| `custom_label_3` | Listing broker |

## Rules in `feed/build.py`

- Excluded: sold, under contract, no asking price, asking price outside $25K–$15M, unknown state.
- Numbers treated as data-entry errors are hidden on the card (collections over $10M, more than 30 operatories).
- If Practice Orbit returns fewer than 20 listings the run fails instead of publishing a near-empty feed.
- `docs/report.json` lists every exclusion and hidden number from the latest run.

## Changing a background image

Replace `assets/backgrounds/<STATE or REGION>.jpg` (landscape, ≥1400px wide, CC0/public domain or licensed
for ads) and update `credits.json`. Pushing the change rebuilds every affected card. A state with no image
gets a plain branded card and a note in `report.json`.

## Meta setup (Commerce Manager + Ads Manager)

1. **Commerce Manager → Catalogues → Add catalogue** (E-commerce), owned by the Practice Orbit business.
2. **Data sources → Data feed → Scheduled feed**, paste the `feed.csv` URL, repeat **hourly** or **daily**, currency USD.
3. **Product sets:** `Arizona` (custom_label_0 = AZ), `California` (custom_label_0 = CA),
   `Other states` (custom_label_0 is not AZ or CA). Add more single-state sets as inventory grows.
4. **Ads Manager:** one campaign using Advantage+ catalog ads with the Practice Orbit catalogue and the
   **Practice Orbit - 2** pixel. One ad set per product set, targeted to the matching location
   (Arizona; California; the other states with listings). Carousel catalog ad, CTA "Learn More".
