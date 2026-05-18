"""
API REST — Análisis de empresas (Modelo 200)
Endpoints:
  POST /analizar-pdf     → extrae BS/PyG del Modelo 200 (pdftotext)
  POST /en-curso         → extrae BS/PyG del ejercicio en curso (pypdf)
  POST /info-empresa     → extrae NIF, socios, administradores (pdftotext)
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Any
from fastapi.middleware.cors import CORSMiddleware
import tempfile, shutil
from pathlib import Path

from parsers.mod200_plumber import process_pdf as parse_mod200, parse_tables_json
from parsers.en_curso import extract_text, parse_lines
from parsers.info_empresa import process_pdf as parse_info_empresa

app = FastAPI(title="Analisis Empresas API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/analizar-pdf")
async def analizar_pdf(file: UploadFile = File(...)):
    """
    Recibe un PDF del Modelo 200 y devuelve las filas BS/PyG extraídas.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Solo se aceptan ficheros PDF")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        rows, info = parse_mod200(tmp_path)
    except Exception as e:
        raise HTTPException(500, f"Error procesando PDF: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)

    return {
        "total": len(rows),
        "nif_empresa":  info.get("nif", ""),
        "razon_social": info.get("razon_social", ""),
        "filas": [
            {
                "ejercicio": r[0], "pdf": r[1], "pagina": r[2],
                "seccion": r[3], "tipo": r[4], "descripcion": r[5],
                "codigo": r[6], "importe_raw": r[7], "importe_norm": r[8],
            }
            for r in rows
        ],
    }


@app.post("/en-curso")
async def en_curso(
    bs_file: UploadFile = File(...),
    pyg_file: UploadFile = File(...),
    ejercicio: str = "2025",
    mes: str = "12",
):
    """
    Recibe dos PDFs (BS y PyG del ejercicio en curso) y devuelve las filas extraídas.
    """
    rows = []
    for seccion, upload in [("BS", bs_file), ("PyG", pyg_file)]:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            shutil.copyfileobj(upload.file, tmp)
            tmp_path = Path(tmp.name)
        try:
            text = extract_text(tmp_path)
            filas = parse_lines(text, seccion, ejercicio, mes, upload.filename)
            rows.extend(filas)
        except Exception as e:
            raise HTTPException(500, f"Error procesando {seccion}: {e}")
        finally:
            tmp_path.unlink(missing_ok=True)

    return {
        "total": len(rows),
        "filas": [
            {
                "ejercicio": r[0], "pdf": r[2], "pagina": "",
                "seccion": r[3], "tipo": "contable", "descripcion": r[5],
                "codigo": r[6], "importe_raw": r[7], "importe_norm": r[8],
                "cuenta": r[4], "mes": r[1],
            }
            for r in rows
        ],
    }


@app.post("/inspeccionar-tablas")
async def inspeccionar_tablas(file: UploadFile = File(...)):
    """
    Diagnóstico: muestra las tablas que pdfplumber detecta en cada página del PDF.
    Devuelve por página: número, texto plano y tablas (filas × columnas).
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Solo se aceptan ficheros PDF")

    import pdfplumber

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        resultado = []
        with pdfplumber.open(tmp_path) as pdf:
            for i, page in enumerate(pdf.pages):
                texto = (page.extract_text() or "").strip()
                tablas = page.extract_tables()
                resultado.append({
                    "pagina": i + 1,
                    "texto_primeras_lineas": texto[:400] if texto else "",
                    "num_tablas": len(tablas),
                    "tablas": [
                        {
                            "filas": len(t),
                            "columnas": len(t[0]) if t else 0,
                            "muestra": t[:6],
                            "filas_data": t,
                        }
                        for t in tablas
                    ],
                })
    except Exception as e:
        raise HTTPException(500, f"Error inspeccionando PDF: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"total_paginas": len(resultado), "paginas": resultado}


class TablesJson(BaseModel):
    filename: str = ""
    total_paginas: int = 0
    paginas: list[dict[str, Any]] = []


@app.post("/analizar-json")
async def analizar_json(body: TablesJson):
    """
    Recibe el JSON de /inspeccionar-tablas (con filas_data completo) y devuelve
    las filas BS extraídas, sin necesidad de volver a procesar el PDF.
    """
    try:
        rows, info = parse_tables_json(body.dict(), filename=body.filename)
    except Exception as e:
        raise HTTPException(500, f"Error procesando JSON: {e}")

    return {
        "total": len(rows),
        "nif_empresa":  info.get("nif", ""),
        "razon_social": info.get("razon_social", ""),
        "filas": [
            {
                "ejercicio": r[0], "pdf": r[1], "pagina": r[2],
                "seccion": r[3], "tipo": r[4], "descripcion": r[5],
                "codigo": r[6], "importe_raw": r[7], "importe_norm": r[8],
            }
            for r in rows
        ],
    }


@app.post("/info-empresa")
async def info_empresa(file: UploadFile = File(...)):
    """
    Recibe un PDF del Modelo 200 y devuelve NIF, nombre, CNAE,
    administradores y socios.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Solo se aceptan ficheros PDF")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        info = parse_info_empresa(tmp_path)
    except Exception as e:
        raise HTTPException(500, f"Error procesando PDF: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)

    return info
