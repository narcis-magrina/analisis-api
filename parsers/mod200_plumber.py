from __future__ import annotations
import re
from pathlib import Path
from .en_curso import MODELO200

try:
    import pdfplumber
except ImportError:
    pdfplumber = None  # type: ignore

AMOUNT_RE  = re.compile(r'^-?[\d]{1,3}(?:\.\d{3})*,\d{2}$')
CODE_RE    = re.compile(r'^0{2}(\d{3})$')
YEAR_RE    = re.compile(r'\b(19\d{2}|20\d{2})\b')
NIF_RE     = re.compile(r'\b([A-Z]\d{7}[A-Z0-9])\b')
# Header presente en cada página del formulario: "200 B61174298 PROMO CIMA SL Página N"
HEADER_RE  = re.compile(r'\b200\s+([A-Z]\d{7}[A-Z0-9])\s+(.+?)\s+P[aá]gina\s+\d', re.IGNORECASE)

# BS codes: 101-252 standard range + PYMES out-of-range codes
BS_MIN, BS_MAX = 101, 252
BS_PYMES = {780, 781, 785, 786}

# Build descriptions from the single source of truth in en_curso.py
DESCRIPTIONS: dict[int, str] = {
    int(code[2:]): desc.capitalize()
    for desc, code, _sec in MODELO200
    if CODE_RE.match(code)
}


def _get_section(code_int: int) -> str | None:
    """Return 'BS', 'PyG', or None if the code is not a known form field."""
    if (BS_MIN <= code_int <= BS_MAX) or code_int in BS_PYMES:
        return "BS"
    # PyG codes: everything above 252 that isn't a BS PYMES code
    # Includes main range (253-500) and high detail codes (760, 761, 791, 925…)
    if code_int > 252 and code_int not in BS_PYMES:
        return "PyG"
    return None


def _extract_pair(row: list) -> tuple[str, str] | None:
    """
    Try to find a (code, amount) pair in a table row using 3 patterns:
      A: [CODE, AMOUNT]                   (2-col totals: 00180, 00252, etc.)
      B: [None, CODE, AMOUNT, ...]        (3-col section totals)
      C: [CODE, AMOUNT, None/anything...] (3-col sub-items)
    Returns (code_str, amount_str) or None.
    """
    cells = [str(c).strip() if c is not None else "" for c in row]

    # Pattern A: exactly 2 cells, first is code, second is amount
    if len(cells) == 2:
        if CODE_RE.match(cells[0]) and AMOUNT_RE.match(cells[1]):
            return cells[0], cells[1]

    if len(cells) < 3:
        return None

    # Pattern B: first cell empty/None, second is code, third is amount
    if cells[0] == "" and CODE_RE.match(cells[1]) and AMOUNT_RE.match(cells[2]):
        return cells[1], cells[2]

    # Pattern C: first cell is code, second is amount
    if CODE_RE.match(cells[0]) and AMOUNT_RE.match(cells[1]):
        return cells[0], cells[1]

    return None


def _extract_year(pdf: "pdfplumber.PDF", pdf_path: Path) -> str:  # type: ignore[name-defined]
    """
    Year extraction priority:
    1. First text line of page 2 (the form page) — always '20YY'
    2. Any page text matching 'Ejercicio YYYY'
    3. Filename
    4. Minimum year found in page 2+ text
    """
    pages = pdf.pages

    # 1. First line of second page
    if len(pages) > 1:
        text = (pages[1].extract_text() or "").lstrip()
        first_line = text.split("\n")[0].strip()
        if re.match(r'^(19|20)\d{2}$', first_line):
            return first_line

    # 2. 'Ejercicio YYYY' in pages 1+
    ejercicio_re = re.compile(r'\bejercicio\D{0,15}((19|20)\d{2})\b', re.IGNORECASE)
    for page in pages[1:]:
        text = page.extract_text() or ""
        m = ejercicio_re.search(text)
        if m:
            return m.group(1)

    # 3. Filename
    m = YEAR_RE.search(pdf_path.name)
    if m:
        return m.group(0)

    # 4. Min year in pages 1+
    for page in pages[1:]:
        years = YEAR_RE.findall(page.extract_text() or "")
        if years:
            return min(years)

    return ""


def _empresa_from_text(text: str) -> tuple[str, str]:
    """Extract (nif, razon_social) from a page text using the form header pattern."""
    m = HEADER_RE.search(text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", ""


def _extract_empresa_info(pdf: "pdfplumber.PDF") -> dict:  # type: ignore[name-defined]
    """Extract NIF and razón social from the standard form page header."""
    for page in pdf.pages:
        text = page.extract_text() or ""
        nif, razon = _empresa_from_text(text)
        if nif and razon:
            return {"nif": nif, "razon_social": razon}
    return {"nif": "", "razon_social": ""}


def parse_tables_json(data: dict, filename: str = "") -> tuple[list[list], dict]:
    """
    Parse BS data from the JSON output of /inspeccionar-tablas.
    'data' must have: { paginas: [{ pagina, texto_primeras_lineas, tablas: [{ filas_data }] }] }
    """
    paginas = data.get("paginas", [])

    # --- Year extraction ---
    ejercicio = ""
    if len(paginas) > 1:
        text = paginas[1].get("texto_primeras_lineas", "")
        first_line = text.lstrip().split("\n")[0].strip()
        if re.match(r'^(19|20)\d{2}$', first_line):
            ejercicio = first_line
    if not ejercicio:
        ejercicio_re = re.compile(r'\bejercicio\D{0,15}((19|20)\d{2})\b', re.IGNORECASE)
        for pg in paginas[1:]:
            m = ejercicio_re.search(pg.get("texto_primeras_lineas", ""))
            if m:
                ejercicio = m.group(1)
                break
    if not ejercicio:
        m = YEAR_RE.search(filename)
        if m:
            ejercicio = m.group(0)

    # --- Empresa info ---
    nif = razon_social = ""
    for pg in paginas:
        text = pg.get("texto_primeras_lineas", "")
        n, r = _empresa_from_text(text)
        if n and r:
            nif, razon_social = n, r
            break
    info = {"nif": nif, "razon_social": razon_social}

    # --- Table parsing ---
    seen: dict[int, list] = {}

    for pg in paginas:
        pg_num = str(pg.get("pagina", ""))
        for tabla in pg.get("tablas", []):
            for row in tabla.get("filas_data", []):
                pair = _extract_pair(row)
                if pair is None:
                    continue
                code_str, amount_raw = pair
                m = CODE_RE.match(code_str)
                if not m:
                    continue
                code_int = int(m.group(1))
                section = _get_section(code_int)
                if section is None:
                    continue
                if code_int in seen:
                    continue
                desc        = DESCRIPTIONS.get(code_int, code_str)
                amount_norm = amount_raw.replace(".", "")
                seen[code_int] = [
                    ejercicio, filename, pg_num,
                    section, "contable",
                    desc, str(code_int), amount_raw, amount_norm,
                ]

    return list(seen.values()), info


def process_pdf(pdf_path: Path) -> tuple[list[list], dict]:
    if pdfplumber is None:
        raise ImportError("pdfplumber is not installed")

    with pdfplumber.open(pdf_path) as pdf:
        ejercicio = _extract_year(pdf, pdf_path)
        info      = _extract_empresa_info(pdf)

        seen: dict[int, list] = {}  # code_int -> row (first occurrence wins)

        for pg_idx, page in enumerate(pdf.pages):
            pg_num = str(pg_idx + 1)
            tables = page.extract_tables() or []
            for tabla in tables:
                for row in (tabla or []):
                    pair = _extract_pair(row)
                    if pair is None:
                        continue
                    code_str, amount_raw = pair
                    m = CODE_RE.match(code_str)
                    if not m:
                        continue
                    code_int = int(m.group(1))
                    section = _get_section(code_int)
                    if section is None:
                        continue
                    if code_int in seen:
                        continue  # first occurrence wins

                    desc        = DESCRIPTIONS.get(code_int, code_str)
                    amount_norm = amount_raw.replace(".", "")
                    seen[code_int] = [
                        ejercicio, pdf_path.name, pg_num,
                        section, "contable",
                        desc, str(code_int), amount_raw, amount_norm,
                    ]

    rows = list(seen.values())
    return rows, info
