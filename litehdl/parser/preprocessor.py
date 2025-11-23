import re

def preprocess_litehdl(code):
    code = code.replace("module ", "def ")
    code = re.sub(r'^(\s*)in\s*:', r'\1if _In:', code, flags=re.MULTILINE)
    code = re.sub(r'^(\s*)out\s*:', r'\1if _Out:', code, flags=re.MULTILINE)
    code = re.sub(r'^(\s*)comb\s*:', r'\1if _Comb:', code, flags=re.MULTILINE)
    code = re.sub(r'^(\s*)sync\((.*?)\):', r'\1if _Sync(\2):', code, flags=re.MULTILINE)
    code = re.sub(r'^(\s*)(\w+)\s*=\s*(\w+)\((.*?)\):',
                  r'\1with _Inst("\3", "\2", \4):',
                  code, flags=re.MULTILINE)
    return code
