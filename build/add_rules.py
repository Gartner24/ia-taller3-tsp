"""One-off: insert the section-2 solution into an already reordered notebook (same cells reorder.py now adds)."""
import json
import sys
from pathlib import Path

from reorder import RULES, marker, md, src

path = Path(sys.argv[1])
nb = json.loads(path.read_text())
cells = nb["cells"]
assert not any("SOLUCIÓN · sección 2" in src(c) for c in cells)
i = next(k for k, c in enumerate(cells) if src(c).startswith("## 2. "))
cells[i + 1:i + 1] = [marker("sección 2"), md(RULES)]
path.write_text(json.dumps(nb, ensure_ascii=False, indent=1))
print(f"inserted after cell {i} in {path.name}")
