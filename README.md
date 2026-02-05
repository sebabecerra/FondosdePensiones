

# Fondos de Pensiones – Chile  
**Descarga y procesamiento de Carteras Agregadas y FECU Fondo**

Pipeline en **Python** para descargar, procesar y persistir información oficial de **Fondos de Pensiones (AFP)** desde el sitio de la **Superintendencia de Pensiones de Chile (SPensiones)**.

El proyecto está diseñado como un **paquete Python reproducible**, listo para uso local, automatización y análisis regulatorio/financiero.

---

## 🎯 Alcance del proyecto

El sistema permite:

- Descargar **Carteras Agregadas** mensuales
- Descargar **FECU Fondo** mensual
- Procesar HTML oficiales (XLS “falso”)
- Normalizar separadores numéricos (`.` / `,`)
- Convertir tablas a **CSV limpios**
- Mantener respaldo en HTML
- Ejecutarse por período o por rangos de años
- Funcionar de forma idéntica en **local**, **VS Code** y **Google Colab**

---

## 🧱 Arquitectura del proyecto

Estructura tipo **data project profesional** (`src layout`):

```bash
FondosdePensiones/
│
├── pyproject.toml # Configuración del paquete
├── README.md
│
├── src/
│ └── fondosdepensiones/
│ ├── init.py
│ ├── config.py # URLs y paths por defecto
│ ├── session.py # Fábrica de sesiones HTTP
│ ├── html_utils.py # Decode HTML, títulos, limpieza
│ ├── io_utils.py # Guardado HTML / CSV
│ ├── carteras.py # Descarga Carteras Agregadas
│ └── fecu.py # Descarga FECU Fondo
│
├── scripts/
│ └── run_descargas.py # Script de ejecución
│
├── data/
│ ├── carteras_agregadas/
│ └── fecu_fondo/
│
└── .venv/ # Entorno virtual (local)
```

---

## ⚙️ Requisitos

- **Python 3.11 o superior** (recomendado)
- macOS / Linux / Windows
- Acceso a internet

---

## 📦 Instalación

### 1️⃣ Clonar el repositorio

git clone <URL_DEL_REPO>
cd FondosdePensiones


2️⃣ Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

3️⃣ Instalar el proyecto (modo editable)
pip install -e .


Esto habilita:

import fondosdepensiones


desde cualquier script del proyecto.

🚀 Uso rápido
Ejecutar descargas desde terminal
python scripts/run_descargas.py


Por defecto:

Recorre un rango de años definido en el script

Descarga Carteras Agregadas y FECU Fondo

Guarda resultados en data/

🧪 Uso desde Python
Descargar un período específico
from fondosdepensiones.carteras import descargar_carteras
from fondosdepensiones.fecu import descargar_fecu

descargar_carteras("202401")
descargar_fecu("202401")

Descargar un rango de años
from fondosdepensiones.carteras import descargar_carteras
from fondosdepensiones.fecu import descargar_fecu

for anio in range(2024, 2026):
    for mes in range(1, 13):
        periodo = f"{anio}{mes:02d}"
        descargar_carteras(periodo)
        descargar_fecu(periodo)

```bash
📁 Datos generados
Estructura de salida
data/
├── carteras_agregadas/
│   ├── html/YYYYMM/
│   └── csv/YYYYMM/
│
└── fecu_fondo/
    ├── html/YYYYMM/
    └── csv/YYYYMM/
```

Contenido

HTML: respaldo exacto de la fuente oficial

CSV: primera tabla relevante, normalizada

🧠 Decisiones técnicas

requests.Session() por período para evitar errores de conexión

Decodificación HTML robusta (UTF-8 + fallback)

Parsing con BeautifulSoup y pandas.read_html

Separación clara entre:

Configuración

IO

Scraping

Orquestación

Sin estado global

Idempotente: puede ejecutarse múltiples veces

⚠️ Nota sobre SSL (macOS)

Si usas el Python de Apple, puedes ver warnings de urllib3 + LibreSSL.

✅ Recomendado: instalar Python desde python.org o usar pyenv.

📌 Estado del proyecto

✔ Producción

✔ Modular

✔ Reproducible

✔ Escalable

✔ Listo para análisis regulatorio y académico

👤 Autor

Pipeline diseñado para análisis financiero, regulatorio y académico
sobre series largas de Fondos de Pensiones en Chile.


---
