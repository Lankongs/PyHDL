import argparse
import os
import ast

from litehdl.parser.preprocessor import preprocess_litehdl
from litehdl.parser.module_parser import LiteHDLParser
from litehdl.generator.vhdl_generator import VHDLGenerator

def main():
    parser = argparse.ArgumentParser(description="LiteHDL to VHDL Compiler")
    parser.add_argument("input_file")
    parser.add_argument("-o", "--output")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found.")
        return

    with open(args.input_file, "r", encoding="utf-8") as f:
        source_code = f.read()

    try:
        valid_py = preprocess_litehdl(source_code)
        tree = ast.parse(valid_py)

        parser_inst = LiteHDLParser()
        parser_inst.visit(tree)

        generator = VHDLGenerator()
        vhdl = generator.generate(parser_inst)

        output = args.output or args.input_file.replace(".lhd", ".vhd")
        with open(output, "w", encoding="utf-8") as f:
            f.write(vhdl)

        print(f"Success! VHDL generated at: {output}")

        if args.verbose:
            print(vhdl)

    except Exception as e:
        print(f"Compiler Error: {e}")

if __name__ == "__main__":
    main()
