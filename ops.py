import bpy
from bpy.props import CollectionProperty, PointerProperty, BoolProperty


def redraw(self, context):
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


class MaterialProperty(bpy.types.PropertyGroup):
    src: PointerProperty(name='Source', type=bpy.types.Material)
    target: PointerProperty(name='Target', type=bpy.types.Material)
    replace: BoolProperty(default=True, update=redraw)


class NodeGroupProperty(bpy.types.PropertyGroup):
    src: PointerProperty(name='Source', type=bpy.types.NodeTree)
    target: PointerProperty(name='Target', type=bpy.types.NodeTree)
    replace: BoolProperty(default=True, update=redraw)


class ReplaceBase():
    bl_options = {'UNDO'}

    base_names = dict()  # coll of the base name
    replace_dict = dict()  # key: object.name, pointer

    def restore(self):
        self.base_names.clear()
        self.replace_dict.clear()

    def get_duplicates(self, lib='materials'):
        base_names = dict()
        replace_dict = dict()
        data_lib = getattr(bpy.data, lib)

        for mat in data_lib:
            base, sep, ext = mat.name.rpartition('.')
            if base == '' and sep == '':
                base_names[ext] = mat  # 若无分隔，ext为名字
            elif len(ext) == 3 and ext.isnumeric():  # 这里用正则识别000之类的应该更准确
                if base not in base_names:  # 由于遍历material是按字符顺序来的，所以如果有重复材质会先进入base_names
                    base_names[base] = mat
                else:
                    replace_dict[mat.name] = base_names.get(base)

        return base_names, replace_dict

    def draw_ui(self, context, temp_list_name='replace_mat_list'):
        temp_list = getattr(context.window_manager, temp_list_name)

        layout = self.layout
        col = layout.column()
        for index, item in enumerate(temp_list):
            box = col.box()
            row = box.row()
            col1 = row.column(align=True)
            col1.prop(item, 'src', text='')
            col1.prop(item, 'target', text='')

            col2 = row.column(align=True)
            col2.label(text='', icon='SORT_ASC')
            col2.prop(item, 'replace', text='', toggle=True, icon='CHECKMARK' if item.replace else 'X')


class RD_OT_replace_nodegroups(ReplaceBase, bpy.types.Operator):
    bl_idname = 'rd.replace_nodegroups'
    bl_label = 'Replace Node Groups'

    def draw(self, context):
        self.draw_ui(context, 'replace_nodegroup_list')

    def invoke(self, context, event):
        self.restore()
        context.window_manager.replace_nodegroup_list.clear()

        self.base_names, self.replace_dict = self.get_duplicates('node_groups')

        for old_name, new in self.replace_dict.items():
            item = context.window_manager.replace_nodegroup_list.add()
            item.src = bpy.data.node_groups.get(old_name)
            item.target = new

        if len(self.replace_dict) == 0:
            def draw_menu(self, context):
                self.layout.label(text='No Node Group is Duplicate!', icon='INFO')

            context.window_manager.popup_menu(draw_menu)
            return {'CANCELLED'}

        return context.window_manager.invoke_props_dialog(self, width=400)

    def execute(self, context):
        confirm_list = [item.src for item in context.window_manager.replace_nodegroup_list if item.replace is True]

        mats = list(bpy.data.materials)
        worlds = list(bpy.data.worlds)

        for mat in mats + worlds:
            if mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == 'GROUP' and node.node_tree.name in self.replace_dict:
                        old = node.node_tree
                        if old not in confirm_list: continue

                        new_mat = self.replace_dict.get(old.name)
                        setattr(node, 'node_tree', new_mat)
                        # report
                        msg = f"Replace object '{node.name}'s nodetree '{old.name}' with '{new_mat.name}'"
                        self.report({"INFO"}, msg)

        return {"FINISHED"}


class RD_OT_replace_materials(ReplaceBase, bpy.types.Operator):
    bl_idname = 'rd.replace_materials'
    bl_label = 'Replace Materials'

    def draw(self, context):
        self.draw_ui(context, 'replace_mat_list')

    def invoke(self, context, event):
        self.restore()
        context.window_manager.replace_mat_list.clear()
        # set
        self.base_names, self.replace_dict = self.get_duplicates()

        for old_mat_name, new_mat in self.replace_dict.items():
            item = context.window_manager.replace_mat_list.add()
            item.src = bpy.data.materials.get(old_mat_name)
            item.target = new_mat

        if len(self.replace_dict) == 0:
            def draw_menu(self, context):
                self.layout.label(text='No Material is Duplicate!', icon='INFO')

            context.window_manager.popup_menu(draw_menu)
            return {'CANCELLED'}

        return context.window_manager.invoke_props_dialog(self, width=400)

    def execute(self, context):
        confirm_list = [item.src for item in context.window_manager.replace_mat_list if item.replace is True]

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


def draw_menu(self, context):
    layout = self.layout
    row = layout.row()
    row.operator('rd.replace_materials', icon='MATSHADERBALL')
    row.operator('rd.replace_nodegroups', icon='NODETREE')
    layout.separator(factor=0.25)


def register():
    bpy.utils.register_class(MaterialProperty)
    bpy.utils.register_class(NodeGroupProperty)
    bpy.utils.register_class(RD_OT_replace_materials)
    bpy.utils.register_class(RD_OT_replace_nodegroups)

    bpy.types.EEVEE_MATERIAL_PT_context_material.prepend(draw_menu)
    bpy.types.CYCLES_PT_context_material.prepend(draw_menu)

    bpy.types.WindowManager.replace_mat_list = CollectionProperty(
        type=MaterialProperty)  # material that confirm to replace
    bpy.types.WindowManager.replace_nodegroup_list = CollectionProperty(
        type=NodeGroupProperty)  # material that confirm to replace


def ungister():
    bpy.utils.unregister_class(MaterialProperty)
    bpy.utils.unregister_class(NodeGroupProperty)
    bpy.utils.unregister_class(RD_OT_replace_materials)
    bpy.utils.unregister_class(RD_OT_replace_nodegroups)

    bpy.types.EEVEE_MATERIAL_PT_context_material.remove(draw_menu)
    bpy.types.CYCLES_PT_context_material.remove(draw_menu)

    del bpy.types.WindowManager.replace_mat_list
    del bpy.types.WindowManager.replace_nodegroup_list
