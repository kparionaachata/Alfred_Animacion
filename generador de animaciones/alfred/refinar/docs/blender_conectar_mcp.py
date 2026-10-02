import bpy

MODULO = "bl_ext.user_default.mcp"
PUERTO = 9876

prefs = bpy.context.preferences

if bpy.app.online_access_override:
    print("[MCP] No se puede activar: Blender se inicio con --offline-mode. Reinicia sin esa opcion.")
else:
    prefs.system.use_online_access = True
    bpy.ops.wm.save_userpref()
    print("[MCP] Allow Online Access: activado y guardado. bpy.app.online_access =", bpy.app.online_access)

if MODULO not in prefs.addons:
    bpy.ops.preferences.addon_enable(module=MODULO)

addon = prefs.addons.get(MODULO)
if addon is None:
    print("[MCP] No se encontro el add-on", MODULO, "-> revisa que este instalado en Preferences > Get Extensions")
else:
    addon.preferences.host = "localhost"
    addon.preferences.port = PUERTO
    addon.preferences.use_autostart = True

    from importlib import import_module
    servidor = import_module(MODULO + ".mcp_to_blender_server")
    if servidor.is_running():
        print("[MCP] El servidor ya estaba corriendo en el puerto", PUERTO)
    else:
        resultado = bpy.ops.blmcp.server_start()
        print("[MCP] server_start ->", resultado, "| corriendo:", servidor.is_running())

for mod in ("higgsfield", "higgsfield_blender", "higgsfield_mcp"):
    if mod in prefs.addons:
        print("[MCP] Aviso: el add-on", mod, "sigue activo y puede competir por el puerto", PUERTO)
