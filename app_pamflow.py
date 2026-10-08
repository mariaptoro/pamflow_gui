import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from PIL import Image

try:
    import customtkinter as ctk
except ImportError:
    import tkinter as tk
    from tkinter import ttk
    messagebox.showerror(
        "CustomTkinter is missing",
        "Install the modern interface with:\n\n pip install customtkinter\n\nThen run python app.py again"
    )
    raise

APP_TITLE = "PamFlow Desktop v1.0"
DEFAULT_PAMFLOW_DIR = r"C:\Users\maria.toro\Documents\pamflow"
CONFIG_FILE = Path(__file__).with_name("pamflow_desktop_config.json")
LOGO_FILE = Path(__file__).with_name("pamflow_logo.png")
ICON_FILE = Path(__file__).with_name("pamflow_icon.ico")

PIPELINE_NODES = {
    "Data preparation": {
        "pipeline": "data_preparation",
        "nodes": {
            "Get media file": "get_media_file_node",
            "Get media summary": "get_media_summary_node",
            "Build deployments": "field_deployments_sheet_to_deployments_node",
        },
    },
    "Quality control": {
        "pipeline": "quality_control",
        "nodes": {
            "Sensor performance": "plot_sensor_performance_node",
            "Sensor location": "plot_sensor_location_node",
            "Survey effort": "plot_survey_effort_node",
            "Timelapse": "get_timelapse_node",
        },
    },
    "Species detection": {
        "pipeline": "species_detection",
        "nodes": {
            "Species detection": "species_detection_node",
            "Filter observations": "filter_observations_node",
            "Create segments": "create_segments_node",
            "Create audio segments": "create_segments_folder_node",
            "Create manual annotation formats": "create_manual_annotation_formats_node",
            "Observations summary": "plot_observations_summary_node",
            "Observations per species": "plot_observations_per_species_node",
        },
    },
    "Acoustic indices": {
        "pipeline": "acoustic_indices",
        "nodes": {
            "Compute acoustic indices": "compute_indices_node",
        },
    },
    "Graphical soundscape": {
        "pipeline": "graphical_soundscape",
        "nodes": {
            "Graphical soundscape": "graphical_soundscape_node",
        },
    },
    "Data science": {
        "pipeline": "data_science",
        "nodes": {
            "Find thresholds": "find_thresholds_node",
            "Build train/test dataset": "build_train_test_dataset_node",
        },
    },
    "Export": {
        "pipeline": "export",
        "nodes": {
            "Export media to GBIF": "from_media_to_media_gbif_node",
            "Export deployments to GBIF": "from_deployments_to_deployments_gbif_node",
            "Export observations to GBIF": "from_observations_to_observations_gbif_node",
            "Export CSA events": "from_deployments_to_CSA_eventos_node",
        },
    },
}

PIPELINES = {
    "Full workflow": None,
    **{label: data["pipeline"] for label, data in PIPELINE_NODES.items()},
}

RUN_MODES = [
    "Full pipeline",
    "Selected node only",
    "Selected node + all dependencies",
]

TIMEZONES = [
    "America/Bogota",
    "America/Lima",
    "America/Mexico_City",
    "America/Santiago",
    "America/New_York",
    "Europe/Berlin",
    "UTC",
]

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Palette inspired by the PamFlow logo
AZUL_PAMFLOW = "#90B8D0"
AZUL_HOVER = "#7AA4BF"

VERDE_PAMFLOW = "#687030"
VERDE_HOVER = "#565D28"

ROJO_DETENER = "#A94747"
ROJO_HOVER = "#8E3939"

FUENTE_APP = "Helvetica"
FUENTE_CONSOLA = "Consolas"

class PamFlowDesktop(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1180x900")
        self.minsize(1000, 820)

        # Application icon.
        # On Windows, .ico gives the best result in the title bar and taskbar.
        self._window_icon = None
        try:
            if ICON_FILE.exists():
                self.iconbitmap(str(ICON_FILE))
            elif LOGO_FILE.exists():
                self._window_icon = tk.PhotoImage(file=str(LOGO_FILE))
                self.iconphoto(True, self._window_icon)
        except Exception:
            # If the icon cannot be loaded, the app continues normally.
            self._window_icon = None
        self.proc = None
        self.log_queue = queue.Queue()

        self.config_data = self.load_config()

        self.pamflow_dir = ctk.StringVar(value=self.config_data.get("pamflow_dir", DEFAULT_PAMFLOW_DIR))
        self.audio_dir = ctk.StringVar(value=self.config_data.get("audio_dir", ""))
        self.deployment_file = ctk.StringVar(value=self.config_data.get("deployment_file", ""))
        self.target_species = ctk.StringVar(value=self.config_data.get("target_species", ""))
        self.timezone = ctk.StringVar(value=self.config_data.get("timezone", "America/Bogota"))
        self.pipeline = ctk.StringVar(value=self.config_data.get("pipeline", "Full workflow"))
        self.node = ctk.StringVar(value=self.config_data.get("node", "Full pipeline"))
        self.run_mode = ctk.StringVar(value=self.config_data.get("run_mode", "Full pipeline"))
        self.status = ctk.StringVar(value="Ready")

        self.build_ui()
        self.after(80, self.flush_logs)

    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def save_config(self):
        data = {
            "pamflow_dir": self.pamflow_dir.get(),
            "audio_dir": self.audio_dir.get(),
            "deployment_file": self.deployment_file.get(),
            "target_species": self.target_species.get(),
            "timezone": self.timezone.get(),
            "pipeline": self.pipeline.get(),
            "node": self.node.get(),
            "run_mode": self.run_mode.get(),
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.status.set("Configuration saved")
        self.write_log("Configuration saved successfully.\n")

    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        # Main PamFlow logo.
        self.logo_image = None
        if LOGO_FILE.exists():
            try:
                logo_pil = Image.open(LOGO_FILE)
                display_width = 300
                display_height = max(1, round(display_width * logo_pil.height / logo_pil.width))
                self.logo_image = ctk.CTkImage(
                    light_image=logo_pil,
                    dark_image=logo_pil,
                    size=(display_width, display_height),
                )
                logo_label = ctk.CTkLabel(header, text="", image=self.logo_image)
                logo_label.grid(row=0, column=0, padx=24, pady=14, sticky="w")
            except Exception:
                self.logo_image = None

        # Fallback if the logo file is unavailable or cannot be loaded.
        if self.logo_image is None:
            title = ctk.CTkLabel(
                header,
                text="PamFlow Desktop",
                font=ctk.CTkFont(family=FUENTE_APP, size=30, weight="bold"),
            )
            title.grid(row=0, column=0, padx=24, pady=(18, 2), sticky="w")
            subtitle = ctk.CTkLabel(
                header,
                text="Modern launcher for running PamFlow pipelines",
                text_color=("gray35", "gray70"),
                font=ctk.CTkFont(family=FUENTE_APP, size=14),
            )
            subtitle.grid(row=1, column=0, padx=24, pady=(0, 18), sticky="w")

        body = ctk.CTkFrame(self, corner_radius=18)
        body.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(9, weight=1)

        self.add_path_row(body, 0, "PamFlow folder", self.pamflow_dir, self.select_pamflow_dir, "Select the folder containing Kedro/PamFlow")
        self.add_path_row(body, 1, "Audio folder", self.audio_dir, self.select_audio_dir, "Root folder with subfolders by recorder")
        self.add_path_row(body, 2, "Deployment sheet (.xlsx)", self.deployment_file, self.select_deployment_file, "Excel file containing the recorderID column")
        self.add_path_row(body, 3, "Target species (.csv)", self.target_species, self.select_target_file, "Optional")

        ctk.CTkLabel(body, text="Time zone", font=ctk.CTkFont(family=FUENTE_APP, weight="bold")).grid(row=4, column=0, padx=18, pady=6, sticky="w")
        tz = ctk.CTkComboBox(body, variable=self.timezone, values=TIMEZONES, height=36, font=ctk.CTkFont(family=FUENTE_APP, size=13))
        tz.grid(row=4, column=1, padx=18, pady=6, sticky="ew")

        ctk.CTkLabel(body, text="Pipeline", font=ctk.CTkFont(family=FUENTE_APP, weight="bold")).grid(row=5, column=0, padx=18, pady=6, sticky="w")
        self.pipeline_box = ctk.CTkComboBox(
            body,
            variable=self.pipeline,
            values=list(PIPELINES.keys()),
            command=self.update_nodes,
            height=36,
            font=ctk.CTkFont(family=FUENTE_APP, size=13),
        )
        self.pipeline_box.grid(row=5, column=1, padx=18, pady=6, sticky="ew")

        ctk.CTkLabel(
            body,
            text="Node",
            font=ctk.CTkFont(family=FUENTE_APP, weight="bold"),
        ).grid(row=6, column=0, padx=18, pady=6, sticky="w")

        self.node_box = ctk.CTkComboBox(
            body,
            variable=self.node,
            values=["Full pipeline"],
            command=self.on_node_changed,
            height=36,
            font=ctk.CTkFont(family=FUENTE_APP, size=13),
        )
        self.node_box.grid(row=6, column=1, padx=18, pady=6, sticky="ew")

        ctk.CTkLabel(
            body,
            text="Run mode",
            font=ctk.CTkFont(family=FUENTE_APP, weight="bold"),
        ).grid(row=7, column=0, padx=18, pady=6, sticky="w")

        self.run_mode_box = ctk.CTkComboBox(
            body,
            variable=self.run_mode,
            values=RUN_MODES,
            command=self.on_run_mode_changed,
            height=36,
            font=ctk.CTkFont(family=FUENTE_APP, size=13),
        )
        self.run_mode_box.grid(row=7, column=1, padx=18, pady=6, sticky="ew")

        self.update_nodes(self.pipeline.get(), preserve_selection=True)

        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=8, column=0, columnspan=2, padx=18, pady=(14, 10), sticky="ew")
        actions.grid_columnconfigure((0,1,2,3,4), weight=1)

        ctk.CTkButton(
            actions,
            text="Save configuration",
            command=self.save_config,
            height=42,
            font=ctk.CTkFont(family=FUENTE_APP, size=14, weight="bold"),
            fg_color=AZUL_PAMFLOW,
            hover_color=AZUL_HOVER,
            text_color="white",
        ).grid(row=0, column=0, padx=6, sticky="ew")

        ctk.CTkButton(
            actions,
            text="▶ Run PamFlow",
            command=self.run_pamflow,
            height=42,
            font=ctk.CTkFont(family=FUENTE_APP, size=14, weight="bold"),
            fg_color=VERDE_PAMFLOW,
            hover_color=VERDE_HOVER,
            text_color="white",
        ).grid(row=0, column=1, padx=6, sticky="ew")

        ctk.CTkButton(
            actions,
            text="■ Stop",
            command=self.stop_process,
            height=42,
            font=ctk.CTkFont(family=FUENTE_APP, size=14, weight="bold"),
            fg_color=ROJO_DETENER,
            hover_color=ROJO_HOVER,
            text_color="white",
        ).grid(row=0, column=2, padx=6, sticky="ew")

        ctk.CTkButton(
            actions,
            text="Open output",
            command=self.open_output,
            height=42,
            font=ctk.CTkFont(family=FUENTE_APP, size=14, weight="bold"),
            fg_color=AZUL_PAMFLOW,
            hover_color=AZUL_HOVER,
            text_color="white",
        ).grid(row=0, column=3, padx=6, sticky="ew")

        ctk.CTkButton(
            actions,
            text="Clear console",
            command=self.clear_log,
            height=42,
            font=ctk.CTkFont(family=FUENTE_APP, size=14, weight="bold"),
            fg_color=AZUL_PAMFLOW,
            hover_color=AZUL_HOVER,
            text_color="white",
        ).grid(row=0, column=4, padx=6, sticky="ew")

        console_card = ctk.CTkFrame(body, corner_radius=14)
        console_card.grid(row=9, column=0, columnspan=3, padx=18, pady=(8, 18), sticky="nsew")
        console_card.grid_rowconfigure(1, weight=1)
        console_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(console_card, textvariable=self.status, font=ctk.CTkFont(family=FUENTE_APP, size=15, weight="bold")).grid(row=0, column=0, padx=14, pady=(12, 6), sticky="w")
        self.console = ctk.CTkTextbox(
            console_card,
            wrap="word",
            height=240,
            font=ctk.CTkFont(family=FUENTE_CONSOLA, size=13),
        )
        self.console.grid(row=1, column=0, padx=14, pady=(0, 14), sticky="nsew")
        self.write_log("PamFlow live console ready. Select your data and click Run PamFlow.\n")

    def update_nodes(self, selected_pipeline=None, preserve_selection=False):
        """Update the Node selector so it only shows nodes from the selected pipeline."""
        pipeline_label = selected_pipeline or self.pipeline.get()
        previous = self.node.get()

        if pipeline_label == "Full workflow":
            values = ["Full pipeline"]
            self.node_box.configure(values=values, state="disabled")
            self.node.set("Full pipeline")
            self.run_mode.set("Full pipeline")
            self.run_mode_box.configure(state="disabled")
            return

        pipeline_info = PIPELINE_NODES.get(pipeline_label, {})
        node_labels = list(pipeline_info.get("nodes", {}).keys())
        values = ["Full pipeline"] + node_labels

        self.node_box.configure(values=values, state="normal")
        self.run_mode_box.configure(state="normal")

        if preserve_selection and previous in values:
            self.node.set(previous)
        else:
            self.node.set("Full pipeline")

        if self.node.get() == "Full pipeline":
            self.run_mode.set("Full pipeline")

    def on_node_changed(self, selected_node):
        if selected_node == "Full pipeline":
            self.run_mode.set("Full pipeline")
        elif self.run_mode.get() == "Full pipeline":
            self.run_mode.set("Selected node + all dependencies")

    def on_run_mode_changed(self, selected_mode):
        if selected_mode == "Full pipeline":
            self.node.set("Full pipeline")
        elif self.pipeline.get() == "Full workflow":
            self.run_mode.set("Full pipeline")
            self.node.set("Full pipeline")
        elif self.node.get() == "Full pipeline":
            node_labels = list(
                PIPELINE_NODES.get(self.pipeline.get(), {}).get("nodes", {}).keys()
            )
            if node_labels:
                self.node.set(node_labels[0])

    def add_path_row(self, parent, row, label, variable, command, placeholder):
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(family=FUENTE_APP, weight="bold")).grid(row=row, column=0, padx=18, pady=6, sticky="w")
        entry = ctk.CTkEntry(parent, textvariable=variable, height=36, placeholder_text=placeholder, font=ctk.CTkFont(family=FUENTE_APP, size=13))
        entry.grid(row=row, column=1, padx=(18, 8), pady=6, sticky="ew")
        btn = ctk.CTkButton(
            parent,
            text="Browse",
            command=command,
            width=110,
            height=36,
            font=ctk.CTkFont(family=FUENTE_APP, size=13, weight="bold"),
            fg_color=VERDE_PAMFLOW,
            hover_color=VERDE_HOVER,
            text_color="white",
        )
        btn.grid(row=row, column=2, padx=(0, 18), pady=6)

    def select_pamflow_dir(self):
        p = filedialog.askdirectory(title="Select PamFlow folder")
        if p: self.pamflow_dir.set(p)

    def select_audio_dir(self):
        p = filedialog.askdirectory(title="Select audio folder")
        if p: self.audio_dir.set(p)

    def select_deployment_file(self):
        p = filedialog.askopenfilename(title="Select deployment sheet", filetypes=[("Excel", "*.xlsx *.xls")])
        if p: self.deployment_file.set(p)

    def select_target_file(self):
        p = filedialog.askopenfilename(title="Select target species CSV", filetypes=[("CSV", "*.csv")])
        if p: self.target_species.set(p)

    def validate_inputs(self):
        pamflow = Path(self.pamflow_dir.get())
        audio = Path(self.audio_dir.get())
        deployment = Path(self.deployment_file.get())
        species = self.target_species.get().strip()

        if not pamflow.exists():
            messagebox.showerror("Error", "The PamFlow folder does not exist.")
            return False
        if not (pamflow / "conf" / "local").exists():
            messagebox.showerror("Error", "The PamFlow folder does not appear to be valid: conf/local is missing.")
            return False
        if not audio.exists():
            messagebox.showerror("Error", "The audio folder does not exist.")
            return False
        if not deployment.exists():
            messagebox.showerror("Error", "The deployment sheet file does not exist.")
            return False
        if species and not Path(species).exists():
            messagebox.showerror("Error", "The target_species.csv file does not exist.")
            return False
        return True

    def write_kedro_config(self):
        pamflow = Path(self.pamflow_dir.get())
        local = pamflow / "conf" / "local"
        local.mkdir(parents=True, exist_ok=True)
        audio = self.audio_dir.get().replace("\\", "/")
        deployment = self.deployment_file.get().replace("\\", "/")
        species = self.target_species.get().strip().replace("\\", "/")
        timezone = self.timezone.get().strip() or "America/Bogota"

        (local / "parameters.yml").write_text(
            f'timezone: "{timezone}"\n'
            f'audio_root_directory: "{audio}"\n',
            encoding="utf-8",
        )
        catalog = (
            "field_deployments_sheet@pandas:\n"
            "  type: pandas.ExcelDataset\n"
            f'  filepath: "{deployment}"\n'
        )
        if species:
            catalog += (
                "\n"
                "target_species@pandas:\n"
                "  type: pamflow.datasets.pamDP.target_species.TargetSpecies\n"
                f'  filepath: "{species}"\n'
            )
        (local / "catalog.yml").write_text(catalog, encoding="utf-8")

    def run_pamflow(self):
        if self.proc and self.proc.poll() is None:
            messagebox.showwarning("PamFlow is running", "A process is already running.")
            return
        if not self.validate_inputs():
            return
        self.save_config()
        self.write_kedro_config()
        self.clear_log()
        self.write_log("Configuration written to conf/local.\n")

        pipeline_key = self.pipeline.get()
        pipeline_name = PIPELINES[pipeline_key]
        run_mode = self.run_mode.get()
        node_key = self.node.get()

        node_name = None
        if pipeline_key != "Full workflow" and node_key != "Full pipeline":
            node_name = PIPELINE_NODES[pipeline_key]["nodes"].get(node_key)

        args = ["kedro", "run"]

        if run_mode == "Full pipeline":
            if pipeline_name:
                args.append(f"--pipeline={pipeline_name}")

        elif run_mode == "Selected node only":
            if not node_name:
                messagebox.showerror("Node required", "Select a node before running this mode.")
                return
            # Keep the pipeline restriction when running only the chosen node.
            if pipeline_name:
                args.append(f"--pipeline={pipeline_name}")
            args.append(f"--nodes={node_name}")

        elif run_mode == "Selected node + all dependencies":
            if not node_name:
                messagebox.showerror("Node required", "Select a node before running this mode.")
                return
            # Intentionally do not add --pipeline here. This lets Kedro include
            # upstream dependencies that may live in other registered pipelines.
            args.append(f"--to-nodes={node_name}")

        self.write_log(f"Selected pipeline: {pipeline_key}\n")
        self.write_log(f"Selected node: {node_key}\n")
        self.write_log(f"Run mode: {run_mode}\n")
        self.write_log("> " + " ".join(args) + "\n\n")
        self.status.set("Running...")

        def worker():
            try:
                env = os.environ.copy()
                env_path = Path(sys.executable).parent
                env["PATH"] = str(env_path) + os.pathsep + str(env_path / "Library" / "bin") + os.pathsep + env.get("PATH", "")
                env["PYTHONUNBUFFERED"] = "1"
                env["PYTHONIOENCODING"] = "utf-8"
                self.proc = subprocess.Popen(
                    args,
                    cwd=self.pamflow_dir.get(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    env=env,
                    shell=False,
                )
                for line in self.proc.stdout:
                    self.log_queue.put(line)
                code = self.proc.wait()
                if code == 0:
                    self.log_queue.put("\nProcess completed successfully.\n")
                    self.log_queue.put(("__STATUS__", "Completed successfully"))
                else:
                    self.log_queue.put(f"\nProcess finished with exit code {code}.\n")
                    self.log_queue.put(("__STATUS__", "Finished with error"))
            except Exception as exc:
                self.log_queue.put(f"\nERROR: {exc}\n")
                self.log_queue.put(("__STATUS__", "Finished with error"))

        threading.Thread(target=worker, daemon=True).start()

    def stop_process(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.status.set("Process stopped")
            self.write_log("\nProcess stopped by the user.\n")

    def open_output(self):
        output = Path(self.pamflow_dir.get()) / "data" / "output"
        if output.exists():
            os.startfile(output)
        else:
            messagebox.showinfo("Output", "The data/output folder does not exist yet.")

    def write_log(self, text):
        self.console.insert("end", text)
        self.console.see("end")

    def clear_log(self):
        self.console.delete("1.0", "end")

    def flush_logs(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple) and item[0] == "__STATUS__":
                    self.status.set(item[1])
                else:
                    self.write_log(item)
        except queue.Empty:
            pass
        self.after(80, self.flush_logs)

if __name__ == "__main__":
    app = PamFlowDesktop()
    app.mainloop()
