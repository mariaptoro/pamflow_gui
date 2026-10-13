pamflow Desktop v1.0

Interfaz gráfica de escritorio para ejecutar los pipelines de pamflow
(preparación de datos, control de calidad, detección de especies, índices
acústicos, paisaje sonoro gráfico, ciencia de datos y exportación).

Documentación de pamflow: https://pamflow.readthedocs.io/en/latest/

Requisitos
- pamflow instalado en un entorno de conda (por ejemplo, pamenv).
- Python con las dependencias de requirements.txt.

Instalación y uso
1. Abre una terminal (Anaconda Prompt en Windows; Terminal en macOS o Linux).
2. Activa tu entorno:
   conda activate pamenv
3. Instala las dependencias una sola vez:
   pip install -r requirements.txt
4. Entra a la carpeta de esta aplicación:
   cd ruta/a/pamflow_gui
5. Ejecuta:
   python app_pamflow.py

Uso básico
1. Selecciona la carpeta de pamflow, la carpeta de audios y la hoja de
   despliegues (.xlsx). El archivo de especies objetivo (.csv) es opcional.
2. Elige la zona horaria, el pipeline, el nodo y el modo de ejecución.
3. Haz clic en "Run pamflow" para ejecutar. Los resultados se pueden abrir
   con el botón "Open output" (carpeta data/output).

Nota: Esta versión ejecuta kedro directamente desde el entorno activo
(pamenv), sin usar conda run. Funciona en Windows, macOS y Linux.
