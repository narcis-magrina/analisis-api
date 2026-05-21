from __future__ import annotations
import re
import unicodedata
from pathlib import Path
from pypdf import PdfReader

AMOUNT_RE  = re.compile(r"^-?(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2}$")
ACCOUNT_RE = re.compile(r"^\d{3,9}$")

MODELO200: list[tuple[str, str, str]] = [
    ("activo no corriente", "00101", "BS"),
    ("inmovilizado intangible", "00102", "BS"),
    ("desarrollo", "00103", "BS"),
    ("concesiones", "00104", "BS"),
    ("patentes licencias marcas y similares", "00105", "BS"),
    ("fondo de comercio", "00106", "BS"),
    ("aplicaciones informaticas", "00107", "BS"),
    ("investigacion", "00108", "BS"),
    ("propiedad intelectual", "00700", "BS"),
    ("otro inmovilizado intangible", "00109", "BS"),
    ("resto inmovilizado intangible", "00110", "BS"),
    ("inmovilizado material", "00111", "BS"),
    ("terrenos y construcciones", "00112", "BS"),
    ("instalaciones tecnicas y otro inmovilizado material", "00113", "BS"),
    ("inmovilizado en curso y anticipos", "00114", "BS"),
    ("inversiones inmobiliarias", "00115", "BS"),
    ("terrenos inversiones inmobiliarias", "00116", "BS"),
    ("construcciones inversiones inmobiliarias", "00117", "BS"),
    ("inversiones en empresas del grupo y asociadas a largo plazo", "00118", "BS"),
    ("inversiones financieras a largo plazo", "00126", "BS"),
    ("activos por impuesto diferido", "00134", "BS"),
    ("deudores comerciales no corrientes", "00135", "BS"),
    ("activo corriente", "00136", "BS"),
    ("activos no corrientes mantenidos para la venta", "00137", "BS"),
    ("existencias", "00138", "BS"),
    ("comerciales", "00139", "BS"),
    ("materias primas y otros aprovisionamientos", "00140", "BS"),
    ("productos en curso", "00141", "BS"),
    ("productos terminados", "00144", "BS"),
    ("anticipos a proveedores", "00148", "BS"),
    ("deudores comerciales y otras cuentas a cobrar", "00149", "BS"),
    ("clientes por ventas y prestaciones de servicios", "00150", "BS"),
    ("clientes empresas del grupo y asociadas", "00153", "BS"),
    ("deudores varios", "00154", "BS"),
    ("personal deudores", "00155", "BS"),
    ("activos por impuesto corriente", "00156", "BS"),
    ("otros creditos con las administraciones publicas", "00157", "BS"),
    ("accionistas socios por desembolsos exigidos", "00158", "BS"),
    ("otros deudores", "00159", "BS"),
    ("inversiones en empresas del grupo y asociadas a corto plazo", "00160", "BS"),
    ("inversiones financieras a corto plazo", "00168", "BS"),
    ("periodificaciones a corto plazo activo", "00176", "BS"),
    ("efectivo y otros activos liquidos equivalentes", "00177", "BS"),
    ("tesoreria", "00178", "BS"),
    ("otros activos liquidos equivalentes", "00179", "BS"),
    ("total activo", "00180", "BS"),
    ("patrimonio neto", "00185", "BS"),
    ("fondos propios", "00186", "BS"),
    ("capital", "00187", "BS"),
    ("capital escriturado", "00188", "BS"),
    ("capital no exigido", "00189", "BS"),
    ("prima de emision", "00190", "BS"),
    ("reservas", "00191", "BS"),
    ("legal y estatutarias", "00192", "BS"),
    ("otras reservas", "00193", "BS"),
    ("acciones y participaciones en patrimonio propias", "00194", "BS"),
    ("resultados de ejercicios anteriores", "00195", "BS"),
    ("otras aportaciones de socios", "00198", "BS"),
    ("resultado del ejercicio", "00199", "BS"),
    ("dividendo a cuenta", "00200", "BS"),
    ("otros instrumentos de patrimonio neto", "00201", "BS"),
    ("ajustes por cambios de valor", "00202", "BS"),
    ("subvenciones donaciones y legados recibidos", "00208", "BS"),
    ("pasivo no corriente", "00210", "BS"),
    ("provisiones a largo plazo", "00211", "BS"),
    ("deudas a largo plazo", "00216", "BS"),
    ("deudas con empresas del grupo y asociadas a largo plazo", "00223", "BS"),
    ("pasivos por impuesto diferido", "00224", "BS"),
    ("periodificaciones a largo plazo", "00225", "BS"),
    ("acreedores comerciales no corrientes", "00226", "BS"),
    ("pasivo corriente", "00228", "BS"),
    ("provisiones a corto plazo", "00229", "BS"),
    ("deudas a corto plazo", "00231", "BS"),
    ("deudas con empresas del grupo y asociadas a corto plazo", "00238", "BS"),
    ("acreedores comerciales y otras cuentas a pagar", "00239", "BS"),
    ("proveedores", "00240", "BS"),
    ("proveedores empresas del grupo y asociadas", "00243", "BS"),
    ("acreedores varios", "00244", "BS"),
    ("personal acreedores", "00245", "BS"),
    ("pasivos por impuesto corriente", "00246", "BS"),
    ("otras deudas con las administraciones publicas", "00247", "BS"),
    ("anticipos de clientes", "00248", "BS"),
    ("periodificaciones a corto plazo pasivo", "00250", "BS"),
    ("total patrimonio neto y pasivo", "00252", "BS"),
    # PyG
    ("importe neto de la cifra de negocios", "00255", "PyG"),
    ("variacion de existencias de productos terminados y en curso de fabricacion", "00258", "PyG"),
    ("trabajos realizados por la empresa para su activo", "00259", "PyG"),
    ("aprovisionamientos", "00260", "PyG"),
    ("importe neto de la cifra de negocios", "00261", "PyG"),
    ("ventas", "00760", "PyG"),
    ("prestaciones de servicios", "00761", "PyG"),
    ("variacion de existencias de productos terminados y en curso de fabricacion", "00262", "PyG"),
    ("trabajos realizados por la empresa para su activo", "00263", "PyG"),
    ("aprovisionamientos", "00264", "PyG"),
    ("otros ingresos de explotacion", "00265", "PyG"),
    ("otros ingresos de explotacion", "00266", "PyG"),
    ("ingresos accesorios y otros de gestion corriente", "00267", "PyG"),
    ("subvenciones de explotacion incorporadas al resultado del ejercicio", "00268", "PyG"),
    ("gastos de personal", "00270", "PyG"),
    ("gastos de personal", "00271", "PyG"),
    ("sueldos salarios y asimilados", "00273", "PyG"),
    ("cargas sociales", "00274", "PyG"),
    ("provisiones gastos de personal", "00275", "PyG"),
    ("otros gastos de explotacion", "00279", "PyG"),   # 00279 en Modelo 200 estándar
    ("amortizacion del inmovilizado", "00284", "PyG"),
    ("imputacion de subvenciones de inmovilizado no financiero y otras", "00285", "PyG"),  # código no mostrado en template
    ("excesos de provisiones", "00286", "PyG"),
    ("deterioro y resultado por enajenaciones del inmovilizado", "00287", "PyG"),
    ("diferencia negativa de combinaciones de negocio", "00294", "PyG"),
    ("otros resultados", "00295", "PyG"),
    ("resultado de explotacion", "00296", "PyG"),
    ("ingresos financieros", "00297", "PyG"),
    ("gastos financieros", "00305", "PyG"),
    ("variacion de valor razonable en instrumentos financieros", "00309", "PyG"),
    ("variacion de valor razonable en instrumentos financiero", "00309", "PyG"),  # alias sin 's' (A3 ERP)
    ("diferencias de cambio", "00312", "PyG"),
    ("deterioro y resultado por enajenaciones de instrumentos financieros", "00313", "PyG"),
    ("deterioro bajas y enajenaciones de instrumentos financieros", "00313", "PyG"),  # alias A3 ERP
    ("otros ingresos y gastos de caracter financiero", "00329", "PyG"),
    ("resultado financiero", "00324", "PyG"),
    ("resultado antes de impuestos", "00325", "PyG"),
    ("impuestos sobre beneficios", "00326", "PyG"),
    ("resultado del ejercicio procedente de operaciones continuadas", "00327", "PyG"),
    ("resultado del ejercicio procedente de operaciones interrumpidas", "00328", "PyG"),
    ("resultado de la cuenta de perdidas y ganancias", "00500", "PyG"),
    ("resultado de actividades interrumpidas neto de impuestos", "00791", "PyG"),
    ("ajustes por cambios de criterio contable y errores", "00925", "PyG"),
    # Aliases cortos para encabezados de secciones usados en PDFs en curso
    ("total activo", "00180", "BS"),
    ("total patrimonio neto y pasivo", "00252", "BS"),
    ("resultado del ejercicio", "00327", "PyG"),
]

# ── Descripción canónica por código (para display en frontend) ────────────────
DESCRIPTIONS_BY_CODE: dict[str, str] = {}
for _desc, _code, _ in MODELO200:
    if _code not in DESCRIPTIONS_BY_CODE:
        DESCRIPTIONS_BY_CODE[_code] = _desc.capitalize()

# ── Regexes para extracción de líneas de concepto ────────────────────────────
_AMT_RE   = re.compile(r"-?[\d]{1,3}(?:\.[\d]{3})*,\d{2}")
# Línea de detalle contable: empieza por importe + código de cuenta (3-9 dígitos + separador)
_ACCT_RE  = re.compile(r"^-?[\d]{1,3}(?:\.[\d]{3})*,\d{2}\s+\d{3,9}\s*[-,]")
# Línea TOTAL invertida: dos importes al principio + descripción al final
_REV_RE   = re.compile(r"^(-?[\d]{1,3}(?:\.[\d]{3})*,\d{2})\s+(-?[\d]{1,3}(?:\.[\d]{3})*,\d{2})\s+(.+)$")

_BS_KW  = ["activo no corriente", "activo corriente", "total activo",
           "patrimonio neto", "pasivo no corriente", "pasivo corriente",
           "balance de situacion", "inmovilizado", "fondos propios"]
_PYG_KW = ["perdidas y ganancias", "cuenta de perdidas", "gastos de personal",
           "aprovisionamientos", "cifra de negocios", "resultado de explotacion",
           "resultado financiero", "resultado antes de impuestos"]


def detect_section(text: str) -> str:
    """Devuelve 'BS' o 'PyG' según las palabras clave presentes en el texto."""
    norm = _normalize(text)
    bs  = sum(1 for kw in _BS_KW  if kw in norm)
    pyg = sum(1 for kw in _PYG_KW if kw in norm)
    return "BS" if bs >= pyg else "PyG"


def is_two_column_bs(text: str) -> bool:
    """Detecta si el balance tiene activo y pasivo en columnas paralelas."""
    for line in text.splitlines():
        n = _normalize(line)
        # Cabecera duplicada: "Descripción 2025 Descripción 2025"
        if n.count("descripcion") >= 2:
            return True
        # Marcadores de activo Y pasivo/patrimonio en la misma línea
        has_activo = any(kw in n for kw in ["activo no corriente", "activo corriente", "total activo"])
        has_pasivo = any(kw in n for kw in ["patrimonio neto", "pasivo no corriente", "pasivo corriente", "fondos propios"])
        if has_activo and has_pasivo:
            return True
    return False


def _find_column_split(by_y: dict, page_width: float) -> float:
    """
    Detecta el punto x que separa la columna izquierda (Activo) de la derecha (Pasivo).

    Estrategia: en un balance de dos columnas cada fila sigue el patrón
    "texto … cifra … texto … cifra". El x0 del primer texto que aparece
    después de una cifra indica el margen izquierdo de la columna derecha.
    Complementariamente se recogen los x0 de palabras precedidas por un
    hueco horizontal > 20 pt. Se clusterizan ambos conjuntos y se toma
    el bin más frecuente.
    """
    candidates: list[float] = []

    for ws in by_y.values():
        ws_s = sorted(ws, key=lambda w: float(w["x0"]))

        # Patrón texto→cifra→texto: x0 del texto post-cifra
        saw_number = False
        for w in ws_s:
            is_num = bool(AMOUNT_RE.match(w["text"]))
            if saw_number and not is_num:
                candidates.append(float(w["x0"]))
                break
            if is_num:
                saw_number = True

        # Hueco grande (>20 pt) seguido de texto (no cifra): separa columnas
        for i in range(len(ws_s) - 1):
            gap = float(ws_s[i + 1]["x0"]) - float(ws_s[i]["x1"])
            if gap > 20 and not AMOUNT_RE.match(ws_s[i + 1]["text"]):
                candidates.append(float(ws_s[i + 1]["x0"]))

    if not candidates:
        return page_width / 2

    # Clustering en bins de 20 pt
    bins: dict[int, int] = {}
    for x in candidates:
        b = round(x / 20) * 20
        bins[b] = bins.get(b, 0) + 1

    best_bin = max(bins, key=lambda b: bins[b])
    best_vals = [x for x in candidates if abs(x - best_bin) <= 20]
    split = sum(best_vals) / len(best_vals)

    # Sanity check: el split no debe estar en los extremos de la página
    if not (page_width * 0.1 < split < page_width * 0.9):
        return page_width / 2

    return split


def _extract_columns_plumber(pdf_path: Path) -> tuple[str, str]:
    """Usa pdfplumber para separar el texto de la columna izquierda (Activo)
    y la derecha (Pasivo/Patrimonio) en un balance de dos columnas."""
    import pdfplumber
    from collections import defaultdict

    left_lines:  list[str] = []
    right_lines: list[str] = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            if not words:
                continue

            # Agrupar palabras por línea (misma y aproximada)
            by_y: dict[int, list] = defaultdict(list)
            for w in words:
                y_key = round(float(w["top"]) / 4) * 4
                by_y[y_key].append(w)

            # Detectar dinámicamente el punto de separación de columnas
            mid = _find_column_split(by_y, page.width)

            for y in sorted(by_y):
                ws = sorted(by_y[y], key=lambda w: float(w["x0"]))
                left  = " ".join(w["text"] for w in ws if float(w["x0"]) <  mid)
                right = " ".join(w["text"] for w in ws if float(w["x0"]) >= mid)
                if left.strip():
                    left_lines.append(left)
                if right.strip():
                    right_lines.append(right)

    return "\n".join(left_lines), "\n".join(right_lines)


def parse_two_column_bs(pdf_path: Path, pdf_name: str, ejercicio: str = "", mes: str = "") -> dict:
    """Parser para balances con Activo | Pasivo en columnas paralelas."""
    left_text, right_text = _extract_columns_plumber(pdf_path)

    # Extraer periodo de la cabecera (aparece en ambas columnas; basta con una)
    if not ejercicio:
        ejercicio, mes = extract_period(left_text + "\n" + right_text)

    # Procesar primero activo (izquierda) y luego pasivo+patrimonio (derecha)
    all_lines = extract_concept_lines(left_text) + extract_concept_lines(right_text)

    matched:   list[dict] = []
    unmatched: list[dict] = []
    seen:      set[str]   = set()
    last_code             = ""

    for idx, item in enumerate(all_lines):
        desc_norm = _normalize(item["desc_clean"])
        codigo    = _find_codigo(desc_norm, last_code, "BS")
        imp_a     = _parse_amt(item["importe_actual_raw"])
        imp_p     = _parse_amt(item.get("importe_anterior_raw"))

        if codigo != "?" and codigo not in seen:
            seen.add(codigo)
            last_code = codigo
            matched.append({
                "codigo":               codigo,
                "descripcion_modelo":   DESCRIPTIONS_BY_CODE.get(codigo, item["desc_clean"].capitalize()),
                "descripcion_pdf":      item.get("desc_con_prefijo", item["desc_clean"]),
                "descripcion_original": item["desc_original"],
                "importe_actual":       imp_a,
                "importe_anterior":     imp_p,
                "seccion":              "BS",
            })
        else:
            if imp_a is not None and imp_a != 0.0:
                unmatched.append({
                    "id":                   f"u{idx}",
                    "desc_con_prefijo":     item.get("desc_con_prefijo", item["desc_clean"]),
                    "desc_clean":           item["desc_clean"],
                    "descripcion_original": item["desc_original"],
                    "importe_actual":       imp_a,
                    "importe_anterior":     imp_p,
                })

    return {
        "seccion":    "BS",
        "ejercicio":  ejercicio,
        "mes":        mes,
        "pdf_nombre": pdf_name,
        "labels":     get_labels("BS"),
        "matched":    matched,
        "unmatched":  unmatched,
    }


def extract_period(text: str) -> tuple[str, str]:
    """Extrae (año, mes) del primer rango de fechas en la cabecera del PDF."""
    m = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b.*?\b(\d{2})/(\d{2})/(\d{4})\b", text[:600])
    if m:
        return m.group(6), m.group(5)  # año y mes de la fecha de cierre
    m = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", text[:600])
    if m:
        return m.group(3), m.group(2)
    return "", ""


def _clean_concept_keep_prefix(raw: str) -> str:
    """Elimina importes y códigos contables pero MANTIENE el prefijo (b), 11., etc.)"""
    desc = _AMT_RE.sub("", raw).strip()
    desc = re.sub(r"\b\d{3,9}\s*[-,]\s*", "", desc)
    desc = re.sub(r"\s*\([A-Za-z0-9+\s]{1,30}\)\s*$", "", desc)
    return re.sub(r"\s+", " ", desc).strip()


def _clean_concept_desc(raw: str) -> str:
    """Elimina importes, códigos contables y prefijos de numeración."""
    desc = _AMT_RE.sub("", raw).strip()
    desc = re.sub(r"\b\d{3,9}\s*[-,]\s*", "", desc)   # códigos contables
    desc = re.sub(r"\s+", " ", desc).strip()
    # Prefijos: A), B), A-1), I., II., 1., a)
    desc = re.sub(r"^[A-Z]-?\d*\)\s*", "", desc)
    desc = re.sub(r"^[IVXivx]+\.\s*", "", desc)
    desc = re.sub(r"^\d+\.\s*", "", desc)
    desc = re.sub(r"^[a-z]\)\s*", "", desc)
    # Fórmulas al final: (A+B), (14+15+16)
    desc = re.sub(r"\s*\([A-Za-z0-9+\s]{1,30}\)\s*$", "", desc)
    return re.sub(r"\s+", " ", desc).strip()


def _parse_amt(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        return float(raw.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def extract_concept_lines(text: str) -> list[dict]:
    """
    Extrae líneas de concepto (nivel sección) saltando las de detalle contable.
    Devuelve lista de dicts con desc_original, desc_clean, importe_actual_raw,
    importe_anterior_raw.
    """
    result = []
    for raw in text.splitlines():
        line = raw.strip()
        if len(line) < 5:
            continue
        if _ACCT_RE.match(line):
            continue  # línea de detalle contable

        # Formato invertido: IMPORTE IMPORTE DESCRIPCIÓN (líneas TOTAL)
        m = _REV_RE.match(line)
        if m:
            desc_part = m.group(3).strip()
            if not re.match(r"^\d{3,9}[\s,-]", desc_part):
                dc = _clean_concept_desc(desc_part)
                if len(dc) >= 3:
                    result.append({"desc_original": line,
                                   "desc_con_prefijo": _clean_concept_keep_prefix(desc_part),
                                   "desc_clean": dc,
                                   "importe_actual_raw": m.group(1),
                                   "importe_anterior_raw": m.group(2)})
                continue

        # Formato normal: DESCRIPCIÓN IMPORTE [IMPORTE …]
        amounts = _AMT_RE.findall(line)
        if not amounts:
            continue
        # Preferir importes con separador de miles (son monetarios, no porcentajes)
        monetary = [a for a in amounts if "." in a] or amounts
        dc = _clean_concept_desc(line)
        if len(dc) < 3:
            continue
        result.append({"desc_original": line,
                        "desc_con_prefijo": _clean_concept_keep_prefix(line),
                        "desc_clean": dc,
                        "importe_actual_raw": monetary[0],
                        "importe_anterior_raw": monetary[1] if len(monetary) > 1 else None})
    return result


def get_labels(seccion: str) -> dict[str, str]:
    """Devuelve {codigo: descripcion} para todos los códigos de la sección."""
    seen: dict[str, str] = {}
    for desc, code, sec in MODELO200:
        if sec == seccion and code not in seen:
            seen[code] = desc.capitalize()
    return seen


def parse_en_curso_auto(text: str, pdf_name: str, ejercicio: str = "", mes: str = "") -> dict:
    """
    Pipeline completo para PDFs en curso:
    1. Detecta sección (BS/PyG)
    2. Extrae líneas de concepto
    3. Fuzzy-match con MODELO200
    4. Devuelve matched + unmatched
    """
    if not ejercicio:
        ejercicio, mes = extract_period(text)
    seccion = detect_section(text)
    lines   = extract_concept_lines(text)

    matched: list[dict]   = []
    unmatched: list[dict] = []
    seen: set[str]        = set()
    last_code             = ""

    for idx, item in enumerate(lines):
        desc_norm = _normalize(item["desc_clean"])
        codigo    = _find_codigo(desc_norm, last_code, seccion)
        imp_a     = _parse_amt(item["importe_actual_raw"])
        imp_p     = _parse_amt(item.get("importe_anterior_raw"))

        if codigo != "?" and codigo not in seen:
            seen.add(codigo)
            last_code = codigo
            matched.append({
                "codigo":               codigo,
                "descripcion_modelo":   DESCRIPTIONS_BY_CODE.get(codigo, item["desc_clean"].capitalize()),
                "descripcion_pdf":      item.get("desc_con_prefijo", item["desc_clean"]),
                "descripcion_original": item["desc_original"],
                "importe_actual":       imp_a,
                "importe_anterior":     imp_p,
                "seccion":              seccion,
            })
        else:
            if imp_a is not None and imp_a != 0.0:
                unmatched.append({
                    "id":                   f"u{idx}",
                    "desc_con_prefijo":     item.get("desc_con_prefijo", item["desc_clean"]),
                    "desc_clean":           item["desc_clean"],
                    "descripcion_original": item["desc_original"],
                    "importe_actual":       imp_a,
                    "importe_anterior":     imp_p,
                })

    return {
        "seccion":   seccion,
        "ejercicio": ejercicio,
        "mes":       mes,
        "pdf_nombre": pdf_name,
        "labels":    get_labels(seccion),
        "matched":   matched,
        "unmatched": unmatched,
    }

ACTIVO_NO_CORRIENTE: list[tuple[str, str]] = [ "00101", "00102,00111,00115,00118,00126,00134,00135"]
ACTIVO_CORRIENTE: list[tuple[str, str]] = [ "00136", "00137,00138,00149,00160,00168,00176,00177"]
TOTAL_ACTIVO: list[tuple[str, str]] = [ "00180", "00101,00136"]

PATRIMONIO_NETO: list[tuple[str, str]] = [ "00185", "00187,00190,00191,00194,00195,00198,00199,00200,00201,00202,00208,00209"]
PASIVO_NO_CORRIENTE: list[tuple[str, str]] = [ "00210", "00780,00781,00211,00216,00223,00224,00225,00226,00227"]
PASIVO_CORRIENTE: list[tuple[str, str]] = [ "00228", "00785,00786,00229,00230,00231,00238,00239,00250,00251"]
TOTAL_PASIVO_Y_PATRIMONIO: list[tuple[str, str]] = [ "00252", "00185,00210,00228"]

RESULTADO_EXPLOTACION: list[tuple[str, str]] = [ "00296", "00255,00258,00259,00260,00265,00270,00279,00284,00285,00286,00287,00791,00294,00925"]
RESULTADO_FINANCIERO: list[tuple[str, str]] = [ "00324", "00297,00305,00309,00312,00313,00329"]

RESULTADO_ANTES_IMPUESTOS: list[tuple[str, str]] = [ "00325", "00296,00324"]
RESULTADO_EJERCICIO: list[tuple[str, str]] = [ "00327", "00325,00326"]



def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def _find_codigo(desc_norm: str, last_code: str = "", seccion: str = "") -> str:
    candidates = []
    best_len = 0
    for key, code, sec in MODELO200:
        if seccion and sec and sec != seccion:
            continue
        clean_key = _normalize(re.sub(r" (lp|cp)$", "", key))
        if clean_key in desc_norm and len(clean_key) > best_len:
            best_len = len(clean_key)

    for key, code, sec in MODELO200:
        if seccion and sec and sec != seccion:
            continue
        clean_key = _normalize(re.sub(r" (lp|cp)$", "", key))
        if clean_key in desc_norm and len(clean_key) == best_len:
            candidates.append((key, code))

    if not candidates:
        return "?"
    if len(candidates) == 1:
        return candidates[0][1]

    if last_code and last_code.isdigit():
        ref = int(last_code)
        candidates.sort(key=lambda x: abs(int(x[1]) - ref))
    return candidates[0][1]


def _clean_desc(raw: str) -> str:
    d = raw.strip()
    d = re.sub(r"^[A-Z][\-\d]*\)\s*", "", d)
    d = re.sub(r"^\d+\.\s*", "", d)
    d = re.sub(r"^[a-z]\)\s*", "", d)
    return d.strip()


def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def parse_lines(text: str, seccion: str, ejercicio: str, mes: str, pdf_name: str) -> list:
    rows = []
    last_code = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        tokens = line.split()
        if not tokens:
            continue

        cuenta = ""
        amounts = []

        for i, tok in enumerate(tokens):
            if AMOUNT_RE.match(tok):
                amounts.append((i, tok))
            elif i == 0 and ACCOUNT_RE.match(tok):
                cuenta = tok

        if not amounts:
            continue

        saldo_raw = amounts[-2][1] if len(amounts) >= 2 else amounts[-1][1]

        amount_idxs = {i for i, _ in amounts}
        desc_tokens = [
            tok for i, tok in enumerate(tokens)
            if i not in amount_idxs and not (i == 0 and cuenta)
        ]
        desc_raw = _clean_desc(" ".join(desc_tokens))

        if len(desc_raw) < 3:
            continue

        if re.sub(r'[0,.]', '', saldo_raw) == '':
            continue

        codigo = _find_codigo(_normalize(desc_raw), last_code, seccion)
        if codigo != "?":
            last_code = codigo
        saldo_norm = saldo_raw.replace(".", "")

        rows.append([ejercicio, mes, pdf_name, seccion, cuenta,
                     desc_raw, codigo, saldo_raw, saldo_norm])

    return rows
