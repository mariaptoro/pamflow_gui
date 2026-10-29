# pamflow Desktop v1.0

Interfaz gráfica de escritorio para ejecutar los pipelines de
[pamflow](https://pamflow.readthedocs.io/en/latest/): preparación de datos,
control de calidad, detección de especies, índices acústicos, paisaje sonoro
gráfico, validación de detecciones y exportación.

📖 **Documentación de pamflow:** <https://pamflow.readthedocs.io/en/latest/>

## Requisitos

- pamflow instalado en un entorno de conda (por ejemplo, `pamenv`).
- Python con las dependencias de `requirements.txt`.

## Instalación

1. Abre una terminal (Anaconda Prompt en Windows; Terminal en macOS o Linux).
2. Activa tu entorno:

   ```bash
   conda activate pamenv
   ```

3. Instala las dependencias (una sola vez):

   ```bash
   pip install -r requirements.txt
   ```

4. Entra a la carpeta de esta aplicación:

   ```bash
   cd ruta/a/pamflow_gui
   ```

5. Ejecuta la aplicación:

   ```bash
   python app_pamflow.py
   ```

## Uso básico

1. Selecciona:
   - la carpeta de **pamflow**,
   - la carpeta de **audios**,
   - la **hoja de despliegues** (`.xlsx`),
   - *(opcional)* el archivo de **especies objetivo** (`.csv`).
2. Elige la **zona horaria**, el **pipeline**, el **nodo** y el **modo de ejecución**.
3. Haz clic en **Run pamflow** para ejecutar.
4. Abre los resultados con el botón **Open output** (carpeta `data/output`).

## Pipelines disponibles

| Pipeline | Nodos |
|---|---|
| Data preparation | Get media file, Get media summary, Build deployments |
| Quality control | Sensor performance, Sensor location, Survey effort, Audio outliers, Timelapse |
| Species detection | Species detection, Filter observations, Create segments, Create audio segments, Create manual annotation formats, Observations summary, Observations per species |
| Acoustic indices | Compute acoustic indices |
| Graphical soundscape | Graphical soundscape |
| Detection validation | Compile manual annotations, Fit precision models, Recommend thresholds, Plot precision models |
| Export | Export media / deployments / observations to GBIF |

## Modos de ejecución

| Modo | Comando de kedro equivalente |
|---|---|
| Full pipeline | `kedro run --pipeline=<pipeline>` |
| Selected node only | `kedro run --pipeline=<pipeline> --nodes=<nodo>` |
| Selected node + all dependencies | `kedro run --to-nodes=<nodo>` |

> **Nota:** esta versión ejecuta `kedro` directamente desde el entorno activo
> (`pamenv`), sin usar `conda run`. Funciona en Windows, macOS y Linux.
