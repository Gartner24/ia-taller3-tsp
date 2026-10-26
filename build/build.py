"""Assemble the delivered notebook: the teacher's cells untouched, our cells inserted under section 18.

Part files use '#%% md' and '#%% code' markers. Writes the notebook and a code-only script for fast tests.
"""
import copy
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = Path("/home/santiago/Documents/university/Inteligencia_Artificial/Tarea_3_TSP")
TEACHER = ROOT / "material_profesor" / "Taller_IA_TSP_AStar_MST_HC_SA_GA_RBFS.ipynb"
OUT = ROOT / "Taller_IA_TSP_AStar_MST_HC_SA_GA_RBFS.ipynb"

# Section 18 letter -> part file
PARTS = {"A": "pa.py", "B": "pb.py", "C": "pc.py", "D": "pd.py", "E": "pe.py",
         "F": "pf.py", "G": "pg.py", "H": "ph.py"}
AFTER_CHECKLIST = "pz.py"


def read_part(name):
    path = HERE / name
    if not path.exists():
        return []
    cells = []
    for block in re.split(r"^#%% ", path.read_text(), flags=re.M)[1:]:
        kind, _, body = block.partition("\n")
        body = body.strip("\n")
        if kind.strip() == "md":
            cells.append({"cell_type": "markdown", "metadata": {}, "source": body})
        else:
            cells.append({"cell_type": "code", "metadata": {}, "source": body,
                          "execution_count": None, "outputs": []})
    return cells


def split_section_18(cell):
    """Split the teacher's section-18 cell at its '### X.' headings without changing any text."""
    text = "".join(cell["source"])
    pieces = re.split(r"(?=^### [A-H]\. )", text, flags=re.M)
    assert "".join(pieces) == text
    out = []
    for piece in pieces:
        c = copy.deepcopy(cell)
        c["source"] = piece.rstrip("\n")
        out.append(c)
    return out


def main():
    nb = json.loads(TEACHER.read_text())
    cells = []
    for cell in nb["cells"]:
        src = "".join(cell["source"])
        if src.startswith("## 18."):
            for piece in split_section_18(cell):
                cells.append(piece)
                m = re.match(r"### ([A-H])\. ", piece["source"])
                if m:
                    cells.extend(read_part(PARTS[m.group(1)]))
        elif src.startswith("## 19."):
            cells.append(cell)
            cells.extend(read_part(AFTER_CHECKLIST))
        else:
            cells.append(cell)
    for c in cells:
        c.pop("id", None)
    nb["cells"] = cells
    # generic kernel so it opens on any machine (Windows, Colab) without our local kernel
    nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3 (ipykernel)", "language": "python"}
    nb["nbformat"], nb["nbformat_minor"] = 4, 4
    OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1))
    sources = ["".join(c["source"]) for c in cells if c["cell_type"] == "code"]
    code = [s for s in sources if not s.startswith("!")]
    (HERE / "all_code.py").write_text("\n\n".join(code) + "\n")
    print(f"{len(cells)} cells -> {OUT.name}")


if __name__ == "__main__":
    sys.exit(main())
