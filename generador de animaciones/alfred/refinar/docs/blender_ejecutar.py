"""Cliente minimo del add-on MCP de Blender (localhost:9876) para usar desde una terminal.

Pensado para que otra IA (Codex/ChatGPT) ejecute codigo Python en la escena abierta de Blender sin un servidor MCP propio.
Uso:   python blender_ejecutar.py archivo.py [--timeout 120]      (o:  python blender_ejecutar.py - < archivo.py)
El codigo debe hacer `import bpy` y dejar `result = {...}` (dict serializable). Imprime la respuesta JSON del add-on.
Regla del tablero: solo UNA IA a la vez toca la escena; cuentalo en TABLERO_TAREAS_IA.md antes de ejecutar.
"""
import json, socket, sys

def ejecutar(code, host="localhost", port=9876, timeout=120):
    s = socket.create_connection((host, port), timeout=10)
    s.settimeout(timeout)
    s.sendall(json.dumps({"type": "execute", "code": code, "strict_json": True}).encode() + b"\0")
    buf = b""
    while b"\0" not in buf:
        chunk = s.recv(65536)
        if not chunk: break
        buf += chunk
    s.close()
    return json.loads(buf.split(b"\0")[0].decode())

if __name__ == "__main__":
    a = sys.argv[1:]
    t = float(a[a.index("--timeout") + 1]) if "--timeout" in a else 120
    src = sys.stdin.read() if a[0] == "-" else open(a[0], encoding="utf-8").read()
    print(json.dumps(ejecutar(src, timeout=t), indent=2, ensure_ascii=False))
