"""Write the hand exercises of Taller 3 as an Obsidian Excalidraw drawing (docs/ejercicios-a-mano.excalidraw.md)."""
import json
import random
import sys
from pathlib import Path

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "docs" / "ejercicios-a-mano.excalidraw.md"
rng = random.Random(7)
elements = []
BLUE, GREEN, RED, GRAY, BLACK = "#1971c2", "#2f9e44", "#e03131", "#868e96", "#1e1e1e"


def base(kind, x, y, w, h, color=BLACK, **kw):
    e = dict(id=f"e{len(elements)}", type=kind, x=x, y=y, width=w, height=h, angle=0, strokeColor=color,
             backgroundColor="transparent", fillStyle="solid", strokeWidth=2, strokeStyle="solid", roughness=1,
             opacity=100, groupIds=[], frameId=None, roundness=None, seed=rng.randrange(1, 2**31),
             version=1, versionNonce=rng.randrange(1, 2**31), isDeleted=False, boundElements=[], updated=1,
             link=None, locked=False)
    e.update(kw)
    elements.append(e)
    return e


def text(x, y, s, size=18, color=BLACK, mono=False, container=None, align="left"):
    lines = s.split("\n")
    w = max(len(l) for l in lines) * size * (0.6 if mono else 0.55)
    h = len(lines) * size * 1.25
    if container:
        x = container["x"] + (container["width"] - w) / 2
        y = container["y"] + (container["height"] - h) / 2
    e = base("text", x, y, w, h, color, text=s, originalText=s, fontSize=size, fontFamily=3 if mono else 1,
             textAlign=align, verticalAlign="middle", containerId=container["id"] if container else None,
             lineHeight=1.25, autoResize=True)
    if container:
        container["boundElements"].append({"type": "text", "id": e["id"]})
    return e


def box(x, y, w, h, label=None, color=BLACK, fill="transparent", size=18, shape="rectangle"):
    b = base(shape, x, y, w, h, color, backgroundColor=fill, roundness={"type": 3})
    if label is not None:
        text(0, 0, label, size, color, container=b, align="center")
    return b


def line(x1, y1, x2, y2, color=BLACK, arrow=False, dashed=False):
    return base("arrow" if arrow else "line", x1, y1, x2 - x1, y2 - y1, color, points=[[0, 0], [x2 - x1, y2 - y1]],
                startBinding=None, endBinding=None, startArrowhead=None, endArrowhead="arrow" if arrow else None,
                lastCommittedPoint=None, strokeStyle="dashed" if dashed else "solid", roundness={"type": 2})


def section(y, title):
    text(0, y, title, 30, BLUE)
    return y + 55


# ---------------------------------------------------------------- title
text(0, 0, "Taller 3 - TSP: ejercicios a mano", 40, BLACK)
text(0, 60, "Santiago Valencia León (C.C. 1032797866) y Juan Manuel Galvis (C.C. 1004520611). Cada ejercicio también está resuelto en el cuaderno "
            "(bloques B.1, C.4, C.5, C.7, F.1).", 18, GRAY)
y = 130

# ---------------------------------------------------------------- 3.1 / 3.2
y = section(y, "Secciones 3.1 y 3.2. Pesos calculados a mano")
text(0, y, "ATT (att48), ciudades 1 y 5: (6734, 1453) y (3082, 1644)\n"
           "  dx = 3652   dy = 191\n"
           "  r = sqrt((3652^2 + 191^2) / 10) = sqrt(1337358.5) = 1156.44\n"
           "  t = nint(r) = 1156;  t < r  ->  d = t + 1 = 1157      lector: 1157\n\n"
           "EUC_2D (berlin52), ciudades 1 y 2: (565, 575) y (25, 185)\n"
           "  dx = 540   dy = 390\n"
           "  r = sqrt(291600 + 152100) = sqrt(443700) = 666.11\n"
           "  d = floor(r + 0.5) = 666                               lector: 666\n\n"
           "EXPLICIT (gr48), ciudades 1 y 2: se lee de la matriz del archivo = 593", 18, mono=True)
y += 290
text(0, y, "¿Por qué una ruta mejor que el óptimo obliga a revisar? Porque es imposible: el error es nuestro.\n"
           "Se revisa la distancia (por ejemplo el +1 de ATT), que se cobre el regreso al origen, y que la ruta\n"
           "tenga todas las ciudades una sola vez.", 18)
y += 110

# ---------------------------------------------------------------- 5
y = section(y, "Sección 5. Dos rutas parciales que terminan en la misma ciudad")
text(0, y, "Subproblema de att48 con 6 ciudades (óptimo 5715):\n\n"
           "  1 -> 3 -> 5    g = 1159    faltan {2, 4, 6}    mejor ciclo posible = 5879\n"
           "  1 -> 6 -> 5    g = 2676    faltan {2, 3, 4}    mejor ciclo posible = 5715  (óptimo)", 18, mono=True)
y += 120
text(0, y, "Si se fusionan por la última ciudad (5), se queda la de menor g (1 -> 3 -> 5) y se borra la otra,\n"
           "que era la única que llevaba al óptimo. En D.5 la búsqueda con esa regla termina en 5879.\n"
           "Por eso la clave del estado es (última ciudad, pendientes, cerrado).", 18)
y += 110

# ---------------------------------------------------------------- 6
y = section(y, "Sección 6. La cota MST: demostración con nuestras palabras")
text(0, y, "Admisible. Para terminar una ruta hay que ir de la ciudad actual a una pendiente, recorrer todas las\n"
           "pendientes y volver al origen. El tramo por las pendientes es un árbol que las une, así que cuesta al\n"
           "menos MST(U). La primera arista cuesta al menos la conexión más barata ciudad -> U, y la última al\n"
           "menos la más barata U -> origen. Sumando, h nunca supera lo que falta. Solo usamos que el TSP es\n"
           "simétrico; no hace falta la desigualdad triangular.\n\n"
           "Consistente, h(n) <= c(n, n') + h(n'), al ir de v a una pendiente u (U' = U sin u):\n"
           "  - MST(U) <= MST(U') + (arista más barata de u a U'), porque eso ya es un árbol de U.\n"
           "  - min d(v, U) <= d(v, u), porque u está en U.\n"
           "  - min d(U, s) <= min d(U', s), porque U' está dentro de U.\n"
           "  Sumando: h(n) <= d(v, u) + h(n'). En el último paso y al cerrar se cumple con igualdad.\n"
           "  Ejemplo del microcaso: h(A-B) = 10 <= d(B, C) + h(A-B-C) = 2 + 8.", 18)
y += 300

# ---------------------------------------------------------------- 6.2
y = section(y, "Sección 6.2. Microcaso manual")
text(0, y, "D    A  B  C  D  E\n"
           "A    0  4  6  7  3\n"
           "B    4  0  2  5  6\n"
           "C    6  2  0  3  4\n"
           "D    7  5  3  0  2\n"
           "E    3  6  4  2  0", 18, mono=True)
text(260, y, "h = MST(pendientes) + mín(actual -> pendiente) + mín(pendiente -> A)\n"
             "Raíz A: MST{B,C,D,E} = 7, A -> U = 3, U -> A = 3, h = 13", 18)
y += 170
text(0, y, "1. Hijos de la raíz\n\n"
           "   hijo   g   MST pendientes   actual->U   U->A    h    f\n"
           "   A-B    4   {C,D,E} = 5      B-C 2       E-A 3   10   14\n"
           "   A-C    6   {B,D,E} = 7      C-B 2       E-A 3   12   18\n"
           "   A-D    7   {B,C,E} = 6      D-E 2       E-A 3   11   18\n"
           "   A-E    3   {B,C,D} = 5      E-D 2       B-A 4   11   14\n\n"
           "2. Primer empate: A-B y A-E, los dos con f = 14.\n"
           "   Regla: menor f; si empatan, el más profundo; si siguen, el generado primero. Gana A-B.\n\n"
           "3. Un pendiente (A-B-C-D): g = 9, h = d(D,E) + d(E,A) = 2 + 3 = 5, f = 14 (exacta).\n"
           "   Ningún pendiente (A-B-C-D-E): g = 11, h = d(E,A) = 3, f = 14.", 18, mono=True)
y += 360

# A* tree diagram
text(0, y, "Árbol de A* (f de cada nodo)", 22, GREEN)
y += 40
NW, NH = 120, 50
nodes = {}


def node(key, x, yy, label, color=BLACK, fill="transparent"):
    nodes[key] = box(x, yy, NW, NH, label, color, fill, 16, "ellipse")


node("A", 430, y, "A  h=13", GREEN, "#d3f9d8")
lvl = [("B", "B  f=14", GREEN, "#d3f9d8"), ("C", "C  f=18", BLACK, "transparent"),
       ("D", "D  f=18", BLACK, "transparent"), ("E", "E  f=14", RED, "#ffe3e3")]
for i, (k, lab, col, fill) in enumerate(lvl):
    node(k, 100 + i * 220, y + 110, lab, col, fill)
for i, (k, lab, col, fill) in enumerate([("BC", "C  f=14", GREEN, "#d3f9d8"), ("BD", "D  f=18", BLACK, "transparent"),
                                          ("BE", "E  f=21", BLACK, "transparent")]):
    node(k, -60 + i * 150, y + 220, lab, col, fill)
node("BCD", -60, y + 330, "D  f=14", GREEN, "#d3f9d8")
node("BCE", 90, y + 330, "E  f=19")
node("BCDE", -60, y + 440, "E  f=14", GREEN, "#d3f9d8")
node("END", -60, y + 550, "A  costo 14", GREEN, "#b2f2bb")
for a, b in [("A", "B"), ("A", "C"), ("A", "D"), ("A", "E"), ("B", "BC"), ("B", "BD"), ("B", "BE"),
             ("BC", "BCD"), ("BC", "BCE"), ("BCD", "BCDE"), ("BCDE", "END")]:
    p, q = nodes[a], nodes[b]
    line(p["x"] + NW / 2, p["y"] + NH, q["x"] + NW / 2, q["y"], GRAY, arrow=True)
text(900, y + 120, "empate con B: gana B\n(se generó primero)", 16, RED)
text(200, y + 560, "Ciclo A-B-C-D-E-A = 14 = óptimo\n(enumeración de las 24 rutas: C.6)", 16, GREEN)
y += 640

text(0, y, "4. Primeros cambios de límite de RBFS\n\n"
           "   llamada       mejor hijo (f)   alternativa   nuevo límite\n"
           "   raíz, inf     B (14)           E 14          min(inf, 14) = 14\n"
           "   A-B           C (14)           D 18          min(14, 18)  = 14\n"
           "   A-B-C         D (14)           E 19          14\n"
           "   A-B-C-D       E (14)           inf           14\n"
           "   A-B-C-D-E     cierra con 14                  encontrado\n\n"
           "   Ningún hijo supera su límite: RBFS llega al óptimo sin retroceder.", 18, mono=True)
y += 270

text(0, y, "5. Swap contra 2-opt sobre la ruta A-B-C-D-E (costo 14)\n\n"
           "   2-opt (i=0, j=2): quita A-B y C-D, invierte B-C:  A-C-B-D-E = 18\n"
           "      delta = d(A,C) + d(B,D) - d(A,B) - d(C,D) = 6 + 5 - 4 - 3 = +4\n"
           "   swap de B y D:  A-D-C-B-E = 21; cambia solo 2 aristas, es el 2-opt (i=0, j=3)\n\n"
           "   Con 5 ciudades todo swap es un 2-opt. Desde 6 ciudades, si entre las dos posiciones hay\n"
           "   2 o más ciudades, el swap cambia 4 aristas; el 2-opt cambia siempre 2.", 18, mono=True)
y += 230

# 2-opt diagram
text(0, y, "2-opt: quitar dos aristas que se cruzan y reconectar", 22, GREEN)
y += 40
pts = {"A": (40, 0), "B": (240, 0), "C": (240, 160), "D": (40, 160)}
for dx, title, edges in [(0, "antes", [("A", "C"), ("B", "D"), ("A", "D"), ("B", "C")]),
                         (420, "después", [("A", "B"), ("D", "C"), ("A", "D"), ("B", "C")])]:
    text(dx + 110, y, title, 18, GRAY)
    for a, b in edges:
        (x1, y1), (x2, y2) = pts[a], pts[b]
        side = (a, b) in [("A", "D"), ("B", "C")]
        line(dx + x1 + 20, y + 50 + y1 + 20, dx + x2 + 20, y + 50 + y2 + 20,
             GRAY if side else (RED if title == "antes" else GREEN), dashed=side)
    for k, (px, py) in pts.items():
        box(dx + px, y + 50 + py, 40, 40, k, BLACK, "#e7f5ff", 16, "ellipse")
text(780, y + 80, "Se quitan A-C y B-D (se cruzan)\ny se ponen A-B y D-C.\nEl tramo entre ellas se recorre\nal revés.", 16)
y += 300

# ---------------------------------------------------------------- 12.1 OX
y = section(y, "Sección 12.1. Cruce OX a mano")
text(0, y, "parent1 = [B,C,D,E,F,G], parent2 = [E,B,G,C,F,D], segmento: posiciones 2 a 4 (contando desde 1)", 18)
y += 50
CW = 60


def row(yy, label, genes, colors):
    text(0, yy + 15, label, 18)
    for i, (gname, col) in enumerate(zip(genes, colors)):
        box(160 + i * CW, yy, CW - 6, 50, gname, BLACK, col, 20)


row(y - 10, "posición", list("123456"), ["transparent"] * 6)
y += 50
row(y, "parent1", list("BCDEFG"), ["transparent", "#ffec99", "#ffec99", "#ffec99", "transparent", "transparent"])
y += 70
row(y, "parent2", list("EBGCFD"), ["#ffe3e3", "#d3f9d8", "#d3f9d8", "#ffe3e3", "#d3f9d8", "#ffe3e3"])
y += 70
row(y, "hijo", list("GCDEFB"), ["#d3f9d8", "#ffec99", "#ffec99", "#ffec99", "#d3f9d8", "#d3f9d8"])
text(560, y - 140, "1. Copiar C, D, E de parent1 en las mismas posiciones (amarillo).\n"
                   "2. Huecos del hijo, en orden circular desde la posición 5: 5, 6, 1.\n"
                   "3. Leer parent2 en orden circular desde la posición 5: F, D, E, B, G, C.\n"
                   "4. Omitir las que ya están (rojo): D, E, C.\n"
                   "5. Poner las demás (verde) en los huecos: F -> 5, B -> 6, G -> 1.\n\n"
                   "Hijo = [G, C, D, E, F, B]: cada ciudad una vez. Conserva el tramo C-D-E\n"
                   "de parent1 y el orden relativo F, B, G de parent2.", 18)
y += 120

doc = {"type": "excalidraw", "version": 2, "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
       "elements": elements, "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"}, "files": {}}
if OUT.suffix == ".excalidraw":   # plain file for excalidraw.com (File > Open)
    OUT.write_text(json.dumps({**doc, "source": "https://excalidraw.com"}, ensure_ascii=False, indent=1))
    print(f"{len(elements)} elements -> {OUT}")
    sys.exit()
texts = "\n".join(f"{e['text']} ^{e['id']}\n" for e in elements if e["type"] == "text")
OUT.write_text("---\n\nexcalidraw-plugin: parsed\ntags: [excalidraw]\n\n---\n"
               "==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠==\n\n\n"
               "# Excalidraw Data\n\n## Text Elements\n" + texts + "\n%%\n## Drawing\n```json\n"
               + json.dumps(doc, ensure_ascii=False, indent=1) + "\n```\n%%")
print(f"{len(elements)} elements -> {OUT}")
