"""Split a code file at its '#%% code' markers into name_1.py, name_2.py, ..."""
import sys
from pathlib import Path

HERE = Path(__file__).parent
src = HERE / sys.argv[1]
blocks = src.read_text().split("#%% code\n")[1:]
for i, b in enumerate(blocks, 1):
    (HERE / f"{src.stem}_{i}.py").write_text("#%% code\n" + b)
print(len(blocks), "blocks")
