"""Gera os dados do site a partir dos arquivos oficiais do TSE (Candidatos 2026).

    python scripts/build_data.py PASTA_COM_OS_CSV

Lê `consulta_cand_2026_BRASIL.csv` e `rede_social_candidato_2026_BRASIL.csv` (layout do
Portal de Dados Abertos do TSE, latin-1, separador ';') e grava `web/data/eleitos-2026.json`
com os eleitos titulares e as redes sociais que eles declararam ao TSE.
Também gera `web/data/br-map.json` (um caminho SVG por estado).
"""

import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.domain.names import smart_title  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ROLES = {
    "PRESIDENTE": "presidente",
    "GOVERNADOR": "governador",
    "SENADOR": "senador",
    "DEPUTADO FEDERAL": "deputado_federal",
    "DEPUTADO ESTADUAL": "deputado_estadual",
    "DEPUTADO DISTRITAL": "deputado_estadual",
}
VICES = {"VICE-PRESIDENTE": "presidente", "VICE-GOVERNADOR": "governador"}
ELECTED = {"ELEITO", "ELEITO POR QP", "ELEITO POR MÉDIA"}
LABEL = re.compile(r"^\s*:?\s*(?:[A-Za-zÀ-ÿ]{1,12}\s*:\s*)?(?!//)")
IG_SKIP = {"p", "reel", "reels", "explore", "stories", "accounts", "tv", "channel", "share", "s"}
FB_SKIP = {"share", "sharer", "groups", "watch", "events", "pages", "photo", "photos", "reel",
           "reels", "videos", "hashtag", "p", "people", "login", "story.php", "permalink.php"}  # fmt: skip
X_SKIP = {"home", "i", "intent", "share", "search", "hashtag", "explore", "settings", "login"}


def br_phone(digits: str) -> str | None:
    if digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]
    if len(digits) not in (10, 11) or digits[0] == "0":
        return None
    return digits


def parse_social(raw: str) -> tuple[str, str, str] | None:
    """Devolve (rede, texto, link seguro) ou None. Só aceita formatos inequívocos."""
    text = LABEL.sub("", raw.strip(), count=1).strip()
    if not text or text.startswith("@") or " " in text:
        return None
    if not re.match(r"^https?://", text, re.I):
        text = "https://" + text
    try:
        parts = urlsplit(text)
    except ValueError:
        return None
    host = (parts.hostname or "").lower()
    for prefix in ("www.", "m.", "web.", "pt-br."):
        host = host.removeprefix(prefix)
    if parts.username or parts.port:
        return None
    seg = [s for s in parts.path.split("/") if s]
    first = seg[0] if seg else ""
    if host == "instagram.com" and first:
        handle = first.lstrip("@").lower()
        if handle not in IG_SKIP and re.fullmatch(r"[a-z0-9._]{1,30}", handle):
            return "instagram", "@" + handle, f"https://www.instagram.com/{handle}/"
    elif host == "wa.me" and first:
        phone = br_phone(re.sub(r"\D", "", first))
        if phone:
            return "whatsapp", f"({phone[:2]}) {phone[2:-4]}-{phone[-4:]}", f"https://wa.me/55{phone}"
    elif host == "api.whatsapp.com":
        phone = br_phone(re.sub(r"\D", "", (parse_qs(parts.query).get("phone") or [""])[0]))
        if phone:
            return "whatsapp", f"({phone[:2]}) {phone[2:-4]}-{phone[-4:]}", f"https://wa.me/55{phone}"
    elif host in ("facebook.com", "fb.com") and first:
        if first.lower() == "profile.php":
            fid = (parse_qs(parts.query).get("id") or parse_qs(parts.query).get("ID") or [""])[0]
            if fid.isdigit():
                return "facebook", "Facebook", f"https://www.facebook.com/profile.php?id={fid}"
        elif first.lower() not in FB_SKIP and re.fullmatch(r"[A-Za-z0-9.]{3,60}", first):
            return "facebook", first.lower(), f"https://www.facebook.com/{first.lower()}"
    elif host in ("x.com", "twitter.com") and first:
        handle = first.lstrip("@")
        if handle.lower() not in X_SKIP and re.fullmatch(r"[A-Za-z0-9_]{1,15}", handle):
            return "x", "@" + handle.lower(), f"https://x.com/{handle.lower()}"
    elif host == "youtube.com" and first.startswith("@"):
        if re.fullmatch(r"@[A-Za-z0-9._-]{3,30}", first):
            return "youtube", first.lower(), f"https://www.youtube.com/{first.lower()}"
    elif host == "tiktok.com" and first.startswith("@"):
        if re.fullmatch(r"@[A-Za-z0-9._]{2,24}", first):
            return "tiktok", first.lower(), f"https://www.tiktok.com/{first.lower()}"
    return None


def build_people(raw: Path) -> dict[str, object]:
    cand = pd.read_csv(raw / "consulta_cand_2026_BRASIL.csv", sep=";", encoding="latin-1", dtype=str)
    cand = cand[cand.DS_SIT_TOT_TURNO.isin(ELECTED) & (cand.CD_TIPO_ELEICAO == "2")]
    vices = cand[cand.DS_CARGO.isin(VICES)]
    vice_of = {(r.CD_ELEICAO, r.SG_UE, r.NR_CANDIDATO): smart_title(r.NM_URNA_CANDIDATO) for r in vices.itertuples()}
    holders = cand[cand.DS_CARGO.isin(ROLES)].drop_duplicates("SQ_CANDIDATO")

    social = pd.read_csv(raw / "rede_social_candidato_2026_BRASIL.csv", sep=";", encoding="latin-1", dtype=str)
    social = social[social.SQ_CANDIDATO.isin(holders.SQ_CANDIDATO)].copy()
    social["ordem"] = social.NR_ORDEM_REDE_SOCIAL.astype(int)
    links: dict[str, dict[str, list[str]]] = {}
    for row in social.sort_values("ordem").itertuples():
        parsed = parse_social(str(row.DS_URL))
        if parsed:
            links.setdefault(row.SQ_CANDIDATO, {}).setdefault(parsed[0], [parsed[1], parsed[2]])

    people = []
    for r in holders.itertuples():
        social_name = r.NM_SOCIAL_CANDIDATO if r.NM_SOCIAL_CANDIDATO != "#NULO" else None
        people.append(
            {
                "id": r.SQ_CANDIDATO,
                "role": ROLES[r.DS_CARGO],
                "label": smart_title(r.DS_CARGO),
                "name": smart_title(r.NM_URNA_CANDIDATO),
                "full": smart_title(social_name or r.NM_CANDIDATO),
                "uf": None if r.SG_UF == "BR" else r.SG_UF,
                "party": r.SG_PARTIDO,
                "num": r.NR_CANDIDATO,
                "fem": r.DS_GENERO == "FEMININO",
                "result": r.DS_SIT_TOT_TURNO,
                "round": int(r.NR_TURNO),
                "vice": vice_of.get((r.CD_ELEICAO, r.SG_UE, r.NR_CANDIDATO)),
                "links": links.get(r.SQ_CANDIDATO, {}),
            }
        )
    people.sort(key=lambda p: (p["uf"] or "", p["name"]))
    return {
        "source": "TSE, Portal de Dados Abertos, conjunto Candidatos 2026 (licença CC-BY)",
        "generated": cand.DT_GERACAO.iloc[0],
        "people": people,
    }


def ring_centroid(ring: list[list[float]]) -> tuple[float, float, float]:
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:], strict=False):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area /= 2
    return (cx / (6 * area), cy / (6 * area), abs(area)) if area else (ring[0][0], ring[0][1], 0.0)


CALLOUTS = {"RN": (604, 150), "PB": (604, 176), "PE": (604, 202), "AL": (604, 228),
            "SE": (604, 254), "ES": (556, 392), "RJ": (520, 452), "DF": (0, 0)}  # fmt: skip
NUDGE = {"SC": (6, 0), "PI": (4, 12), "CE": (2, -2), "MA": (-4, 6), "GO": (-10, 14), "AP": (0, 4),
         "PR": (-4, 0), "SP": (-6, -2), "MG": (6, 4), "BA": (0, 6), "TO": (0, 6), "RO": (0, 2)}  # fmt: skip


def build_map() -> dict[str, object]:
    features = json.loads((ROOT / "data/geo/br_states.geojson").read_text(encoding="utf-8"))["features"]
    width, pad, pad_right, island_lon = 640, 10, 76, -34.6
    shapes = {}
    for f in features:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        shapes[f["properties"]["sigla"]] = [p for p in polys if sum(pt[0] for pt in p[0]) / len(p[0]) < island_lon]
    pts = [pt for polys in shapes.values() for p in polys for ring in p for pt in ring]
    west, east = min(p[0] for p in pts), max(p[0] for p in pts)
    south, north = min(p[1] for p in pts), max(p[1] for p in pts)
    kx = math.cos(math.radians(-15))
    scale = (width - pad - pad_right) / ((east - west) * kx)

    def project(lon: float, lat: float) -> tuple[float, float]:
        return round(pad + (lon - west) * kx * scale, 1), round(pad + (north - lat) * scale, 1)

    states = []
    for f in sorted(features, key=lambda f: f["properties"]["sigla"]):
        uf = f["properties"]["sigla"]
        d = "".join("M" + "L".join("{},{}".format(*project(*pt)) for pt in ring) + "Z" for p in shapes[uf] for ring in p)
        lon, lat, _ = max((ring_centroid(p[0]) for p in shapes[uf]), key=lambda c: c[2])
        x, y = project(lon, lat)
        dx, dy = NUDGE.get(uf, (0, 0))
        state = {"uf": uf, "name": f["properties"]["nome"], "d": d, "x": x + dx, "y": y + dy}
        if uf in CALLOUTS:
            state["ax"], state["ay"] = x, y
            state["x"], state["y"] = (x + 34, y - 30) if uf == "DF" else CALLOUTS[uf]
        states.append(state)
    return {"width": width, "height": round((north - south) * scale + 2 * pad), "states": states}


def main() -> None:
    raw = Path(sys.argv[1])
    data = build_people(raw)
    out = ROOT / "web" / "data"
    out.mkdir(parents=True, exist_ok=True)
    (out / "eleitos-2026.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (out / "br-map.json").write_text(json.dumps(build_map(), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    people = data["people"]
    counts: dict[str, int] = {}
    for p in people:
        counts[p["label"]] = counts.get(p["label"], 0) + 1
    print("eleitos:", len(people), counts)
    for kind in ("instagram", "whatsapp", "facebook", "x", "youtube", "tiktok"):
        print(f"  com {kind}: {sum(1 for p in people if kind in p['links'])}")
    print("tamanhos:", {f.name: f.stat().st_size for f in out.iterdir()})


if __name__ == "__main__":
    main()
