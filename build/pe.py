#%% md
### E.1 Vecindad 2-opt y swap (sección 9)

Una ruta es una lista `route[0..n-1]` con el origen en la posición 0. Un movimiento 2-opt `(i, j)` quita las aristas `(route[i], route[i+1])` y `(route[j], route[(j+1) mod n])` e invierte el tramo de posiciones $i+1$ a $j$. Como $i \ge 0$, el tramo nunca incluye la posición 0 y el origen no se mueve.

- `two_opt_pairs(n)` lista los pares válidos: $0 \le i < j < n$, sin $j = i+1$ (aristas que se tocan) y sin $(0, n-1)$ (las dos aristas comparten el origen). Deben ser $n(n-3)/2$.
- `two_opt_delta` calcula $\Delta = d(a,c) + d(b,d) - d(a,b) - d(c,d)$ en $O(1)$. Cuando $j = n-1$, la arista $(c, d)$ es la de **cierre**, de vuelta al origen.
- `swap_move` intercambia dos ciudades. Lo usamos solo para compararlo con 2-opt; ningún algoritmo lo usa.

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
**Lo que encontramos (E.1):** el delta coincide con el recálculo completo en todos los movimientos probados, incluidos los que tocan la arista de cierre, y cada 2-opt cambia exactamente 2 aristas. Con 5 ciudades **todo** swap coincide con algún 2-opt, como vimos a mano en C.5. Desde 6 ciudades aparecen swaps que cambian 4 aristas y no son ningún 2-opt.

Un swap cambia solo 2 aristas, y entonces es un 2-opt, cuando las dos posiciones son vecinas o tienen exactamente una ciudad entre ellas. Esto incluye el par que rodea al origen (las posiciones 1 y $n-1$). En otro caso cambia 4 aristas. Con $n=8$ lo vimos así: los 12 swaps de 2 aristas son 6 de posiciones vecinas, 5 con una ciudad en medio y 1 alrededor del origen. Los otros 9 cambian 4 aristas.
#%% md
### E.2 Hill Climbing (sección 10)

`hill_climbing` recorre **todo** el vecindario 2-opt, elige la mejor mejora estricta y la aplica. Se detiene cuando ningún movimiento mejora (`LOCAL_OPTIMUM`) o cuando se acaba el presupuesto. La interrupción de la sección 10 (`INTERRUPTED`) es, en nuestro código, `EVALUATIONS` o `TIME`. Si el presupuesto corta un recorrido a la mitad, **no** reportamos óptimo local.

- **Evaluaciones.** Cada delta calculado cuenta 1. Calcular el costo de una ruta completa (la inicial o la de un reinicio) también cuenta 1. Revisamos el presupuesto **antes** de cada evaluación, así que nunca se pasa.
- **Reinicios** (`restarts=True`): al llegar a un óptimo local, empieza desde una ruta aleatoria nueva y conserva la mejor global. Los reinicios comparten el mismo presupuesto.
- **Primera mejora** (`first_improvement=True`): recorre los pares en orden aleatorio y aplica la primera que mejore. Solo la usamos en el experimento aparte de E.3.
- **Empates.** Solo una mejora estricta ($\Delta < 0$) reemplaza al mejor movimiento. Si dos movimientos tienen el mismo $\Delta$, gana el primero en el orden de `two_opt_pairs`.
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


_chk_inst = INSTANCES["berlin52"].subproblem(10)
_chk = hill_climbing(_chk_inst, initial_tour(_chk_inst, 0), dict(evaluations=2000, seconds=5.0), random.Random(0))
print(f"HC berlin52 k=10: costo={_chk.cost}, parada={_chk.stop_reason}, evaluaciones={_chk.candidate_evaluations}")
#%% md
**Pruebas de HC (tabla de la sección 13).**

- **Óptimo local.** Dejamos que HC llegue a `LOCAL_OPTIMUM` en las cuatro instancias. Después, **por fuera del algoritmo**, aplicamos cada uno de los $n(n-3)/2$ movimientos a la ruta final y recalculamos el costo completo. Ninguno debe mejorar.
- **Cruces.** Contamos los cruces en las rutas de att48 y berlin52, las que tienen coordenadas: pares de aristas del dibujo que se cortan. Sirve para la pregunta de la sección 10.
- **Interrupción forzada.** Con 500 evaluaciones debe salir `EVALUATIONS`, con una ruta válida y a lo más 500 evaluaciones. Con un límite de tiempo minúsculo debe salir `TIME`, también con una ruta válida. Lo probamos con y sin reinicios.
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

# forced interruptions: our EVALUATIONS and TIME are the teacher's INTERRUPTED
inst = INSTANCES["berlin52"]
for restarts in (False, True):
    res = hill_climbing(inst, initial_tour(inst, 0), dict(evaluations=500, seconds=30), random.Random(0), restarts=restarts)
    assert res.stop_reason == "EVALUATIONS" and is_valid_tour(res.tour, inst.n) and res.candidate_evaluations <= 500
    res_t = hill_climbing(inst, initial_tour(inst, 0), dict(evaluations=10**7, seconds=1e-9), random.Random(0), restarts=restarts)
    assert res_t.stop_reason == "TIME" and is_valid_tour(res_t.tour, inst.n)
    print(f"HC (reinicios={restarts}): EVALUATIONS con {res.candidate_evaluations} evaluaciones; "
          f"TIME con {res_t.candidate_evaluations}; en los dos casos devuelve una ruta válida")
#%% md
**Contraejemplo de la pregunta (sección 10).** Seis puntos en el plano, con distancia euclidiana exacta: A(0,0), B(10,0), C(10,10), D(0,10), E(5,3) y F(5,7). Enumeramos las 120 rutas desde A, contamos los cruces de cada una y buscamos la mejor ruta sin cruces y la óptima.
#%% code
pts = np.array([[0, 0], [10, 0], [10, 10], [0, 10], [5, 3], [5, 7]], dtype=float)
Wp = np.hypot(pts[:, None, 0] - pts[None, :, 0], pts[:, None, 1] - pts[None, :, 1])
letters = "ABCDEF"
tours = [[0] + list(p) for p in itertools.permutations(range(1, 6))]
costs_p = [tour_cost(Wp, t) for t in tours]
free = [(c, t) for c, t in zip(costs_p, tours) if count_crossings(pts, t) == 0]
best_c = min(costs_p)
opt_t = tours[costs_p.index(best_c)]
bad = [0, 1, 2, 3, 5, 4]                                      # A-B-C-D-F-E
bad_improving = sum(two_opt_delta(Wp, bad, i, j) < -1e-9 for i, j in two_opt_pairs(6))
print(f"A-B-C-D-F-E: costo {tour_cost(Wp, bad):.2f}, cruces {count_crossings(pts, bad)}, "
      f"2-opt que lo mejoran {bad_improving}")
print(f"óptima: {'-'.join(letters[v] for v in opt_t)}, costo {best_c:.2f}, cruces {count_crossings(pts, opt_t)}")
print(f"rutas sin cruces: {len(free)} de {len(tours)}, sus costos distintos (2 decimales): "
      f"{sorted({round(float(c), 2) for c, _ in free})}")
assert count_crossings(pts, bad) == 0 and tour_cost(Wp, bad) > best_c + 1
assert count_crossings(pts, opt_t) == 0
#%% md
**Lo que encontramos (E.2):**

- En las cuatro instancias HC termina en un óptimo local **verificado**: con el recálculo completo, ningún 2-opt mejora la ruta final.
- **Llegar al primer óptimo local cuesta más de 30 000 evaluaciones** (columna de evaluaciones) desde una ruta aleatoria. Cada pasada del vecindario son más de 1000 evaluaciones y hacen falta decenas de mejoras. Con el presupuesto de 30 000 de la sección 14, HC se cortaría antes de terminar su primer descenso. Usamos este dato en G para fijar el presupuesto.
- **Interrupción.** Con 500 evaluaciones HC se detiene con `EVALUATIONS`, y con un tiempo minúsculo con `TIME` (en la evaluación 1024, la primera en que se revisa el reloj). En los cuatro casos devuelve una ruta válida.

**Respuesta a la pregunta de la sección 10: ¿una ruta sin cruces visibles es necesariamente óptima? No.**

- **Caso geométrico.** Si dos aristas se cruzan, cambiarlas por las dos que descruzan el tramo baja el costo con distancia euclidiana exacta, por la desigualdad triangular. Por eso un óptimo local de 2-opt en el plano no tiene cruces. Con distancias redondeadas (ATT, EUC_2D) la mejora puede ser 0. La condición es **necesaria pero no suficiente**: las rutas finales de att48 y berlin52 no tienen ningún cruce y aun así su gap es mayor que 0 (5.26 % y 7.57 %).
- **Contraejemplo.** Con los 6 puntos de arriba, la ruta A-B-C-D-F-E cuesta 45.66 y no tiene cruces. Ningún 2-opt la mejora, así que es un óptimo local. La ruta óptima, A-D-F-C-B-E, cuesta 43.32 y tampoco tiene cruces. De las 120 rutas, 26 no tienen cruces y sus costos son 5 valores distintos.
- **Matriz explícita (brazil58, gr48).** Solo hay costos, no posiciones, así que no existe un dibujo real. Cualquier ruta se puede dibujar sin cruces si ponemos las ciudades en un círculo en el orden de la ruta, así que "no se ve cruce" no dice nada. Además, sin desigualdad triangular ni siquiera descruzar tiene que mejorar el costo. La única evidencia es comparar el costo con el óptimo conocido: en la tabla, brazil58 queda 6.54 % y gr48 4.70 % por encima.
#%% md
### E.3 Primera mejora contra mejor mejora (experimento aparte)

Lo corremos en las subinstancias de 20 ciudades de las cuatro instancias, con 10 semillas, desde la misma ruta inicial y hasta llegar al óptimo local. No se mezcla con la comparación principal.
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
**Lo que encontramos (E.3):** en 20 ciudades, las dos variantes llegan a óptimos locales de calidad parecida. Las medianas casi coinciden (la mayor diferencia es 1 % en att48) y el mejor costo de las 10 semillas es igual o cercano. La diferencia está en el trabajo: primera mejora usa entre 3.8 y 4.9 veces menos evaluaciones, porque no recorre todo el vecindario antes de moverse. Con 20 ciudades no vemos una diferencia clara de calidad. Para afirmarlo en las instancias completas habría que medirlo allí. No lo mezclamos con la comparación principal, que usa mejor mejora como pide la sección 10.
#%% md
### E.4 Simulated Annealing (sección 11)

`simulated_annealing` sigue el pseudocódigo de la sección 11 con la misma vecindad 2-opt:

- **Calibración de $T_0$.** Desde la ruta inicial evaluamos 100 movimientos al azar (cuentan en el presupuesto) y tomamos la mediana de los deltas positivos: $T_0 = -\operatorname{mediana}(\Delta^+)/\ln(p_0)$. Así, al principio, un empeoramiento típico se acepta con probabilidad $p_0$. **Regla de respaldo:** si ninguno de los 100 deltas es positivo, usamos $T_0 = \operatorname{mediana}(|\Delta|)/(-\ln p_0)$ sobre los deltas distintos de cero. Dividimos por $-\ln p_0$ para que también aquí un cambio típico se acepte con probabilidad $p_0$. Si todos los deltas son cero, $T_0 = 1$. La regla usada queda registrada en `extra`.
- **Enfriamiento.** $T_{min} = 10^{-3}\,T_0$ y $T \leftarrow \alpha T$. El número de niveles es $L = \lceil \ln(10^{-3}) / \ln \alpha \rceil$ y cada nivel recibe `steps` = (presupuesto restante) // $L$ propuestas. Así cualquier $\alpha$ usa todo el presupuesto y termina al enfriarse (`TMIN`); si no, para por presupuesto.
- **Aceptación.** $\Delta \le 0$ siempre se acepta (mejoras y empates). Si $\Delta > 0$, se acepta con probabilidad $e^{-\Delta/T}$.
- **Mejor contra actual.** `current` y `best` son listas distintas y se devuelve `best`.
- **Registro por nivel.** La ventana de aceptación es **un nivel de temperatura**. Guardamos $T$, el costo actual, el mejor costo y la tasa de aceptación de empeoramientos: aceptados con $\Delta > 0$ entre propuestos con $\Delta > 0$.
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
        t0, t0_rule = ((statistics.median(nonzero) / -math.log(p0), "median |delta| / -ln(p0) (no positive deltas)")
                       if nonzero else (1.0, "T0 = 1"))
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


_chk_inst = INSTANCES["berlin52"].subproblem(10)
_chk = simulated_annealing(_chk_inst, initial_tour(_chk_inst, 0), dict(evaluations=2000, seconds=5.0), random.Random(0), alpha=0.9, p0=0.5)
print(f"SA berlin52 k=10: costo={_chk.cost}, parada={_chk.stop_reason}, evaluaciones={_chk.candidate_evaluations}")
#%% md
**Pruebas de SA (tabla de la sección 13).**

- **Mejor distinta de la actual.** Con $p_0 = 0.8$ y un enfriamiento que se detiene todavía caliente ($T_{min} = T_0/2$), la ruta actual termina peor que la mejor observada. Debe devolverse la mejor.
- **Presupuesto y validez.** El presupuesto nunca se excede, la ruta devuelta es una permutación válida y su costo coincide con `tour_cost`.
- **Interrupción forzada.** Con 500 evaluaciones debe salir `EVALUATIONS` y con un tiempo minúsculo `TIME`, siempre con una ruta válida.
- **Regla de respaldo de $T_0$.** Se activa solo si ningún delta de prueba es positivo. La probamos en dos casos reales. En el primero, todos los pesos son iguales y todos los deltas valen 0 (debe salir $T_0 = 1$). En el segundo, empezamos desde la **peor ruta** de una instancia de 7 ciudades, donde ningún 2-opt puede subir el costo, todos los deltas son menores o iguales a 0 y hay algunos negativos. Además mostramos que arrancar desde el óptimo local de E.2 **no** activa el respaldo: ahí hay deltas positivos y se usa la regla principal.
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

res = simulated_annealing(inst, initial_tour(inst, 0), dict(evaluations=500, seconds=30), random.Random(0), alpha=0.99, p0=0.5)
assert res.stop_reason == "EVALUATIONS" and is_valid_tour(res.tour, inst.n) and res.candidate_evaluations <= 500
res_t = simulated_annealing(inst, initial_tour(inst, 0), dict(evaluations=10**7, seconds=1e-9), random.Random(0), alpha=0.99, p0=0.5)
assert res_t.stop_reason == "TIME" and is_valid_tour(res_t.tour, inst.n)
print(f"SA interrumpido: EVALUATIONS con {res.candidate_evaluations} evaluaciones, TIME con {res_t.candidate_evaluations}; "
      "los dos devuelven una ruta válida")

flat = TSPInstance("flat", "EXPLICIT", None, list(range(1, 9)), np.ones((8, 8), dtype=np.int64) - np.eye(8, dtype=np.int64))
res = simulated_annealing(flat, list(range(8)), dict(evaluations=500, seconds=5), random.Random(0), alpha=0.9, p0=0.5)
assert res.extra["T0_rule"] == "T0 = 1" and res.cost == 8
print("SA con todos los deltas en 0: regla de respaldo", res.extra["T0_rule"])

res = simulated_annealing(inst, hill_climbing(inst, initial_tour(inst, 0), BIG, random.Random(0)).tour,
                          dict(evaluations=5000, seconds=30), random.Random(1), alpha=0.9, p0=0.5)
print("SA desde un óptimo local: regla", res.extra["T0_rule"], f"T0 = {res.extra['T0']:.1f}")

# fallback rule for real: the worst tour of a 7-city instance has no improving move, but many that lower the cost
small = INSTANCES["att48"].subproblem(7)
worst = max(([0] + list(p) for p in itertools.permutations(range(1, 7))), key=lambda t: tour_cost(small.W, t))
deltas = [two_opt_delta(small.W, worst, i, j) for i, j in two_opt_pairs(7)]
assert max(deltas) <= 0 and min(deltas) < 0
res = simulated_annealing(small, worst, dict(evaluations=500, seconds=5), random.Random(0), alpha=0.9, p0=0.5)
assert res.extra["T0_rule"].startswith("median |delta|") and res.extra["T0"] > 0
print(f"SA desde la peor ruta de 7 ciudades (deltas entre {min(deltas)} y {max(deltas)}): regla {res.extra['T0_rule']}, "
      f"T0 = {res.extra['T0']:.1f}; con p0 = 0.5 vale mediana/{-math.log(0.5):.3f}")

demo_sa = simulated_annealing(inst, initial_tour(inst, 0), dict(evaluations=200_000, seconds=30),
                              random.Random(0), alpha=0.97, p0=0.5)
display(pd.DataFrame(demo_sa.extra["levels"]).iloc[::25])
print(f"corrida de ejemplo: costo actual final {demo_sa.extra['final_current']}, mejor {demo_sa.cost}, parada {demo_sa.stop_reason}")
#%% md
**Lo que encontramos (E.4):**

- La mejor ruta y la actual se separan: si la corrida termina caliente, la actual queda peor y el algoritmo devuelve la mejor. En las 5 corridas cortas pasó las 5 veces. En la corrida de ejemplo con enfriamiento completo ($T_{min} = 10^{-3} T_0$) terminaron iguales (7542), porque al final SA se comporta como un descenso. Es una sola corrida; no la generalizamos.
- Desde un óptimo local de 2-opt los deltas de prueba son mayores o iguales a cero y hay positivos (T0 = 1162.8), así que se usa la regla principal. Un óptimo local no deja $T_0$ sin definir.
- La regla de respaldo solo se activa en casos degenerados. La probamos con la matriz de pesos iguales ($T_0 = 1$) y con la peor ruta de 7 ciudades (deltas entre -3779 y -24), donde dio $T_0 = 1846.6$, la mediana de $|\Delta|$ dividida por $-\ln 0.5$.
- Con 500 evaluaciones SA se detiene con `EVALUATIONS` y con un tiempo minúsculo con `TIME` (en la evaluación 1024), siempre con una ruta válida.
- En la corrida de ejemplo (berlin52, $\alpha = 0.97$, $p_0 = 0.5$) la temperatura empieza alta y se acepta cerca del 38 % de los empeoramientos. Es algo menos que $p_0$, porque $T_0$ se calibró con la mediana y la mitad de los empeoramientos son mayores. La ruta actual sube y baja. Al enfriarse, la tasa cae casi a 0 y la actual y la mejor se juntan. SA llegó a 7542, el óptimo oficial de berlin52. Es una sola semilla; la distribución está en G.
