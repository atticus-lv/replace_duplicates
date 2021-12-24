import bpy
from bpy.props import CollectionProperty, PointerProperty, BoolProperty


def redraw(self, context):
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


class MatProperty(bpy.types.PropertyGroup):
    old_material: PointerProperty(type=bpy.types.Material)
    new_material: PointerProperty(type=bpy.types.Material)
    replace: BoolProperty(default=True, update=redraw)


class RD_OT_replace_materials(bpy.types.Operator):
    bl_idname = 'rd.replace_materials'
    bl_label = 'Replace Materials'
    bl_options = {'UNDO'}

    base_names = dict()
    replace_dict = dict()

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        for index, item in enumerate(context.window_manager.replace_mat_list):
            box = col.box()
            row = box.row()
            col1 = row.column(align=True)
            col1.prop(item, 'old_material', text='')
            col1.prop(item, 'new_material', text='')

            col2 = row.column(align=True)
            col2.label(text='', icon='SORT_ASC')
            col2.prop(item, 'replace', text='', toggle=True, icon='CHECKMARK' if item.replace else 'X')

    def invoke(self, context, event):
        # restore
        self.base_names.clear()
        self.replace_dict.clear()
        context.window_manager.replace_mat_list.clear()
        # set
        self.base_names, self.replace_dict = self.get_duplicates()

        for old_mat_name, new_mat in self.replace_dict.items():
            item = context.window_manager.replace_mat_list.add()
            item.old_material = bpy.data.materials.get(old_mat_name)
            item.new_material = new_mat

        if len(self.replace_dict) == 0:
            def draw_menu(self, context):
                self.layout.label(text='No Material is Duplicate!', icon='INFO')

            context.window_manager.popup_menu(draw_menu)
            return {'CANCELLED'}

        return context.window_manager.invoke_props_dialog(self, width=400)

    def execute(self, context):
        confirm_list = [item.old_material for item in context.window_manager.replace_mat_list if item.replace is True]

        for obj in bpy.data.objects:
            for slot in obj.material_slots:
                mat = slot.material
                if mat is not None and mat.name in self.replace_dict:
                    old_mat = mat
                    if mat not in confirm_list: continue

                    new_mat = self.replace_dict.get(mat.name)
                    setattr(slot, 'material', new_mat)
                    # report
                    msg = f"Replace object '{obj.name}'s material '{old_mat.name}' with '{new_mat.name}'"
                    self.report({"INFO"}, msg)

        return {"FINISHED"}

    def get_duplicates(self):
        base_names = dict()
        replace_dict = dict()

        for mat in bpy.data.materials:
            base, sep, ext = mat.name.rpartition('.')
            if base == '' and sep == '':
                base_names[ext] = mat  # 若无分隔，ext为名字
            elif len(ext) == 3 and ext.isnumeric():  # 这里用正则识别000之类的应该更准确
                if base not in base_names:  # 由于遍历material是按字符顺序来的，所以如果有重复材质会先进入base_names
                    base_names[base] = mat
                else:
                    replace_dict[mat.name] = base_names.get(base)

        return base_names, replace_dict


def draw_menu(self, context):
    layout = self.layout
    layout.operator('rd.replace_materials', icon='MATSHADERBALL')
    layout.separator(factor=0.5)


def register():
    bpy.utils.register_class(MatProperty)
    bpy.utils.register_class(RD_OT_replace_materials)

    bpy.types.WindowManager.replace_mat_list = CollectionProperty(type=MatProperty)  # material that confirm to replace

    bpy.types.EEVEE_MATERIAL_PT_context_material.prepend(draw_menu)
    bpy.types.CYCLES_PT_context_material.prepend(draw_menu)


def ungister():
    bpy.utils.unregister_class(MatProperty)
    bpy.utils.unregister_class(RD_OT_replace_materials)

    del bpy.types.WindowManager.replace_mat_list
