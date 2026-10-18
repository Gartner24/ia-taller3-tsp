"""Join the pieces of a part file: pX.py = concatenation of the listed files, in order."""
import sys
from pathlib import Path

HERE = Path(__file__).parent
out, *pieces = sys.argv[1:]
(HERE / out).write_text("\n".join((HERE / p).read_text().rstrip("\n") for p in pieces) + "\n")
print(out, "<-", pieces)
