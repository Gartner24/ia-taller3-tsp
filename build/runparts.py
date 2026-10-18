"""Exec the code cells of the given part files in order (fast test without Jupyter), then an extra script."""
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
os.chdir("/home/santiago/Documents/university/Inteligencia_Artificial/Tarea_3_TSP")
import matplotlib
matplotlib.use("Agg")
g = {"__name__": "__main__"}
for name in sys.argv[1:]:
    text = (HERE / name).read_text()
    if name.endswith("_scratch.py"):
        exec(compile(text, name, "exec"), g)
        continue
    for block in re.split(r"^#%% ", text, flags=re.M)[1:]:
        kind, _, body = block.partition("\n")
        if kind.strip() == "code" and not body.lstrip().startswith("!"):
            exec(compile(body, name, "exec"), g)
