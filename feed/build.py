"""Build the Practice Orbit Meta catalog feed.

Pulls live listings from Practice Orbit, keeps only those that are live (not sold,
not under contract) AND have an asking price, renders a branded 1080x1080 card for
each, and writes docs/feed.csv for Meta Commerce Manager (served by GitHub Pages).

Run:  python feed/build.py            (network + render)
      BASE_URL=https://example.github.io/repo python feed/build.py
"""
import csv, hashlib, html, json, os, pathlib, sys, datetime, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "feed"))
from card import card_html  # noqa: E402

DOCS = ROOT / "docs"
CARDS = DOCS / "cards"
BG = ROOT / "assets" / "backgrounds"
ENDPOINT = "https://us-central1-practice-orbit.cloudfunctions.net/searchPractices"

# Where GitHub Pages serves docs/. In Actions this is derived from the repo name.
def base_url():
    if os.environ.get("BASE_URL"):
        return os.environ["BASE_URL"].rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY", "practiceorbit/practice-orbit-meta-feed")
    owner, name = repo.split("/")
    return f"https://{owner.lower()}.github.io/{name}"

UTM = "utm_source=facebook&utm_medium=paid_social&utm_campaign=state_listing_catalog"

# Sanity limits: numbers outside these are treated as data-entry errors.
MAX_COLLECTIONS = 10_000_000   # hide the collections stat above this
MAX_OPS = 30                   # hide the operatories stat above this
ASKING_RANGE = (25_000, 15_000_000)  # exclude the listing if asking price is outside

ABBR = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA","Colorado":"CO",
"Connecticut":"CT","Delaware":"DE","Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID","Illinois":"IL",
"Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY","Louisiana":"LA","Maine":"ME","Maryland":"MD",
"Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Mississippi":"MS","Missouri":"MO","Montana":"MT",
"Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM","New York":"NY",
"North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK","Oregon":"OR","Pennsylvania":"PA",
"Rhode Island":"RI","South Carolina":"SC","South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT",
"Vermont":"VT","Virginia":"VA","Washington":"WA","West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY",
"District of Columbia":"DC"}

# California listings get a regional background image.
CA_REGIONS = {
 "CA-BAY": ["San Jose","Palo Alto","Los Altos","Redwood City","San Carlos","San Mateo","Fremont","San Leandro",
            "Walnut Creek","Saratoga","Monterey County","Oakland","San Francisco","Santa Clara","Sunnyvale",
            "Mountain View","Hayward","Concord","Pleasanton","Livermore","Berkeley","Cupertino","Milpitas"],
 "CA-NORTH": ["Rohnert Park","Santa Rosa","Roseville","Modesto","Solano County","Bakersfield","Kern County",
              "Sacramento","Fresno","Stockton","Napa","Petaluma","Chico","Redding","Visalia","Merced","Davis"],
 "CA-OC": ["Aliso Viejo","Anaheim","Anaheim Hills","Corona Del Mar","Costa Mesa","Fullerton","Garden Grove",
           "Huntington Beach","Ladera Ranch","Laguna Hills","Laguna Niguel","Los Alamitos","Mission Viejo",
           "Newport Beach","Westminster","Irvine","Orange","Santa Ana","Tustin","Lake Forest","Yorba Linda"],
 "CA-SD": ["San Diego","El Cajon","Escondido","La Mesa","San Marcos","Chula Vista","Oceanside","Carlsbad",
           "Encinitas","Vista","Poway","Santee"],
 "CA-IE": ["Menifee","Moreno Valley","Rancho Mirage","Temecula","Victorville","Upland","SB County","Ridgecrest",
           "Riverside","San Bernardino","Ontario","Rancho Cucamonga","Corona","Palm Springs","Palm Desert",
           "Murrieta","Hemet","Fontana","Redlands","Indio"],
}

def region(state, city):
    if state != "CA":
        return state
    c = (city or "").strip().lower()
    for r, cities in CA_REGIONS.items():
        if c in (x.lower() for x in cities):
            return r
    return "CA-LA"   # LA, Ventura and anything unmapped


def fetch():
    req = urllib.request.Request(ENDPOINT, data=json.dumps({"data": {"radius": 3500}}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "po-meta-feed"})
    with urllib.request.urlopen(req, timeout=120) as r:
        practices = json.load(r)["result"]["practices"]
    if len(practices) < 20:
        raise SystemExit(f"Practice Orbit returned only {len(practices)} listings; refusing to publish a suspect feed.")
    return practices


def tidy_city(c):
    c = (c or "").strip()
    return c.title() if c.isupper() else c


def money_words(v):
    if v >= 1_000_000:
        return f"${v/1e6:.2f}".rstrip("0").rstrip(".") + "M"
    return f"${round(v/1000):,}K"


def main():
    practices = fetch()
    CARDS.mkdir(parents=True, exist_ok=True)
    report = {"built_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
              "fetched": len(practices), "included": 0, "excluded": {}, "notes": [], "by_state": {}}

    def skip(reason, p):
        report["excluded"].setdefault(reason, []).append(p.get("slug"))

    items = []
    for p in practices:
        if p.get("status_sold"):
            skip("sold", p); continue
        if p.get("status_salePending"):
            skip("under_contract", p); continue
        ask = p.get("financial_askingPrice")
        if not ask:
            skip("no_asking_price", p); continue
        if not (ASKING_RANGE[0] <= ask <= ASKING_RANGE[1]):
            skip("asking_price_out_of_range", p); continue
        state = ABBR.get((p.get("location_state") or "").strip())
        if not state:
            skip("unknown_state", p); continue

        coll = p.get("financial_totalCollections")
        ops = p.get("financial_totalOperatories")
        if coll and coll > MAX_COLLECTIONS:
            report["notes"].append(f"{p['slug']}: collections {coll:,} hidden (over limit)"); coll = None
        if ops and ops > MAX_OPS:
            report["notes"].append(f"{p['slug']}: operatories {ops} hidden (over limit)"); ops = None

        city = tidy_city(p.get("location_city"))
        ptype = p.get("practiceType") or "Dental Practice"
        reg = region(state, city)
        bg = BG / f"{reg}.jpg"
        if not bg.exists():
            bg = BG / f"{state}.jpg"
        if not bg.exists():
            report["notes"].append(f"{p['slug']}: no background image for {reg}; used plain branded card")
            bg = None

        L = dict(type=ptype, city=city, state=state, state_name=p["location_state"],
                 collections=coll, ops=ops, asking=ask)
        h = hashlib.sha1(json.dumps(L, sort_keys=True).encode()
                         + (bg.read_bytes() if bg else b"") + (ROOT / "feed" / "card.py").read_bytes()).hexdigest()[:10]
        img_name = f"{p['slug']}-{h}.jpg"
        items.append(dict(p=p, L=L, reg=reg, bg=bg, img=img_name))

    # Render cards that don't exist yet.
    todo = [it for it in items if not (CARDS / it["img"]).exists()]
    if todo:
        from playwright.sync_api import sync_playwright
        from PIL import Image
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 1080, "height": 1080})
            for it in todo:
                pg.set_content(card_html(it["L"], it["bg"]))
                pg.evaluate("document.fonts.ready")
                tmp = CARDS / (it["img"] + ".png")
                pg.screenshot(path=str(tmp))
                Image.open(tmp).convert("RGB").save(CARDS / it["img"], quality=88, optimize=True)
                tmp.unlink()
            b.close()
    # Remove cards no longer referenced.
    keep = {it["img"] for it in items}
    for f in CARDS.glob("*.jpg"):
        if f.name not in keep:
            f.unlink()

    base = base_url()
    rows = []
    for it in items:
        p, L = it["p"], it["L"]
        place = f"{L['city']}, {L['state']}" if L["city"] else L["state_name"]
        facts = []
        if L["collections"]: facts.append(f"{money_words(L['collections'])} annual collections")
        if L["ops"]: facts.append(f"{L['ops']} operatories")
        facts.append(f"asking {money_words(L['asking'])}")
        desc = f"{L['type']} practice for sale in {place}: " + ", ".join(facts) + "."
        broker = p.get("company_organizationName")
        if broker:
            desc += f" Listed by {broker} on Practice Orbit."
        link = p["url"] + ("&" if "?" in p["url"] else "?") + UTM
        rows.append({
            "id": p["slug"],
            "title": f"{L['type']} Practice for Sale – {place}"[:150],
            "description": desc[:5000],
            "availability": "in stock",
            "condition": "used",
            "price": f"{L['asking']:.2f} USD",
            "link": link,
            "image_link": f"{base}/cards/{it['img']}",
            "brand": "Practice Orbit",
            "custom_label_0": L["state"],          # state abbreviation (AZ, CA, ...)
            "custom_label_1": it["reg"],            # region (CA-BAY, CA-LA, ... or the state)
            "custom_label_2": L["type"],            # specialty
            "custom_label_3": broker or "",         # listing broker
        })
        report["by_state"][L["state"]] = report["by_state"].get(L["state"], 0) + 1

    rows.sort(key=lambda r: (r["custom_label_0"], r["id"]))
    with open(DOCS / "feed.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    report["included"] = len(rows)
    report["excluded_counts"] = {k: len(v) for k, v in report["excluded"].items()}
    report["by_state"] = dict(sorted(report["by_state"].items(), key=lambda kv: -kv[1]))
    (DOCS / "report.json").write_text(json.dumps(report, indent=1))
    write_index(rows, report, base)
    print(f"{len(rows)} listings in feed; rendered {len(todo)} new cards; excluded {report['excluded_counts']}")


def write_index(rows, report, base):
    cards = "".join(
        f'<figure><img src="cards/{html.escape(r["image_link"].rsplit("/",1)[1])}" loading="lazy" alt="">'
        f'<figcaption><a href="{html.escape(r["link"])}">{html.escape(r["id"])}</a> · {html.escape(r["custom_label_1"])}</figcaption></figure>'
        for r in rows)
    states = " · ".join(f"{k} {v}" for k, v in report["by_state"].items())
    (DOCS / "index.html").write_text(f"""<!doctype html><meta charset="utf-8"><title>Practice Orbit Meta Feed</title>
<meta name="robots" content="noindex">
<style>body{{font:15px/1.5 system-ui,sans-serif;margin:24px;color:#12242f}}h1{{font-size:22px}}
.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px}}figure{{margin:0}}img{{width:100%;border-radius:8px}}
figcaption{{font-size:12px;color:#5a6b76}}code{{background:#eef3f6;padding:2px 6px;border-radius:4px}}</style>
<h1>Practice Orbit · Meta catalog feed</h1>
<p>Feed URL for Commerce Manager: <code>{base}/feed.csv</code></p>
<p>Built {report['built_at']} · {len(rows)} listings · {states}</p>
<p>Excluded: {html.escape(json.dumps(report['excluded_counts']))} · <a href="report.json">full report</a></p>
<div class="g">{cards}</div>""")


if __name__ == "__main__":
    main()
