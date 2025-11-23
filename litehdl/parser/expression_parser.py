import ast

class VHDLExpressionParser:
    def parse(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str): return f"'{node.value}'"
            return str(node.value)
        elif isinstance(node, ast.BinOp):
            left = self.parse(node.left)
            right = self.parse(node.right)
            op = self._map_operator(node.op)
            return f"({left} {op} {right})"
        elif isinstance(node, ast.Call):
            func_name = node.func.id
            if node.args:
                arg = self.parse(node.args[0])
                if func_name == 'v': return f"std_logic_vector({arg})"
                if func_name == 'u': return f"unsigned({arg})"
                if func_name == 's': return f"signed({arg})"
                if func_name == 'int': return f"to_integer({arg})"
                return f"{func_name}({arg})"
            return f"{func_name}()"
        elif isinstance(node, ast.Subscript):
            value = self.parse(node.value)
            if isinstance(node.slice, ast.Slice):
                high = self.parse(node.slice.lower) if node.slice.lower else "0"
                low = self.parse(node.slice.upper) if node.slice.upper else "0"
                return f"{value}({high} downto {low})"
            else:
                slice_node = node.slice.value if isinstance(node.slice, ast.Index) else node.slice
                index_expr = self.parse(slice_node)
                if index_expr.isdigit():
                    return f"{value}({index_expr})"
                else:
                    return f"{value}(to_integer({index_expr}))"
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Invert) or isinstance(node.op, ast.Not):
                return f"not {self.parse(node.operand)}"
        return "UNKNOWN_EXPR"

    def _map_operator(self, op):
        if isinstance(op, ast.Add): return "+"
        if isinstance(op, ast.Sub): return "-"
        if isinstance(op, ast.Mult): return "*"
        if isinstance(op, ast.BitAnd): return "and"
        if isinstance(op, ast.BitOr): return "or"
        if isinstance(op, ast.BitXor): return "xor"
        return "?"

    def _map_comparator(self, op):
        if isinstance(op, ast.Eq): return "="
        if isinstance(op, ast.NotEq): return "/="
        if isinstance(op, ast.Gt): return ">"
        if isinstance(op, ast.Lt): return "<"
        return "?"
