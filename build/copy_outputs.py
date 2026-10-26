"""Copy outputs from an executed notebook into the rebuilt one after text-only edits (code cells must match).

Extra arguments name the first line of code cells allowed to differ: use it only for edits that leave the
executed path on this machine unchanged (e.g. a Windows-only fallback branch).
"""
import json
import sys
from pathlib import Path

from build import OUT

executed = json.loads(Path(sys.argv[1]).read_text())
allowed = sys.argv[2:]
nb = json.loads(OUT.read_text())
done = [c for c in executed["cells"] if c["cell_type"] == "code"]
todo = [c for c in nb["cells"] if c["cell_type"] == "code"]
assert len(done) == len(todo), (len(done), len(todo))
for old, new in zip(done, todo):
    src = "".join(new["source"])
    if "".join(old["source"]) != src:
        assert any(src.startswith(a) for a in allowed), src[:80]
    new["outputs"], new["execution_count"] = old["outputs"], old["execution_count"]
    new["metadata"] = old["metadata"]
nb["metadata"]["language_info"] = executed["metadata"].get("language_info", {})
OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1))
print(f"outputs copied into {OUT.name}")
