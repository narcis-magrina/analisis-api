from __future__ import annotations
import re
import subprocess
from pathlib import Path

LINE_RE = re.compile(
    r'(.+?)\s+'
    r'(0[0-9]{4}|[0-9]{5})\s+'
    r'(-?[\d]{1,3}(?:\.\d{3})*,\d{2})'
)
YEAR_RE = re.compile(r'\b(19\d{2}|20\d{2})\b')
SKIP_PATTERNS = [
    "autenticidad", "Verificación", "Modelo normal",
    "Registro Mercantil", "Modelo PYMES",
]


def pdf_to_text(pdf_path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True, check=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


def get_section(page_text: str) -> str | None:
    if re.search(r'Balance.*Activo|Activo \(cont', page_text):
        return "BS"
    if re.search(r'Balance.*Patrimonio neto y pasivo', page_text):
        return "BS"
    if re.search(r'Cuenta de pérdidas y ganancias \([II]+\)', page_text):
        return "PyG"
    return None


def clean_desc(raw: str) -> str:
    desc = re.sub(r'[\.]{3,}', '', raw).strip()
    desc = re.sub(r'\s*\([NAP,\s]+\)\s*$', '', desc).strip()
    desc = re.sub(r'\s{2,}', ' ', desc).strip()
    return desc


def extract_year(pdf_path: Path, first_page: str) -> str:
    m = YEAR_RE.search(pdf_path.name)
    if m:
        return m.group(0)
    m = YEAR_RE.search(first_page)
    return m.group(0) if m else ""


def process_pdf(pdf_path: Path) -> list[list]:
    text = pdf_to_text(pdf_path)
    pages = text.split("\f")
    ejercicio = extract_year(pdf_path, pages[0] if pages else "")
    rows = []

    for pg_idx, page in enumerate(pages):
        section = get_section(page)
        if not section:
            continue

        m = re.search(r'Página\s+(\d+)', page)
        pg_num = m.group(1) if m else str(pg_idx + 1)

        for line in page.splitlines():
            if any(pat in line for pat in SKIP_PATTERNS):
                continue
            for m in LINE_RE.finditer(line):
                desc = clean_desc(m.group(1))
                code = m.group(2)
                importe_raw = m.group(3)
                importe_norm = importe_raw.replace(".", "")
                rows.append([
                    ejercicio, pdf_path.name, pg_num,
                    section, "contable",
                    desc, code, importe_raw, importe_norm,
                ])

    return rows
