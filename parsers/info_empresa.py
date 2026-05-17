from __future__ import annotations
import re
import subprocess
from pathlib import Path
from typing import List, Dict


def pdf_to_text(pdf_path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True, check=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


def extract_identificacion(pages: List[str]) -> Dict:
    data = {"nif": "", "nombre": "", "cnae": "", "ejercicio": ""}

    for line in pages[1].splitlines():
        m = re.match(r'\s{1,4}([A-Z]\d{7}[A-Z0-9])\s{2,}(.+)', line)
        if m:
            nombre = m.group(2).strip()
            nombre = re.split(r'\s{3,}', nombre)[0].strip()
            data["nif"] = m.group(1)
            data["nombre"] = nombre
            break

    for line in pages[1].splitlines():
        if "CNAE" in line:
            m = re.search(r'(\d{4})\s*$', line.strip())
            if m:
                data["cnae"] = m.group(1)
        if re.search(r'período impositivo.*?(\d{4})', line):
            m = re.search(r'\b(20\d{2})\b', line)
            if m:
                data["ejercicio"] = m.group(1)

    if not data["ejercicio"]:
        m = re.search(r'\b(20\d{2})\b', pages[1][:500])
        if m:
            data["ejercicio"] = m.group(1)

    return data


def extract_administradores(pages: List[str]) -> List[dict]:
    admins = []
    page = pages[2] if len(pages) > 2 else ""

    in_section = False
    for line in page.splitlines():
        if "A. Relación de administradores" in line:
            in_section = True
            continue
        if in_section and "B. Participaciones" in line:
            break
        if in_section:
            m = re.match(r'\s*([A-Z0-9]\d{7}[A-Z0-9])\s+[FJ]\s+([A-ZÁÉÍÓÚÑ].+)', line)
            if m:
                nombre = re.sub(r'\s{2,}.*', '', m.group(2)).strip()
                admins.append({"nif": m.group(1), "nombre": nombre})

    return admins


def extract_socios(pages: List[str]) -> List[dict]:
    socios = []
    page = pages[2] if len(pages) > 2 else ""

    in_b2 = False
    for line in page.splitlines():
        if "B.2." in line:
            in_b2 = True
            continue
        if in_b2 and "Suma de porcentajes" in line:
            break
        if in_b2:
            m = re.match(
                r'\s+([A-Z0-9]\d{7}[A-Z0-9])\s+[FJ]\s+([A-ZÁÉÍÓÚÑ].+?)\s{3,}\d{2}\s+([\d\.]+,\d{2})\s+([\d]+,\d{2})',
                line
            )
            if m:
                nombre = re.sub(r'\s{2,}', ' ', m.group(2)).strip()
                nominal = m.group(3)
                pct = float(m.group(4).replace(',', '.'))
                socios.append({
                    "nif": m.group(1),
                    "nombre": nombre,
                    "nominal": nominal,
                    "participacion_pct": pct,
                })

    return socios


def process_pdf(pdf_path: Path) -> Dict:
    text = pdf_to_text(pdf_path)
    pages = text.split("\f")

    info = extract_identificacion(pages)
    info["administradores"] = extract_administradores(pages)
    info["socios"] = extract_socios(pages)
    info["pdf"] = pdf_path.name

    return info
