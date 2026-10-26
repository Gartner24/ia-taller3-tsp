#%% md
### D.1 A* con MST (sección 7)

Seguimos el pseudocódigo de la sección 7 casi línea por línea:

- La frontera es un montículo (`heapq`) con entradas `(f, -profundidad, contador, nodo)`. El desempate es el de C.5: menor $f$, luego el nodo más profundo, luego el que se generó primero. El contador evita comparar dos nodos directamente.
- `bestG` guarda el mejor $g$ conocido por **clave de estado** `(last, remaining, closed)`. Si llega un hijo con mejor $g$, se inserta aunque el estado ya se haya expandido. Las entradas viejas de la cola se saltan al sacarlas y se cuentan como `stale`.
- La meta se prueba **al sacar** el nodo de la cola, no al generarlo. Con una $h$ admisible, eso garantiza la optimalidad.
- Contamos expansiones, nodos generados, entradas obsoletas, llamadas al MST y el tamaño máximo de la frontera.

El parámetro `key_mode` existe solo para la demostración de D.5. `"last_city"` y `"city_depth"` son reglas de fusión **incorrectas**; la segunda es una versión simplificada de la regla de TSP Solve, que decide por nombre de ciudad con comparaciones de costo y profundidad. `close_cycle=False` es la meta incorrecta de la pregunta 4: aceptar el primer nodo sin pendientes sin cobrar el regreso. Con los valores por defecto, el algoritmo es el correcto y el único que reporta `OPTIMAL`. El parámetro opcional `upper_bound` es la ampliación de la sección 7 y se explica en D.9.
#%% code
def astar(inst, budget=EXACT_BUDGET, h_kind="mst", start=0, use_cache=False, close_cycle=True,
          key_mode="state", trace=None, upper_bound=None):
    """A* over partial routes. key_mode 'last_city' and 'city_depth' are wrong merge rules, kept for the demo.
    upper_bound: optional feasible tour (section 7 extension). A child whose g+h >= its cost is pruned."""
    W, n = inst.W, inst.n
    meter = Meter(**budget)
    H = MSTHeuristic(W, start, h_kind, close_cycle, use_cache)
    key = {"state": state_key,
           "last_city": lambda nd: (nd.last, nd.closed),
           "city_depth": lambda nd: (nd.last, nd.depth, nd.closed)}[key_mode]
    root = root_node(n, start)
    tie = itertools.count()
    open_heap = [(H(root), 0, next(tie), root)]
    best_g = {key(root): 0}
    expanded = generated = stale = pruned = 0
    frontier_peak = 1
    ub_cost = tour_cost(W, upper_bound) if upper_bound is not None else INF
    goal, reason = None, "EXHAUSTED"
    try:
        while open_heap:
            meter.check_search(expanded)
            f, _, _, node = heapq.heappop(open_heap)
            if node.g > best_g[key(node)]:
                stale += 1
                continue
            if node.closed or (not close_cycle and node.remaining == 0):
                goal, reason = node, "GOAL"
                break
            expanded += 1
            children = successors(W, node, start, close_cycle)
            if trace is not None:
                trace.append({"step": expanded, "expanded": reconstruct(node), "g": node.g, "f": f,
                              "frontier_before": len(open_heap) + 1})
            for child in children:
                generated += 1
                k = key(child)
                if child.g < best_g.get(k, INF):
                    f_child = child.g + H(child)
                    if f_child >= ub_cost:      # h is admissible: no completion can beat the upper bound
                        pruned += 1
                        continue
                    best_g[k] = child.g
                    heapq.heappush(open_heap, (f_child, -child.depth, next(tie), child))
            frontier_peak = max(frontier_peak, len(open_heap))
    except Interrupted as stop:
        reason = stop.reason
    elapsed, peak = meter.finish()
    # with an upper bound, an empty open list means nothing beats it: the bound tour is optimal
    tour = reconstruct(goal) if goal is not None else (list(upper_bound) if upper_bound is not None else None)
    cost = tour_cost(W, tour) if tour is not None else None
    exact = (reason == "GOAL" or (reason == "EXHAUSTED" and upper_bound is not None)) \
        and key_mode == "state" and close_cycle
    return RunResult(inst.name, inst.subset, "A* + MST" if h_kind == "mst" else "A* (h=0)", None,
                     dict(h=h_kind, start=start, cache=use_cache, key=key_mode, close_cycle=close_cycle,
                          upper_bound=upper_bound is not None),
                     tour, cost, gap_percent(cost, inst.optimum), elapsed, peak, reason,
                     "OPTIMAL" if exact else ("NO_TOUR" if tour is None else "NOT_CERTIFIED"),
                     expanded=expanded, generated=generated, mst_calls=H.mst_calls, frontier_peak=frontier_peak,
                     stale=stale, extra=dict(cache_hits=H.cache_hits, path_cost=goal.g if goal else None,
                                             pruned=pruned, upper_bound=ub_cost if upper_bound is not None else None))


_chk = astar(micro)
print(f"astar(micro): costo={_chk.cost}, expansiones={_chk.expanded}, estado={_chk.optimality_status}")
#%% md
### D.2 RBFS (secciones 8 y 8.1)

Es el pseudocódigo de la sección 8, con el mismo modelo de estados y la misma cota MST que A*:

- Cada hijo recibe $f = \max(g + h,\ f_{padre})$, donde $f_{padre}$ es el valor **respaldado** con que se llamó al padre.
- Se baja al mejor hijo con límite $\min(\text{límite}, \text{segunda mejor } f)$. Al volver, el hijo guarda el $f$ respaldado que devolvió la llamada (`best[0] = ...`). Por eso cada hijo es una lista mutable `[f, nodo]` y no una copia.
- El orden es estable (`sort` de Python): los empates conservan el orden de generación. Es el desempate de A* sin la profundidad, que entre hermanos es siempre igual.
- Las interrupciones son excepciones (`Interrupted`) que cruzan toda la recursión, así que no se confunden con un fracaso.

**Instrumentación (8.1).** Contamos expansiones, llamadas, profundidad máxima y `retained_peak`: el máximo de registros `[f, nodo]` vivos a la vez en la pila de recursión. En la teoría, ese máximo es $O(bd)$. Las **regeneraciones** se miden con un registro externo de auditoría (`audit=True`): un conjunto con la **ruta exacta** de cada nodo ya expandido. Si la misma ruta vuelve a expandirse, es una regeneración. Usamos la ruta y no la clave de estado porque dos órdenes distintos de las mismas ciudades (una transposición) son nodos distintos para RBFS, y contarlos como repetidos exagera la cifra. Además contamos (`raised`) cuántas veces el máximo de la fórmula sube el valor de un hijo. El conjunto de auditoría crece sin límite, así que **sí altera la memoria**. Por eso las corridas que miden memoria y tiempo van con `audit=False`, y el conteo de regeneraciones sale de una corrida aparte.
#%% code
def rbfs(inst, budget=EXACT_BUDGET, h_kind="mst", start=0, audit=False, trace=None):
    """Recursive best-first search with backed-up f values (section 8). audit=True counts regenerations."""
    W, n = inst.W, inst.n
    meter = Meter(**budget)
    H = MSTHeuristic(W, start, h_kind)
    st = dict(expanded=0, generated=0, calls=0, max_depth=0, retained=1, retained_peak=1, regenerations=0, raised=0)
    seen = set() if audit else None    # external audit record; it costs memory, so it is off when measuring

    def search(node, f_node, limit):
        st["calls"] += 1
        st["max_depth"] = max(st["max_depth"], node.depth)
        meter.check_search(st["expanded"])
        if node.closed:
            return node, f_node
        children = successors(W, node, start)
        st["expanded"] += 1
        st["generated"] += len(children)
        if audit:
            k = tuple(reconstruct(node))      # exact path: a transposition is another node, not a regeneration
            if k in seen:
                st["regenerations"] += 1
            else:
                seen.add(k)
        if not children:
            return None, INF
        gh = [c.g + H(c) for c in children]
        st["raised"] += sum(v < f_node for v in gh)       # children where the max changed the value
        entries = [[max(v, f_node), c] for v, c in zip(gh, children)]
        st["retained"] += len(entries)
        st["retained_peak"] = max(st["retained_peak"], st["retained"])
        try:
            while True:
                entries.sort(key=lambda e: e[0])          # stable: ties keep successor order
                best = entries[0]
                if best[0] == INF or best[0] > limit:
                    return None, best[0]
                alternative = entries[1][0] if len(entries) > 1 else INF
                if trace is not None:
                    trace.append({"call": st["calls"], "node": reconstruct(node), "limit": limit,
                                  "best": reconstruct(best[1]), "best_f": best[0], "alternative": alternative})
                result, best[0] = search(best[1], best[0], min(limit, alternative))
                if result is not None:
                    return result, best[0]
        finally:
            st["retained"] -= len(entries)

    root = root_node(n, start)
    goal, reason = None, "EXHAUSTED"
    try:
        goal, _ = search(root, H(root), INF)
        reason = "GOAL" if goal is not None else "EXHAUSTED"
    except Interrupted as stop:
        reason = stop.reason
    except RecursionError:
        reason = "RECURSION"
    elapsed, peak = meter.finish()
    tour = reconstruct(goal) if goal is not None else None
    cost = tour_cost(W, tour) if tour is not None else None
    return RunResult(inst.name, inst.subset, "RBFS + MST" if h_kind == "mst" else "RBFS (h=0)", None,
                     dict(h=h_kind, start=start, audit=audit), tour, cost, gap_percent(cost, inst.optimum),
                     elapsed, peak, reason, "OPTIMAL" if reason == "GOAL" else "NO_TOUR",
                     expanded=st["expanded"], generated=st["generated"], mst_calls=H.mst_calls,
                     frontier_peak=st["retained_peak"], regenerations=st["regenerations"] if audit else None,
                     calls=st["calls"], max_depth=st["max_depth"], extra=dict(raised=st["raised"]))


_chk = rbfs(micro)
print(f"rbfs(micro): costo={_chk.cost}, expansiones={_chk.expanded}, estado={_chk.optimality_status}")
#%% md
### D.3 Trazas

Primero el microcaso de C.5, para comparar con lo que hicimos a mano. Después una subinstancia de 6 ciudades donde RBFS **sí retrocede**. En las tablas de RBFS, `call` es el valor del contador de llamadas en el momento de escribir la fila. Las llamadas que fallan sin elegir ningún hijo no escriben fila: aquí son la 2 (23-24 la primera vez), la 3 (23-25) y la 9 (el nodo cerrado, que devuelve la ruta directamente).
#%% code
trace_a, trace_r = [], []
res_a = astar(micro, trace=trace_a)
res_r = rbfs(micro, trace=trace_r)
show = lambda rows, cols: pd.DataFrame(rows).assign(**{c: lambda d, c=c: d[c].map(name_of) for c in cols})
print("A* en el microcaso:")
display(show(trace_a, ["expanded"]))
print("RBFS en el microcaso:")
display(show(trace_r, ["node", "best"]))
assert [name_of(t["expanded"]) for t in trace_a] == ["A", "A-B", "A-B-C", "A-B-C-D", "A-B-C-D-E"]
oracle_micro = brute_force(micro)[0]
assert res_a.cost == res_r.cost == oracle_micro and res_a.optimality_status == res_r.optimality_status == "OPTIMAL"
assert [t["limit"] for t in trace_r] == [INF, 14, 14, 14, 14]
#%% code
base = INSTANCES["berlin52"]
pos6 = list(range(22, 28))
case6 = TSPInstance("berlin52", base.weight_type, None, [base.node_ids[p] for p in pos6],
                    base.D[np.ix_(pos6, pos6)].copy(), base.coords[pos6], None, "ids 23-28")
ids6 = case6.node_ids
label6 = lambda path: "-".join(str(ids6[p]) for p in path)
trace6 = []
res6 = rbfs(case6, trace=trace6, audit=True)
t6 = pd.DataFrame(trace6)
for c in ["node", "best"]:
    t6[c] = t6[c].map(label6)
display(t6)
backtracks = sum(1 for a, b in zip(trace6, trace6[1:]) if len(b["node"]) <= len(a["node"]))
print(f"costo {res6.cost} (fuerza bruta {brute_force(case6)[0]}), llamadas {res6.calls}, "
      f"expansiones {res6.expanded}, regeneraciones {res6.regenerations}, retrocesos {backtracks}, "
      f"profundidad máxima {res6.max_depth}, registros vivos como máximo {res6.frontier_peak}")
assert res6.cost == brute_force(case6)[0] and backtracks > 0 and res6.regenerations > 0
H6 = MSTHeuristic(case6.W)
reentry_f = trace6[2]["best_f"]       # backed-up f of 23-24 when the root goes back to it
print(f"hijos de 23-24 al volver a entrar (f respaldado del padre = {reentry_f}):")
for c in successors(case6.W, successors(case6.W, root_node(6))[0]):
    print(f"  {label6(reconstruct(c))}: g+h = {c.g + H6(c)}, f asignado = max(g+h, {reentry_f}) = "
          f"{max(c.g + H6(c), reentry_f)}")
#%% md
**El máximo en acción.** En las 6 ciudades el máximo no cambia ningún valor, así que no sirve para ver por qué está. Buscamos un caso donde sí: berlin52 con $k=8$. Tomamos una entrada de la traza donde RBFS vuelve a un nodo con un $f$ respaldado alto y mostramos, para sus hijos, $g+h$ contra el $f$ que reciben.
#%% code
def node_of(inst, path):
    node = root_node(inst.n)
    for p in path[1:]:
        node = next(c for c in successors(inst.W, node) if c.last == p)
    return node


sub8 = INSTANCES["berlin52"].subproblem(8)
label8 = lambda path: "-".join(str(sub8.node_ids[p]) for p in path)
trace8 = []
res8 = rbfs(sub8, trace=trace8)
H8 = MSTHeuristic(sub8.W)
entry = next(t for t in trace8 if t["best"] == [0, 4] and t["best_f"] == 2202)
print(f"RBFS entra a {label8(entry['best'])} con f respaldado = {entry['best_f']}; sus hijos:")
rows = []
for c in successors(sub8.W, node_of(sub8, entry["best"])):
    gh = c.g + H8(c)
    rows.append({"hijo": label8(reconstruct(c)), "g+h": gh, "f asignado": max(gh, entry["best_f"]),
                 "el máximo lo cambia": gh < entry["best_f"]})
display(pd.DataFrame(rows))
raised8 = rbfs(INSTANCES["att48"].subproblem(8)).extra["raised"]
print(f"asignaciones de f que el máximo sube en toda la corrida (k=8): berlin52 {res8.extra['raised']}, att48 {raised8}")
assert any(r["el máximo lo cambia"] for r in rows) and res8.extra["raised"] > 0
#%% md
**Lo que encontramos (D.3):**

- **Microcaso.** A* expande A, A-B, A-B-C, A-B-C-D y A-B-C-D-E y devuelve 14, igual que a mano en C.5 y igual que la fuerza bruta. RBFS sigue el mismo camino: el límite pasa de $\infty$ a 14 y no cambia. La alternativa de la raíz es 14 porque A-E empata con A-B.
- **Caso de 6 ciudades (berlin52, ids 23 a 28).** Aquí sí hay retroceso. Paso a paso:
  1. En la raíz, 23-24 es el mejor ($f=1646$) y la alternativa es 23-25 (1789). RBFS baja a 23-24 con límite 1789.
  2. Dentro de 23-24, el mejor hijo ya vale 1878 > 1789. La llamada **falla** y devuelve 1878, el valor respaldado. La raíz lo guarda en 23-24. La rama no se borra: queda en espera con un $f$ más alto.
  3. Ahora el mejor es 23-25 (1789) y la alternativa es 1878. RBFS baja a 23-25, que también falla y vuelve con un valor de al menos 1878.
  4. La raíz ordena otra vez: 23-24 (1878) empata con 23-26 (1878) y gana 23-24 por orden de generación. **La rama del paso 2 reaparece** y RBFS la expande de nuevo. Esa es la regeneración que cuenta la auditoría (1). Desde ahí llega a la ruta de costo 1878, igual que la fuerza bruta.

  La corrida hizo 9 llamadas y 8 expansiones. La profundidad máxima fue 6 (un nodo por ciudad más el cierre) y hubo como máximo 17 registros `[f, nodo]` vivos a la vez.
- **La segunda alternativa** es el $f$ del mejor "plan B". Mientras la rama actual no pase de ese valor, conviene seguirla. Cuando lo pasa, se vuelve al plan B. Por eso el límite de cada llamada es $\min(\text{límite}, \text{alternativa})$.
- **Por qué el máximo.** El $f$ respaldado de un nodo resume lo que ya se aprendió de su subárbol. En las 6 ciudades el máximo no cambia ningún número: el 1878 venía justo del mejor nieto (23-24-25 tiene $g+h=1878$). En berlin52 con $k=8$ sí lo cambia. RBFS vuelve a entrar al nodo 1-5 con $f$ respaldado 2202. Su hijo 1-5-6 tiene $g+h=2166$, pero recibe 2202. Sin el máximo, ese hijo parecería más barato de lo que ya sabemos que es, y RBFS volvería a bajar por él una y otra vez. En toda esa corrida el máximo sube 42 asignaciones; en att48 con $k=8$, 249.
#%% md
### D.4 Validación exacta y pruebas de la sección 7

Para cada instancia obligatoria y $k \in \{6, 8, 10, 12\}$ corremos A* (MST y $h=0$), A* con **otro origen** (la última posición) y RBFS, y comparamos contra el oráculo: fuerza bruta hasta $k=10$ y Held-Karp en $k=12$. Las corridas son independientes, así que se reparten entre núcleos con `parallel_map`; cada una mide su propio tiempo.
#%% code
def exact_check(name, k):
    sub = INSTANCES[name].subproblem(k)
    oracle = brute_force(sub)[0] if k <= 10 else held_karp(sub)
    a, a0, a_other, r = astar(sub), astar(sub, h_kind="zero"), astar(sub, start=k - 1), rbfs(sub)
    for res in (a, a0, a_other):
        assert res.stop_reason == "GOAL" and is_valid_tour(res.tour, k, res.parameters["start"])
    assert a.cost == a0.cost == a_other.cost == oracle, (name, k)
    if r.stop_reason == "GOAL":
        assert r.cost == oracle and is_valid_tour(r.tour, k)
    return {"instancia": name, "k": k, "oráculo": oracle, "A* MST": a.cost, "A* h=0": a0.cost,
            "A* otro origen": a_other.cost, "RBFS": r.cost if r.cost is not None else "N/A",
            "RBFS parada": r.stop_reason, "exp. A* MST": a.expanded, "exp. A* h=0": a0.expanded,
            "exp. RBFS": r.expanded, "MST calls A*": a.mst_calls, "obsoletas A*": a.stale,
            "frontera máx A*": a.frontier_peak, "s A*": round(a.elapsed_seconds, 3),
            "s RBFS": round(r.elapsed_seconds, 2)}


exact = pd.DataFrame(parallel_map(exact_check, [(nm, k) for nm in MANDATORY for k in (6, 8, 10, 12)]))
display(exact)
print("A* (MST, h=0 y otro origen) coincide con el oráculo en los 16 casos;",
      f"RBFS terminó en {(exact['RBFS parada'] == 'GOAL').sum()} de 16 y coincide en todos los que terminó")
#%% md
**Lo que encontramos (D.4):**

- **A\* es exacto en los 16 casos.** Con MST, con $h=0$ y desde otro origen da el mismo costo que el oráculo. Cambiar el origen no cambia el óptimo, como debe ser: un ciclo es el mismo empiece donde empiece.
- **La cota MST ahorra mucho trabajo.** Con $h=0$ (costo uniforme), A* expande casi todos los estados posibles: unos 11 260 en $k=12$, en cualquier instancia. Con MST, en $k=12$, expande 376 en att48, 437 en berlin52 y 38 en gr48, entre 25 y 300 veces menos. brazil58 es la más difícil: 4478 expansiones, solo 2.5 veces menos que con $h=0$. También es la que más entradas obsoletas genera (1233), porque muchos estados se alcanzan primero por un camino caro y después por uno mejor.
- **RBFS es exacto cuando termina**, pero cuesta mucho más. En $k=12$ hace 32 375 expansiones en att48 y 80 651 en berlin52, contra 376 y 437 de A*. En brazil58 se corta por el límite de 100 000 expansiones ya en $k=10$ y lo reportamos como **interrumpido** (`N/A`), no como fracaso. La causa son las regeneraciones: RBFS no recuerda los estados y vuelve a expandir los mismos subárboles (las medimos con la auditoría en G).
- Los tiempos de esta tabla se midieron con varios casos corriendo en paralelo. Los tiempos para comparar salen de G, con repeticiones.
#%% md
### D.5 Reglas de fusión y de meta incorrectas (actividad de la sección 5 y preguntas 3 y 4)

Corremos el mismo A* cambiando solo la clave de fusión o la meta, y comparamos con el óptimo certificado:

- `last_city`: fusiona por ciudad final (pregunta 3).
- `city_depth`: fusiona por ciudad y profundidad. Es una regla parecida a la de TSP Solve, que compara nodos por nombre de ciudad y luego decide con el costo y la profundidad. No reprodujimos el código MATLAB de la página, así que esta es solo una regla simplificada.
- `close_cycle=False`: la meta es "no quedan pendientes" y la cota no cobra el regreso (pregunta 4).
#%% code
rows = []
for name, k in [("att48", 6), ("att48", 8), ("brazil58", 10), ("gr48", 10), ("berlin52", 10)]:
    sub = INSTANCES[name].subproblem(k)
    opt = astar(sub).cost
    by_city, by_depth, no_return = (astar(sub, key_mode="last_city"), astar(sub, key_mode="city_depth"),
                                    astar(sub, close_cycle=False))
    rows.append({"instancia": name, "k": k, "óptimo": opt,
                 "last_city": by_city.cost if by_city.cost is not None else f"sin ruta ({by_city.stop_reason})",
                 "city_depth": by_depth.cost, "estado city_depth": by_depth.optimality_status,
                 "sin regreso: camino": no_return.extra["path_cost"], "sin regreso: ciclo": no_return.cost})
merge = pd.DataFrame(rows)
display(merge)
assert all(c != "OPTIMAL" for c in merge["estado city_depth"])
assert (merge["city_depth"] >= merge["óptimo"]).all() and (merge["sin regreso: ciclo"] >= merge["óptimo"]).all()
#%% md
**Lo que encontramos (D.5):**

- **Fusionar por la última ciudad (pregunta 3) no da ninguna ruta.** En los 5 casos A* termina con `EXHAUSTED`. El primer prefijo que llega a cada ciudad es el directo desde el origen, y casi siempre es el más barato. Cualquier prefijo más largo que termine en esa ciudad tiene $g$ mayor y se descarta. Así ningún prefijo pasa de unos pocos niveles y nunca se cierra un ciclo.
- **Fusionar por ciudad y profundidad (la regla parecida a la de TSP Solve) da rutas, pero no óptimas:** 5879 contra 5715 en att48 $k=6$ (el par de C.7), 6083 contra 5919, 19 108 contra 17 652 y 2486 contra 2431. En berlin52 $k=10$ salió el óptimo, 2826, pero por casualidad: la regla no lo garantiza, y por eso el estado es `NOT_CERTIFIED` aunque el número coincida. Es coherente con lo que reporta la página (óptimo solo desde 8 de 48 orígenes en att48), aunque su regla exacta es otra y no podemos afirmar que esta sea la causa.
- **Aceptar como meta "sin pendientes" sin cobrar el regreso (pregunta 4)** devuelve el mejor **camino** abierto, no el mejor ciclo. En att48 $k=6$ el camino cuesta 4151. Al cerrarlo, el ciclo cuesta 6163, un 7.8 % más que el óptimo 5715. El camino más barato puede terminar lejos del origen y el regreso se paga después. En berlin52 $k=10$ también coincidió por casualidad.
#%% md
### D.6 Pruebas de interrupción y casos de RBFS (tabla de la sección 13)

- **Presupuesto:** forzamos cada límite (expansiones, tiempo y memoria) en una subinstancia de 12 ciudades. Debe salir el motivo correcto, sin ruta y con estado `NO_TOUR`. No debe salir un "fracaso" ni una ruta inventada.
- **RBFS, un hijo:** con 2 ciudades cada nodo tiene un único hijo y la alternativa es $\infty$.
- **RBFS, empate:** en la raíz del microcaso, B y E empatan en 14. Gana B por el orden de generación y la alternativa es 14.
- **RBFS, límite:** en la traza de 6 ciudades hay llamadas que devuelven fracaso porque el mejor hijo supera el límite. Después la rama se retoma.
- **Agotamiento:** una instancia sin ciclo posible (todas las aristas de una ciudad con peso infinito). A* y RBFS deben terminar con `EXHAUSTED` y sin ruta.
#%% code
sub12 = INSTANCES["brazil58"].subproblem(12)
for solver in (astar, rbfs):
    for limit, expected in [(dict(expansions=5), "EXPANSIONS"), (dict(seconds=1e-6), "TIME"),
                            (dict(memory_mib=1e-4), "MEMORY")]:
        res = solver(sub12, budget=limit)
        assert res.stop_reason == expected and res.tour is None and res.optimality_status == "NO_TOUR", res
        assert res.stop_reason in INTERRUPTIONS
print("interrupciones forzadas: motivo correcto, sin ruta y sin certificado (A* y RBFS)")

two = TSPInstance("two", "EXPLICIT", None, [1, 2], np.array([[0, 5], [5, 0]]))
tr = []
res = rbfs(two, trace=tr)
assert res.cost == 10 and all(t["alternative"] == INF for t in tr)
assert trace_r[0]["best"] == [0, 1] and trace_r[0]["best_f"] == 14 and trace_r[0]["alternative"] == 14
# a call that fails (best f above its limit) returns before tracing; it shows up as a node visited again later
revisited = [label6(t["node"]) for i, t in enumerate(trace6) if any(u["node"] == t["node"] for u in trace6[:i])]
assert revisited
print("RBFS: un hijo, empate y retroceso verificados; nodos que se retoman en la traza de 6:", sorted(set(revisited)))

blocked = TSPInstance("blocked", "EXPLICIT", None, [1, 2, 3, 4], np.zeros((4, 4)))
blocked.W = [[0, 1, 1, INF], [1, 0, 1, INF], [1, 1, 0, INF], [INF, INF, INF, 0]]
for solver in (astar, rbfs):
    res = solver(blocked)
    assert res.stop_reason == "EXHAUSTED" and res.tour is None, res
print("agotamiento: A* y RBFS terminan con EXHAUSTED y sin ruta")
#%% md
### D.7 Experimento opcional de 6.1: caché del MST

En A*, el mismo conjunto de pendientes aparece en varios estados: un estado es (ciudad, pendientes) y el mismo conjunto puede terminar en cualquiera de sus ciudades. Guardar `MST(U)` por conjunto evita repetir Prim. Medimos tiempo, memoria y llamadas con y sin caché en $k=12$. La caché **no** se usa en RBFS: crece con cada conjunto distinto y contradice la idea de memoria reducida, como advierte 6.1.
#%% code
def cache_run(name, use_cache):
    sub = INSTANCES[name].subproblem(12)
    best = min((astar(sub, use_cache=use_cache) for _ in range(3)), key=lambda r: r.elapsed_seconds)
    return {"instancia": name, "caché": use_cache, "s (mejor de 3)": round(best.elapsed_seconds, 4),
            "memoria MiB": round(best.peak_memory_mib, 2), "llamadas a Prim": best.mst_calls,
            "aciertos de caché": best.extra["cache_hits"], "costo": best.cost}


cache = pd.DataFrame([cache_run(nm, c) for nm in MANDATORY for c in (False, True)])
display(cache)
assert cache.groupby("instancia")["costo"].nunique().eq(1).all()
#%% md
**Lo que encontramos (D.7):** la caché no cambia el resultado y reduce las llamadas a Prim: a la mitad en att48 y berlin52, y a casi la quinta parte en brazil58, donde más se repiten los conjuntos. El tiempo baja menos: unos 23 % en att48, 28 % en berlin52 y 25 % en brazil58, y solo 4 % en gr48, donde casi no hay conjuntos repetidos. Son tiempos de una sola máquina y pueden variar unos puntos. El tiempo baja menos que las llamadas porque, aun con caché, cada estado calcula sus dos mínimos de conexión. La memoria sube un poco. En $k=12$ todo es pequeño, pero el número de conjuntos distintos crece como $2^k$, así que en instancias grandes una caché sin límite consume mucha memoria. Por eso la dejamos apagada en la comparación principal.
#%% md
### D.8 Ampliación: gr17 y burma14 completas

Las dos instancias de ampliación son lo bastante pequeñas para correr los exactos sobre la instancia **completa** y compararlos con el óptimo oficial (3323 y 2085), con el presupuesto de exactos para A* (30 s, 100 000 expansiones, 256 MiB). Para RBFS bajamos el límite de tiempo a **10 s**. Esta ampliación es opcional y RBFS no termina ninguna de las dos, así que 30 s solo alargarían la ejecución. Cuando RBFS se corta lo reportamos como **interrumpido** (`N/A`), no como fracaso.
#%% code
RBFS_EXT_BUDGET = dict(EXACT_BUDGET, seconds=10.0)     # optional extension: RBFS never finishes here, so 10 s instead of 30 s
ext = []
for name in ["burma14", "gr17"]:
    for solver in (astar, rbfs):
        res = solver(INSTANCES[name], budget=RBFS_EXT_BUDGET if solver is rbfs else EXACT_BUDGET)
        ext.append({"instancia": name, "algoritmo": res.algorithm, "costo": res.cost if res.cost else "N/A",
                    "óptimo oficial": INSTANCES[name].optimum, "parada": res.stop_reason,
                    "estado": res.optimality_status, "expansiones": res.expanded,
                    "s": round(res.elapsed_seconds, 2), "MiB": round(res.peak_memory_mib, 1)})
        if res.stop_reason == "GOAL":
            assert res.cost == INSTANCES[name].optimum and res.gap_percent == 0
display(pd.DataFrame(ext))
#%% md
**Lo que encontramos (D.8):** A* certifica el óptimo oficial de las dos instancias completas, 3323 en burma14 y 2085 en gr17, dentro del presupuesto de exactos. gr17 ya necesita unas 21 000 expansiones y unos 35 MiB. RBFS no termina ninguna de las dos y se interrumpe por tiempo a los 10 s de esta ampliación (`N/A`): lleva unas 37 000 expansiones en burma14 y 19 000 en gr17, sin ruta (como el corte es por tiempo, el número exacto cambia entre corridas). Su memoria es menor que 0.05 MiB, pero el tiempo se va en regenerar. Es lo que dice 8.1 en la práctica: menos memoria no significa menos tiempo.
#%% md
### D.9 Ampliación: A* con una ruta inicial como cota superior (sección 7)

La ampliación de la sección 7 pide partir de una ruta factible y usar su costo $UB$ como cota superior. Lo hacemos con el vecino más cercano (`nearest_neighbour`, desempate por la posición menor). `astar(..., upper_bound=ruta)` cambia tres cosas, y el resto es igual a D.1:

- **Poda.** Al generar un hijo con mejor $g$, calculamos $g+h$. Si $g+h \ge UB$, no lo insertamos y lo contamos en `pruned`. La poda es válida porque $h$ es admisible: toda ruta completa que pase por ese hijo cuesta al menos $g+h$, o sea, no mejora estrictamente a $UB$. Por eso no buscamos rutas que empaten con la cota.
- **Certificación.** Si se saca un nodo cerrado, es una ruta estrictamente mejor que $UB$ y es óptima (la meta se prueba al sacar el nodo, como en D.1). Si la cola se vacía sin sacar ninguno, nada mejora a $UB$ y **la ruta inicial es la óptima**; el resultado es `OPTIMAL`, con motivo `EXHAUSTED`. Si el presupuesto se acaba antes, devolvemos la ruta inicial con `NOT_CERTIFIED`.
- **Otras reglas.** La fusión por estado, el desempate y la reapertura con `bestG` no cambian. No usamos ninguna variante que conserve solo los mejores $K$ nodos: no sería A* exacto.

La ruta inicial es un argumento explícito de esta ampliación. Los experimentos de G no la usan: ahí, si A* o RBFS se interrumpen, el resultado sigue siendo `NO_TOUR`.
#%% code
def nearest_neighbour(inst, start=0):
    W = inst.W
    tour, left = [start], set(range(inst.n)) - {start}
    while left:
        nxt = min(sorted(left), key=lambda v: W[tour[-1]][v])      # ties: lowest position
        tour.append(nxt)
        left.remove(nxt)
    return tour


def ub_check(name, k):
    sub = INSTANCES[name].subproblem(k)
    plain = astar(sub)
    nn = nearest_neighbour(sub)
    with_ub = astar(sub, upper_bound=nn)
    assert is_valid_tour(with_ub.tour, k) and with_ub.cost == plain.cost
    assert with_ub.optimality_status == "OPTIMAL" and with_ub.expanded <= plain.expanded
    ub = tour_cost(sub.W, nn)
    return {"instancia": name, "k": k, "óptimo": plain.cost, "UB (vecino más cercano)": ub,
            "UB sobre el óptimo %": round(100 * (ub - plain.cost) / plain.cost, 1),
            "exp. sin UB": plain.expanded, "exp. con UB": with_ub.expanded, "podados": with_ub.extra["pruned"],
            "frontera máx sin UB": plain.frontier_peak, "frontera máx con UB": with_ub.frontier_peak,
            "parada": with_ub.stop_reason}


ub_table = pd.DataFrame(parallel_map(ub_check, [(nm, k) for nm in MANDATORY for k in (6, 8, 10, 12)]))
display(ub_table)
print(f"expansiones totales: sin UB {ub_table['exp. sin UB'].sum()}, con UB {ub_table['exp. con UB'].sum()}; "
      f"suma de las fronteras máximas: sin UB {ub_table['frontera máx sin UB'].sum()}, "
      f"con UB {ub_table['frontera máx con UB'].sum()}")

# the three ways the search can end, on one subproblem
sub = INSTANCES["att48"].subproblem(10)
opt_tour = astar(sub).tour
loose = astar(sub, upper_bound=list(range(sub.n)))             # a poor bound: identity tour
tight = astar(sub, upper_bound=opt_tour)                        # the bound is already optimal
cut = astar(sub, upper_bound=nearest_neighbour(sub), budget=dict(expansions=3))
print(f"cota mala: costo {loose.cost}, parada {loose.stop_reason}, {loose.expanded} expansiones, {loose.extra['pruned']} podados")
print(f"cota óptima: costo {tight.cost}, parada {tight.stop_reason}, estado {tight.optimality_status}, "
      f"{tight.expanded} expansiones, {tight.extra['pruned']} podados")
print(f"presupuesto corto: costo {cut.cost}, parada {cut.stop_reason}, estado {cut.optimality_status}")
assert loose.cost == tight.cost == tour_cost(sub.W, opt_tour) and loose.optimality_status == "OPTIMAL"
assert tight.stop_reason == "EXHAUSTED" and tight.tour == opt_tour and tight.optimality_status == "OPTIMAL"
assert cut.stop_reason == "EXPANSIONS" and cut.optimality_status == "NOT_CERTIFIED" and cut.tour == nearest_neighbour(sub)
#%% md
**Lo que encontramos (D.9):**

- **El resultado no cambia.** En los 16 subproblemas, A* con la cota da el mismo costo que sin ella y el mismo estado `OPTIMAL`. La cota del vecino más cercano queda entre 2.7 % y 19.6 % sobre el óptimo, y en ningún caso es la ruta óptima.
- **Las expansiones no bajan, la frontera sí.** Las expansiones son idénticas en los 16 casos (6956 en total). Tiene sentido: A* con una $h$ admisible solo expande nodos con $f$ menor que el costo óptimo $C^*$, y como $UB \ge C^*$, esos nodos nunca se podan. La poda descarta nodos que de todos modos no se habrían expandido, pero que sí ocupaban la frontera. Sumando las fronteras máximas de los 16 casos pasamos de 9591 a 6369 nodos. La ganancia es de memoria y no de expansiones.
- **Una cota floja casi no poda.** Con la ruta identidad como cota en att48 $k=10$ no se poda ningún nodo. Con el vecino más cercano se podan 507.
- **Una cota óptima certifica por agotamiento.** Con la ruta óptima como cota, la cola se vacía sin sacar ninguna meta nueva: A* termina con `EXHAUSTED`, devuelve la ruta inicial y la marca `OPTIMAL`, con 168 expansiones contra 170 y 706 nodos podados. Las 2 expansiones de menos son coherentes con la poda estricta ($g+h \ge UB$), que descarta también los nodos con $f=C^*$.
- **Con presupuesto corto no hay certificado.** Con 3 expansiones, A* devuelve la ruta del vecino más cercano (costo 6704) como `NOT_CERTIFIED`. Es una ruta válida, pero sin prueba de optimalidad.
