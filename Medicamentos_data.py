# ============================================================
# IMPORTACIÓN DE LIBRERÍAS
# ============================================================

import pandas as pd
import requests
import subprocess
from pathlib import Path
from bs4 import BeautifulSoup
from sqlalchemy import create_engine


# ============================================================
# 1. CONFIGURACIÓN
# ============================================================

# Página de PROFECO que contiene los enlaces a los archivos
# de datos abiertos.
URL_PROFECO = (
    "https://datos.profeco.gob.mx/datos_abiertos/qqp.php"
)

# URL base para convertir enlaces relativos en URLs completas.
URL_BASE = (
    "https://datos.profeco.gob.mx/datos_abiertos/"
)

# Directorio donde se almacenarán los archivos extraídos.
OUTPUT_DIR = Path("profeco_data_all")

# Ruta del ejecutable de 7-Zip.
SEVEN_ZIP = Path(
    r"C:\Program Files\7-Zip\7z.exe"
)

# Archivo temporal utilizado para guardar cada RAR descargado.
RAR_PATH = Path("profeco.rar")


# ============================================================
# 2. CREAR DIRECTORIO DE SALIDA
# ============================================================

OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# 3. VERIFICAR 7-ZIP
# ============================================================

if not SEVEN_ZIP.exists():
    raise FileNotFoundError(
        f"No se encontró 7-Zip en: {SEVEN_ZIP}"
    )


# ============================================================
# 4. OBTENER LAS URLS DE LOS ARCHIVOS DE PROFECO
# ============================================================

def obtener_urls(url_pagina, url_base):
    """
    Obtiene las URLs de los archivos comprimidos disponibles
    en la página de datos abiertos de PROFECO.

    Parameters
    ----------
    url_pagina : str
        Página HTML que contiene los enlaces.

    url_base : str
        URL base para construir las URLs completas.

    Returns
    -------
    list
        Lista de URLs completas de archivos RAR, ZIP o 7Z.
    """

    response = requests.get(
        url_pagina,
        timeout=120
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    urls = []

    for link in soup.find_all("a", href=True):

        href = link["href"]

        # Selecciona únicamente archivos comprimidos.
        if href.lower().endswith(
            (".rar", ".zip", ".7z")
        ):
            urls.append(url_base + href)

    return urls


# Obtiene las URLs de los archivos.
urls = obtener_urls(
    URL_PROFECO,
    URL_BASE
)

print(
    f"Archivos encontrados: {len(urls)}"
)


# ============================================================
# 5. DESCARGAR Y EXTRAER UN ARCHIVO
# ============================================================

def Prof_csv(url, directorio_salida):
    """
    Descarga un archivo comprimido de PROFECO y extrae
    su contenido utilizando 7-Zip.

    Parameters
    ----------
    url : str
        URL del archivo que se desea descargar.

    directorio_salida : pathlib.Path
        Directorio donde se extraerán los archivos.

    Returns
    -------
    None
    """

    print("\nProcesando:")
    print(url)

    # --------------------------------------------------------
    # Descarga
    # --------------------------------------------------------

    response = requests.get(
        url,
        timeout=120
    )

    response.raise_for_status()

    # Guarda el archivo temporalmente.
    with open(RAR_PATH, "wb") as f:
        f.write(response.content)

    print("Descarga terminada.")


    # --------------------------------------------------------
    # Extracción
    # --------------------------------------------------------

    cmd = [
        str(SEVEN_ZIP),
        "x",
        str(RAR_PATH),
        f"-o{directorio_salida}",
        "-y"
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )


    # --------------------------------------------------------
    # Verificación
    # --------------------------------------------------------

    if result.returncode != 0:

        print("ERROR durante la extracción:")
        print(result.stderr)

    else:

        print("Extracción terminada correctamente.")


# ============================================================
# 6. DESCARGAR Y EXTRAER TODOS LOS ARCHIVOS
# ============================================================

for url in urls:

    try:
        Prof_csv(
            url,
            OUTPUT_DIR
        )

    except requests.RequestException as error:

        print(
            f"Error al descargar {url}: {error}"
        )


# ============================================================
# 7. IDENTIFICAR LOS CSV EXTRAÍDOS
# ============================================================

csv_files = list(
    OUTPUT_DIR.rglob("*.csv")
)

print(
    f"\nCSV encontrados: {len(csv_files)}"
)

for file in csv_files:
    print(file)


# ============================================================
# 8. EXPLORACIÓN DE LOS CSV
# ============================================================

def revisar_data(archivo):
    """
    Realiza una revisión exploratoria de un archivo CSV.

    Muestra:
        - dimensiones del DataFrame
        - primeras cinco filas
        - nombres de columnas
        - tipos de datos
        - número de valores únicos por columna
    """

    df = pd.read_csv(
        archivo,
        encoding="utf-8-sig",
        low_memory=False
    )

    print("\n========================================")
    print(f"Archivo: {archivo}")
    print("========================================")

    # Dimensiones.
    print("Dimensiones:", df.shape)

    # Primeras cinco filas.
    print("\nPrimeras filas:")
    print(df.head())

    # Información general.
    print("\nInformación del DataFrame:")
    df.info()

    # Valores únicos.
    print("\nValores únicos por columna:")

    for columna in df.columns:

        print(
            f"{columna}: "
            f"{df[columna].nunique(dropna=False)}"
        )


# Revisa todos los CSV.
for file in csv_files:
    revisar_data(file)


# ============================================================
# 9. FILTRADO Y CONSOLIDACIÓN DE LOS DATOS
# ============================================================

# Lista para almacenar los DataFrames.
dfs = []


for file in csv_files:

    # --------------------------------------------------------
    # Lectura
    # --------------------------------------------------------

    temp = pd.read_csv(
        file,
        encoding="utf-8-sig",
        low_memory=False
    )


    # --------------------------------------------------------
    # Limpieza de nombres de columnas
    # --------------------------------------------------------

    temp.columns = (
        temp.columns
        .str.replace(
            "\ufeff",
            "",
            regex=False
        )
        .str.strip()
    )


    # --------------------------------------------------------
    # Conversión de fecha
    # --------------------------------------------------------

    if "fecha_registro" in temp.columns:

        temp["fecha_registro"] = pd.to_datetime(
            temp["fecha_registro"],
            errors="coerce"
        )


    # --------------------------------------------------------
    # Trazabilidad
    # --------------------------------------------------------

    # Guarda el nombre del archivo de procedencia.
    temp["source_file"] = file.name


    # --------------------------------------------------------
    # Selección de medicamentos
    # --------------------------------------------------------

    if "categoria" in temp.columns:

        temp = temp[
            temp["categoria"] == "Medicamentos"
        ]

        dfs.append(temp)


# ============================================================
# 10. UNIÓN DE LOS DATAFRAMES
# ============================================================

if not dfs:
    raise ValueError(
        "No se encontraron registros de medicamentos."
    )


profeco = pd.concat(
    dfs,
    ignore_index=True
)

print(
    "\nDimensiones de la base consolidada:",
    profeco.shape
)


# ============================================================
# 11. CONTROL DE CALIDAD
# ============================================================

# ------------------------------------------------------------
# Valores faltantes
# ------------------------------------------------------------

print("\nValores faltantes:")
print(
    profeco.isnull().sum()
)


# ------------------------------------------------------------
# Registros duplicados
# ------------------------------------------------------------

print("\nRegistros duplicados:")
print(
    profeco.duplicated().sum()
)


# ============================================================
# 12. MEDICAMENTOS ÚNICOS
# ============================================================

if "producto" in profeco.columns:

    medicamentos_unicos = (
        profeco["producto"]
        .dropna()
        .unique()
    )

    print(
        "\nNúmero de medicamentos únicos:",
        len(medicamentos_unicos)
    )


# ============================================================
# 13. GUARDAR COMO CSV
# ============================================================

CSV_SALIDA = (
    "medicamentos_profeco2024_2026.csv"
)

profeco.to_csv(
    CSV_SALIDA,
    index=False,
    encoding="utf-8-sig"
)

print(
    f"\nArchivo CSV guardado: {CSV_SALIDA}"
)


# ============================================================
# 14. CREAR BASE DE DATOS SQLITE
# ============================================================

engine = create_engine(
    "sqlite:///profeco_medicamentos.db"
)


# Guarda el DataFrame como tabla SQL.
profeco.to_sql(
    "medicamentos",
    con=engine,
    if_exists="replace",
    index=False
)

print(
    "Base de datos SQLite creada correctamente."
)


# ============================================================
# 15. CONSULTA SQL
# ============================================================

query = """
SELECT *
FROM medicamentos
LIMIT 10
"""


# Ejecuta la consulta y obtiene el resultado como DataFrame.
resultado = pd.read_sql(
    query,
    engine
)


print("\nPrimeros 10 medicamentos:")
print(resultado)