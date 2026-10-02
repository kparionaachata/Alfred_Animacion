#!/usr/bin/env python3
"""Deriva los artefactos JSON de zombie_3..5 sin usar Blender ni bpy.

Uso habitual:
    python derivar_zombie.py
    python derivar_zombie.py --zombies 3 5
    python derivar_zombie.py --solo-validar

El script parte de z2_antes_estilos.animacion.json, aplica deformacion
temporal, estilo de marcha, carril y caida, renombra todos los objetos y
escribe el JSON mas su manifest. Al final imprime y valida el informe E1.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable


N_FRAMES = 860
MAX_FINAL_SPEED = 0.0849
FALL_REFERENCE = {1: 550, 2: 598}
MATRIX_FRAMES = (1, 100, 200, 300, 400, 476, 560, 700, 800, 860)
CONFIG = {
    3: {
        "style": "NORMAL",
        "phase": 6,
        "cycle": 20,
        "delay": 97,
        "approach_speed": 0.94,
        "approach_lane": 0.7,
        "queue_y": 1.3,
        "lane_x": 0.9,
        "requested_landing": (-123.0, -120.4),
        # Ajuste minimo para quedar a >=3 m del aterrizaje real de zombie_2.
        "landing": (-112.5, -118.9),
        "final_target": (-109.6, -118.6),
        "holding_point": (-112.5, -118.9),
        "final_start": 780,
        "fall_detour_x": 0.0,
        "eye": {"left": 1.08, "right": 1.0},
    },
    4: {
        "style": "NORMAL",
        "phase": 13,
        "cycle": 20,
        "delay": 120,
        "approach_speed": 0.90,
        "approach_lane": -0.7,
        "queue_y": 2.6,
        "lane_x": 0.5,
        "requested_landing": (-108.5, -120.6),
        "landing": (-116.6, -119.2),
        "final_target": (-113.0, -121.7),
        "holding_point": (-116.6, -119.2),
        "final_start": 800,
        "fall_detour_x": 0.0,
        "eye": {"left": 1.0, "right": 1.10},
    },
    5: {
        "style": "NORMAL",
        "phase": 3,
        "cycle": 20,
        "delay": 155,
        "approach_speed": 0.86,
        "approach_lane": 0.0,
        "queue_y": 3.7,
        "lane_x": -0.7,
        "requested_landing": (-118.6, -121.0),
        # El punto propuesto estaba a <3 m de zombie_2.
        "landing": (-114.4, -119.1),
        "final_target": (-111.4, -120.0),
        "holding_point": (-114.4, -119.1),
        "final_start": 830,
        "fall_detour_x": 0.0,
        "eye": {"left": 1.0, "right": 1.0},
    },
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def frame_tau(frame: int, delay: int, approach_speed: float = 1.0) -> float:
    """Tiempo de aproximacion en cola y retraso final S, continuo en f=490."""
    if frame <= 490:
        remaining_delay = delay - 490.0 * (1.0 - approach_speed)
        return frame * approach_speed - remaining_delay * smoothstep((frame - 330) / 160.0)
    return frame - delay * (1.0 - smoothstep((frame - 740) / 110.0))


def sample(values: list[float], frame: float) -> float:
    index = max(0.0, min(len(values) - 1.0, frame - 1.0))
    low = int(math.floor(index))
    high = min(low + 1, len(values) - 1)
    mix = index - low
    return values[low] * (1.0 - mix) + values[high] * mix


def round5(value: float) -> float:
    value = round(float(value), 5)
    return 0.0 if value == -0.0 else value


def warp_frame_lists(value: Any, delay: int, approach_speed: float) -> Any:
    """Remuestrea recursivamente cada serie numerica de exactamente 860 frames."""
    if isinstance(value, dict):
        return {key: warp_frame_lists(item, delay, approach_speed) for key, item in value.items()}
    if isinstance(value, list):
        if len(value) == N_FRAMES and all(isinstance(item, (int, float)) for item in value):
            return [
                round5(sample(value, frame_tau(frame, delay, approach_speed)))
                for frame in range(1, N_FRAMES + 1)
            ]
        return [warp_frame_lists(item, delay, approach_speed) for item in value]
    return copy.deepcopy(value)


def walk_weight(warped_frame: float) -> float:
    if warped_frame <= 440:
        return 1.0
    if warped_frame < 476:
        return 1.0 - smoothstep((warped_frame - 440) / 36.0)
    if warped_frame <= 660:
        return 0.0
    if warped_frame < 690:
        return smoothstep((warped_frame - 660) / 30.0)
    return 1.0


def series_value(axis: Any, index: int) -> float:
    return float(axis[index] if isinstance(axis, list) else axis)


def style_row(rows: list[list[float]], frame: int, cycle: int | None, phase: int = 0) -> list[float]:
    if cycle is None:
        return rows[(frame - 1) % len(rows)]
    return rows[20 + (frame + phase) % cycle]


def style_mean(rows: list[list[float]], cycle: int | None) -> list[float]:
    selected = rows if cycle is None else rows[20 : 20 + cycle]
    return [sum(row[axis] for row in selected) / len(selected) for axis in range(3)]


def apply_walk_style(
    data: dict[str, Any],
    style: dict[str, list[list[float]]],
    delay: int,
    approach_speed: float,
    cycle: int | None,
    phase: int = 0,
) -> None:
    bones = data["armature"]["bones"]
    neck_name = "Neck_zombie_2"
    neck_average = style_mean(style[neck_name], cycle)

    for bone_name, rows in style.items():
        if bone_name not in bones:
            raise KeyError(f"El hueso de estilo no existe en la base: {bone_name}")
        rotation = bones[bone_name]["rotation_euler"]
        output_axes = [[] for _ in range(3)]
        for frame in range(1, N_FRAMES + 1):
            weight = walk_weight(frame_tau(frame, delay, approach_speed))
            target = neck_average if bone_name == neck_name else style_row(rows, frame, cycle, phase)
            for axis in range(3):
                original = series_value(rotation[axis], frame - 1)
                output_axes[axis].append(round5(original + (target[axis] - original) * weight))
        bones[bone_name]["rotation_euler"] = output_axes

    hips_location = bones["Hips_zombie_2"]["location"]
    fixed_axes = [[] for _ in range(3)]
    for frame in range(1, N_FRAMES + 1):
        weight = walk_weight(frame_tau(frame, delay, approach_speed))
        for axis in range(3):
            fixed_axes[axis].append(round5(series_value(hips_location[axis], frame - 1) * (1.0 - weight)))
    bones["Hips_zombie_2"]["location"] = fixed_axes


def apply_eye_scale(data: dict[str, Any], left: float, right: float) -> None:
    for side, factor in (("izquierdo", left), ("derecho", right)):
        eye = data["ojos"][f"ojo_{side}_zombie_2"]
        scale = eye["canales"]["scale"]
        for axis, target in ((0, factor), (1, 1.0), (2, factor)):
            scale[axis] = [round5(target)] * N_FRAMES if isinstance(scale[axis], list) else round5(target)


def apply_approach_spacing(
    data: dict[str, Any], lane_x: float, queue_y: float, delay: int
) -> None:
    """Separa carriles y cola; el lateral se funde antes que la distancia longitudinal."""
    root = data["root"]["canales"]["location"]
    fall_frame = 553 + delay
    for frame in range(1, N_FRAMES + 1):
        lane_keep = 1.0 - smoothstep((frame - 380) / 100.0)
        queue_keep = 1.0 - smoothstep((frame - fall_frame) / 30.0)
        root[0][frame - 1] = round5(root[0][frame - 1] + lane_x * lane_keep)
        root[1][frame - 1] = round5(root[1][frame - 1] + queue_y * queue_keep)


def apply_route_and_fall(
    data: dict[str, Any],
    delay: int,
    lane_x: float,
    landing: tuple[float, float],
    fall_detour_x: float,
    z1: dict[str, Any],
) -> tuple[int, int]:
    root = data["root"]["canales"]["location"]
    fall_frame = 553 + delay
    landing_frame = fall_frame + 30
    fade_at_landing = 1.0 - smoothstep((landing_frame - 712) / 140.0)
    if fade_at_landing <= 0:
        raise ValueError("El fade termina antes del aterrizaje")

    index = landing_frame - 1
    lane_at_landing = lane_x * smoothstep((landing_frame - 380) / 120.0)
    fall_x = (landing[0] - root[0][index]) / fade_at_landing - lane_at_landing
    fall_y = (landing[1] - root[1][index]) / fade_at_landing

    z1_axis = z1["root"]["canales"]["location"][2]
    for frame in range(1, N_FRAMES + 1):
        i = frame - 1
        fade = 1.0 - smoothstep((frame - 712) / 140.0)
        lane = lane_x * smoothstep((frame - 380) / 120.0)
        fall_mix = smoothstep((frame - fall_frame) / 30.0)
        fall_phase = max(0.0, min(1.0, (frame - fall_frame) / 30.0))
        detour_x = fall_detour_x * math.sin(math.pi * fall_phase)
        root[0][i] = round5(root[0][i] + (lane + fall_x * fall_mix) * fade + detour_x)
        root[1][i] = round5(root[1][i] + fall_y * fall_mix * fade)

        dz = -0.95 * smoothstep((frame - (fall_frame + 13)) / 16.0) * (
            1.0 - smoothstep((frame - (fall_frame + 127)) / 12.0)
        )
        z_value = max(root[2][i] + dz, 6.95)
        settle = smoothstep((frame - (fall_frame + 147)) / 20.0)
        z_value += (6.95 - z_value) * settle
        z1_mix = smoothstep((frame - 790) / 20.0)
        z1_value = series_value(z1_axis, i)
        z_value += (z1_value - z_value) * z1_mix
        root[2][i] = round5(z_value)

    return fall_frame, landing_frame


def apply_post_fall_path(
    data: dict[str, Any],
    landing_frame: int,
    landing: tuple[float, float],
    holding_point: tuple[float, float],
    target: tuple[float, float],
    move_start: int,
) -> int:
    """Mantiene el aterrizaje y luego avanza al carril final sin superar 0.085 m/f."""
    root = data["root"]["canales"]["location"]
    move_start = max(landing_frame, min(N_FRAMES, move_start))
    x, y = landing
    root[0][landing_frame - 1] = round5(x)
    root[1][landing_frame - 1] = round5(y)
    for frame in range(landing_frame + 1, move_start + 1):
        dx, dy = holding_point[0] - x, holding_point[1] - y
        distance = math.hypot(dx, dy)
        if distance:
            step = min(MAX_FINAL_SPEED, distance)
            x += dx / distance * step
            y += dy / distance * step
        root[0][frame - 1] = round5(x)
        root[1][frame - 1] = round5(y)

    for frame in range(move_start + 1, N_FRAMES + 1):
        dx, dy = target[0] - x, target[1] - y
        distance = math.hypot(dx, dy)
        if distance:
            step = min(MAX_FINAL_SPEED, distance)
            x += dx / distance * step
            y += dy / distance * step
        root[0][frame - 1] = round5(x)
        root[1][frame - 1] = round5(y)
    return move_start


def renamed(value: Any, zombie: int) -> Any:
    def rename_text(text: str) -> str:
        # La base ya contiene ademas el hueso excepcional
        # Neck_zombie_1.001; al no llevar el sufijo _zombie_2 se conserva.
        return text.replace("zombie_2", f"zombie_{zombie}")

    if isinstance(value, dict):
        return {rename_text(str(key)): renamed(item, zombie) for key, item in value.items()}
    if isinstance(value, list):
        return [renamed(item, zombie) for item in value]
    if isinstance(value, str):
        return rename_text(value)
    return value


def make_manifest(template: dict[str, Any], zombie: int, cfg: dict[str, Any]) -> dict[str, Any]:
    name = f"zombie_{zombie}_camina_acantilado"
    landing = cfg["landing"]
    manifest = {
        "formato": template.get("formato", "alfred_ia_anim/1"),
        "flujo": "IA",
        "nombre": name,
        "agente": "codex",
        "creado": dt.datetime.now().isoformat(timespec="seconds"),
        "blender": template.get("blender", "5.2.1 LTS"),
        "fps": 24,
        "frames": [1, N_FRAMES],
        "objetos": [
            f"zombie_{zombie}",
            f"zombie_{zombie}_Armature",
            f"ojo_izquierdo_zombie_{zombie}",
            f"ojo_derecho_zombie_{zombie}",
        ],
        "guion_fuente": "alfred\\refinar\\docs\\datos_zombies\\z2_antes_estilos.animacion.json",
        "notas": (
            f"Derivacion E1: marcha {cfg['style']}, retraso {cfg['delay']} frames, "
            f"velocidad {cfg['approach_speed']:.2f}, carril inicial {cfg['approach_lane']:+.2f}, "
            f"carril de borde {cfg['lane_x']:+.2f}, aterrizaje ({landing[0]:.2f}, {landing[1]:.2f}), "
            f"objetivo final ({cfg['final_target'][0]:.2f}, {cfg['final_target'][1]:.2f}). "
            "Generado sin Blender; pendiente de revision visual del usuario."
        ),
        "archivos": [f"{name}.animacion.json"],
        "aplicar": f"ai_export.importar('{name}', personaje=ai_export.zombie({zombie}))",
        "limitaciones": [
            "Derivado numericamente de la base entregada por el maestro; no validado visualmente en Blender.",
            "No incluye props ni invisibilidad de mallas.",
        ],
    }
    if cfg["requested_landing"] != landing:
        manifest["notas"] += (
            f" El punto propuesto ({cfg['requested_landing'][0]:.2f}, {cfg['requested_landing'][1]:.2f}) "
            "se ajusto lo minimo necesario para respetar 3 m entre zombies."
        )
    return manifest


def derive_one(
    base: dict[str, Any], styles: dict[str, Any], z1: dict[str, Any], zombie: int
) -> tuple[dict[str, Any], int, int]:
    cfg = CONFIG[zombie]
    data = warp_frame_lists(base, cfg["delay"], cfg["approach_speed"])
    apply_walk_style(
        data, styles[cfg["style"]], cfg["delay"], cfg["approach_speed"], cfg["cycle"], cfg.get("phase", 0)
    )
    apply_approach_spacing(data, cfg["approach_lane"], cfg["queue_y"], cfg["delay"])
    apply_eye_scale(data, cfg["eye"]["left"], cfg["eye"]["right"])
    fall_frame, landing_frame = apply_route_and_fall(
        data, cfg["delay"], cfg["lane_x"], cfg["landing"], cfg["fall_detour_x"], z1
    )
    apply_post_fall_path(
        data,
        landing_frame,
        cfg["landing"],
        cfg["holding_point"],
        cfg["final_target"],
        cfg["final_start"],
    )
    data = renamed(data, zombie)
    data["nombre"] = f"zombie_{zombie}_camina_acantilado"
    data["root"]["objeto"] = f"zombie_{zombie}"
    data["armature"]["objeto"] = f"zombie_{zombie}_Armature"
    return data, fall_frame, landing_frame


def iter_numeric_lists(value: Any, path: str = "") -> Iterable[tuple[str, list[float]]]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield from iter_numeric_lists(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        if value and all(isinstance(item, (int, float)) for item in value):
            yield path, value
        else:
            for index, item in enumerate(value):
                yield from iter_numeric_lists(item, f"{path}[{index}]")


def root_position(data: dict[str, Any], frame: int) -> tuple[float, float, float]:
    channels = data["root"]["canales"]["location"]
    return tuple(series_value(axis, frame - 1) for axis in channels)  # type: ignore[return-value]


def horizontal_distance(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def alfred_position(first: dict[str, Any], second: dict[str, Any], frame: int) -> tuple[float, float, float]:
    data = first if frame <= first["frame_fin"] else second
    index = frame - data["frame_inicio"]
    channels = data["root"]["canales"]["location"]
    return tuple(series_value(axis, index) for axis in channels)  # type: ignore[return-value]


def validate_animation(data: dict[str, Any], zombie: int, fall_frame: int) -> list[str]:
    errors: list[str] = []
    for path, values in iter_numeric_lists(
        {"root": data["root"], "armature": data["armature"], "ojos": data["ojos"]}
    ):
        if len(values) not in (3, N_FRAMES):
            errors.append(f"lista inesperada {path}: {len(values)}")

    worst_angle = (0.0, "", 0)
    for bone_name, bone in data["armature"]["bones"].items():
        rotation = bone.get("rotation_euler")
        if not rotation:
            continue
        for frame in range(2, N_FRAMES + 1):
            if fall_frame - 5 <= frame <= fall_frame + 40:
                continue
            jump = max(
                abs(series_value(rotation[axis], frame - 1) - series_value(rotation[axis], frame - 2))
                for axis in range(3)
            )
            if jump > worst_angle[0]:
                worst_angle = (jump, bone_name, frame)
    if worst_angle[0] > 0.35 + 1e-9:
        errors.append(
            f"salto angular {worst_angle[0]:.5f} en {worst_angle[1]} frame {worst_angle[2]}"
        )

    worst_root = (0.0, 0, 0)
    for frame in range(2, N_FRAMES + 1):
        before = root_position(data, frame - 1)
        after = root_position(data, frame)
        for axis in range(3):
            jump = abs(after[axis] - before[axis])
            if jump > worst_root[0]:
                worst_root = (jump, frame, axis)
    if worst_root[0] > 0.5 + 1e-9:
        errors.append(
            f"salto root {worst_root[0]:.5f} m en frame {worst_root[1]}, eje {worst_root[2]}"
        )

    serialized = json.dumps(data, ensure_ascii=False)
    if "zombie_2" in serialized:
        errors.append("queda texto residual zombie_2")
    if not data.get("brillo_ojos") or len(data["brillo_ojos"].get("objetos", [])) != 2:
        errors.append("falta brillo_ojos con sus dos objetos")
    return errors


def validate_group(
    animations: dict[int, dict[str, Any]],
    z1: dict[str, Any],
    z2: dict[str, Any],
    alfred_first: dict[str, Any],
    alfred_second: dict[str, Any],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    report: list[str] = []
    landings: dict[int, tuple[float, float, float]] = {
        1: root_position(z1, FALL_REFERENCE[1] + 30),
        2: root_position(z2, FALL_REFERENCE[2] + 30),
    }
    falls = dict(FALL_REFERENCE)

    for zombie, data in sorted(animations.items()):
        fall_frame = 553 + CONFIG[zombie]["delay"]
        landing_frame = fall_frame + 30
        falls[zombie] = fall_frame
        landings[zombie] = root_position(data, landing_frame)
        errors.extend(f"zombie_{zombie}: {message}" for message in validate_animation(data, zombie, fall_frame))
        # El criterio habla de la posicion de Alfred en el frame de caida Fc;
        # se compara contra el punto donde aterrizara el zombie.
        alfred = alfred_position(alfred_first, alfred_second, fall_frame)
        distance = horizontal_distance(landings[zombie], alfred)
        report.append(
            f"zombie_{zombie}: caida={fall_frame}, aterrizaje={landing_frame}, "
            f"xy=({landings[zombie][0]:.2f},{landings[zombie][1]:.2f}), Alfred={distance:.2f} m"
        )
        if distance < 4.5 - 1e-9:
            errors.append(f"zombie_{zombie}: distancia a Alfred {distance:.3f} m < 4.5 m")

    ordered_falls = sorted(falls.items(), key=lambda item: item[1])
    for (za, fa), (zb, fb) in zip(ordered_falls, ordered_falls[1:]):
        gap = fb - fa
        report.append(f"separacion caidas zombie_{za}->zombie_{zb}: {gap} frames")
        if gap < 35:
            errors.append(f"caidas zombie_{za}/zombie_{zb} separadas solo {gap} frames")

    for za in sorted(landings):
        for zb in sorted(landings):
            if zb <= za:
                continue
            distance = horizontal_distance(landings[za], landings[zb])
            report.append(f"distancia aterrizajes zombie_{za}/zombie_{zb}: {distance:.2f} m")
            if distance < 3.0 - 1e-9:
                errors.append(f"aterrizajes zombie_{za}/zombie_{zb}: {distance:.3f} m < 3 m")

    all_animations = {1: z1, 2: z2, **animations}

    def pairs(ids: Iterable[int]) -> Iterable[tuple[int, int]]:
        ordered = sorted(ids)
        for index, za in enumerate(ordered):
            for zb in ordered[index + 1 :]:
                yield za, zb

    def minimum_distance(
        pair_list: Iterable[tuple[int, int]], first_frame: int, last_frame: int
    ) -> tuple[float, int, int, int]:
        minimum = (float("inf"), 0, 0, 0)
        for za, zb in pair_list:
            for frame in range(first_frame, last_frame + 1):
                distance = horizontal_distance(
                    root_position(all_animations[za], frame), root_position(all_animations[zb], frame)
                )
                if distance < minimum[0]:
                    minimum = (distance, frame, za, zb)
        return minimum

    approach_ids = [zombie for zombie in (2, 3, 4, 5) if zombie in all_animations]
    frame1_min = minimum_distance(pairs(approach_ids), 1, 1)
    report.append(
        f"minimo aproximacion f1: {frame1_min[0]:.2f} m "
        f"(zombie_{frame1_min[2]}/zombie_{frame1_min[3]})"
    )
    if frame1_min[0] < 0.7 - 1e-9:
        errors.append(f"distancia minima frame 1: {frame1_min[0]:.3f} m < 0.7 m")

    approach_min = minimum_distance(pairs(approach_ids), 40, 560)
    report.append(
        f"minimo aproximacion f40-560: {approach_min[0]:.2f} m en f{approach_min[1]} "
        f"(zombie_{approach_min[2]}/zombie_{approach_min[3]})"
    )
    if approach_min[0] < 1.2 - 1e-9:
        errors.append(
            f"distancia aproximacion f40-560: {approach_min[0]:.3f} m en f{approach_min[1]} "
            f"zombie_{approach_min[2]}/zombie_{approach_min[3]} < 1.2 m"
        )

    # zombie_1 y zombie_2 son entradas inmutables y ya se superponen al final.
    # Se valida toda pareja del 1..5 que incluya al menos un artefacto entregado.
    final_pairs = [pair for pair in pairs(all_animations) if pair != (1, 2)]
    final_min = minimum_distance(final_pairs, 600, 860)
    fixed_min = minimum_distance([(1, 2)], 600, 860)
    report.append(
        f"minimo f600-860 (pares corregibles): {final_min[0]:.2f} m en f{final_min[1]} "
        f"(zombie_{final_min[2]}/zombie_{final_min[3]})"
    )
    report.append(
        f"par fijo zombie_1/zombie_2 fuera de alcance: {fixed_min[0]:.2f} m en f{fixed_min[1]}"
    )
    if final_min[0] < 1.3 - 1e-9:
        errors.append(
            f"distancia f600-860: {final_min[0]:.3f} m en f{final_min[1]} "
            f"zombie_{final_min[2]}/zombie_{final_min[3]} < 1.3 m"
        )

    report.append("matriz de distancias xy por frame:")
    matrix_pairs = list(pairs(all_animations))
    for frame in MATRIX_FRAMES:
        values = []
        for za, zb in matrix_pairs:
            distance = horizontal_distance(
                root_position(all_animations[za], frame), root_position(all_animations[zb], frame)
            )
            values.append(f"{za}-{zb}={distance:.2f}")
        report.append(f"  f{frame}: " + ", ".join(values))

    for zombie, data in sorted(animations.items()):
        move_start = CONFIG[zombie]["final_start"]
        worst_speed = 0.0
        for frame in range(move_start + 1, N_FRAMES + 1):
            worst_speed = max(
                worst_speed,
                horizontal_distance(root_position(data, frame - 1), root_position(data, frame)),
            )
        end = root_position(data, N_FRAMES)
        report.append(
            f"zombie_{zombie}: final=({end[0]:.2f},{end[1]:.2f}), "
            f"velocidad final maxima={worst_speed:.3f} m/f"
        )
        if worst_speed > 0.085 + 1e-9:
            errors.append(f"zombie_{zombie}: velocidad final {worst_speed:.5f} m/f > 0.085")
    return errors, report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zombies", nargs="+", type=int, choices=sorted(CONFIG), default=sorted(CONFIG))
    parser.add_argument("--solo-validar", action="store_true", help="No regenera; valida los artefactos existentes")
    parser.add_argument(
        "--raiz",
        type=Path,
        default=Path(__file__).resolve().parents[4],
        help="Ruta a 'generador de animaciones'",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.raiz.resolve()
    data_dir = Path(__file__).resolve().parent
    base = load_json(data_dir / "z2_antes_estilos.animacion.json")
    styles = load_json(data_dir / "estilos_zombie2.json")
    z1 = load_json(
        root / "zombie_1/refinar/animaciones_ia/zombie_1_camina_acantilado/zombie_1_camina_acantilado.animacion.json"
    )
    z2_dir = root / "zombie_2/refinar/animaciones_ia/zombie_2_camina_acantilado"
    z2 = load_json(z2_dir / "zombie_2_camina_acantilado.animacion.json")
    manifest_template = load_json(z2_dir / "manifest.json")
    alfred_first = load_json(
        root / "alfred/refinar/animaciones_ia/persecucion_zombie_agua/persecucion_zombie_agua.animacion.json"
    )
    alfred_second = load_json(
        root / "alfred/refinar/animaciones_ia/alfred_nada_hacia_piedras/alfred_nada_hacia_piedras.animacion.json"
    )

    animations: dict[int, dict[str, Any]] = {}
    for zombie in sorted(set(args.zombies)):
        name = f"zombie_{zombie}_camina_acantilado"
        output_dir = root / f"zombie_{zombie}/refinar/animaciones_ia/{name}"
        animation_path = output_dir / f"{name}.animacion.json"
        if args.solo_validar:
            animations[zombie] = load_json(animation_path)
            continue
        animation, _, _ = derive_one(base, styles, z1, zombie)
        animations[zombie] = animation
        save_json(animation_path, animation)
        save_json(output_dir / "manifest.json", make_manifest(manifest_template, zombie, CONFIG[zombie]))
        print(f"GENERADO {animation_path}")

    errors, report = validate_group(animations, z1, z2, alfred_first, alfred_second)
    print("\nINFORME E1")
    for line in report:
        print(f"- {line}")
    if errors:
        print("\nFALLOS")
        for error in errors:
            print(f"- {error}")
        return 1
    print("\nE1_VALIDACION_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
