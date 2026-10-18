#%% md
### F.1 OX a mano (actividad de 12.1)

`parent1 = [B,C,D,E,F,G]`, `parent2 = [E,B,G,C,F,D]`, segmento de posiciones 2 a 4 contando desde 1.

1. **Copiar el segmento de parent1** en las mismas posiciones: posiciones 2, 3 y 4 reciben C, D, E. Hijo: `[_, C, D, E, _, _]`.
2. **Posiciones vacías**, recorridas circularmente desde la siguiente al segmento (la 5): **5, 6, 1**.
3. **Orden de lectura de parent2**, circular desde la posición 5: F (pos. 5), D (6), E (1), B (2), G (3), C (4).
4. **Ciudades omitidas** porque ya están en el hijo: D, E y C.
5. **Se rellenan** en orden las que quedan, F, B y G, en las posiciones 5, 6 y 1.

Resultado: **`[G, C, D, E, F, B]`**. Cada ciudad aparece una sola vez. El hijo conserva el **tramo** C-D-E de parent1 y el **orden relativo** F, B, G de parent2.
#%% code
def ox(p1, p2, left, right):
    """Order crossover: keep p1[left..right], fill the rest circularly from right+1 in p2's circular order."""
    m = len(p1)
    child = [None] * m
    child[left:right + 1] = p1[left:right + 1]
    used = set(p1[left:right + 1])
    genes = [g for g in p2[right + 1:] + p2[:right + 1] if g not in used]
    for pos, gene in zip(list(range(right + 1, m)) + list(range(left)), genes):
        child[pos] = gene
    return child


def random_cut(m, rng):
    return tuple(sorted((rng.randrange(m), rng.randrange(m))))       # left == right allowed


def inversion_mutation(chrom, rng):
    i, j = random_cut(len(chrom), rng)
    return chrom[:i] + chrom[i:j + 1][::-1] + chrom[j + 1:]


def tournament(costs, rng, size=3):
    """Index of the cheapest of `size` individuals sampled without replacement; ties go to the first sampled."""
    sample = rng.sample(range(len(costs)), size)
    return min(sample, key=lambda k: costs[k])


p1, p2 = list("BCDEFG"), list("EBGCFD")
child = ox(p1, p2, 1, 3)
print("parent1:", p1, " parent2:", p2, " segmento: posiciones 2..4")
print("lectura de parent2 desde la posición 5:", p2[4:] + p2[:4])
print("omitidas:", [g for g in p2[4:] + p2[:4] if g in p1[1:4]], " hijo:", child)
assert child == list("GCDEFB")

rng = random.Random(11)
for m in (1, 2, 5, 47, 57):
    for _ in range(2000):
        a, b = rng.sample(range(1, m + 1), m), rng.sample(range(1, m + 1), m)
        left, right = random_cut(m, rng)
        for kid in (ox(a, b, left, right), ox(b, a, left, right), inversion_mutation(a, rng)):
            assert sorted(kid) == list(range(1, m + 1))
    for left, right in [(0, 0), (0, m - 1), (m - 1, m - 1), (m // 2, m // 2)]:
        assert sorted(ox(a, b, left, right)) == list(range(1, m + 1))
    assert ox(a, b, 0, m - 1) == a                      # the whole segment: the child is parent1
print("OX e inversión: 30 000 hijos con semillas distintas y cortes frontera, todos permutaciones válidas")

costs = [5, 3, 3, 9]
picks = collections.Counter(tournament(costs, random.Random(s)) for s in range(500))
assert set(picks) <= {1, 2} and all(costs[k] == 3 for k in picks)
r = random.Random(4)
sample = random.Random(4).sample(range(4), 3)
assert tournament(costs, r) == min(sample, key=lambda k: costs[k])
print("torneo: siempre gana un costo mínimo; en empate gana el primero muestreado")

a, b = [1, 2, 3, 4, 5, 6], [6, 5, 4, 3, 2, 1]
one_point = a[:3] + b[3:]
print("cruce de un punto convencional:", one_point, "-> repite", sorted({g for g in one_point if one_point.count(g) > 1}),
      "y omite", sorted(set(a) - set(one_point)))
#%% md
### F.2 GA básico (sección 12)

Decisiones:

- **Cromosoma:** las $n-1$ ciudades sin el origen. Para evaluar se antepone el origen y `tour_cost` cierra el ciclo.
- **Población inicial:** permutaciones aleatorias del generador del GA (no se usa la ruta inicial compartida de HC y SA, ni ninguna ruta `.opt.tour`).
- **Selección:** torneo de 3 sin reemplazo; en empate gana el primero muestreado.
- **Cruce:** con probabilidad $p_c$, `OX(p1, p2)` y `OX(p2, p1)` con los **mismos** cortes; si no, copias de los padres.
- **Mutación:** con probabilidad $p_m$ **por individuo**, inversión de un tramo al azar. Es lo mismo que un 2-opt aplicado sin mirar el costo: el GA lo usa para diversificar, no para mejorar.
- **Elitismo:** las `elite` mejores pasan copiadas con su costo guardado, sin reevaluarse.
- **Duplicados:** se permiten y se miden (no los eliminamos).
- **Presupuesto:** la población inicial cuenta $N$ evaluaciones y cada generación $N - \text{elite}$. Una generación solo empieza si cabe completa (14.1).
- **Diversidad por generación:** fracción de individuos **únicos**, contando una ruta y su reversa como la misma: forma canónica `min(c, c[::-1])` del cromosoma; como el origen está fijo, no hace falta rotar. Y **aristas distintas** en toda la población dividido por $n$: vale 1 si todos son iguales. La forma canónica solo se usa para contar; la evaluación usa el cromosoma tal cual.
#%% code
def genetic_algorithm(inst, budget, rng, pop_size, elite, pc, pm, tsize=3):
    W, n = inst.W, inst.n
    meter = Meter(seconds=budget["seconds"], evaluations=budget["evaluations"])
    evaluate = lambda chrom: tour_cost(W, [0] + chrom)
    pop = [rng.sample(range(1, n), n - 1) for _ in range(pop_size)]
    costs = [evaluate(c) for c in pop]
    evals = pop_size
    best_k = min(range(pop_size), key=lambda k: costs[k])
    best, best_cost = pop[best_k][:], costs[best_k]
    history, gen_log = [(evals, meter.elapsed(), best_cost)], []

    def log(gen):
        canon = {min(tuple(c), tuple(c[::-1])) for c in pop}
        edges = {frozenset(e) for c in pop for e in zip([0] + c, c + [0])}
        gen_log.append({"generation": gen, "evals": evals, "best": best_cost, "median": statistics.median(costs),
                        "unique": len(canon) / pop_size, "edge_diversity": len(edges) / n})

    log(0)
    reason, gen = None, 0
    while reason is None:
        if meter.elapsed() >= budget["seconds"]:
            reason = "TIME"
        elif meter.out_of_evaluations(evals, needed=pop_size - elite):
            reason = meter.reason
        if reason:
            break
        order = sorted(range(pop_size), key=lambda k: costs[k])
        new_pop, new_costs = [pop[k][:] for k in order[:elite]], [costs[k] for k in order[:elite]]
        while len(new_pop) < pop_size:
            a, b = pop[tournament(costs, rng, tsize)], pop[tournament(costs, rng, tsize)]
            if rng.random() < pc:
                left, right = random_cut(n - 1, rng)
                children = [ox(a, b, left, right), ox(b, a, left, right)]
            else:
                children = [a[:], b[:]]
            for child in children:
                if len(new_pop) == pop_size:
                    break
                if rng.random() < pm:
                    child = inversion_mutation(child, rng)
                assert len(child) == n - 1 and len(set(child)) == n - 1 and 0 not in child
                new_pop.append(child)
                new_costs.append(evaluate(child))
                evals += 1
        pop, costs = new_pop, new_costs
        gen += 1
        k = min(range(pop_size), key=lambda i: costs[i])
        if costs[k] < best_cost:
            best, best_cost = pop[k][:], costs[k]
            history.append((evals, meter.elapsed(), best_cost))
        log(gen)
    elapsed, peak = meter.finish()
    tour = [0] + best
    assert is_valid_tour(tour, n) and tour_cost(W, tour) == best_cost
    return RunResult(inst.name, inst.subset, "GA básico", None,
                     dict(pop=pop_size, elite=elite, pc=pc, pm=pm, tournament=tsize, budget=budget["evaluations"]),
                     tour, best_cost, gap_percent(best_cost, inst.optimum), elapsed, peak, reason, "NOT_CERTIFIED",
                     candidate_evaluations=evals, history=history, extra=dict(generations=gen, gen_log=gen_log))
#%% md
**Pruebas del GA:** el presupuesto nunca se excede y las evaluaciones son exactamente $N + \text{generaciones}\cdot(N-\text{elite})$, lo que confirma que las élites no se reevalúan. Con elitismo, el mejor de cada generación nunca empeora. Después, una corrida de ejemplo en berlin52.
#%% code
inst = INSTANCES["berlin52"]
for pop_size, elite in [(40, 1), (80, 2)]:
    res = genetic_algorithm(inst, dict(evaluations=10_000, seconds=30), random.Random(5), pop_size, elite, 0.9, 0.3)
    glog = pd.DataFrame(res.extra["gen_log"])
    assert res.candidate_evaluations == pop_size + res.extra["generations"] * (pop_size - elite) <= 10_000
    assert res.candidate_evaluations + (pop_size - elite) > 10_000 and res.stop_reason == "EVALUATIONS"
    assert glog["best"].is_monotonic_decreasing and res.cost == glog["best"].iloc[-1]
print("GA: presupuesto exacto, élites sin reevaluar, mejor monótono")

demo_ga = genetic_algorithm(inst, dict(evaluations=30_000, seconds=30), random.Random(0), 80, 2, 0.9, 0.3)
glog = pd.DataFrame(demo_ga.extra["gen_log"])
display(glog.iloc[::40])
print(f"costo final {demo_ga.cost} (gap {demo_ga.gap_percent:.1f} %), {demo_ga.extra['generations']} generaciones")
#%% md
**Lo que encontramos (F):**

- OX e inversión siempre devuelven permutaciones válidas, también con cortes en los extremos; el cruce de un punto convencional, en cambio, repite y omite ciudades.
- En la corrida de ejemplo las dos medidas de diversidad cuentan cosas distintas. Las **aristas distintas** bajan sin parar: de unas 24 por ciudad al inicio a menos de 2 al final, o sea, casi toda la población usa las mismas aristas. La fracción de **únicos** sigue cerca de 1 hasta la generación 100 y después oscila entre 0.3 y 0.8: los individuos siguen siendo "distintos", pero solo por unas pocas inversiones de la misma ruta. Al mismo tiempo la mediana de la población se pega al mejor. Esas son señales de convergencia: el cruce ya casi no tiene material nuevo que combinar.
- Con 30 000 evaluaciones terminó en 8004 (gap 6.1 %). Es una sola semilla y sin calibrar; en G calibramos y medimos 10 semillas (pregunta 8).
