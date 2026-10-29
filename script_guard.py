"""Static checks for generated bpy code. This is validation, not an OS sandbox."""
import ast


def validate_script(code):
    if len(code) > 200000:
        raise ValueError("Blender skripti çox böyükdür.")
    tree = ast.parse(code)
    allowed = {"bpy", "math", "mathutils", "random"}
    blocked_calls = {"open", "exec", "eval", "compile", "__import__", "getattr", "setattr", "globals", "locals", "vars", "input", "breakpoint"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(a.name.split(".")[0] not in allowed for a in node.names):
            raise ValueError("Blender skriptində icazəsiz import var.")
        if isinstance(node, ast.ImportFrom) and (not node.module or node.module.split(".")[0] not in allowed):
            raise ValueError("Blender skriptində icazəsiz import var.")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("Blender skriptində xüsusi sistem atributuna müraciət var.")
        if isinstance(node, ast.Call):
            call = ast.unparse(node.func)
            if call in blocked_calls or call.startswith(("bpy.ops.wm.", "bpy.ops.script.", "bpy.ops.preferences.")):
                raise ValueError("Blender skripti fayl və sistem əməliyyatı çağırmağa çalışır.")
    return True
