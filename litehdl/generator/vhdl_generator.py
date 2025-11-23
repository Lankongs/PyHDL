class VHDLGenerator:
    def generate(self, parser):
        lines = ["library IEEE;", "use IEEE.STD_LOGIC_1164.ALL;", "use IEEE.NUMERIC_STD.ALL;", "",
                 f"entity {parser.module_name} is"]
        if parser.generics:
            lines.append("    Generic (")
            lines.append(";\n".join([f"        {n} : INTEGER := {v}" for n, v in parser.generics]))
            lines.append("    );")
        lines.append("    Port (")
        p_strs = []
        for name, d, t in parser.ports:
            vhdl_d, vhdl_t = ("IN", "OUT")[d=='o'], parser._map_type(t)
            p_strs.append(f"        {name} : {vhdl_d} {vhdl_t}")
        lines.append(";\n".join(p_strs))
        lines.append("    );")
        lines.append(f"end {parser.module_name};")
        lines.append("")
        lines.append(f"architecture Behavioral of {parser.module_name} is")
        for t in parser.type_defs: lines.append(t)
        for s in parser.internal_signals: lines.append(s)
        lines.append("begin")
        lines.append("")
        for inst in parser.instances: lines.append(inst + "\n")
        for proc in parser.processes: lines.append(proc + "\n")
        lines.append("end Behavioral;")
        return "\n".join(lines)
