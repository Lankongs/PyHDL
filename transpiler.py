import ast
import re
import sys

# ==============================================================================
# 1. VHDL 表達式解析器 (Expression Parser)
#    負責將 Python 的運算 (a+b, mem[i]) 轉換為 VHDL (a+b, mem(to_integer(i)))
# ==============================================================================
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
        
        # [NEW] 支援函數呼叫 (型別轉換)
        elif isinstance(node, ast.Call):
            func_name = node.func.id
            # 處理單參數函數
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
                # [FIX] 修正 Slice 方向: [High:Low] -> High downto Low
                # Python AST: node.slice.lower 是冒號左邊 (High)
                # Python AST: node.slice.upper 是冒號右邊 (Low)
                high = self.parse(node.slice.lower) if node.slice.lower else "0"
                low = self.parse(node.slice.upper) if node.slice.upper else "0"
                return f"{value}({high} downto {low})"
            else:
                # Indexing logic (保持不變)
                slice_node = node.slice.value if isinstance(node.slice, ast.Index) else node.slice
                index_expr = self.parse(slice_node)
                if index_expr.isdigit():
                    return f"{value}({index_expr})"
                else:
                    return f"{value}(to_integer({index_expr}))"
        
        # ... (其餘 UnaryOp, Compare 保持不變) ...
        elif isinstance(node, ast.UnaryOp):
             if isinstance(node.op, ast.Invert) or isinstance(node.op, ast.Not):
                return f"not {self.parse(node.operand)}"
        
        return "UNKNOWN_EXPR"
    
    # ... (_map_operator, _map_comparator 保持不變) ...
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

# ==============================================================================
# 2. 主解析器 (Main Parser)
#    遍歷 AST 並建立 VHDL 結構
# ==============================================================================
class LiteHDLParser(ast.NodeVisitor):
    def __init__(self):
        self.module_name = ""
        self.generics = [] 
        self.ports = []
        self.internal_signals = []
        self.type_defs = []
        self.processes = []
        self.instances = []
        self.expr_parser = VHDLExpressionParser()

    def visit_FunctionDef(self, node):
        self.module_name = node.name
        # 解析 Generics (從函數預設參數)
        offset = len(node.args.args) - len(node.args.defaults)
        for idx, arg in enumerate(node.args.args):
            if idx >= offset:
                val_node = node.args.defaults[idx-offset]
                val = val_node.value if isinstance(val_node, ast.Constant) else val_node.n
                self.generics.append((arg.arg, val))
        self.generic_visit(node)

    def visit_If(self, node):
        # 處理特殊區塊 (In, Out, Comb, Sync)
        if isinstance(node.test, ast.Name):
            tag = node.test.id
            if tag == '_In': self._parse_io_block(node.body, 'i')
            elif tag == '_Out': self._parse_io_block(node.body, 'o')
            elif tag == '_Comb': self._parse_comb_block(node.body)
        elif isinstance(node.test, ast.Call) and isinstance(node.test.func, ast.Name):
            if node.test.func.id == '_Sync':
                self._parse_sync_block(node)

    def visit_AnnAssign(self, node):
        # 處理內部訊號宣告 & 陣列定義
        name = node.target.id
        # 避免重複宣告 Port
        if any(p[0] == name for p in self.ports): return

        # 檢查是否為陣列 v[W][D]
        is_array, sig_decl, type_def = self._parse_complex_type(node.annotation, name)
        if is_array:
            self.type_defs.append(type_def)
            self.internal_signals.append(sig_decl)
        else:
            type_str = self._node_to_string(node.annotation)
            vhdl_type = self._map_type(type_str)
            self.internal_signals.append(f"    signal {name} : {vhdl_type};")

    def visit_With(self, node):
        # 處理實例化: with _Inst(...)
        if len(node.items) > 0:
            call_expr = node.items[0].context_expr
            if isinstance(call_expr, ast.Call) and isinstance(call_expr.func, ast.Name):
                if call_expr.func.id == '_Inst':
                    self._parse_instantiation(node, call_expr)

    # --- 內部邏輯處理函數 ---

    def _parse_io_block(self, body, direction):
        for item in body:
            if isinstance(item, ast.AnnAssign):
                name = item.target.id
                dtype = self._node_to_string(item.annotation)
                self.ports.append((name, direction, dtype))

    def _parse_complex_type(self, node, signal_name):
        # 解析 v[WIDTH][DEPTH]
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Subscript):
            depth_expr = self._node_to_string(node.slice)
            depth_val = f"{int(depth_expr)-1}" if depth_expr.isdigit() else f"{depth_expr}-1"
            
            inner_node = node.value
            width_expr = self._node_to_string(inner_node.slice)
            width_val = f"{int(width_expr)-1}" if width_expr.isdigit() else f"{width_expr}-1"
            base_tag = self._node_to_string(inner_node.value)
            
            base_vhdl = "std_logic_vector" if base_tag == 'v' else "unsigned"
            type_name = f"t_{signal_name}_array"
            
            type_def = f"    type {type_name} is array (0 to {depth_val}) of {base_vhdl}({width_val} downto 0);"
            sig_decl = f"    signal {signal_name} : {type_name};"
            return True, sig_decl, type_def
        return False, "", ""

    def _parse_comb_block(self, body):
        lines = ["    process(all)", "    begin"]
        for stmt in body:
            lines.extend(self._stmt_to_vhdl(stmt, indent=8))
        lines.append("    end process;")
        self.processes.append("\n".join(lines))

    def _parse_sync_block(self, node):
        args = node.test.args
        clk_node = args[0]
        rst_node = args[1] if len(args) > 1 else None
        
        # Clock Edge
        if isinstance(clk_node, ast.UnaryOp) and isinstance(clk_node.op, ast.Invert):
            clk_edge, clk_name = "falling_edge", clk_node.operand.id
        else:
            clk_edge, clk_name = "rising_edge", clk_node.id
            
        # Reset Logic
        rst_name, rst_val = "", '1'
        if rst_node:
            if isinstance(rst_node, ast.UnaryOp) and isinstance(rst_node.op, ast.Invert):
                rst_name, rst_val = rst_node.operand.id, '0'
            else:
                rst_name = rst_node.id
        
        reset_logic, clock_logic = [], []
        # Check if first statement is 'if rst:'
        if node.body and isinstance(node.body[0], ast.If):
            reset_logic = [l for s in node.body[0].body for l in self._stmt_to_vhdl(s, 12)]
            clock_logic = [l for s in node.body[0].orelse for l in self._stmt_to_vhdl(s, 12)]
        else:
            clock_logic = [l for s in node.body for l in self._stmt_to_vhdl(s, 12)]

        lines = [f"    process({clk_name}, {rst_name})" if rst_name else f"    process({clk_name})", "    begin"]
        if rst_name:
            lines.append(f"        if {rst_name} = '{rst_val}' then")
            lines.extend(reset_logic)
            lines.append(f"        elsif {clk_edge}({clk_name}) then")
        else:
            lines.append(f"        if {clk_edge}({clk_name}) then")
        lines.extend(clock_logic)
        lines.append("        end if;")
        lines.append("    end process;")
        self.processes.append("\n".join(lines))

    def _parse_instantiation(self, node, call_expr):
        args = call_expr.args
        mod_name = args[0].value if isinstance(args[0], ast.Constant) else args[0].s
        inst_name = args[1].value if isinstance(args[1], ast.Constant) else args[1].s
        
        # Generics from keywords
        gen_map = []
        for kw in call_expr.keywords:
            val = self.expr_parser.parse(kw.value)
            gen_map.append(f"{kw.arg} => {val}")
            
        # Ports from body
        port_map = []
        is_positional = False
        for item in node.body:
            if isinstance(item, ast.If): # Block mapping (in/out)
                for stmt in item.body:
                    if isinstance(stmt, ast.Assign):
                        target = stmt.targets[0].id
                        val = self.expr_parser.parse(stmt.value)
                        port_map.append(f"{target} => {val}")
            elif isinstance(item, ast.Expr): # Positional
                val_node = item.value
                exprs = val_node.elts if isinstance(val_node, ast.Tuple) else [val_node]
                for e in exprs: port_map.append(self.expr_parser.parse(e))
                is_positional = True

        lines = [f"    {inst_name} : entity work.{mod_name}"]
        if gen_map:
            lines.append("    generic map (")
            lines.append(",\n".join([f"        {g}" for g in gen_map]))
            lines.append("    )")
        lines.append("    port map (")
        lines.append(", ".join([f"        {p}" for p in port_map]) if is_positional else ",\n".join([f"        {p}" for p in port_map]))
        lines.append("    );")
        self.instances.append("\n".join(lines))

    def _stmt_to_vhdl(self, stmt, indent=8):
        spaces = " " * indent
        if isinstance(stmt, ast.Assign):
            target = self.expr_parser.parse(stmt.targets[0])
            value = self.expr_parser.parse(stmt.value)
            return [f"{spaces}{target} <= {value};"]
        elif isinstance(stmt, ast.If):
            # Implicit Boolean Conversion
            raw_test = stmt.test
            if isinstance(raw_test, ast.Name): 
                test_str = f"{raw_test.id} = '1'"
            elif isinstance(raw_test, ast.UnaryOp) and isinstance(raw_test.op, ast.Not):
                operand = raw_test.operand
                test_str = f"{operand.id} = '0'" if isinstance(operand, ast.Name) else self.expr_parser.parse(raw_test)
            else:
                test_str = self.expr_parser.parse(raw_test)
                
            lines = [f"{spaces}if {test_str} then"]
            for s in stmt.body: lines.extend(self._stmt_to_vhdl(s, indent+4))
            if stmt.orelse:
                lines.append(f"{spaces}else")
                for s in stmt.orelse: lines.extend(self._stmt_to_vhdl(s, indent+4))
            lines.append(f"{spaces}end if;")
            return lines
        return []

    def _node_to_string(self, node):
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Subscript):
            return f"{self._node_to_string(node.value)}[{self._node_to_string(node.slice)}]"
        if isinstance(node, ast.Constant): return str(node.value)
        return "unknown"

    def _map_type(self, t):
        if t == 'bit': return "STD_LOGIC"
        if 'u[' in t or 'v[' in t or 's[' in t:
            base = "UNSIGNED" if 'u' in t else ("SIGNED" if 's' in t else "STD_LOGIC_VECTOR")
            w = t.split('[')[1].replace(']', '')
            limit = f"{int(w)-1}" if w.isdigit() else f"{w}-1"
            return f"{base}({limit} downto 0)"
        return "STD_LOGIC"

    def generate_vhdl(self):
        lines = ["library IEEE;", "use IEEE.STD_LOGIC_1164.ALL;", "use IEEE.NUMERIC_STD.ALL;", "",
                 f"entity {self.module_name} is"]
        if self.generics:
            lines.append("    Generic (")
            lines.append(";\n".join([f"        {n} : INTEGER := {v}" for n, v in self.generics]))
            lines.append("    );")
        lines.append("    Port (")
        p_strs = []
        for name, d, t in self.ports:
            vhdl_d, vhdl_t = ("IN", "OUT")[d=='o'], self._map_type(t)
            p_strs.append(f"        {name} : {vhdl_d} {vhdl_t}")
        lines.append(";\n".join(p_strs))
        lines.append("    );")
        lines.append(f"end {self.module_name};")
        lines.append("")
        lines.append(f"architecture Behavioral of {self.module_name} is")
        for t in self.type_defs: lines.append(t)
        for s in self.internal_signals: lines.append(s)
        lines.append("begin")
        lines.append("")
        for inst in self.instances: lines.append(inst + "\n")
        for proc in self.processes: lines.append(proc + "\n")
        lines.append("end Behavioral;")
        return "\n".join(lines)

# ==============================================================================
# 3. 前處理器 (Preprocessor) - Regex Magic
# ==============================================================================
def preprocess_litehdl(code):
    # 1. Module -> Def
    code = code.replace("module ", "def ")
    # 2. Block keywords
    code = re.sub(r'^(\s*)in\s*:', r'\1if _In:', code, flags=re.MULTILINE)
    code = re.sub(r'^(\s*)out\s*:', r'\1if _Out:', code, flags=re.MULTILINE)
    code = re.sub(r'^(\s*)comb\s*:', r'\1if _Comb:', code, flags=re.MULTILINE)
    code = re.sub(r'^(\s*)sync\((.*?)\):', r'\1if _Sync(\2):', code, flags=re.MULTILINE)
    # 3. Instantiation: u = Mod(A=1): -> with _Inst("Mod", "u", A=1):
    code = re.sub(r'^(\s*)(\w+)\s*=\s*(\w+)\((.*?)\):', r'\1with _Inst("\3", "\2", \4):', code, flags=re.MULTILINE)
    return code

# ==============================================================================
# 5. 命令列工具介面 (CLI Entry Point)
# ==============================================================================
import argparse
import os

def main():
    # 1. 設定參數解析
    parser = argparse.ArgumentParser(description="LiteHDL to VHDL Compiler")
    parser.add_argument("input_file", help="Path to the LiteHDL source file (.lhd)")
    parser.add_argument("-o", "--output", help="Path to the output VHDL file (default: same as input with .vhd)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print generated VHDL to console")
    
    args = parser.parse_args()

    # 2. 檢查輸入檔案
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found.")
        return

    # 3. 讀取原始碼
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # 4. 編譯過程
    try:
        print(f"Compiling {args.input_file} ...")
        
        # Step A: Preprocessing
        valid_python = preprocess_litehdl(source_code)
        
        # Step B: AST Parsing
        tree = ast.parse(valid_python)
        compiler = LiteHDLParser()
        compiler.visit(tree)
        
        # Step C: VHDL Generation
        vhdl_code = compiler.generate_vhdl()
        
        # 5. 輸出結果
        output_path = args.output
        if not output_path:
            # 預設輸出檔名: input.lhd -> input.vhd
            base_name = os.path.splitext(args.input_file)[0]
            output_path = base_name + ".vhd"
            
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(vhdl_code)
            
        print(f"Success! VHDL generated at: {output_path}")
        
        if args.verbose:
            print("\n--- Generated VHDL Code ---")
            print(vhdl_code)
            print("---------------------------")

    except SyntaxError as e:
        print(f"\n[Syntax Error] Line {e.lineno}: {e.msg}")
        print(f" >> {e.text.strip() if e.text else ''}")
        print("Tip: Check your indentation and colons.")
    except Exception as e:
        print(f"\n[Compiler Error]: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()