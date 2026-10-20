"""Estudio local para crear variaciones instrumentales con ACE-Step 1.5.

La interfaz es deliberadamente independiente del sistema de voces. ACE-Step se
ejecuta como servicio local y esta aplicacion conserva entradas, resultados,
parametros y calificaciones dentro de ``musica_variaciones``.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterator
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import gradio as gr
import requests


ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "entradas"
OUTPUTS = ROOT / "resultados"
RUNS = ROOT / "historial"
PREFERENCES = ROOT / "aprendizaje" / "calificaciones.jsonl"
API_URL = os.environ.get("MUSICA_API_URL", "http://127.0.0.1:6974").rstrip("/")
FFPROBE = shutil.which("ffprobe") or "ffprobe"
SUPPORTED = {".wav", ".mp3", ".flac", ".ogg", ".opus", ".m4a", ".aac"}

for directory in (INPUTS, OUTPUTS, RUNS, PREFERENCES.parent):
    directory.mkdir(parents=True, exist_ok=True)


def _request_json(path: str, payload: dict | None = None, timeout: int = 30) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{API_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc


def _release_with_audio(payload: dict, audio_path: Path, timeout: int = 120) -> dict:
    """Submit cover audio using multipart upload; the API rejects absolute paths."""
    form = {
        key: ("true" if value is True else "false" if value is False else str(value))
        for key, value in payload.items()
        if key != "src_audio_path" and value is not None
    }
    session = requests.Session()
    session.trust_env = False
    with audio_path.open("rb") as stream:
        response = session.post(
            f"{API_URL}/release_task",
            data=form,
            files={"src_audio": (audio_path.name, stream, "application/octet-stream")},
            timeout=timeout,
        )
    if not response.ok:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
    return response.json()


def estado_motor() -> str:
    try:
        response = _request_json("/v1/models", timeout=3)
        data = response.get("data", [])
        models = data.get("models", []) if isinstance(data, dict) else data
        loaded = [
            m.get("name") or m.get("id") or "modelo"
            for m in models
            if not isinstance(data, dict) or m.get("is_loaded")
        ]
        if loaded:
            return "Motor listo: " + ", ".join(loaded)
        return "Servicio activo. El modelo se descargara/cargara al crear la primera variacion."
    except Exception:
        return "Motor detenido. Abre el estudio con 'Abrir Variador de Musica.cmd'."


def duracion_audio(path: str | Path) -> float:
    result = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        timeout=30,
    )
    if result.returncode:
        raise ValueError("No se pudo leer la duracion del audio.")
    return float(result.stdout.strip())


def _safe_stem(name: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in "-_" else "_" for char in name)
    return cleaned.strip("_")[:70] or "musica"


def _copy_source(source: Path, run_id: str) -> Path:
    destination = INPUTS / f"{run_id}_{_safe_stem(source.stem)}{source.suffix.lower()}"
    shutil.copy2(source, destination)
    return destination


def _download_result(url_or_path: str, destination: Path) -> None:
    url = url_or_path if url_or_path.startswith("http") else f"{API_URL}{url_or_path}"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=180) as response, destination.open("wb") as stream:
        shutil.copyfileobj(response, stream)


def _wait_for_task(task_id: str, timeout_seconds: int = 7200) -> Iterator[tuple[str, list[dict] | None]]:
    started = time.monotonic()
    while time.monotonic() - started < timeout_seconds:
        response = _request_json("/query_result", {"task_id_list": [task_id]}, timeout=30)
        rows = response.get("data") or []
        if not rows:
            yield "En cola...", None
            time.sleep(3)
            continue
        row = rows[0]
        status = int(row.get("status", 0))
        if status == 1:
            raw = row.get("result") or "[]"
            return_value = json.loads(raw) if isinstance(raw, str) else raw
            yield "Terminada", return_value
            return
        if status == 2:
            raise RuntimeError(row.get("error") or row.get("result") or "ACE-Step no pudo generar la variacion.")
        yield "Generando con la GPU...", None
        time.sleep(3)
    raise TimeoutError("La generacion supero el limite de dos horas.")


def _empty_outputs(status: str, run_id: str = "") -> tuple:
    return (None, None, None, None, None, None, None, None, status, run_id)


def generar_variaciones(
    upload: str | None,
    descripcion: str,
    fidelidad: float,
    cantidad: int,
) -> Iterator[tuple]:
    source = Path(upload or "")
    if not source.is_file():
        raise gr.Error("Carga una pista instrumental.")
    if source.suffix.lower() not in SUPPORTED:
        raise gr.Error("Formato no compatible. Usa WAV, MP3, FLAC, OGG, OPUS, M4A o AAC.")
    try:
        duration = duracion_audio(source)
    except Exception as exc:
        raise gr.Error(str(exc)) from exc
    if not 10 <= duration <= 600:
        raise gr.Error(f"La pista dura {duration:.1f} s. El motor admite de 10 s a 10 min.")
    if not descripcion.strip():
        descripcion = "cinematic instrumental background music, no vocals"

    cantidad = max(1, min(4, int(cantidad)))
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    saved_source = _copy_source(source, run_id)
    run_dir = OUTPUTS / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    prompt = descripcion.strip() + ", instrumental only, background music, no vocals, no spoken voice"
    generated: list[str | None] = [None, None, None, None]
    downloads: list[str | None] = [None, None, None, None]
    seeds: list[str] = []

    yield _empty_outputs(
        f"Entrada validada: {duration:.1f} s. Preparando {cantidad} variacion(es)...", run_id
    )

    for index in range(cantidad):
        payload = {
            "prompt": prompt,
            "lyrics": "[Instrumental]",
            "thinking": False,
            "model": "acestep-v15-turbo",
            "task_type": "cover",
            "src_audio_path": str(saved_source.resolve()),
            "audio_duration": round(duration, 3),
            "audio_cover_strength": float(fidelidad),
            "inference_steps": 8,
            "use_random_seed": True,
            "batch_size": 1,
            "audio_format": "wav",
            "use_tiled_decode": True,
        }
        try:
            released = _release_with_audio(payload, saved_source, timeout=120)
            task_id = released.get("data", {}).get("task_id")
            if not task_id:
                raise RuntimeError(released.get("error") or "El motor no devolvio un identificador de tarea.")
            for task_status, result in _wait_for_task(task_id):
                status = f"Variacion {index + 1}/{cantidad}: {task_status}"
                yield (*generated, *downloads, status, run_id)
                if result is None:
                    continue
                item = result[0]
                destination = run_dir / f"variacion_{index + 1}.wav"
                _download_result(item["file"], destination)
                generated[index] = str(destination)
                downloads[index] = str(destination)
                seeds.append(str(item.get("seed_value", "")))
        except (urllib.error.URLError, TimeoutError, RuntimeError, ValueError) as exc:
            raise gr.Error(f"Fallo en la variacion {index + 1}: {exc}") from exc

    metadata = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_original": str(source),
        "source_saved": str(saved_source),
        "duration_seconds": duration,
        "description": descripcion.strip(),
        "prompt_sent": prompt,
        "instrumental": True,
        "fidelity": float(fidelidad),
        "variation_count": cantidad,
        "seeds": seeds,
        "outputs": [path for path in generated if path],
        "engine": "ACE-Step 1.5 turbo",
    }
    (RUNS / f"{run_id}.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    yield (*generated, *downloads, f"Listo. {cantidad} variacion(es) guardadas en {run_dir}", run_id)


def guardar_calificacion(run_id: str, variante: str, estrellas: int, nota: str) -> str:
    if not run_id:
        raise gr.Error("Primero genera un lote de variaciones.")
    run_file = RUNS / f"{run_id}.json"
    if not run_file.is_file():
        raise gr.Error("No se encontro el historial de ese lote.")
    run = json.loads(run_file.read_text(encoding="utf-8"))
    index = int(variante.split()[-1]) - 1
    outputs = run.get("outputs", [])
    if index < 0 or index >= len(outputs):
        raise gr.Error("Esa variacion no existe en el lote actual.")
    record = {
        "rated_at": datetime.now().isoformat(timespec="seconds"),
        "run_id": run_id,
        "variant": index + 1,
        "output": outputs[index],
        "rating": int(estrellas),
        "note": nota.strip(),
        "description": run.get("description", ""),
        "fidelity": run.get("fidelity", 0.7),
    }
    with PREFERENCES.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    return "Calificacion guardada. El boton 'Aplicar lo aprendido' usara las mejores elecciones."


def _ratings() -> list[dict]:
    if not PREFERENCES.exists():
        return []
    records = []
    for line in PREFERENCES.read_text(encoding="utf-8").splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def sugerencia_aprendida() -> tuple[str, float, str]:
    ratings = [row for row in _ratings() if int(row.get("rating", 0)) >= 4]
    if not ratings:
        return (
            "cinematica ambiental, instrumental, clara y discreta para dialogos",
            0.70,
            "Aun no hay elecciones de 4 o 5 estrellas; se aplicaron valores iniciales.",
        )
    weighted = sum(float(row.get("fidelity", 0.7)) * int(row["rating"]) for row in ratings)
    total = sum(int(row["rating"]) for row in ratings)
    descriptions = Counter(row.get("description", "") for row in ratings if row.get("description"))
    prompt = descriptions.most_common(1)[0][0] if descriptions else "instrumental cinematic background music"
    fidelity = round(weighted / total, 2)
    return prompt, fidelity, f"Aprendizaje aplicado desde {len(ratings)} calificacion(es) positivas."


CSS = """
.app-title {text-align:center; margin-bottom:0.25rem}
.app-subtitle {text-align:center; color:#aab2c0; margin-bottom:1.25rem}
.result-card {border:1px solid #394150; border-radius:12px; padding:8px}
"""

with gr.Blocks(title="Variador de musica instrumental") as demo:
    gr.Markdown("# Variador de música instrumental", elem_classes="app-title")
    gr.Markdown(
        "Carga una pista de hasta 10 minutos y crea versiones nuevas sin voz. "
        "La original nunca se sobrescribe.",
        elem_classes="app-subtitle",
    )
    engine_state = gr.Textbox(value=estado_motor, label="Estado del motor", interactive=False)
    refresh = gr.Button("Actualizar estado", size="sm")
    refresh.click(estado_motor, outputs=engine_state)

    with gr.Row():
        source_audio = gr.Audio(sources=["upload"], type="filepath", label="Pista instrumental original")
        with gr.Column():
            description = gr.Textbox(
                value="cinematica ambiental, instrumental, clara y discreta para dialogos",
                label="Como debe sonar la variacion",
                lines=4,
                placeholder="Ej.: aventura suave, cuerdas y percusion ligera, sin voz",
            )
            fidelity = gr.Slider(
                0.2, 0.95, value=0.70, step=0.05,
                label="Fidelidad a la melodia y estructura original",
                info="0.2 cambia mucho; 0.95 conserva mucho.",
            )
            count = gr.Slider(1, 4, value=2, step=1, label="Cantidad de variaciones")
            apply_learning = gr.Button("Aplicar lo aprendido")
            learning_status = gr.Markdown("El aprendizaje comienza cuando calificas resultados.")
            apply_learning.click(sugerencia_aprendida, outputs=[description, fidelity, learning_status])

    generate = gr.Button("Generar variaciones", variant="primary")
    status = gr.Textbox(label="Progreso", interactive=False)
    run_id = gr.State("")

    audio_outputs = []
    file_outputs = []
    with gr.Row():
        for i in range(4):
            with gr.Column(elem_classes="result-card"):
                audio_outputs.append(gr.Audio(label=f"Variacion {i + 1}"))
                file_outputs.append(gr.File(label="Descargar WAV"))

    generate.click(
        generar_variaciones,
        inputs=[source_audio, description, fidelity, count],
        outputs=[*audio_outputs, *file_outputs, status, run_id],
        concurrency_limit=1,
    )

    with gr.Accordion("Enseñar preferencias al sistema", open=True):
        gr.Markdown(
            "Escucha el lote, elige una versión y califícala. Esto aprende tus ajustes y "
            "descripciones preferidas; no reentrena el modelo profundo con una sola canción."
        )
        with gr.Row():
            selected_variant = gr.Dropdown(
                choices=["Variacion 1", "Variacion 2", "Variacion 3", "Variacion 4"],
                value="Variacion 1", label="Resultado",
            )
            stars = gr.Slider(1, 5, value=5, step=1, label="Calificacion")
        note = gr.Textbox(label="Nota opcional", placeholder="Ej.: buena para escenas de suspenso")
        save_rating = gr.Button("Guardar calificacion")
        rating_status = gr.Textbox(label="Aprendizaje", interactive=False)
        save_rating.click(
            guardar_calificacion,
            inputs=[run_id, selected_variant, stars, note],
            outputs=rating_status,
        )

    gr.Markdown(
        "**Uso responsable:** carga música propia, licenciada o con permiso para crear derivados. "
        "Los archivos quedan únicamente en este equipo."
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch(
        server_name="127.0.0.1",
        server_port=6973,
        css=CSS,
        inbrowser="--open" in sys.argv,
        allowed_paths=[str(ROOT)],
        share=False,
    )
