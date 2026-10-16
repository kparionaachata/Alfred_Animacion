# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

"""
Sistema de Visualización de Texturas en Viewport
Extraído y adaptado del addon MCprep para Alfred_Animacion

Este módulo permite mostrar texturas en el modo de sombreado sólido (solid shading)
del viewport de Blender, optimizando la visualización de materiales Minecraft.
Permite selección individual de objetos .obj para aplicar la visualización.
"""

# Import bpy solo cuando esté disponible (dentro de Blender)
try:
    import bpy
    from bpy.types import Operator, Panel
    bpy_available = True
except ImportError:
    # Fuera de Blender, crear clases dummy
    bpy = None
    bpy_available = False

    class DummyOperator:
        pass

    class DummyPanel:
        pass

    Operator = DummyOperator
    Panel = DummyPanel


class VIEWPORT_OT_enable_texture_solid(Operator):
    """Habilita la visualización de texturas en modo sólido del viewport"""
    bl_idname = "viewport.enable_texture_solid"
    bl_label = "Enable Texture Solid View"
    bl_description = "Show textures in solid shading mode for better material preview"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Verificar si estamos en modo background (sin interfaz)
        if bpy.app.background:
            self.report({'WARNING'}, "Cannot modify viewport in background mode")
            return {'CANCELLED'}

        # Obtener el espacio de vista actual
        view = context.space_data
        if not view:
            self.report({'ERROR'}, "No active 3D view found")
            return {'CANCELLED'}

        # Configurar visualización de texturas según versión de Blender
        try:
            # Para Blender 2.7
            if hasattr(view, "show_textured_solid"):
                view.show_textured_solid = True
                print("Enabled textured solid view (Blender 2.7)")

            # Para Blender 2.8+
            elif view.type == 'VIEW_3D':
                if hasattr(view, "shading"):
                    view.shading.color_type = "TEXTURE"
                    print("Enabled texture color type in viewport")
                elif hasattr(context.scene, "display") and hasattr(context.scene.display, "shading"):
                    context.scene.display.shading.color_type = "TEXTURE"
                    print("Enabled texture color type in scene display")

            # Asegurar que el modo de sombreado sea al menos sólido
            if hasattr(context.scene, "display") and hasattr(context.scene.display, "shading"):
                view28_modes = ['SOLID', 'MATERIAL', 'RENDERED']
                current_mode = context.scene.display.shading.type

                if current_mode not in view28_modes:
                    context.scene.display.shading.type = 'SOLID'
                    print(f"Changed shading mode from {current_mode} to SOLID")

            self.report({'INFO'}, "Viewport texture display enabled")

        except Exception as e:
            self.report({'ERROR'}, f"Failed to enable texture display: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}


class VIEWPORT_OT_disable_texture_solid(Operator):
    """Deshabilita la visualización de texturas en modo sólido"""
    bl_idname = "viewport.disable_texture_solid"
    bl_label = "Disable Texture Solid View"
    bl_description = "Return to default viewport shading"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if bpy.app.background:
            return {'CANCELLED'}

        view = context.space_data
        if not view:
            return {'CANCELLED'}

        try:
            # Restaurar configuración por defecto
            if hasattr(view, "show_textured_solid"):
                view.show_textured_solid = False
            elif view.type == 'VIEW_3D' and hasattr(view, "shading"):
                view.shading.color_type = "MATERIAL"
            elif hasattr(context.scene, "display") and hasattr(context.scene.display, "shading"):
                context.scene.display.shading.color_type = "MATERIAL"

            print("Disabled custom texture display settings")
            self.report({'INFO'}, "Viewport texture display disabled")

        except Exception as e:
            self.report({'ERROR'}, f"Failed to disable texture display: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}


def enable_texture_solid_view():
    """
    Función utilitaria para habilitar visualización de texturas en viewport
    Puede ser llamada directamente desde otros scripts
    """
    try:
        # Simular contexto si no está disponible
        if not bpy.context:
            print("No Blender context available")
            return False

        # Ejecutar el operador
        bpy.ops.viewport.enable_texture_solid()
        return True

    except Exception as e:
        print(f"Error enabling texture solid view: {str(e)}")
        return False


def is_texture_solid_enabled():
    """
    Verifica si la visualización de texturas en sólido está habilitada
    """
    try:
        view = bpy.context.space_data
        if not view:
            return False

        # Verificar según versión de Blender
        if hasattr(view, "show_textured_solid"):
            return view.show_textured_solid
        elif hasattr(view, "shading"):
            return view.shading.color_type == "TEXTURE"
        elif hasattr(bpy.context.scene, "display") and hasattr(bpy.context.scene.display, "shading"):
            return bpy.context.scene.display.shading.color_type == "TEXTURE"

        return False

    except:
        return False


class VIEWPORT_OT_apply_texture_to_object(Operator):
    """Aplica visualización de texturas sólidas a objetos .obj seleccionados"""
    bl_idname = "viewport.apply_texture_to_object"
    bl_label = "Apply to Selected .obj"
    bl_description = "Apply texture solid view to selected .obj objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = context.selected_objects

        if not selected_objects:
            self.report({'ERROR'}, "No objects selected")
            return {'CANCELLED'}

        obj_applied = 0
        for obj in selected_objects:
            # Verificar si es un objeto mesh (típicamente de .obj importado)
            if obj.type == 'MESH':
                # Marcar el objeto para visualización especial
                obj["viewport_texture_solid"] = True
                obj_applied += 1
                print(f"Applied texture solid view to: {obj.name}")
            else:
                print(f"Skipped non-mesh object: {obj.name}")

        if obj_applied > 0:
            # Habilitar la visualización global si no está activa
            if not is_texture_solid_enabled():
                enable_texture_solid_view()

            self.report({'INFO'}, f"Applied texture solid view to {obj_applied} objects")
        else:
            self.report({'WARNING'}, "No mesh objects found in selection")

        return {'FINISHED'}


class VIEWPORT_PT_texture_solid_panel(Panel):
    """Panel de control para el sistema de texturas sólidas en viewport"""
    bl_label = "Viewport Texture Solid"
    bl_idname = "VIEWPORT_PT_texture_solid_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Viewport Texture'
    bl_order = 0  # Asegurar que aparezca primero en la categoría

    def draw(self, context):
        layout = self.layout

        # Estado global
        is_enabled = is_texture_solid_enabled()

        # Controles principales
        col = layout.column(align=True)
        col.label(text="Global Controls:", icon='VIEW3D')

        row = col.row(align=True)
        if is_enabled:
            row.operator("viewport.disable_texture_solid", text="Disable Global", icon='CANCEL')
        else:
            row.operator("viewport.enable_texture_solid", text="Enable Global", icon='CHECKMARK')

        # Separador
        layout.separator()

        # Controles por objeto
        col = layout.column(align=True)
        col.label(text="Object Controls:", icon='OBJECT_DATA')

        # Mostrar objetos .obj en la escena
        obj_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']

        if obj_objects:
            col.label(text="Select .obj objects and apply:")

            # Botón para aplicar a seleccionados
            selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
            if selected_meshes:
                col.operator("viewport.apply_texture_to_object",
                           text=f"Apply to {len(selected_meshes)} Selected",
                           icon='MATERIAL')
            else:
                col.operator("viewport.apply_texture_to_object",
                           text="Select Objects First",
                           icon='ERROR')

            # Lista de objetos con estado
            col.separator()
            col.label(text="Object Status:")

            box = col.box()
            for obj in obj_objects[:10]:  # Limitar a 10 para no sobrecargar UI
                row = box.row(align=True)
                has_texture_solid = obj.get("viewport_texture_solid", False)
                icon = 'TEXTURE' if has_texture_solid else 'MATERIAL'

                row.label(text=obj.name, icon=icon)
                if has_texture_solid:
                    row.label(text="Active", icon='CHECKMARK')
                else:
                    row.label(text="Inactive", icon='X')
        else:
            col.label(text="No .obj objects in scene", icon='INFO')

        # Información de ayuda
        layout.separator()
        col = layout.column(align=True)
        col.label(text="Help:", icon='HELP')
        col.label(text="1. Import .obj files", icon='IMPORT')
        col.label(text="2. Select mesh objects", icon='RESTRICT_SELECT_OFF')
        col.label(text="3. Apply texture view", icon='MATERIAL')
        col.label(text="4. Enable global if needed", icon='VIEW3D')


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------


classes = (
    VIEWPORT_OT_enable_texture_solid,
    VIEWPORT_OT_disable_texture_solid,
    VIEWPORT_PT_texture_solid_panel,
    VIEWPORT_OT_apply_texture_to_object,
)


def register():
    if bpy_available:
        for cls in classes:
            bpy.utils.register_class(cls)
        print("✅ Viewport Texture System registrado correctamente")
    else:
        print("⚠️ Viewport Texture System: bpy no disponible, omitiendo registro")


def unregister():
    if bpy_available:
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)
        print("✅ Viewport Texture System desregistrado correctamente")
    else:
        print("⚠️ Viewport Texture System: bpy no disponible, omitiendo desregistro")


if __name__ == "__main__":
    register()
    # Ejemplo de uso directo
    enable_texture_solid_view()