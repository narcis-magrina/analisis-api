from __future__ import annotations
import re
from io import StringIO
from pathlib import Path
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams

# Línea con descripción + código al final (pdfminer separa importe en línea siguiente)
CODE_END_RE  = re.compile(r'^(.+?)\s{2,}(\d{5})\s*$')
AMOUNT_RE    = re.compile(r'^-?[\d]{1,3}(?:\.\d{3})*,\d{2}$')
YEAR_RE      = re.compile(r'\b(19\d{2}|20\d{2})\b')
# Fin del período impositivo: "al DD-MM-YYYY" or "al DD/MM/YYYY"
PERIOD_END_RE = re.compile(r'\bal\s+\d{1,2}[-/\.]\d{1,2}[-/\.]((19|20)\d{2})\b', re.IGNORECASE)
# "Ejercicio: YYYY" label
EJERCICIO_RE  = re.compile(r'\bejercicio\D{0,15}((19|20)\d{2})\b', re.IGNORECASE)
# NIF/CIF: letra + 7 dígitos + letra/dígito (con o sin etiqueta "NIF")
NIF_RE        = re.compile(r'\b([A-Z]\d{7}[A-Z0-9])\b')
# Razón social en cabecera del formulario
RAZON_RE      = re.compile(r'(?:Raz[oó]n social|Denominaci[oó]n)[:\s]+([^\n]{3,80})', re.IGNORECASE)
SKIP_PATTERNS = [
    "autenticidad", "Verificación", "Modelo normal",
    "Registro Mercantil", "Modelo PYMES",
]


def pdf_to_text(pdf_path: Path) -> str:
    output = StringIO()
    with open(pdf_path, "rb") as f:
        extract_text_to_fp(f, output, laparams=LAParams(), output_type="text", codec="utf-8")
    return output.getvalue()


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


def extract_year(pdf_path: Path, pages: list[str]) -> str:
    # 0. Primera línea de la página del formulario (pages[1]) = año directamente
    #    Ej: "2022\nAgencia Tributaria\nImpuesto sobre Sociedades..."
    if len(pages) > 1:
        first_line = pages[1].lstrip().split('\n')[0].strip()
        if re.match(r'^(19|20)\d{2}$', first_line):
            return first_line
    # 1. Buscar "Ejercicio YYYY" en todas las páginas excepto la de presentación (pages[0])
    for page in pages[1:]:
        m = EJERCICIO_RE.search(page)
        if m:
            return m.group(1)
    # 2. Patrón fin de período "al DD-MM-YYYY" en todas las páginas
    for page in pages:
        m = PERIOD_END_RE.search(page)
        if m:
            return m.group(1)
    # 3. Nombre del fichero — más fiable que el mínimo de años en una página
    m = YEAR_RE.search(pdf_path.name)
    if m:
        return m.group(0)
    # 4. Año mínimo en páginas del formulario (fiscal < presentación)
    for page in pages[1:]:
        years = YEAR_RE.findall(page)
        if years:
            return min(years)
    return ""


def extract_empresa_info(pages: list[str]) -> dict:
    """Extrae NIF y razón social de las cabeceras de las páginas BS/PyG."""
    nif = razon_social = ""
    # Las páginas de sección tienen el NIF y nombre en la cabecera
    search_pages = [p for p in pages if get_section(p)] or pages[:2]
    for page in search_pages:
        if not nif:
            m = NIF_RE.search(page)
            if m:
                nif = m.group(1)
        if not razon_social:
            m = RAZON_RE.search(page)
            if m:
                razon_social = m.group(1).strip().rstrip('.,;')
        if nif and razon_social:
            break
    return {"nif": nif, "razon_social": razon_social}


def process_pdf(pdf_path: Path) -> tuple[list[list], dict]:
    text = pdf_to_text(pdf_path)
    pages = text.split("\f")
    ejercicio = extract_year(pdf_path, pages)
    info      = extract_empresa_info(pages)
    rows = []

    for pg_idx, page in enumerate(pages):
        section = get_section(page)
        if not section:
            continue

        m = re.search(r'Página\s+(\d+)', page)
        pg_num = m.group(1) if m else str(pg_idx + 1)

        lines = page.splitlines()
        for i, line in enumerate(lines):
            if any(pat in line for pat in SKIP_PATTERNS):
                continue
            m = CODE_END_RE.match(line)
            if not m:
                continue
            desc = clean_desc(m.group(1))
            code = m.group(2)

            # El importe aparece en la siguiente línea no vacía.
            # Si esa línea no es un importe, este código no tiene valor en este ejercicio.
            importe_raw = None
            j = i + 1
            while j < len(lines) and j < i + 4:
                stripped = lines[j].strip()
                if stripped:
                    if AMOUNT_RE.match(stripped):
                        importe_raw = stripped
                    break
                j += 1

            if importe_raw:
                importe_norm = importe_raw.replace(".", "")
                rows.append([
                    ejercicio, pdf_path.name, pg_num,
                    section, "contable",
                    desc, code, importe_raw, importe_norm,
                ])

    return rows, info
