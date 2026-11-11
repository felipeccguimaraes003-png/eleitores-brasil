"""Junta o site em um único arquivo (dist/index.html), com CSS, JS e dados embutidos.

    python scripts/build_page.py

Útil para publicar em qualquer hospedagem estática ou abrir direto do disco.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


def embed(element_id: str, path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/json" id="{element_id}">{text}</script>'


def main() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "app.css").read_text(encoding="utf-8")
    js = (WEB / "app.js").read_text(encoding="utf-8")
    html = html.replace('<link rel="stylesheet" href="app.css">', f"<style>\n{css}</style>")
    data = embed("dados-eleitos", WEB / "data" / "eleitos-2026.json") + embed("dados-mapa", WEB / "data" / "br-map.json")
    html = html.replace('<script src="app.js"></script>', f"{data}\n<script>\n{js}</script>")
    out = ROOT / "dist" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(out, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
