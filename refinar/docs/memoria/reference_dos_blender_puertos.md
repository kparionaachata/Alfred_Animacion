---
name: reference_dos_blender_puertos
description: "Dos Blender abiertos a la vez - el de trabajo en el puerto MCP 9877, cliente b9877.py y entrada MCP blender_9877"
metadata:
  node_type: memory
  type: reference
  originSessionId: 93ef65a7-e5c0-4f1e-ac65-91c8b9f7c4e7
  modified: 2026-11-07T05:47:06.584Z
---

El usuario trabaja con dos Blender abiertos (2026-11-05): el de trabajo (ranas / alfred_buscando_hierro) con el add-on MCP en el **puerto 9877** (Auto Start apagado: el usuario arranca el servidor a mano) y otro en el 9876.
- La extension "Blender" de Claude esta fija en 9876 (`BLENDER_MCP_PORT`, `blmcp/tools_helpers/connection.py`).
- Se anadio la entrada MCP de usuario `blender_9877` (`claude mcp add -s user blender_9877 -e BLENDER_MCP_PORT=9877 -- <venv>\Scripts\blender-mcp.exe`).
- Mientras tanto se usa un cliente directo: `capitulos/capitulo_4/scripts_2026-11_ranas_y_hierro/b9877.py` (manda `{"type":"execute","code":...,"strict_json":true}` + `\0` al socket y lee hasta `\0`). Uso: `python -I b9877.py script.py`; el script devuelve un dict en `result`.
- Si `ConnectionRefused`: el servidor MCP de ese Blender no esta iniciado -> pedir al usuario que lo inicie (no es un fallo del codigo).
- Un script mandado a Blender NO se cancela al matar el cliente: sigue corriendo dentro de Blender. Comprobar con un ping corto antes de lanzar otro.
Relacionado: [[project_ranas_y_hierro_2026-11]].
