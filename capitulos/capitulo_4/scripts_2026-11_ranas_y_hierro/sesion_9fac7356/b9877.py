"""Cliente directo al add-on MCP de Blender en el puerto 9877. Uso: python b9877.py archivo.py"""
import json, socket, sys
code = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else sys.stdin.read()
s = socket.create_connection(("localhost", 9877), timeout=600)
s.sendall((json.dumps({"type": "execute", "code": code, "strict_json": True}) + "\0").encode())
buf = b""
while b"\0" not in buf:
    c = s.recv(65536)
    if not c: break
    buf += c
print(buf.partition(b"\0")[0].decode("utf-8"))
