import requests
import subprocess
from pathlib import Path
from bs4 import BeautifulSoup
import os


# ============================================================
# 1. OBTENCIÓN DE LAS URLS DE PROFECO
# ============================================================

# Página de PROFECO que contiene los enlaces a los archivos
# de datos abiertos.
url = "https://datos.profeco.gob.mx/datos_abiertos/qqp.php"

# URL base para construir las rutas completas de los archivos.
u = "https://datos.profeco.gob.mx/datos_abiertos/"


# Descarga de la página HTML.
response = requests.get(url, timeout=120)
response.raise_for_status()

# Analiza el código HTML.
soup = BeautifulSoup(response.text, "html.parser")


# Lista para almacenar los enlaces encontrados.
Href = []

# Extrae el atributo href de todas las etiquetas <a>.
for link in soup.find_all("a"):
    href = link.get("href")

    if href:
        Href.append(href)


# Selección de los enlaces correspondientes a los archivos.
# NOTA: depende de la estructura actual de la página de PROFECO.
Href = Href[3:len(Href)-1]


# Construcción de las URLs completas.
urls = []

for i in Href:
    urls.append(u + i)


# ============================================================
# 2. VERIFICACIÓN DE 7-ZIP
# ============================================================

# Ruta del ejecutable de 7-Zip.
seven_zip = Path(r"C:\Program Files\7-Zip\7z.exe")

# Verifica que 7-Zip esté instalado.
if not seven_zip.exists():
    raise FileNotFoundError(
        f"No se encontró 7-Zip en: {seven_zip}"
    )


# ============================================================
# 3. DIRECTORIO DE SALIDA
# ============================================================

# Directorio donde se almacenarán los archivos extraídos.
output_dir = Path("profeco_data_all")

# Crea el directorio si no existe.
output_dir.mkdir(exist_ok=True)


# ============================================================
# 4. FUNCIÓN PARA DESCARGAR Y EXTRAER LOS ARCHIVOS
# ============================================================

def Prof_csv(url, Dsav):
    """
    Descarga un archivo RAR de PROFECO y extrae su contenido
    utilizando 7-Zip.

    Parameters
    ----------
    url : str
        URL del archivo RAR.

    Dsav : pathlib.Path
        Directorio donde se almacenarán los archivos extraídos.
    """

    # --------------------------------------------------------
    # Descarga del archivo
    # --------------------------------------------------------

    response = requests.get(url, timeout=120)
    response.raise_for_status()

    # Guarda temporalmente el archivo descargado.
    rar_path = Path("profeco.rar")

    with open(rar_path, "wb") as f:
        f.write(response.content)

    print("Descarga terminada")


    # --------------------------------------------------------
    # Extracción del archivo RAR
    # --------------------------------------------------------

    cmd = [
        str(seven_zip),
        "x",
        str(rar_path),
        f"-o{Dsav}",
        "-y"
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    print(result.stdout)


    # --------------------------------------------------------
    # Verificación de la extracción
    # --------------------------------------------------------

    if result.returncode != 0:
        print("ERROR:")
        print(result.stderr)

    else:
        print(
            "Extracción terminada correctamente:",
            url
        )


# ============================================================
# 5. DESCARGA Y EXTRACCIÓN DE TODOS LOS ARCHIVOS
# ============================================================

for i in urls:
    print("Procesando:", i)
    Prof_csv(i, output_dir)


# ============================================================
# 6. BÚSQUEDA DE LOS ARCHIVOS CSV
# ============================================================

# Busca todos los CSV dentro del directorio de salida,
# incluyendo los que se encuentran en subdirectorios.
csv_files = list(
    output_dir.rglob("*.csv")
)

print("CSV encontrados:", len(csv_files))


# Muestra la ruta de cada archivo CSV.
for f in csv_files:
    print(f)