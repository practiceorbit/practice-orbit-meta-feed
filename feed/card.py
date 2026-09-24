"""HTML template for a 1080x1080 Practice Orbit listing card (rendered to JPG by build.py)."""
import base64, html, pathlib

ASSETS = pathlib.Path(__file__).resolve().parent.parent / "assets"
FONT = base64.b64encode((ASSETS / "os.woff2").read_bytes()).decode()
LOGO = (ASSETS / "logo.svg").read_text()


def money(v):
    if not v:
        return None
    if v >= 1_000_000:
        s = f"{v / 1e6:.2f}".rstrip("0").rstrip(".")
        return f"${s}M"
    return f"${round(v / 1000):,}K"


def card_html(L, bg_path=None):
    """L: dict(type, city, state, state_name, collections, ops, asking)."""
    stats = [(money(L.get("collections")), "Annual collections"),
             (str(L["ops"]) if L.get("ops") else None, "Operatories"),
             (money(L.get("asking")), "Asking price")]
    stats = [s for s in stats if s[0]]
    stat_html = "".join(f'<div class="stat"><div class="v">{v}</div><div class="l">{l}</div></div>'
                        for v, l in stats)
    city = L.get("city") or ""
    place = f"{html.escape(city)},<br>{L['state']}" if city else html.escape(L["state_name"])
    size = 92 if len(city) <= 12 else 78 if len(city) <= 16 else 66
    bg_css, bg_div = "", ""
    if bg_path:
        b64 = base64.b64encode(pathlib.Path(bg_path).read_bytes()).decode()
        bg_div = '<div class="bg"></div>'
        bg_css = f"""
.bg{{position:absolute;left:0;right:0;top:0;height:720px;background:url(data:image/jpeg;base64,{b64}) center 40%/cover}}
.bg::after{{content:'';position:absolute;inset:0;background:linear-gradient(90deg,rgba(27,77,105,.7) 0%,rgba(27,77,105,0) 60%),linear-gradient(180deg,rgba(27,77,105,.55) 0%,rgba(27,77,105,.15) 30%,rgba(27,77,105,.35) 55%,#1b4d69 100%)}}
.orbit,.dot{{display:none}}
.city,.spec{{text-shadow:0 4px 24px rgba(0,0,0,.45)}}
.spec{{color:#fff}}"""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:OS;src:url(data:font/woff2;base64,{FONT}) format('woff2');font-weight:300 800}}
*{{box-sizing:border-box;margin:0}}
body{{width:1080px;height:1080px;font-family:OS,sans-serif;background:#1b4d69;color:#fff;position:relative;overflow:hidden}}
.orbit{{position:absolute;border-radius:50%;border:2px solid rgba(106,163,195,.35)}}
.o1{{width:1300px;height:1300px;right:-760px;top:-520px}}
.o2{{width:900px;height:900px;right:-560px;top:-320px;border-color:rgba(106,163,195,.22)}}
.dot{{position:absolute;width:64px;height:64px;border-radius:50%;background:#6aa3c3;right:118px;top:318px}}
.wrap{{position:absolute;inset:64px}}
.eyebrow{{display:inline-block;background:#ffa424;color:#12191d;font-weight:800;font-size:26px;letter-spacing:.14em;padding:12px 22px;border-radius:10px}}
.head{{margin-top:44px}}
.spec{{font-size:40px;font-weight:600;color:#a9cde0}}
.city{{font-weight:800;line-height:1.02;margin-top:8px;letter-spacing:-.02em}}
.stats{{position:absolute;left:0;right:0;bottom:170px;display:flex;gap:20px}}
.stat{{flex:1;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);border-radius:22px;padding:30px 30px 26px}}
.v{{font-size:68px;font-weight:800;letter-spacing:-.02em}}
.l{{font-size:24px;font-weight:600;color:#a9cde0;text-transform:uppercase;letter-spacing:.08em;margin-top:4px}}
.foot{{position:absolute;left:0;right:0;bottom:0;display:flex;align-items:center;justify-content:space-between}}
.brand{{display:flex;align-items:center;gap:18px;font-size:38px;font-weight:700}}
.brand svg{{width:78px;height:78px}}
.cta{{background:#fff;color:#1b4d69;font-weight:800;font-size:30px;padding:22px 34px;border-radius:14px}}
{bg_css}
</style></head><body>
{bg_div}<div class="orbit o1"></div><div class="orbit o2"></div><div class="dot"></div>
<div class="wrap">
  <div class="eyebrow">PRACTICE FOR SALE</div>
  <div class="head"><div class="spec">{html.escape(L['type'])}</div><div class="city" style="font-size:{size}px">{place}</div></div>
  <div class="stats">{stat_html}</div>
  <div class="foot"><div class="brand">{LOGO}Practice Orbit</div><div class="cta">View listing →</div></div>
</div></body></html>"""
