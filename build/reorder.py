"""Move each of our blocks under the teacher section it answers, behind a 'SOLUCIÓN' marker.

Runs on the notebook written by build.py (or an executed copy): teacher text stays unchanged,
section 16 is split per question and each answer from H.2 goes under its question.
"""
import copy
import json
import re
import sys
from pathlib import Path

from build import OUT, TEACHER, split_section_18


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text}


def marker(title):
    return md(f"---\n### SOLUCIÓN · {title}")


HOW_TO_READ = """**Cómo leer este cuaderno.** El enunciado del profesor está completo y sin cambios. Nuestra solución \
está debajo de cada sección, siempre después de una celda que dice **SOLUCIÓN · sección N**, y llega hasta \
donde empieza la siguiente sección del enunciado. Las 12 preguntas de la sección 16 tienen su respuesta \
justo debajo de cada pregunta.

Integrantes: Santiago Valencia León (C.C. 1032797866) y Juan Manuel Galvis (C.C. 1004520611)."""

A_INTRO = """**Integrantes:** Santiago Valencia León (C.C. 1032797866) y Juan Manuel Galvis (C.C. 1004520611).

**Dónde está cada apartado.** Para que cada respuesta quede junto a su enunciado, desarrollamos los \
apartados A a H debajo de las secciones que responden, cada uno detrás de una celda **SOLUCIÓN**. Los \
nombres de los bloques (B.2, D.4, G.5...) se conservan porque las respuestas y la lista de entrega los citan. \
El código va en inglés y las explicaciones en español.

| Apartado | Qué hay | Dónde está |
|---|---|---|
| A | Entorno, utilidades comunes, presupuestos y contrato de salida | Soluciones de 3.1 (entorno) y 4 (A.1) |
| B | Lectura de TSPLIB, fichas, pesos a mano, costo y pruebas de rutas | Soluciones de 3.1, 3.2 y 13 (B.3) |
| C | Lectura crítica, modelo de búsqueda, MST, admisibilidad, microcaso | Soluciones de 1, 5, 6, 6.1, 6.2 y 13 (C.8) |
| D | A\\* y RBFS: implementación, trazas, validación, interrupciones | Soluciones de 7, 8, 8.1 y 13 (D.6) |
| E | 2-opt, Hill Climbing y Simulated Annealing | Soluciones de 9, 10 y 11 |
| F | Algoritmo genético: OX, inversión, diversidad | Solución de 12 y 12.1 |
| G | Protocolo, calibración, escalas A y B, tablas, gráficas, animación | Soluciones de 11.1, 14, 14.1, 15.1 y 15.2 |
| H | Las 12 preguntas, conclusiones, referencias y bitácora | Sección 16 (preguntas) y aquí (H.3 a H.5) |

**Presupuestos.** Exactos (A\\* y RBFS): 30 s, 100 000 expansiones o 256 MiB, lo que ocurra primero (A.1). \
Métodos locales: 30 000 evaluaciones y 30 s (presupuesto del enunciado) y, además, 200 000 evaluaciones y \
120 s como presupuesto principal, con el mismo valor para los cuatro métodos y todas las instancias. La razón \
del cambio está en G.1; la calibración y los experimentos de HC y SA están en G.2 y G.5.

**Políticas de desempate.** A\\* y RBFS: menor $f$, luego el nodo más profundo, luego el orden de generación. \
HC: solo acepta mejoras estrictas, y entre movimientos igual de buenos se queda con el primero que encontró. \
SA: acepta siempre $\\Delta \\le 0$. GA: en el torneo gana el primer individuo muestreado si hay empate. \
Calibración: si dos configuraciones empatan, gana la primera de la lista (G.2).

**Ayuda externa.** La declaramos en las referencias (H.4, referencia 7)."""

POINTERS = {
    "B": "Desarrollado en las soluciones de las secciones 3.1, 3.2 y 13 (bloques B, B.1 a B.4).",
    "C": "Desarrollado en las soluciones de las secciones 1, 5, 6, 6.1, 6.2 y 13 (bloques C.1 a C.8).",
    "D": "Desarrollado en las soluciones de las secciones 7, 8, 8.1 y 13 (bloques D.1 a D.9).",
    "E": "Desarrollado en las soluciones de las secciones 9, 10 y 11 (bloques E.1 a E.4).",
    "F": "Desarrollado en la solución de las secciones 12 y 12.1 (bloques F.1 y F.2).",
    "G": "Desarrollado en las soluciones de las secciones 11.1, 14, 14.1, 15.1 y 15.2 (bloques G.1 a G.8).",
    "H": "Las 12 preguntas están respondidas debajo de cada pregunta en la sección 16. Aquí quedan las "
         "conclusiones, las referencias y la bitácora.",
}

VALIDATION = """Cada fila de la tabla de arriba tiene su prueba. Las de ruta, MST, heurística, RBFS y presupuesto \
están aquí abajo; las demás están junto al algoritmo que prueban, porque usan su código.

| Elemento | Dónde está la prueba |
|---|---|
| Ruta | B.3, aquí abajo |
| Costo | B.2, solución de 3.1 |
| MST y heurística | C.8, aquí abajo |
| A* contra enumeración | D.4, solución de 8.1 |
| A* sin fusionar por ciudad final | C.7 (solución de 6.2) y D.5 (solución de 8.1) |
| RBFS: un hijo, empate, límite, agotamiento | D.6, aquí abajo |
| HC: óptimo local | E.2, solución de 10 |
| SA: mejor distinta de la actual | E.4, solución de 11 |
| OX e inversión | F.1 y F.2, solución de 12 y 12.1 |
| Presupuesto: interrupción forzada | D.6, aquí abajo (y F.2 para el GA) |"""

RULES = """**Dónde se ve cada objetivo.**

| Objetivo | Dónde está |
|---|---|
| Rutas parciales y permutaciones completas | C.2 (solución de 5) y E.1 (solución de 9) |
| Heurística MST y su justificación | C.3, C.4 y C.8 (soluciones de 6, 6.1 y 13) |
| Los cinco algoritmos | A\\* (D.1), RBFS (D.2), HC (E.2), SA (E.4), GA (F.2) |
| Experimentos reproducibles; solución válida, mejor observada y óptimo demostrado | A.1 (estados `OPTIMAL`, `NOT_CERTIFIED`, `NO_TOUR`) y G.1 a G.4 |
| Convergencia, gap, memoria y costo | G.4 a G.7 y las preguntas de la sección 16 |

**Cómo cumplimos las reglas.**

- **Los cinco algoritmos son nuestros**, escritos desde cero en este cuaderno. No usamos solvers, SimpleAI, DEAP ni \
bibliotecas parecidas.
- **El MST es nuestro, con Prim** (C.3). También escribimos un Kruskal, pero solo para comprobar que Prim da el \
árbol correcto (C.8).
- **Herramientas:** `numpy` para arreglos, `pandas` para tablas, `matplotlib` para gráficas, `time` y \
`tracemalloc` para medir, y `tsplib95` solo para leer los archivos y obtener los pesos oficiales (B). Las \
versiones están en la tabla de entorno, al comienzo de la solución de 3.1.
- **Idioma:** el código y los identificadores van en inglés (`astar`, `hill_climbing`, `RunResult`); las \
explicaciones y conclusiones, en español.
- **Ayuda externa:** usamos Claude (Anthropic) como herramienta de apoyo para consultar conceptos y \
documentación, y como apoyo en la implementación, la depuración y la redacción. Consultamos el cuaderno de TSP de \
Peter Norvig como ejemplo de 2-opt y de dibujo de rutas, sin copiar su código. Están en las referencias (H.4)."""

# teacher cell (source prefix) -> (marker title, our blocks or literal markdown)
PLACEMENT = [
    ("## 1. ", "sección 1", ["C.1"]),
    ("## 2. ", "sección 2", [md(RULES)]),
    ("!pip install", "sección 3.1", ["A0c", "B0", "B.2", "B.4"]),
    ("### 3.2. ", "sección 3.2", ["B.1"]),
    ("## 4. ", "sección 4", ["A.1"]),
    ("## 5. ", "sección 5", ["C.2", md("La actividad de las dos rutas parciales (C.7) usa el oráculo exacto de "
                                       "la sección 6.2, así que está al final de la solución de 6.2.")]),
    ("## 6. ", "sección 6", ["C.4"]),
    ("### 6.1. ", "sección 6.1", ["C.3", md("El experimento opcional de la caché necesita A\\*, así que está en la "
                                         "solución de la sección 7 (D.7).")]),
    ("### 6.2. ", "sección 6.2", ["C.5", "C.6", "C.7"]),
    ("## 7. ", "sección 7", ["D.1", "D.7", "D.9", md("La validación exacta (D.4), las reglas de fusión (D.5) y la "
                                             "ampliación con gr17 y burma14 (D.8) corren A\\* y RBFS juntos, así "
                                             "que están en la solución de 8.1.")]),
    ("## 8. ", "sección 8", ["D.2"]),
    ("### 8.1. ", "sección 8.1", ["D.3", "D.4", "D.5", "D.8"]),
    ("## 9. ", "sección 9", ["E.1"]),
    ("## 10. ", "sección 10", ["E.2", "E.3"]),
    ("## 11. ", "sección 11", ["E.4", md("La calibración de $\\alpha$ y $p_0$ que pide el diseño está en la "
                                        "solución de la sección 14 (G.2), junto con la del GA.")]),
    ("### 11.1. ", "sección 11.1", [md("Las respuestas usan la comparación por pares de G.5 (solución de la "
                                       "sección 14) y la figura 5 (solución de 15.2), porque necesitan los "
                                       "experimentos completos."), "G.5a"]),
    ("### 12.1. ", "secciones 12 y 12.1", ["F.1", "F.2"]),
    ("## 13. ", "sección 13", [md(VALIDATION), "B.3", "C.8", "D.6"]),
    ("## 14. ", "sección 14", ["G.1", "G.2", "G.3", "G.4", "G.5"]),
    ("### 14.1. ", "sección 14.1", ["G.7"]),
    ("### 15.1. ", "sección 15.1", ["G.4t"]),
    ("### 15.2. ", "sección 15.2", ["G.6", "G.8"]),
]


def src(cell):
    return "".join(cell["source"])


def group_blocks(cells, teacher_sources):
    """Our cells grouped by the '### X.n' heading that starts them; teacher cells are left out."""
    blocks, current = {}, None
    for cell in cells:
        s = src(cell)
        if s in teacher_sources:
            m = re.match(r"### ([A-H])\. ", s)
            current = f"{m.group(1)}0" if m else ("Z" if s.startswith("## 19.") else None)
            continue
        m = re.match(r"### ([A-H]\.\d+) ", s)
        if m:
            current = m.group(1)
        elif s.startswith("**Tablas por instancia"):
            current = "G.4t"
        elif s.startswith("**Lo que encontramos (G.5)"):
            current = "G.5a"
        elif s.startswith("import collections"):
            current = "A0c"
        assert current, s[:80]
        blocks.setdefault(current, []).append(cell)
    return blocks


def demote(cell):
    c = copy.deepcopy(cell)
    if c["cell_type"] == "markdown":
        c["source"] = re.sub(r"^### ", "#### ", src(c))
    return c


def split_questions(cell):
    """Teacher section 16 -> header, one cell per question, closing paragraph (text unchanged)."""
    text = src(cell)
    pieces = re.split(r"(?=^\d+\. )|(?=^Cada conclusión)", text, flags=re.M)
    assert "".join(pieces) == text and len(pieces) == 14, len(pieces)
    out = []
    for piece in pieces:
        c = copy.deepcopy(cell)
        c["source"] = piece.rstrip("\n")
        out.append(c)
    return out


def split_answers(h2):
    """H.2 -> {question number: answer text without the restated bold question}."""
    text = src(h2[0])
    parts = re.split(r"^\*\*(\d+)\. .*?\*\*[ \n]?", text, flags=re.M)
    answers = {int(parts[i]): parts[i + 1].strip() for i in range(1, len(parts), 2)}
    assert sorted(answers) == list(range(1, 13))
    return answers


def main():
    nb = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else OUT).read_text())
    teacher = json.loads(TEACHER.read_text())["cells"]
    teacher_sources = set()
    for cell in teacher:
        pieces = split_section_18(cell) if src(cell).startswith("## 18.") else [cell]
        teacher_sources.update(src(p) for p in pieces)

    blocks = group_blocks(nb["cells"], teacher_sources)
    used = set()

    def take(name):
        assert name not in used, name
        used.add(name)
        return [demote(c) for c in blocks[name]]

    cells = []
    for cell in nb["cells"]:
        s = src(cell)
        if s not in teacher_sources:
            continue
        if s.startswith("## 16. "):
            pieces = split_questions(cell)
            answers = split_answers(blocks["H.2"])
            used.add("H.2")
            cells.append(pieces[0])
            cells += [marker("tabla de apoyo para las preguntas")] + take("H.1")
            for n, piece in enumerate(pieces[1:13], start=1):
                cells += [piece, marker(f"pregunta {n}"), md(answers[n])]
            cells.append(pieces[13])
            continue
        cells.append(cell)
        if s.startswith("# Taller de IA"):
            cells.append(md(HOW_TO_READ))
        m = re.match(r"### ([A-H])\. ", s)
        if m:
            letter = m.group(1)
            if letter == "A":
                used.add("A0")
                cells.append(md(A_INTRO))
            else:
                cells.append(md(POINTERS[letter]))
            if letter == "H":
                cells += take("H.3") + take("H.4") + take("H.5")
        if s.startswith("## 19."):
            cells += take("Z")
        for prefix, title, items in PLACEMENT:
            if s.startswith(prefix):
                cells.append(marker(title))
                for item in items:
                    cells += take(item) if isinstance(item, str) else [item]

    missing = set(blocks) - used
    assert not missing, missing
    for c in cells:
        c.pop("id", None)
    nb["cells"] = cells
    OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1))
    print(f"{len(cells)} cells -> {OUT.name}")


if __name__ == "__main__":
    sys.exit(main())
