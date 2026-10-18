#%% md
### G.1 Presupuesto y configuraciones

**Por qué cambiamos el presupuesto.** La sección 14 propone 30 000 evaluaciones y 30 s por ejecución, y permite ajustarlos si se hace antes de la comparación final y para todos por igual. En E.2 medimos que HC de una ruta necesita entre 49 681 (gr48) y 98 891 (brazil58) evaluaciones para llegar a su **primer** óptimo local. Con 30 000 se cortaría a mitad del primer descenso, y la comparación HC contra SA mediría sobre todo el corte, no los algoritmos. Por eso:

- **Presupuesto principal (uniforme):** 200 000 evaluaciones y 120 s por ejecución, para los cuatro métodos locales. Antes de fijarlo cronometramos una corrida de cada método: HC tarda menos de 1 s, SA entre 3 y 6 s y GA unos 55 s, porque cada evaluación del GA calcula una ruta completa y además copia y cruza cromosomas. Con 60 s el GA se cortaba por tiempo en gr48; con 120 s ninguna corrida debería cortarse por tiempo.
- **Presupuesto del enunciado:** 30 000 evaluaciones y 30 s. Lo corremos **también**, como ejecuciones reales y no como un punto leído de la curva. SA reparte su enfriamiento según el presupuesto, así que leer su curva larga en 30 000 lo dejaría todavía caliente y lo perjudicaría.
- **Exactos:** el presupuesto de A.1 (30 s, 100 000 expansiones o 256 MiB), en las dos escalas.
- **Subinstancias (escala A):** los métodos locales usan el presupuesto del enunciado. Con $k \le 12$ alcanza de sobra.

**Semillas y generadores.** La ruta inicial de cada (instancia, semilla) sale de su propio generador (`initial_tour`, E.1), y HC de una ruta, HC con reinicios y SA arrancan de **la misma** ruta (11.1). Cada algoritmo tiene otro generador, con nombre `instancia-subconjunto-algoritmo-semilla`, así que cambiar un algoritmo no cambia las rutas iniciales de los demás. El GA genera su propia población.

**Corridas en paralelo.** Las ejecuciones son independientes y se reparten entre 8 procesos con `parallel_map`. Cada una mide su propio tiempo, que sale un poco más alto que en una máquina sin carga. Lo tenemos en cuenta al comparar tiempos, y en G.7 medimos aparte cuánto pesa `tracemalloc`.
#%% code
import resource
from matplotlib import animation

BUDGET_TEACHER = dict(evaluations=30_000, seconds=30.0)
BUDGET_MAIN = dict(evaluations=200_000, seconds=120.0)
BUDGETS = {30_000: BUDGET_TEACHER, 200_000: BUDGET_MAIN}
LOCAL = ["HC una ruta", "HC reinicios", "SA", "GA básico"]
SEEDS = range(10)
WORKERS = 8
FIG_DIR = Path("figuras")
FIG_DIR.mkdir(exist_ok=True)


def run_local(name, k, algorithm, seed, budget, params, reference=None):
    """One run of a local method on the full instance (k=None) or on its first-k subproblem."""
    inst = INSTANCES[name] if k is None else INSTANCES[name].subproblem(k)
    rng = random.Random(f"{inst.name}-{inst.subset}-{algorithm}-{seed}")
    if algorithm == "GA básico":
        res = genetic_algorithm(inst, budget, rng, **params)
    elif algorithm == "SA":
        res = simulated_annealing(inst, initial_tour(inst, seed), budget, rng, **params)
    else:
        res = hill_climbing(inst, initial_tour(inst, seed), budget, rng, restarts=algorithm == "HC reinicios")
    res.seed = seed
    if reference is not None:
        res.gap_percent = gap_percent(res.cost, reference)
    return res


def table(results, **extra):
    return pd.DataFrame([{**r.row(), **extra} for r in results])
#%% md
### G.2 Calibración separada (sección 11.1 y días 9 a 11 del plan)

Calibramos en las instancias de **ampliación** eil51 y gr17, con las semillas 100 a 104, para no elegir parámetros mirando las instancias de prueba ni las semillas 0 a 9. Usamos el presupuesto principal.

- SA: $\alpha \in \{0.90, 0.97, 0.995\}$ y $p_0 \in \{0.5, 0.8\}$.
- GA: población $\{40, 80\}$, $p_m \in \{0.1, 0.3\}$ y élite $\{1, 2\}$, con $p_c = 0.9$ y torneo de 3.

Se congela la configuración de menor gap medio entre las dos instancias. En empate gana la que aparece primero en la lista.
#%% code
CALIBRATION, CAL_SEEDS = ["eil51", "gr17"], range(100, 105)
SA_GRID = [dict(alpha=a, p0=p) for a in (0.90, 0.97, 0.995) for p in (0.5, 0.8)]
GA_GRID = [dict(pop_size=pop, elite=e, pc=0.9, pm=pm, tsize=3) for pop in (40, 80) for pm in (0.1, 0.3) for e in (1, 2)]
cal_jobs = [(nm, None, alg, s, BUDGET_MAIN, p) for alg, grid in (("SA", SA_GRID), ("GA básico", GA_GRID))
            for p in grid for nm in CALIBRATION for s in CAL_SEEDS]
cal_runs = parallel_map(run_local, cal_jobs, WORKERS)
label = lambda p: ", ".join(f"{k}={v}" for k, v in p.items() if k not in ("pc", "tsize"))
cal = pd.DataFrame([{"algoritmo": r.algorithm, "config": label(job[5]), "instancia": r.instance, "gap": r.gap_percent,
                     "s": r.elapsed_seconds, "parada": r.stop_reason} for job, r in zip(cal_jobs, cal_runs)])
assert (cal["gap"] >= 0).all()
cal_summary = (cal.pivot_table(index=["algoritmo", "config"], columns="instancia", values="gap", aggfunc="mean", sort=False)
               .assign(**{"gap medio": lambda d: d.mean(axis=1)}).round(2))
cal_summary["s mediano"] = cal.groupby(["algoritmo", "config"], sort=False)["s"].median().round(1)
display(cal_summary)
FROZEN = {"HC una ruta": {}, "HC reinicios": {}}
for alg, grid in (("SA", SA_GRID), ("GA básico", GA_GRID)):
    gaps = cal_summary.loc[alg, "gap medio"]
    FROZEN[alg] = grid[[label(p) for p in grid].index(gaps.idxmin())]
print("configuraciones congeladas:", FROZEN)
print("motivos de parada en calibración:", cal["parada"].value_counts().to_dict())
#%% md
**Lo que encontramos (G.2):**

- **SA:** gana $\alpha = 0.90$ con $p_0 = 0.8$, aunque por poco: las seis configuraciones quedan entre 1.2 % y 1.8 % de gap medio. Con $\alpha = 0.90$ hay menos niveles de temperatura (66) y cada uno recibe más propuestas, así que en cada nivel la ruta alcanza a estabilizarse antes de enfriar. gr17 no ayuda a decidir: las 30 corridas de SA llegan a su óptimo (gap 0). Todo el desempate lo hace eil51. Es una limitación de la calibración: con dos instancias y 5 semillas, diferencias de unas décimas no son concluyentes.
- **GA:** gana población 80, élite 2 y $p_m = 0.3$ (2.91 % de gap medio). En las dos poblaciones, la mutación alta ($p_m = 0.3$) da mejor resultado que la baja: la diversidad se pierde rápido (lo vimos en F) y la mutación es lo único que trae aristas nuevas.
- Ninguna corrida de calibración se cortó por tiempo: SA siempre termina al enfriarse (`TMIN`) y GA al agotar las evaluaciones.
#%% md
### G.3 Escala A: subinstancias de 6 a 12 ciudades

Para cada instancia obligatoria y $k \in \{6, 8, 10, 12\}$ tomamos los primeros $k$ identificadores (la tabla muestra cuáles) con sus pesos originales.

- **A\***: tres repeticiones para el tiempo (reportamos la mediana) y una corrida con otro origen, la última ciudad, que debe dar el mismo costo.
- **RBFS**: tres repeticiones si la primera tarda menos de 2 s; si tarda más, una sola. Además, una corrida de **auditoría** (`audit=True`) para contar regeneraciones. Esa corrida no se usa para medir tiempo ni memoria, porque el registro de auditoría ocupa memoria (D.2).
- El óptimo certificado es el de A\*, y lo comparamos otra vez con el oráculo independiente: fuerza bruta hasta $k=8$ y Held-Karp en $k = 10, 12$.
- **Métodos locales**: las semillas 0 a 9 con el presupuesto del enunciado y las configuraciones congeladas. Su gap se calcula contra el óptimo **del subproblema** certificado por A\*, nunca contra el de la instancia completa.
#%% code
def exact_case(name, k):
    sub = INSTANCES[name].subproblem(k)
    oracle = brute_force(sub)[0] if k <= 8 else held_karp(sub)
    a_runs = [astar(sub) for _ in range(3)]
    r_runs = [rbfs(sub)]
    if r_runs[0].elapsed_seconds < 2:
        r_runs += [rbfs(sub) for _ in range(2)]
    audit, other = rbfs(sub, audit=True), astar(sub, start=k - 1)
    a, r = a_runs[0], r_runs[0]
    assert all(x.cost == oracle and x.optimality_status == "OPTIMAL" for x in a_runs + [other]), (name, k)
    assert r.stop_reason != "GOAL" or r.cost == oracle
    return {"instancia": name, "nodos": sub.node_ids, "k": k, "óptimo certificado": a.cost, "oráculo": oracle,
            "otro origen": other.cost, "exp. A*": a.expanded, "exp. RBFS": r.expanded, "parada RBFS": r.stop_reason,
            "regeneraciones RBFS": audit.regenerations, "llamadas RBFS": r.calls,
            "s A* (mediana)": statistics.median(x.elapsed_seconds for x in a_runs),
            "s RBFS (mediana)": statistics.median(x.elapsed_seconds for x in r_runs), "reps RBFS": len(r_runs),
            "MiB A*": max(x.peak_memory_mib for x in a_runs), "MiB RBFS": max(x.peak_memory_mib for x in r_runs),
            "frontera máx A*": a.frontier_peak, "registros vivos máx RBFS": r.frontier_peak}


CASES = [(nm, k) for nm in MANDATORY for k in (6, 8, 10, 12)]
scale_a = pd.DataFrame(parallel_map(exact_case, CASES, WORKERS))
display(scale_a[["instancia", "nodos", "k", "óptimo certificado", "exp. A*", "exp. RBFS", "MiB A*", "MiB RBFS"]]
        .round(3))
display(scale_a.drop(columns=["nodos"]).round(4))
certified = dict(zip(zip(scale_a["instancia"], scale_a["k"]), scale_a["óptimo certificado"]))
#%% code
sub_jobs = [(nm, k, alg, s, BUDGET_TEACHER, FROZEN[alg], certified[(nm, k)])
            for nm, k in CASES for alg in LOCAL for s in SEEDS]
sub_runs = parallel_map(run_local, sub_jobs, WORKERS)
sub_df = table(sub_runs)
sub_df["k"] = sub_df["subset"].str[2:].astype(int)
assert (sub_df["gap_percent"] >= 0).all()
match = (sub_df.assign(coincide=sub_df["gap_percent"] == 0)
         .pivot_table(index="algorithm", columns=["instance", "k"], values="coincide", aggfunc="sum")
         .reindex(LOCAL))
print("Semillas (de 10) que llegan al óptimo certificado del subproblema:")
display(match)
display(sub_df.pivot_table(index="algorithm", columns="k", values="gap_percent", aggfunc="max").reindex(LOCAL)
        .round(2).rename_axis(columns="gap máximo % por k"))
#%% md
**Lo que encontramos (G.3):**

- **A\* certifica los 16 subproblemas** y coincide con el oráculo independiente y con el otro origen. RBFS termina 14 y en brazil58 con $k = 10$ y $k = 12$ se corta en las 100 000 expansiones: en la tabla queda como interrumpido, sin costo.
- **Memoria contra recomputación (pregunta 5).** En $k = 12$, A\* guarda hasta 1296 a 4204 nodos en la frontera y usa entre 0.05 y 2.35 MiB adicionales. RBFS nunca pasa de 68 registros vivos ni de 0.02 MiB, o sea, entre 3 y 130 veces menos memoria. El precio son las regeneraciones: en berlin52 $k = 12$, de 80 651 expansiones, 80 214 son estados que ya había expandido antes (99.5 %), y tarda 17 s contra 0.08 s de A\*. Los registros vivos crecen como $k^2/2$ (17, 30, 47, 68 contra 18, 32, 50, 72), que es el $O(bd)$ de la teoría con un factor de ramificación $b$ y una profundidad $d$ que crecen los dos con $k$.
- **gr48 es mucho más fácil que att48 para los exactos (pregunta 6),** aunque las dos tienen 48 ciudades: en $k = 12$, A\* hace 38 expansiones en gr48 y 376 en att48, y RBFS 79 contra 32 375. La cota MST se ajusta mejor al costo real en los primeros 12 nodos de gr48.
- **Métodos locales:** SA y HC con reinicios llegan al óptimo del subproblema en las 160 corridas. HC de una ruta falla sobre todo en brazil58 con $k = 10$ y $k = 12$ (2 de 10 aciertos) y una vez en att48 con $k = 10$: se queda en un óptimo local hasta 5.4 % peor. GA llega en 157 de 160, con gap máximo de 0.19 %. Con $k \le 12$, 30 000 evaluaciones sobran para todos, así que estas tablas sirven para comprobar que los métodos son correctos, no para ordenarlos.
#%% md
### G.4 Escala B: las cuatro instancias completas

Cuatro métodos locales × 4 instancias × 10 semillas × 2 presupuestos = 320 ejecuciones, más un ensayo diagnóstico de A\* y de RBFS por instancia con el presupuesto de exactos. Antes de resumir comprobamos dos cosas:

- **Ningún gap negativo** (15): si apareciera uno, habría un error de datos o de costo y nos detendríamos.
- **Reproducibilidad entre presupuestos:** HC de una ruta, HC con reinicios y GA no dependen del presupuesto mientras no se acaba, así que la corrida de 30 000 debe terminar con el mismo mejor costo que la curva de la corrida de 200 000 en la evaluación 30 000. Si no coincidiera, habría azar no controlado.
#%% code
b_jobs = [(nm, None, alg, s, BUDGETS[b], FROZEN[alg]) for b in BUDGETS for nm in MANDATORY for alg in LOCAL for s in SEEDS]
b_runs = parallel_map(run_local, b_jobs, WORKERS)
runs_b = {(r.instance, r.algorithm, r.seed, r.parameters["budget"]): r for r in b_runs}
df_b = table(b_runs)
df_b["presupuesto"] = df_b["parameters"].str.extract(r"budget=(\d+)")[0].astype(int)
assert (df_b["gap_percent"] >= 0).all(), "negative gap: audit data, tour and cost"
assert all(is_valid_tour(r.tour, INSTANCES[r.instance].n) and tour_cost(INSTANCES[r.instance].W, r.tour) == r.cost
           for r in b_runs)


def best_at(history, evals):
    return [b for e, _, b in history if e <= evals][-1]


for (nm, alg, s, b), r in runs_b.items():
    if b == 30_000 and alg != "SA":
        assert r.cost == best_at(runs_b[(nm, alg, s, 200_000)].history, 30_000), (nm, alg, s)
print(f"{len(b_runs)} ejecuciones: rutas válidas, ningún gap negativo; HC, HC reinicios y GA reproducen en 30 000 "
      "el valor de su curva de 200 000")


def diagnostic(name, solver):
    return {"astar": astar, "rbfs": rbfs}[solver](INSTANCES[name])


diag = parallel_map(diagnostic, [(nm, s) for nm in MANDATORY for s in ("astar", "rbfs")], WORKERS)
display(pd.DataFrame([{"instancia": r.instance, "algoritmo": r.algorithm, "parada": r.stop_reason,
                       "estado": r.optimality_status, "costo": r.cost if r.cost is not None else "N/A",
                       "expansiones": r.expanded, "generados": r.generated, "llamadas MST": r.mst_calls,
                       "profundidad máx": r.max_depth if r.max_depth is not None else "-",
                       "s": round(r.elapsed_seconds, 1), "MiB": round(r.peak_memory_mib, 1)} for r in diag]))
#%% md
**Tablas por instancia (plantilla de 15.1, ampliada con lo que pide 15).** Una fila por método y presupuesto. Las columnas de costo y gap se calculan sobre las ejecuciones **válidas**: las que devolvieron ruta. Los exactos tienen una sola ejecución diagnóstica y, si no encontraron ruta, su costo y gap quedan en `N/A` y cuentan como censurados. "Coincide con óptimo" es cuántas semillas llegaron exactamente al óptimo oficial.
#%% code
def summary_rows(name):
    rows = []
    for r in diag:
        if r.instance == name:
            rows.append({"método": r.algorithm, "presupuesto": "exactos", "válidas/previstas": f"{int(r.tour is not None)}/1",
                         "mejor costo": r.cost if r.cost is not None else "N/A",
                         "gap mediano %": round(r.gap_percent, 2) if r.cost is not None else "N/A",
                         "tiempo mediano s": round(r.elapsed_seconds, 2), "memoria máx MiB": round(r.peak_memory_mib, 2),
                         "motivo predominante": r.stop_reason, "censuradas": int(r.tour is None)})
    for b in BUDGETS:
        for alg in LOCAL:
            d = df_b[(df_b["instance"] == name) & (df_b["algorithm"] == alg) & (df_b["presupuesto"] == b)]
            rows.append({"método": alg, "presupuesto": b, "válidas/previstas": f"{d['cost'].notna().sum()}/{len(SEEDS)}",
                         "mejor costo": d["cost"].min(), "costo mediano": d["cost"].median(),
                         "costo medio": round(d["cost"].mean(), 1), "costo desv.": round(d["cost"].std(), 1),
                         "gap mejor %": round(d["gap_percent"].min(), 2),
                         "gap mediano %": round(d["gap_percent"].median(), 2),
                         "gap medio %": round(d["gap_percent"].mean(), 2), "gap desv. %": round(d["gap_percent"].std(), 2),
                         "tiempo mediano s": round(d["elapsed_seconds"].median(), 2),
                         "memoria máx MiB": round(d["peak_memory_mib"].max(), 2),
                         "motivo predominante": d["stop_reason"].mode()[0],
                         "coincide con óptimo": int((d["gap_percent"] == 0).sum()), "censuradas": 0})
    return pd.DataFrame(rows).astype(object).fillna("")


for name in MANDATORY:
    print(f"{name} (óptimo oficial {INSTANCES[name].optimum})")
    display(summary_rows(name))
#%% md
**Lo que encontramos (G.4):**

- **Exactos en las instancias completas.** Los 8 ensayos diagnósticos se cortan por los 30 s, sin ruta (`NO_TOUR`, censurados). A\* llega a 1165-1964 expansiones y 17-24 MiB; RBFS a 808-1346 expansiones con unos 0.1 MiB, y nunca pasa de la profundidad 8 de las 48 que necesita una ruta. No es un error: la sección 17 avisa que no se penaliza, y el diagnóstico muestra por qué (cada expansión calcula decenas de MST de unas 45 ciudades).
- **Con 30 000 evaluaciones, HC de una ruta y HC con reinicios dan exactamente lo mismo,** porque ninguna corrida llega a su primer óptimo local y por lo tanto nunca reinicia. Su gap mediano es de 25 % a 81 %: es una ruta a mitad de descenso. Esto confirma la razón del cambio de presupuesto de G.1.
- **Con 200 000 evaluaciones,** HC de una ruta para siempre en un óptimo local (gap mediano 4.5 % a 8.1 %). HC con reinicios usa todo el presupuesto y baja la mediana a 1.7-5.7 %. SA es el mejor en las cuatro instancias (gap mediano 0.3 % a 2.9 %) y la única que llega al óptimo oficial: 2 semillas en berlin52, 3 en brazil58 y 1 en gr48. GA queda cerca de HC de una ruta en mediana (3.6 % a 5.5 %), con una dispersión parecida o mayor.
- **Tiempo.** HC termina en menos de 1 s, SA en 2-4 s y GA en 17-43 s. Los tiempos del GA varían mucho entre instancias porque las corridas compartían la máquina (G.1). Ninguna se cortó por tiempo.
- **Memoria.** Los métodos locales usan a lo sumo 1.1 MiB adicionales (el GA, que guarda 80 rutas y su registro por generación). A\* llega a 24 MiB en los diagnósticos.
#%% md
### G.5 Comparación controlada HC contra SA (sección 11.1)

Como las tres variantes arrancan de la misma ruta en cada semilla, podemos compararlas **por pares**: para cada semilla miramos si SA terminó mejor, igual o peor que HC. Comparación 1: HC de una ruta contra SA (el efecto de aceptar empeoramientos). Comparación 2: HC con reinicios contra SA (cómo usa cada uno el mismo presupuesto global).

Aparte, para la pregunta de 11.1 sobre la temperatura inicial demasiado baja, repetimos SA en berlin52 con las mismas semillas y el mismo $\alpha$, pero con $p_0 = 0.01$: al principio casi ningún empeoramiento se acepta.
#%% code
rows = []
for b in BUDGETS:
    for rival in ("HC una ruta", "HC reinicios"):
        for nm in MANDATORY:
            diff = [runs_b[(nm, "SA", s, b)].cost - runs_b[(nm, rival, s, b)].cost for s in SEEDS]
            rows.append({"presupuesto": b, "comparación": f"SA vs {rival}", "instancia": nm,
                         "SA mejor": sum(d < 0 for d in diff), "empate": sum(d == 0 for d in diff),
                         "SA peor": sum(d > 0 for d in diff),
                         "diferencia mediana de costo (SA - HC)": statistics.median(diff),
                         "s mediano SA": round(statistics.median(runs_b[(nm, "SA", s, b)].elapsed_seconds for s in SEEDS), 2),
                         f"s mediano {rival}": round(statistics.median(runs_b[(nm, rival, s, b)].elapsed_seconds
                                                                      for s in SEEDS), 2)})
display(pd.DataFrame(rows).astype(object).fillna(""))

cold_params = dict(FROZEN["SA"], p0=0.01)
cold = parallel_map(run_local, [("berlin52", None, "SA", s, BUDGET_MAIN, cold_params) for s in SEEDS], WORKERS)
first_rate = lambda r: r.extra["levels"][0]["worse_acceptance"]
display(pd.DataFrame([{"p0": p0, "T0 mediana": round(statistics.median(r.extra["T0"] for r in rs), 1),
                       "aceptación de empeoramientos en el primer nivel (mediana)":
                           round(statistics.median(first_rate(r) for r in rs), 3),
                       "gap mediano %": round(statistics.median(r.gap_percent for r in rs), 2),
                       "gap máximo %": round(max(r.gap_percent for r in rs), 2)}
                      for p0, rs in ((FROZEN["SA"]["p0"], [runs_b[("berlin52", "SA", s, 200_000)] for s in SEEDS]),
                                     (0.01, cold))]))
#%% md
**Lo que encontramos (G.5), con las preguntas de 11.1:**

- **¿SA mejora siempre a HC?** No siempre. Contra HC de una ruta gana en 39 de 40 pares con el presupuesto principal; la excepción es una semilla de gr48. Contra HC con reinicios gana en 35 de 40: pierde en 2 semillas de att48 y en 3 de gr48, y en gr48 la diferencia mediana es de solo 38 unidades (0.75 %). Con 30 000 evaluaciones SA gana los 40 pares contra los dos, pero esa comparación favorece a SA por construcción: SA se enfría dentro del presupuesto y HC no alcanza a terminar ni su primer descenso.
- **¿Temperatura inicial demasiado baja?** Con $p_0 = 0.01$, $T_0$ baja de unos 1020 a unos 50 y en el primer nivel se acepta el 3.8 % de los empeoramientos en lugar del 73 %. SA se vuelve casi un descenso: el gap mediano en berlin52 sube de 2.87 % a 3.24 % y el peor caso de 4.55 % a 8.35 %. Lo que más empeora es la cola: algunas semillas quedan atrapadas como HC.
- **¿Cómo afecta el enfriamiento a la aceptación?** La aceptación de empeoramientos cae con la temperatura, de cerca de $p_0$ al principio a casi 0 al final (figura 5).
- **¿Una mejora final compensa el trabajo adicional?** Depende de lo que se pague. SA tarda unas 10 veces más que HC con reinicios (3.9 s contra 0.4 s en att48) por 0.8 a 3.3 puntos de gap mediano. En G.7 se ve que buena parte de ese tiempo extra es la medición de memoria, así que la respuesta cambia según se mida por evaluaciones o por tiempo (pregunta 9).
#%% md
### G.6 Visualizaciones obligatorias (sección 15.2)

Todas las gráficas se dibujan **después** de las corridas, leyendo los registros (`history`, `levels`, `gen_log` y las tablas de arriba). Nada se dibuja dentro de la región cronometrada.

**Figura 1. Rutas inicial y final.** La inicial es la ruta compartida de la semilla 0. La final es la mejor ruta de las 40 ejecuciones con presupuesto principal en esa instancia. att48 y berlin52 se dibujan con sus coordenadas reales. brazil58 y gr48 solo tienen matriz, así que las ciudades se ponen en un **círculo esquemático** que no representa geografía; su matriz de calor está en B.
#%% code
def layout(inst):
    if inst.coords is not None:
        return inst.coords
    angle = 2 * np.pi * np.arange(inst.n) / inst.n
    return np.column_stack([np.cos(angle), np.sin(angle)])


def draw_tour(ax, inst, tour, title):
    xy = layout(inst)
    closed = list(tour) + [tour[0]]
    ax.plot(xy[closed, 0], xy[closed, 1], "-", lw=1, color="tab:blue")
    ax.plot(xy[:, 0], xy[:, 1], "o", ms=3, color="black")
    ax.plot(*xy[tour[0]], "s", ms=7, color="tab:red")
    ax.set_title(title, fontsize=9)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")


fig, axes = plt.subplots(2, 4, figsize=(18, 9))
for col, name in enumerate(MANDATORY):
    inst = INSTANCES[name]
    start = initial_tour(inst, 0)
    best = min((r for r in b_runs if r.instance == name and r.parameters["budget"] == 200_000), key=lambda r: r.cost)
    kind = "plano real" if inst.coords is not None else "círculo esquemático"
    draw_tour(axes[0, col], inst, start, f"{name}: inicial semilla 0, costo {tour_cost(inst.W, start)}\n({kind})")
    draw_tour(axes[1, col], inst, best.tour, f"{name}: mejor final, {best.algorithm} semilla {best.seed}\n"
                                             f"costo {best.cost}, gap {best.gap_percent:.2f} % ({kind})")
plt.tight_layout()
plt.show()
#%% md
**Figura 2. Mejor costo acumulado frente a evaluaciones y frente a tiempo** (presupuesto principal). La línea es la mediana de las 10 semillas y la banda va del mínimo al máximo. El eje vertical es el gap, para poder poner las cuatro instancias en la misma escala. Cuando una ejecución para antes del final (HC de una ruta para en su óptimo local), su último valor se **conserva**: a partir de la primera parada la línea sigue **punteada**, para que no se lea como evaluaciones ejecutadas.
#%% code
COLORS = dict(zip(LOCAL, ["tab:blue", "tab:orange", "tab:green", "tab:red"]))


def curve(history, grid, axis):
    xs = np.array([h[axis] for h in history])
    ys = np.array([h[2] for h in history], dtype=float)
    return ys[np.maximum(np.searchsorted(xs, grid, side="right") - 1, 0)]


def plot_curves(axis, xlabel, grid_max, log_x):
    fig, axes = plt.subplots(1, 4, figsize=(19, 4.3), sharey=True)
    for ax, name in zip(axes, MANDATORY):
        opt = INSTANCES[name].optimum
        for alg in LOCAL:
            rs = [runs_b[(name, alg, s, 200_000)] for s in SEEDS]
            top = grid_max(rs)
            grid = np.geomspace(1e-3 if axis else 1, top, 300) if log_x else np.linspace(1, top, 300)
            gaps = np.array([100 * (curve(r.history, grid, axis) - opt) / opt for r in rs])
            ends = [r.candidate_evaluations if axis == 0 else r.elapsed_seconds for r in rs]
            med = np.median(gaps, axis=0)
            live = grid <= min(ends)
            ax.fill_between(grid, gaps.min(axis=0), gaps.max(axis=0), color=COLORS[alg], alpha=0.15)
            ax.plot(grid[live], med[live], color=COLORS[alg], label=alg)
            ax.plot(grid[~live], med[~live], ":", color=COLORS[alg])
        ax.set_ylim(0, 25)
        ax.set_title(name)
        ax.set_xlabel(xlabel)
        if log_x:
            ax.set_xscale("log")
    axes[0].set_ylabel("gap % del mejor acumulado")
    axes[0].legend(fontsize=8)
    plt.tight_layout()
    plt.show()


plot_curves(0, "evaluaciones de candidatos", lambda rs: 200_000, False)
plot_curves(1, "segundos (escala log)", lambda rs: max(r.elapsed_seconds for r in rs), True)
#%% md
**Figura 3. Gap por algoritmo e instancia,** con cajas y cada semilla como un punto, en los dos presupuestos.
#%% code
fig, axes = plt.subplots(2, 4, figsize=(19, 8), sharey="row")
jitter = np.random.default_rng(0)
for row, b in enumerate(BUDGETS):
    for ax, name in zip(axes[row], MANDATORY):
        data = [df_b[(df_b["instance"] == name) & (df_b["algorithm"] == alg) & (df_b["presupuesto"] == b)]["gap_percent"]
                for alg in LOCAL]
        ax.boxplot(data, widths=0.5, showfliers=False)
        for i, d in enumerate(data, start=1):
            ax.plot(i + jitter.uniform(-0.12, 0.12, len(d)), d, "o", ms=4, alpha=0.7, color=COLORS[LOCAL[i - 1]])
        ax.set_xticks(range(1, 5), ["HC", "HC reinicios", "SA", "GA"], fontsize=8)
        ax.set_title(f"{name}, {b} evaluaciones")
    axes[row, 0].set_ylabel("gap %")
plt.tight_layout()
plt.show()
#%% md
**Figura 4. Tiempo y memoria de A\* y RBFS contra el tamaño de la subinstancia** (escala A, escala logarítmica). Una **x** marca una ejecución interrumpida por el presupuesto de exactos.
#%% code
fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
for name, marker in zip(MANDATORY, "osD^"):
    d = scale_a[scale_a["instancia"] == name]
    for algo, color, col_s, col_m in (("A*", "tab:blue", "s A* (mediana)", "MiB A*"),
                                      ("RBFS", "tab:red", "s RBFS (mediana)", "MiB RBFS")):
        axes[0].plot(d["k"], d[col_s], marker=marker, color=color, alpha=0.8, label=f"{algo} {name}")
        axes[1].plot(d["k"], d[col_m].clip(lower=1e-3), marker=marker, color=color, alpha=0.8)
        if algo == "RBFS":
            cut = d[d["parada RBFS"] != "GOAL"]
            axes[0].plot(cut["k"], cut[col_s], "x", ms=14, mew=3, color="black")
            axes[1].plot(cut["k"], cut[col_m].clip(lower=1e-3), "x", ms=14, mew=3, color="black")
axes[0].set(yscale="log", xlabel="k (ciudades)", ylabel="segundos (mediana)", title="Tiempo")
axes[1].set(yscale="log", xlabel="k (ciudades)", ylabel="MiB adicionales (tracemalloc)", title="Memoria")
axes[0].legend(fontsize=7, ncol=2)
plt.tight_layout()
plt.show()
#%% md
**Figura 5. SA en berlin52, semilla 0, presupuesto principal:** temperatura, costo actual y mejor costo, y tasa de aceptación de empeoramientos. La **ventana de aceptación es un nivel de temperatura**: la tasa es aceptados con $\Delta > 0$ sobre propuestos con $\Delta > 0$ dentro de ese nivel.
#%% code
sa_demo = runs_b[("berlin52", "SA", 0, 200_000)]
lv = pd.DataFrame(sa_demo.extra["levels"])
fig, axes = plt.subplots(1, 3, figsize=(18, 4))
axes[0].plot(lv["evals"], lv["T"])
axes[0].set(yscale="log", title=f"Temperatura (T0 = {sa_demo.extra['T0']:.0f}, alpha = {FROZEN['SA']['alpha']})",
            xlabel="evaluaciones")
axes[1].plot(lv["evals"], lv["current"], label="actual (fin de cada nivel)")
axes[1].plot(lv["evals"], lv["best"], label="mejor")
axes[1].axhline(INSTANCES["berlin52"].optimum, ls="--", color="gray", label="óptimo oficial")
axes[1].set(title="Costo", xlabel="evaluaciones")
axes[1].legend()
axes[2].plot(lv["evals"], lv["worse_acceptance"])
axes[2].set(title="Aceptación de empeoramientos por nivel", xlabel="evaluaciones", ylim=(0, 1))
plt.tight_layout()
plt.show()
#%% md
**Figura 6. GA en berlin52, semilla 0, presupuesto principal:** mejor costo y costo mediano de la población, y las dos medidas de diversidad de F.2 por generación.
#%% code
ga_demo = runs_b[("berlin52", "GA básico", 0, 200_000)]
gl = pd.DataFrame(ga_demo.extra["gen_log"])
fig, axes = plt.subplots(1, 2, figsize=(15, 4))
axes[0].plot(gl["generation"], gl["best"], label="mejor")
axes[0].plot(gl["generation"], gl["median"], label="mediana de la población")
axes[0].axhline(INSTANCES["berlin52"].optimum, ls="--", color="gray", label="óptimo oficial")
axes[0].set(xlabel="generación", ylabel="costo", ylim=(7000, 16000), title="Costo")
axes[0].legend()
axes[1].plot(gl["generation"], gl["unique"], label="fracción de rutas únicas")
axes[1].plot(gl["generation"], gl["edge_diversity"] / gl["edge_diversity"].iloc[0],
             label="aristas distintas / n (relativo a la generación 0)")
axes[1].set(xlabel="generación", title="Diversidad", ylim=(0, 1.05))
axes[1].legend()
plt.tight_layout()
plt.show()
print(f"{ga_demo.extra['generations']} generaciones; aristas distintas / n: {gl['edge_diversity'].iloc[0]:.1f} al inicio, "
      f"{gl['edge_diversity'].iloc[-1]:.2f} al final")
#%% md
### G.7 Cómo medimos la memoria y cuánto cuesta medirla (secciones 4 y 14.1)

- **Sobrecosto de `tracemalloc`.** Corremos lo mismo con la medición encendida y apagada (con apagada, `Meter` solo mide el tiempo), tres veces cada una, y comparamos la mediana. Esta celda corre sola, sin otros procesos en paralelo.
- **Memoria del proceso contra memoria del solver.** `tracemalloc` solo ve las asignaciones de Python del solver. El proceso completo (intérprete, numpy, pandas, matplotlib, los datos y los resultados guardados) ocupa mucho más. Lo leemos con `resource.getrusage` (máximo de memoria residente, RSS), para este proceso y para el mayor de los procesos de trabajo.
#%% code
class PlainMeter(Meter):
    """Same budget checks as Meter, without tracemalloc (memory reported as NaN)."""

    def __init__(self, seconds=INF, expansions=None, evaluations=None, memory_mib=None):
        self.seconds, self.expansions, self.evaluations, self.memory_mib = seconds, expansions, evaluations, memory_mib
        self._own_tracing, self.t0 = False, time.perf_counter()

    def peak_mib(self):
        return float("nan")


def timed(fn, traced):
    global Meter
    saved = Meter
    Meter = saved if traced else PlainMeter
    try:
        return statistics.median(fn().elapsed_seconds for _ in range(3))
    finally:
        Meter = saved


berlin = INSTANCES["berlin52"]
probes = {"HC una ruta (hasta óptimo local), berlin52": lambda: hill_climbing(berlin, initial_tour(berlin, 0), BIG,
                                                                               random.Random(0)),
          "SA 200 000 evaluaciones, berlin52": lambda: simulated_annealing(berlin, initial_tour(berlin, 0), BUDGET_MAIN,
                                                                           random.Random(0), **FROZEN["SA"]),
          "GA 30 000 evaluaciones, berlin52": lambda: genetic_algorithm(berlin, BUDGET_TEACHER, random.Random(0),
                                                                        **FROZEN["GA básico"]),
          "A* k=12, berlin52": lambda: astar(berlin.subproblem(12)),
          "RBFS k=10, att48": lambda: rbfs(INSTANCES["att48"].subproblem(10))}
overhead = pd.DataFrame([{"ejecución": label, "s con tracemalloc": timed(fn, True), "s sin tracemalloc": timed(fn, False)}
                         for label, fn in probes.items()])
overhead["factor"] = overhead["s con tracemalloc"] / overhead["s sin tracemalloc"]
display(overhead.round(3))

solver_peak = max([r.peak_memory_mib for r in b_runs + diag] + scale_a["MiB A*"].tolist())
display(pd.Series({
    "RSS máximo de este proceso (MiB)": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
    "RSS máximo del mayor proceso de trabajo (MiB)": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024,
    "mayor memoria adicional de un solver, tracemalloc (MiB)": solver_peak,
}, name="valor").round(1).to_frame())
#%% md
**Lo que encontramos (G.7):**

- **Medir la memoria cuesta mucho tiempo y no afecta a todos por igual.** Con `tracemalloc` encendido, HC tarda 1.3 veces más, pero SA 7.5 veces, RBFS 4.5, GA 3.9 y A\* 3.1. `tracemalloc` cobra por cada objeto que se crea, y SA crea una lista nueva cada vez que acepta un movimiento, mientras que HC casi solo calcula deltas. Por eso **los tiempos absolutos de las tablas están inflados**, y la diferencia de tiempo entre SA y HC es en parte un efecto de la medición. Para comparar tiempos entre familias hay que tenerlo presente; los costos y las evaluaciones no cambian.
- **Memoria del proceso contra memoria del solver.** El proceso de Jupyter llega a unos 456 MiB de RSS, y cada proceso de trabajo a unos 420 MiB (heredan el intérprete y las bibliotecas). El solver que más memoria adicional usó, A\* en un diagnóstico, apenas pasa de 23 MiB. Casi toda la memoria del proceso es el entorno, no el algoritmo. Por eso reportamos la memoria adicional del solver y decimos que solo cubre las asignaciones de Python.
#%% md
### G.8 Animación didáctica: HC mejorando una ruta de berlin52

Corremos HC de una ruta en berlin52 con la semilla 0 y guardamos la ruta en cada mejora (`snapshots`). Es una corrida aparte, que no se usa para medir. Los cuadros se dibujan **después** de la corrida. Cada cuadro muestra el algoritmo, el costo y las evaluaciones acumuladas. El GIF queda en `figuras/` y se ve aquí abajo.
#%% code
snaps = []
anim_run = hill_climbing(berlin, initial_tour(berlin, 0), BIG, random.Random(0), snapshots=snaps)
assert anim_run.cost == runs_b[("berlin52", "HC una ruta", 0, 200_000)].cost
frames = [(1, initial_tour(berlin, 0), anim_run.extra["initial_cost"])] + snaps
fig, ax = plt.subplots(figsize=(7, 5))


def draw_frame(i):
    ax.clear()
    evals, tour, cost = frames[i]
    draw_tour(ax, berlin, tour, f"HC una ruta (2-opt, mejor mejora), berlin52\n"
                                f"mejora {i}/{len(frames) - 1}: costo {cost}, gap {gap_percent(cost, 7542):.1f} %, "
                                f"{evals} evaluaciones")


gif_path = FIG_DIR / "hc_berlin52.gif"
animation.FuncAnimation(fig, draw_frame, frames=len(frames)).save(gif_path, writer=animation.PillowWriter(fps=4))
plt.close(fig)
print(f"{len(frames)} cuadros -> {gif_path}")
display(Image(filename=str(gif_path)))
