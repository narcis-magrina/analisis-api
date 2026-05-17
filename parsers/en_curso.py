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
    ("importe neto de la cifra de negocios", "00261", "PyG"),
    ("ventas", "00760", "PyG"),
    ("prestaciones de servicios", "00761", "PyG"),
    ("variacion de existencias de productos terminados y en curso de fabricacion", "00262", "PyG"),
    ("trabajos realizados por la empresa para su activo", "00263", "PyG"),
    ("aprovisionamientos", "00264", "PyG"),
    ("otros ingresos de explotacion", "00266", "PyG"),
    ("ingresos accesorios y otros de gestion corriente", "00267", "PyG"),
    ("subvenciones de explotacion incorporadas al resultado del ejercicio", "00268", "PyG"),
    ("gastos de personal", "00271", "PyG"),
    ("sueldos salarios y asimilados", "00273", "PyG"),
    ("cargas sociales", "00274", "PyG"),
    ("provisiones gastos de personal", "00275", "PyG"),
    ("otros gastos de explotacion", "00276", "PyG"),
    ("amortizacion del inmovilizado", "00278", "PyG"),
    ("imputacion de subvenciones de inmovilizado no financiero y otras", "00279", "PyG"),
    ("excesos de provisiones", "00284", "PyG"),
    ("deterioro y resultado por enajenaciones del inmovilizado", "00285", "PyG"),
    ("resultado de explotacion", "00296", "PyG"),
    ("ingresos financieros", "00297", "PyG"),
    ("gastos financieros", "00305", "PyG"),
    ("variacion de valor razonable en instrumentos financieros", "00309", "PyG"),
    ("diferencias de cambio", "00312", "PyG"),
    ("deterioro y resultado por enajenaciones de instrumentos financieros", "00313", "PyG"),
    ("otros ingresos y gastos de caracter financiero", "00329", "PyG"),
    ("resultado financiero", "00324", "PyG"),
    ("resultado antes de impuestos", "00325", "PyG"),
    ("impuestos sobre beneficios", "00326", "PyG"),
    ("resultado del ejercicio procedente de operaciones continuadas", "00327", "PyG"),
    ("resultado del ejercicio procedente de operaciones interrumpidas", "00328", "PyG"),
    ("resultado de la cuenta de perdidas y ganancias", "00500", "PyG"),
]


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
        clean_key = re.sub(r" (lp|cp)$", "", key)
        if clean_key in desc_norm and len(clean_key) > best_len:
            best_len = len(clean_key)

    for key, code, sec in MODELO200:
        if seccion and sec and sec != seccion:
            continue
        clean_key = re.sub(r" (lp|cp)$", "", key)
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
