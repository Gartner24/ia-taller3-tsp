#%% md
### E.1 Vecindad 2-opt y swap (sección 9)

Una ruta es una lista `route[0..n-1]` con el origen en la posición 0. Un movimiento 2-opt `(i, j)` quita las aristas `(route[i], route[i+1])` y `(route[j], route[(j+1) mod n])`, e invierte el tramo de posiciones $i+1$ a $j$. Como $i \ge 0$, el tramo nunca incluye la posición 0 y el origen no se mueve.

- `two_opt_pairs(n)` lista los pares válidos: $0 \le i < j < n$, sin $j = i+1$ (aristas que se tocan) y sin $(0, n-1)$ (las dos aristas comparten el origen). Deben ser $n(n-3)/2$.
- `two_opt_delta` calcula $\Delta = d(a,c) + d(b,d) - d(a,b) - d(c,d)$ en $O(1)$. Cuando $j = n-1$, la arista $(c, d)$ es la de **cierre**, de vuelta al origen.
- `swap_move` intercambia dos ciudades. Lo usamos solo para la comparación con 2-opt; ningún algoritmo lo usa.

Antes de usar el delta lo validamos contra la versión lenta, que recalcula todo el costo con `tour_cost`.
#%% code
def two_opt_pairs(n):
    return [(i, j) for i in range(n - 1) for j in range(i + 2, n) if not (i == 0 and j == n - 1)]


def two_opt_delta(W, route, i, j):
    n = len(route)
    a, b, c, d = route[i], route[i + 1], route[j], route[(j + 1) % n]
    return W[a][c] + W[b][d] - W[a][b] - W[c][d]


def two_opt_move(route, i, j):
    assert j > i + 1 and not (i == 0 and j == len(route) - 1), "adjacent edges"
    return route[:i + 1] + route[i + 1:j + 1][::-1] + route[j + 1:]


def swap_move(route, p, q):
    out = route[:]
    out[p], out[q] = out[q], out[p]
    return out


def random_tour(n, rng):
    return [0] + rng.sample(range(1, n), n - 1)


def initial_tour(inst, seed):
    """Shared initial tour for (instance, seed): its own RNG, separate from every algorithm's RNG (section 11.1)."""
    return random_tour(inst.n, random.Random(f"{inst.name}-{inst.subset}-init-{seed}"))


def edge_set(route):
    return {frozenset(e) for e in zip(route, route[1:] + route[:1])}


for n in range(4, 60):
    assert len(two_opt_pairs(n)) == n * (n - 3) // 2
rng = random.Random(3)
checked = 0
for name in MANDATORY:
    inst = INSTANCES[name]
    for _ in range(3):
        route = random_tour(inst.n, rng)
        base_cost = tour_cost(inst.W, route)
        for i, j in two_opt_pairs(inst.n):
            moved = two_opt_move(route, i, j)
            assert is_valid_tour(moved, inst.n)
            assert tour_cost(inst.W, moved) - base_cost == two_opt_delta(inst.W, route, i, j)
            assert len(edge_set(route) - edge_set(moved)) == 2
            checked += 1
print(f"2-opt: n(n-3)/2 pares para n = 4..59; {checked} movimientos con permutación válida, "
      "exactamente 2 aristas cambiadas y delta igual al recálculo completo (incluye la arista de cierre)")

for n in (5, 6, 8):
    route = list(range(n))
    opt_sets = [edge_set(two_opt_move(route, i, j)) for i, j in two_opt_pairs(n)]
    changed = collections.Counter()
    for p, q in itertools.combinations(range(1, n), 2):
        moved = swap_move(route, p, q)
        changed[(len(edge_set(route) - edge_set(moved)), edge_set(moved) in opt_sets)] += 1
    print(f"n={n}: swaps por (aristas cambiadas, coincide con algún 2-opt) -> {dict(changed)}")
#%% md
**Lo que encontramos (E.1):** el delta coincide con el recálculo completo en todos los movimientos probados, incluidos los que tocan la arista de cierre, y cada 2-opt cambia exactamente 2 aristas. Con 5 ciudades **todo** swap coincide con algún 2-opt, como vimos a mano en C.5. Desde 6 ciudades aparecen swaps que cambian 4 aristas y no son ningún 2-opt. Los swaps de ciudades vecinas en el ciclo sí equivalen a un 2-opt de un tramo de 2.
#%% md
### E.2 Hill Climbing (sección 10)

`hill_climbing` recorre **todo** el vecindario 2-opt, se queda con la mejor mejora estricta y la aplica. Para cuando ningún movimiento mejora (`LOCAL_OPTIMUM`) o cuando se acaba el presupuesto (`EVALUATIONS` o `TIME`). Si se corta a mitad de un recorrido, **no** reporta óptimo local.

- **Evaluaciones.** Cada delta calculado cuenta 1. Calcular el costo de una ruta completa (la inicial o la de un reinicio) también cuenta 1. Revisamos el presupuesto **antes** de cada evaluación, así que nunca se pasa.
- **Reinicios** (`restarts=True`): al llegar a un óptimo local, empieza desde una ruta aleatoria nueva y conserva la mejor global. Los reinicios comparten el mismo presupuesto.
- **Primera mejora** (`first_improvement=True`): recorre los pares en un orden aleatorio y aplica la primera que mejore. Solo la usamos en el experimento aparte de E.3.
- `history` guarda `(evaluaciones, segundos, mejor costo)` cada vez que mejora el mejor. `snapshots` (opcional) guarda la ruta en cada mejora, para la animación de G; no se usa al medir.
#%% code
def hill_climbing(inst, initial, budget, rng, restarts=False, first_improvement=False, snapshots=None):
    W, n = inst.W, inst.n
    pairs = two_opt_pairs(n)
    meter = Meter(seconds=budget["seconds"], evaluations=budget["evaluations"])
    current = initial[:]
    cost = tour_cost(W, current)
    evals, local_optima, reason = 1, 0, None
    best, best_cost = current[:], cost
    history = [(evals, meter.elapsed(), best_cost)]
    while reason is None:
        if first_improvement:
            rng.shuffle(pairs)
        best_delta, best_move = 0, None
        for i, j in pairs:
            if meter.out_of_evaluations(evals):
                reason = meter.reason
                break
            evals += 1
            delta = two_opt_delta(W, current, i, j)
            if delta < best_delta:
                best_delta, best_move = delta, (i, j)
                if first_improvement:
                    break
        if reason is not None:
            break
        if best_move is None:
            local_optima += 1
            if not restarts:
                reason = "LOCAL_OPTIMUM"
                break
            if meter.out_of_evaluations(evals):
                reason = meter.reason
                break
            evals += 1                                  # a restart computes the cost of a new random tour
            current = random_tour(n, rng)
            cost = tour_cost(W, current)
        else:
            current = two_opt_move(current, *best_move)
            cost += best_delta
        if cost < best_cost:
            best, best_cost = current[:], cost
            history.append((evals, meter.elapsed(), best_cost))
            if snapshots is not None:
                snapshots.append((evals, best[:], best_cost))
    elapsed, peak = meter.finish()
    assert is_valid_tour(best, n) and tour_cost(W, best) == best_cost
    name = "HC primera mejora" if first_improvement else ("HC reinicios" if restarts else "HC una ruta")
    return RunResult(inst.name, inst.subset, name, None, dict(budget=budget["evaluations"], restarts=restarts,
                     first_improvement=first_improvement), best, best_cost, gap_percent(best_cost, inst.optimum),
                     elapsed, peak, reason, "NOT_CERTIFIED", candidate_evaluations=evals, history=history,
                     extra=dict(local_optima=local_optima, initial_cost=tour_cost(W, initial)))
#%% md
**Prueba del óptimo local (tabla de la sección 13).** Dejamos que HC llegue a `LOCAL_OPTIMUM` en las cuatro instancias y después, **por fuera del algoritmo**, aplicamos cada uno de los $n(n-3)/2$ movimientos a la ruta final y recalculamos el costo completo. Ninguno debe mejorar.

Aprovechamos para contar **cruces** en las rutas de att48 y berlin52 (las que tienen coordenadas): dos aristas del dibujo que se cortan. Esto sirve para la pregunta de la sección 10.
#%% code
def segments_cross(p1, p2, p3, p4):
    orient = lambda a, b, c: np.sign((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
    return (orient(p1, p2, p3) * orient(p1, p2, p4) < 0) and (orient(p3, p4, p1) * orient(p3, p4, p2) < 0)


def count_crossings(coords, route):
    edges = list(zip(route, route[1:] + route[:1]))
    return sum(segments_cross(coords[a], coords[b], coords[c], coords[d])
               for (a, b), (c, d) in itertools.combinations(edges, 2) if len({a, b, c, d}) == 4)


BIG = dict(evaluations=10**7, seconds=120.0)
rows = []
for name in MANDATORY:
    inst = INSTANCES[name]
    res = hill_climbing(inst, initial_tour(inst, 0), BIG, random.Random(0))
    assert res.stop_reason == "LOCAL_OPTIMUM"
    improving = sum(tour_cost(inst.W, two_opt_move(res.tour, i, j)) < res.cost for i, j in two_opt_pairs(inst.n))
    assert improving == 0
    rows.append({"instancia": name, "costo inicial": res.extra["initial_cost"], "costo final": res.cost,
                 "gap %": round(res.gap_percent, 2), "evaluaciones": res.candidate_evaluations,
                 "movimientos que mejoran (recálculo completo)": improving,
                 "cruces": count_crossings(inst.coords, res.tour) if inst.coords is not None else "sin coordenadas"})
display(pd.DataFrame(rows))
#%% md
**Lo que encontramos (E.2):**

- En las cuatro instancias HC termina en un óptimo local **verificado**: con el recálculo completo, ningún 2-opt mejora la ruta final.
- **Llegar al primer óptimo local cuesta más de 30 000 evaluaciones** (ver la columna de evaluaciones) desde una ruta aleatoria. Cada pasada completa del vecindario son más de 1000 evaluaciones, y hacen falta decenas de mejoras. Con el presupuesto de 30 000 de la sección 14, HC se cortaría antes de terminar su primer descenso. Esto lo usamos en G para fijar el presupuesto.
- **¿Sin cruces es óptima?** No. Las rutas finales de att48 y berlin52 no tienen ningún cruce, y aun así su gap es mayor que 0. En el plano, si dos aristas se cruzan, el 2-opt que las descruza siempre baja el costo (por la desigualdad triangular), así que un óptimo local de 2-opt no tiene cruces. Pero eso es una condición necesaria, no suficiente: hay muchas rutas sin cruces y solo una es la óptima. En una **matriz explícita** (brazil58, gr48) ni siquiera existe la idea de "cruce": no hay geometría, y el dibujo circular esquemático tiene cruces que no significan nada.
#%% md
### E.3 Primera mejora contra mejor mejora (experimento aparte)

Lo corremos en las subinstancias de 20 ciudades de las cuatro instancias, 10 semillas, desde la misma ruta inicial, hasta llegar al óptimo local. No se mezcla con la comparación principal.
#%% code
rows = []
for name in MANDATORY:
    sub = INSTANCES[name].subproblem(20)
    for seed in range(10):
        start = initial_tour(sub, seed)
        for first in (False, True):
            res = hill_climbing(sub, start, BIG, random.Random(f"{name}-fi-{seed}"), first_improvement=first)
            assert res.stop_reason == "LOCAL_OPTIMUM"
            rows.append({"instancia": name, "seed": seed, "variante": res.algorithm, "costo": res.cost,
                         "evaluaciones": res.candidate_evaluations})
fi = pd.DataFrame(rows)
display(fi.groupby(["instancia", "variante"]).agg(costo_mediano=("costo", "median"), costo_mejor=("costo", "min"),
                                                  evaluaciones_medianas=("evaluaciones", "median")))
#%% md
**Lo que encontramos (E.3):** en 20 ciudades, las dos variantes llegan a óptimos locales de calidad parecida: las medianas casi coinciden y la mejor de las 10 semillas es la misma o muy cercana. La diferencia es el trabajo: primera mejora llega con unas **4 veces menos evaluaciones**, porque no recorre todo el vecindario antes de moverse. Con 20 ciudades no hay una diferencia clara de calidad; para afirmarlo en las instancias completas haría falta medirlo allá, y no lo mezclamos con la comparación principal, que usa mejor mejora como pide la sección 10.
#%% md
### E.4 Simulated Annealing (sección 11)

`simulated_annealing` sigue el pseudocódigo de la sección 11 con la misma vecindad 2-opt:

- **Calibración de $T_0$.** Desde la ruta inicial evaluamos 100 movimientos al azar (cuentan en el presupuesto) y tomamos la mediana de los deltas positivos: $T_0 = -\operatorname{mediana}(\Delta^+)/\ln(p_0)$. Así, al principio un empeoramiento típico se acepta con probabilidad $p_0$. Si ninguno de los 100 deltas es positivo (la ruta ya es muy buena), usamos la mediana de $|\Delta|$ de los deltas distintos de cero, y si todos son cero, $T_0 = 1$. Lo dejamos registrado en `extra`.
- **Enfriamiento.** $T_{min} = 10^{-3}\,T_0$ y $T \leftarrow \alpha T$. El número de niveles es $L = \lceil \ln(10^{-3}) / \ln \alpha \rceil$, y cada nivel recibe `steps` = (presupuesto restante) // $L$ propuestas. Así cualquier $\alpha$ usa todo el presupuesto y termina justo al enfriarse (`TMIN`); si no, para por presupuesto.
- **Aceptación.** $\Delta \le 0$ siempre se acepta (mejoras y empates). Si $\Delta > 0$, se acepta con probabilidad $e^{-\Delta/T}$.
- **Mejor contra actual.** `current` y `best` son listas distintas. Se devuelve `best`.
- **Registro por nivel** (la ventana de aceptación es **un nivel de temperatura**): $T$, costo actual, mejor costo y tasa de aceptación de empeoramientos = aceptados con $\Delta > 0$ / propuestos con $\Delta > 0$.
#%% code
def simulated_annealing(inst, initial, budget, rng, alpha, p0, tmin_ratio=1e-3, calibration_samples=100):
    W, n = inst.W, inst.n
    pairs = two_opt_pairs(n)
    meter = Meter(seconds=budget["seconds"], evaluations=budget["evaluations"])
    current = initial[:]
    cost = tour_cost(W, current)
    evals = 1
    best, best_cost = current[:], cost
    history = [(evals, meter.elapsed(), best_cost)]
    samples = []
    for _ in range(calibration_samples):
        if meter.out_of_evaluations(evals):
            break
        evals += 1
        samples.append(two_opt_delta(W, current, *pairs[rng.randrange(len(pairs))]))
    positive = [d for d in samples if d > 0]
    if positive:
        t0, t0_rule = -statistics.median(positive) / math.log(p0), "median positive delta"
    else:
        nonzero = [abs(d) for d in samples if d != 0]
        t0, t0_rule = (statistics.median(nonzero), "median |delta| (no positive deltas)") if nonzero else (1.0, "T0 = 1")
    levels = math.ceil(math.log(tmin_ratio) / math.log(alpha))
    steps = max(1, (budget["evaluations"] - evals) // levels)
    T, reason, level_log = t0, "TMIN", []
    for level in range(levels):
        worse_proposed = worse_accepted = 0
        for _ in range(steps):
            if meter.out_of_evaluations(evals):
                reason = meter.reason
                break
            evals += 1
            i, j = pairs[rng.randrange(len(pairs))]
            delta = two_opt_delta(W, current, i, j)
            if delta > 0:
                worse_proposed += 1
            if delta <= 0 or rng.random() < math.exp(-delta / T):
                current = two_opt_move(current, i, j)
                cost += delta
                worse_accepted += delta > 0
                if cost < best_cost:
                    best, best_cost = current[:], cost
                    history.append((evals, meter.elapsed(), best_cost))
        level_log.append({"level": level, "evals": evals, "T": T, "current": cost, "best": best_cost,
                          "worse_acceptance": worse_accepted / worse_proposed if worse_proposed else None})
        if reason != "TMIN":
            break
        T *= alpha
    elapsed, peak = meter.finish()
    assert is_valid_tour(best, n) and tour_cost(W, best) == best_cost and tour_cost(W, current) == cost
    return RunResult(inst.name, inst.subset, "SA", None, dict(alpha=alpha, p0=p0, tmin_ratio=tmin_ratio,
                     budget=budget["evaluations"], levels=levels, steps=steps), best, best_cost,
                     gap_percent(best_cost, inst.optimum), elapsed, peak, reason, "NOT_CERTIFIED",
                     candidate_evaluations=evals, history=history,
                     extra=dict(T0=t0, T0_rule=t0_rule, calibration_evals=len(samples), final_current=cost,
                                levels=level_log, initial_cost=tour_cost(W, initial)))
#%% md
**Pruebas de SA (tabla de la sección 13).**

- **Mejor distinta de la actual:** con $p_0 = 0.8$ y un enfriamiento que se detiene todavía caliente ($T_{min} = T_0/2$), la ruta actual termina peor que la mejor observada; debe devolverse la mejor.
- El presupuesto nunca se excede, la ruta devuelta es una permutación válida y su costo coincide con `tour_cost`.
- Sin deltas positivos, se usa la regla de respaldo para $T_0$: lo probamos empezando desde el óptimo local de E.2, donde ningún 2-opt mejora pero casi todos empeoran, y desde una instancia con todos los pesos iguales, donde todos los deltas son 0.
#%% code
inst = INSTANCES["berlin52"]
differs = 0
for seed in range(5):
    res = simulated_annealing(inst, initial_tour(inst, seed), dict(evaluations=3000, seconds=30), random.Random(seed),
                              alpha=0.9, p0=0.8, tmin_ratio=0.5)     # stops while still hot
    assert res.candidate_evaluations <= 3000 and is_valid_tour(res.tour, inst.n)
    assert res.cost == min(h[2] for h in res.history) <= res.extra["final_current"]
    differs += res.extra["final_current"] > res.cost
assert differs > 0
print(f"SA: en {differs} de 5 corridas cortas la actual terminó peor que la mejor; siempre se devolvió la mejor")

flat = TSPInstance("flat", "EXPLICIT", None, list(range(1, 9)), np.ones((8, 8), dtype=np.int64) - np.eye(8, dtype=np.int64))
res = simulated_annealing(flat, list(range(8)), dict(evaluations=500, seconds=5), random.Random(0), alpha=0.9, p0=0.5)
assert res.extra["T0_rule"] == "T0 = 1" and res.cost == 8
print("SA con todos los deltas en 0: regla de respaldo", res.extra["T0_rule"])

res = simulated_annealing(inst, hill_climbing(inst, initial_tour(inst, 0), BIG, random.Random(0)).tour,
                          dict(evaluations=5000, seconds=30), random.Random(1), alpha=0.9, p0=0.5)
print("SA desde un óptimo local: regla", res.extra["T0_rule"], f"T0 = {res.extra['T0']:.1f}")
demo = pd.DataFrame(simulated_annealing(inst, initial_tour(inst, 0), dict(evaluations=200_000, seconds=30),
                                        random.Random(0), alpha=0.97, p0=0.5).extra["levels"])
display(demo.iloc[::25])
#%% md
**Lo que encontramos (E.4):**

- La mejor ruta y la actual sí se separan: si la corrida termina caliente, la actual queda peor y el algoritmo devuelve la mejor. Con el enfriamiento completo ($T_{min} = 10^{-3} T_0$) casi siempre terminan iguales, porque al final SA se comporta como un descenso.
- Desde un óptimo local de 2-opt **todos** los deltas de prueba son mayores o iguales a cero, pero hay positivos, así que la regla principal funciona: un óptimo local no deja $T_0$ sin definir. La regla de respaldo solo se activa en casos degenerados como la matriz de pesos iguales.
- En la corrida de ejemplo (berlin52, $\alpha = 0.97$, $p_0 = 0.5$) se ve el comportamiento esperado: al principio la temperatura es alta, se acepta cerca del 40 % de los empeoramientos (un poco menos que $p_0$, porque $p_0$ se calibró con la mediana y la mitad de los empeoramientos son más grandes) y la ruta actual sube y baja. Al enfriarse, la tasa de aceptación cae casi a 0, y la actual y la mejor se juntan. En esta corrida SA llegó a 7542, el óptimo oficial de berlin52. Es una sola semilla: la distribución está en G.
