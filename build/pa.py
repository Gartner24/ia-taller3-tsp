#%% md
**Integrantes:** Santiago Valencia León (código 1032797866) y Juan Manuel Galvis.

**Cómo está organizado nuestro desarrollo.** Dejamos intacto el enunciado (secciones 1 a 17) y desarrollamos todo aquí, en los apartados A a H. Cada apartado empieza con la idea en palabras simples, luego el código y al final lo que encontramos. El código va en inglés y las explicaciones en español.

| Apartado | Qué hay | Secciones del enunciado |
|---|---|---|
| A | Entorno, utilidades comunes, presupuestos y decisiones | 2, 4, 14.1 |
| B | Lectura de TSPLIB, fichas, pesos a mano y costo de rutas | 3, 3.1, 3.2 |
| C | Lectura crítica de TSP Solve, modelo de búsqueda, MST, microcaso manual | 1, 5, 6, 6.1, 6.2 |
| D | A* y RBFS: implementación, trazas, validación e interrupciones | 7, 8, 8.1, 13 |
| E | 2-opt, Hill Climbing y Simulated Annealing | 9, 10, 11 |
| F | Algoritmo genético: OX, inversión, diversidad | 12, 12.1 |
| G | Protocolo, calibración, escalas A y B, tablas, gráficas y animación | 11.1, 14, 15 |
| H | Las 12 preguntas, conclusiones, referencias y bitácora | 16 |
#%% code
import collections
import heapq
import itertools
import math
import multiprocessing as mp
import os
import platform
import random
import statistics
import sys
import time
import tracemalloc
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tsplib95
from IPython.display import Image, display

DATA = Path("data")
INF = math.inf
plt.rcParams.update({"figure.dpi": 100, "axes.grid": True, "grid.alpha": 0.3})
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)


def parallel_map(func, jobs, processes=None):
    """Run func(*job) for every job; fork workers when the platform allows it, same results either way."""
    jobs = list(jobs)
    try:
        ctx = mp.get_context("fork")
    except ValueError:
        return [func(*job) for job in jobs]
    with ctx.Pool(processes) as pool:
        return pool.starmap(func, jobs, chunksize=1)


def cpu_name():
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


env = {
    "CPU": f"{cpu_name()} ({os.cpu_count()} hilos)",
    "Sistema operativo": platform.platform(),
    "Python": sys.version.split()[0],
    "Entorno": "Jupyter (kernel local, .venv)",
    "numpy": np.__version__,
    "pandas": pd.__version__,
    "matplotlib": matplotlib.__version__,
    "tsplib95": tsplib95.__version__,
}
display(pd.Series(env, name="valor").to_frame())
#%% md
### A.1 Presupuestos, medición y contrato de salida

Todas las ejecuciones pasan por las mismas dos piezas:

- **`Meter`** mide tiempo y memoria y corta la ejecución cuando se acaba el presupuesto. El tiempo es `time.perf_counter` y no incluye la carga de datos ni las gráficas. La memoria es la **memoria adicional del solver**: el pico de `tracemalloc` menos lo que ya estaba asignado al empezar. `tracemalloc` solo ve las asignaciones de Python, no la memoria total del proceso; esa la reportamos aparte (al final de G). Se revisa cada 256 expansiones (A*, RBFS) o cada 1024 evaluaciones (HC, SA, GA). Medir con `tracemalloc` hace todo más lento; en G medimos cuánto.
- **`RunResult`** es el contrato de salida de la sección 4: instancia, algoritmo, parámetros, semilla, ruta o ausencia de ruta, costo, gap, tiempo, memoria, contadores, motivo de parada y estado de optimalidad.

Motivos de parada que usamos: `GOAL` (A*/RBFS cerraron un ciclo), `EXHAUSTED`, `LOCAL_OPTIMUM` (HC), `TMIN` (SA se enfrió), y las interrupciones `TIME`, `EXPANSIONS`, `MEMORY`, `EVALUATIONS`. Estados de optimalidad: `OPTIMAL` (solo A* y RBFS terminados), `NOT_CERTIFIED` (hay ruta pero no prueba) y `NO_TOUR`.
#%% code
EXACT_BUDGET = dict(seconds=30.0, expansions=100_000, memory_mib=256.0)
INTERRUPTIONS = {"TIME", "EXPANSIONS", "MEMORY", "EVALUATIONS"}


class Interrupted(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class Meter:
    """Wall time plus the solver's extra Python memory (tracemalloc peak over the starting baseline)."""

    def __init__(self, seconds=INF, expansions=None, evaluations=None, memory_mib=None):
        self.seconds, self.expansions, self.evaluations, self.memory_mib = seconds, expansions, evaluations, memory_mib
        self._own_tracing = not tracemalloc.is_tracing()
        if self._own_tracing:
            tracemalloc.start()
        tracemalloc.reset_peak()
        self.base = tracemalloc.get_traced_memory()[0]
        self.t0 = time.perf_counter()

    def elapsed(self):
        return time.perf_counter() - self.t0

    def peak_mib(self):
        return max(0, tracemalloc.get_traced_memory()[1] - self.base) / 2**20

    def check_search(self, expanded):
        if self.expansions is not None and expanded >= self.expansions:
            raise Interrupted("EXPANSIONS")
        if self.elapsed() >= self.seconds:
            raise Interrupted("TIME")
        if self.memory_mib is not None and expanded % 256 == 0 and self.peak_mib() >= self.memory_mib:
            raise Interrupted("MEMORY")

    def out_of_evaluations(self, evaluations, needed=1):
        """True when `needed` more evaluations would exceed the budget, or time ran out (checked every 1024)."""
        if self.evaluations is not None and evaluations + needed > self.evaluations:
            self.reason = "EVALUATIONS"
            return True
        if evaluations % 1024 == 0 and self.elapsed() >= self.seconds:
            self.reason = "TIME"
            return True
        return False

    def finish(self):
        elapsed, peak = self.elapsed(), self.peak_mib()
        if self._own_tracing:
            tracemalloc.stop()
        return elapsed, peak


@dataclass
class RunResult:
    instance: str
    subset: str
    algorithm: str
    seed: object
    parameters: dict
    tour: object
    cost: object
    gap_percent: object
    elapsed_seconds: float
    peak_memory_mib: float
    stop_reason: str
    optimality_status: str
    candidate_evaluations: object = None
    expanded: object = None
    generated: object = None
    mst_calls: object = None
    frontier_peak: object = None
    stale: object = None
    regenerations: object = None
    calls: object = None
    max_depth: object = None
    history: list = field(default_factory=list, repr=False)
    extra: dict = field(default_factory=dict, repr=False)

    def row(self):
        d = {k: v for k, v in self.__dict__.items() if k not in ("history", "extra", "tour")}
        d["parameters"] = ", ".join(f"{k}={v}" for k, v in self.parameters.items())
        return d


def gap_percent(cost, reference):
    if cost is None or reference is None:
        return None
    return 100.0 * (cost - reference) / reference
