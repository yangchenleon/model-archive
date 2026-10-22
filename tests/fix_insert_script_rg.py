import re
from pathlib import Path

file_path = Path("tests/insert_bandai_rg.py")
content = file_path.read_text(encoding="utf-8")
new_content = re.sub(r'("product_code":\s*)"RG(\d+)"', r'\1"\2"', content)
file_path.write_text(new_content, encoding="utf-8")
print("Updated tests/insert_bandai_rg.py successfully.")
