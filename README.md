# Analisis Empresas API

API REST para extracción de datos del Modelo 200 (AEAT).

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/analizar-pdf` | Extrae BS/PyG del Modelo 200 |
| POST | `/en-curso` | Extrae BS/PyG del ejercicio en curso |
| POST | `/info-empresa` | Extrae NIF, socios y administradores |

## Despliegue en Railway

1. Sube este directorio a un repositorio GitHub
2. En [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Selecciona el repositorio
4. Railway detecta automáticamente Python y aplica `nixpacks.toml`
5. La URL pública aparece en el dashboard de Railway

## Uso desde Vue

```javascript
// Analizar Modelo 200
const formData = new FormData()
formData.append('file', pdfFile)

const res = await fetch('https://tu-api.railway.app/analizar-pdf', {
  method: 'POST',
  body: formData
})
const data = await res.json()
// data.filas → array de { ejercicio, seccion, codigo, importe_norm, ... }

// Info empresa
const res2 = await fetch('https://tu-api.railway.app/info-empresa', {
  method: 'POST',
  body: formData
})
const info = await res2.json()
// info → { nif, nombre, cnae, ejercicio, administradores, socios }

// Ejercicio en curso (dos PDFs: BS y PyG)
const fd = new FormData()
fd.append('bs_file', bsFile)
fd.append('pyg_file', pygFile)
fd.append('ejercicio', '2025')
fd.append('mes', '12')

const res3 = await fetch('https://tu-api.railway.app/en-curso', {
  method: 'POST',
  body: fd
})
```

## Dependencias del sistema

- `poppler-utils` (pdftotext) — instalado automáticamente via nixpacks.toml

## Dependencias Python

- fastapi
- uvicorn
- pypdf
- python-multipart
# analisis-api
