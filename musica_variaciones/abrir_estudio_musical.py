"""Inicia el motor ACE-Step y abre una sola instancia del estudio musical."""

from pathlib import Path
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser


ROOT = Path(__file__).resolve().parent
ACE = ROOT / "ACE-Step-1.5"
PYTHON = ACE / ".venv" / "Scripts" / "python.exe"
API_URL = "http://127.0.0.1:6974/v1/models"
UI_URL = "http://127.0.0.1:6973"


def ready(url: str, timeout: float = 2.0) -> bool:
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url, timeout=timeout) as response:
            return response.status == 200
    except OSError:
        return False


def launch(command: list[str], cwd: Path, stdout_name: str, stderr_name: str, env: dict) -> subprocess.Popen:
    stdout = (ROOT / stdout_name).open("a", encoding="utf-8")
    stderr = (ROOT / stderr_name).open("a", encoding="utf-8")
    return subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=stdout,
        stderr=stderr,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


if not PYTHON.is_file():
    raise RuntimeError("Falta el entorno de ACE-Step. Ejecuta instalar.ps1 primero.")

environment = os.environ.copy()
environment.update(
    {
        "ACESTEP_API_HOST": "127.0.0.1",
        "ACESTEP_API_PORT": "6974",
        "ACESTEP_CONFIG_PATH": "acestep-v15-turbo",
        "ACESTEP_INIT_LLM": "false",
        "ACESTEP_OFFLOAD_TO_CPU": "true",
        "ACESTEP_OFFLOAD_DIT_TO_CPU": "true",
        "ACESTEP_DOWNLOAD_SOURCE": "huggingface",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "GRADIO_ANALYTICS_ENABLED": "False",
        "MUSICA_API_URL": "http://127.0.0.1:6974",
        "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
    }
)

api_process = None
if not ready(API_URL):
    api_process = launch(
        [str(PYTHON), "-m", "acestep.api_server", "--host", "127.0.0.1", "--port", "6974", "--no-init"],
        ACE,
        "motor.stdout.log",
        "motor.stderr.log",
        environment,
    )
    for _ in range(120):
        if ready(API_URL):
            break
        if api_process.poll() is not None:
            raise RuntimeError("El motor no pudo iniciar. Revisa motor.stderr.log.")
        time.sleep(1)
    else:
        raise TimeoutError("El motor no respondio. Revisa motor.stderr.log.")

if not ready(UI_URL):
    ui_process = launch(
        [str(PYTHON), "-u", str(ROOT / "estudio_musical.py")],
        ROOT,
        "estudio.stdout.log",
        "estudio.stderr.log",
        environment,
    )
    for _ in range(90):
        if ready(UI_URL):
            break
        if ui_process.poll() is not None:
            raise RuntimeError("La interfaz no pudo iniciar. Revisa estudio.stderr.log.")
        time.sleep(1)
    else:
        raise TimeoutError("La interfaz no respondio. Revisa estudio.stderr.log.")

webbrowser.open(UI_URL)
