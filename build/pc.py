#%% md
### C.1 Lectura crítica de TSP Solve (actividad de la sección 1)

Leímos el código MATLAB de las tres páginas: A*, RBFS y Hill Climbing. No lo reprodujimos ni lo ejecutamos; solo lo leímos. Esto encontramos.

**1. El "2-opt" del Hill Climbing es un swap.** La función `getNextSolution` hace:

```matlab
tempNode = newTour(p1);
newTour(p1) = curState.node(p2);
newTour(p2) = tempNode;
```

Eso **intercambia las ciudades** de las posiciones `p1` y `p2`. El comentario y el texto lo llaman "2-opt neighbours", pero es un swap. Un swap cambia **2 aristas** (y entonces coincide con un 2-opt) solo cuando las posiciones son vecinas o tienen exactamente una ciudad entre ellas, incluido el par que rodea al origen. En los demás pares cambia **4 aristas**, y un 2-opt siempre cambia **2**. Con n = 8 y el origen fijo hay 21 pares de posiciones: 12 cambian 2 aristas (6 vecinas, 5 con una ciudad en medio y 1 alrededor del origen) y 9 cambian 4. Para que fuera 2-opt habría que invertir el tramo entre las dos aristas, por ejemplo con `newTour(p1+1:p2) = flip(newTour(p1+1:p2))` (en E.1 lo comprobamos con código). Además, el ciclo acepta mejoras **dentro** del mismo recorrido del vecindario. No es "mejor mejora" sino una mezcla de primera mejora con barrido completo.

**2. La clave de estado del A\* "de grafo" es la ciudad.** Las listas `open` y `closed` se buscan con `ismember(nodelist(i).name, {closed.name})`: dos rutas parciales que terminan en la misma ciudad se tratan como **el mismo estado**, aunque les falten ciudades distintas. Luego decide con comparaciones de costo y **profundidad** (`s.depth > s_inClosed.depth`), que tampoco identifican el estado. Con esa regla se pueden descartar prefijos de la ruta óptima. Esto es **coherente con** lo que reporta la página: el óptimo solo desde 8 de los 48 orígenes de att48, y entre 10648 y 10795 en el resto. La página no da la causa y no reprodujimos su código MATLAB, así que no podemos afirmar que esta sea la explicación. **La clave correcta es `(última ciudad, conjunto de pendientes, cerrado)`**, la de la sección 5. En D.5 usamos una regla simplificada parecida (`key_mode="city_depth"`, no es la de TSP Solve) y nuestro A* también pierde el óptimo.

**3. Otros detalles del código:**

- En la versión de árbol y en RBFS, la `f` es `node.cost = node.h_n + node.g_n - node.depth`: le **resta la profundidad**. Eso ya no es $g+h$. Además, `isGoal` devuelve `solution.cost = node.cost`, así que el costo reportado queda corrido en $n-1$.
- En RBFS, `suc = nodelist(i); suc.cost = max(...)` modifica una **copia**, porque en MATLAB las estructuras se copian por valor. Por eso el `max` con la `f` del padre nunca se guarda en `nodelist`.
- La sección de código "A* (tree search)" llama a `RBFS(...)`: es una copia del código de RBFS.

**Qué debería tener la clave de un estado de A\*:** la ciudad actual, el **conjunto** de ciudades pendientes y si el ciclo ya se cerró, con el origen fijo. Dos nodos con la misma clave tienen las mismas continuaciones posibles. Por eso, entre ellos, basta quedarse con el de menor $g$. Esa es la única fusión segura.

No usamos los tiempos publicados como meta: son de otro lenguaje, otra máquina y otro código.
#%% md
### C.2 Modelo de búsqueda: rutas parciales (sección 5)

Un nodo guarda `last`, `remaining`, `g`, `closed`, `parent` y `depth`. Guardamos las ciudades pendientes como una **máscara de bits**: el bit $v$ vale 1 si la ciudad $v$ falta. Así la clave `(last, remaining, closed)` no cambia y sirve como llave de un diccionario. Generamos los sucesores en orden creciente de posición, y por eso todo es determinista.
#%% code
@dataclass(frozen=True, slots=True)
class SearchNode:
    last: int
    remaining: int        # bitmask over positions still to visit
    g: int
    closed: bool
    parent: object
    depth: int


def bits(mask):
    """Positions set in mask, in increasing order (deterministic successor order)."""
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low


def root_node(n, start=0):
    return SearchNode(start, ((1 << n) - 1) & ~(1 << start), 0, False, None, 0)


def successors(W, node, start=0, close_cycle=True):
    if node.closed:
        return []
    if node.remaining == 0:
        if not close_cycle:
            return []
        return [SearchNode(start, 0, node.g + W[node.last][start], True, node, node.depth + 1)]
    return [SearchNode(v, node.remaining & ~(1 << v), node.g + W[node.last][v], False, node, node.depth + 1)
            for v in bits(node.remaining)]


def state_key(node):
    return (node.last, node.remaining, node.closed)


def reconstruct(node):
    path = []
    while node is not None:
        path.append(node.last)
        node = node.parent
    path.reverse()
    return path[:-1] if len(path) > 1 and path[-1] == path[0] else path   # drop the closing return


_chk = INSTANCES["berlin52"].subproblem(5)
_chk_kids = successors(_chk.W, root_node(_chk.n))
print(f"berlin52 k=5: la raíz tiene {len(_chk_kids)} sucesores; primer hijo state_key={state_key(_chk_kids[0])}, g={_chk_kids[0].g}")
#%% md
### C.3 Prim en $O(|U|^2)$ y la cota MST (secciones 6 y 6.1)

`prim` guarda, para cada ciudad que todavía no está en el árbol, su conexión más barata al árbol. En cada paso agrega la más barata y actualiza las demás en una sola pasada. Son $|U|$ pasos de $O(|U|)$, o sea $O(|U|^2)$, como pide 6.1.

`MSTHeuristic` aplica la fórmula de la sección 6 y cuenta las llamadas al MST. La opción `use_cache` guarda el MST de cada conjunto de pendientes. Es el experimento opcional de 6.1 y solo lo usamos en D.6. Con `kind="zero"` la heurística vale siempre 0 y A* se vuelve búsqueda de costo uniforme.
#%% code
def prim(W, nodes):
    """MST of the complete graph on `nodes` with O(k^2) Prim: keep each outside node's cheapest link."""
    nodes = list(nodes)
    if len(nodes) <= 1:
        return 0, []
    best = {v: (W[nodes[0]][v], nodes[0]) for v in nodes[1:]}
    total, edges = 0, []
    while best:
        v = min(best, key=lambda u: best[u][0])
        cost, parent = best.pop(v)
        total += cost
        edges.append((parent, v))
        for u in best:
            if W[v][u] < best[u][0]:
                best[u] = (W[v][u], v)
    return total, edges


class MSTHeuristic:
    """h(v, U) of section 6. kind='zero' gives h = 0 (uniform-cost search) with the same interface."""

    def __init__(self, W, start=0, kind="mst", close_cycle=True, use_cache=False):
        self.W, self.start, self.kind, self.close_cycle = W, start, kind, close_cycle
        self.cache = {} if use_cache else None
        self.mst_calls = 0
        self.cache_hits = 0

    def mst(self, mask):
        if self.cache is not None and mask in self.cache:
            self.cache_hits += 1
            return self.cache[mask]
        self.mst_calls += 1
        value = prim(self.W, bits(mask))[0]
        if self.cache is not None:
            self.cache[mask] = value
        return value

    def __call__(self, node):
        if node.closed or self.kind == "zero":
            return 0
        W, s = self.W, self.start
        if node.remaining == 0:
            return W[node.last][s] if self.close_cycle else 0
        U = list(bits(node.remaining))
        h = self.mst(node.remaining) + min(W[node.last][u] for u in U)
        if self.close_cycle:
            h += min(W[u][s] for u in U)
        return h


_chk = INSTANCES["berlin52"].subproblem(5)
print(f"berlin52 k=5: MST de las 5 ciudades = {prim(_chk.W, range(5))[0]}, h(raíz) = {MSTHeuristic(_chk.W)(root_node(_chk.n))}")
#%% md
### C.4 Por qué la cota MST es admisible (con nuestras palabras)

Estamos en la ciudad $v$, nos faltan las ciudades $U$ y el origen es $s$. Tomemos **cualquier** forma de terminar el ciclo: $v \to u_1 \to u_2 \to \dots \to u_m \to s$, donde $u_1, \dots, u_m$ son las ciudades de $U$ en algún orden. Su costo tiene tres partes:

1. **La primera arista** $v \to u_1$. Como $u_1$ está en $U$, cuesta al menos $\min_{u\in U} d(v,u)$.
2. **El camino interno** $u_1 \to \dots \to u_m$. Es un camino que toca todas las ciudades de $U$ sin ciclos. Un camino que cubre $U$ es un **árbol generador** de $U$. El MST es el árbol generador más barato, así que este camino cuesta al menos $\operatorname{MST}(U)$.
3. **La última arista** $u_m \to s$. Cuesta al menos $\min_{u\in U} d(u,s)$.

Sumando, cualquier continuación cuesta al menos $h(v,U)$. Entonces $h$ **nunca sobreestima** lo que falta: es admisible.

Casos frontera:

- Si queda un solo pendiente $u$: $\operatorname{MST}=0$ y $h = d(v,u) + d(u,s)$, que es **exactamente** lo que falta.
- Si no queda ninguno pero falta cerrar: $h = d(v,s)$, también exacto.
- Si el ciclo está cerrado: $h=0$.

No usamos la desigualdad triangular en ningún paso. Sí usamos dos hechos. Primero, el TSP es simétrico: el camino $u_1 \to \dots \to u_m$ se puede leer como un árbol no dirigido, y la arista $u_m \to s$ pesa lo mismo que $s \to u_m$. Segundo, un camino que cubre $U$ es un árbol generador de $U$. Los pesos no negativos no hacen falta para esta cota; hacen falta para que A* sea óptimo.

En la raíz los dos mínimos pueden escoger **la misma ciudad**. Por ejemplo, en el microcaso los dos escogen E. Con dos o más pendientes, una ruta real no puede usar la misma ciudad como primera y como última del tramo, así que la cota queda floja, pero sigue siendo válida.

**Consistencia.** La cota también es consistente. Sea $n'$ el hijo que va de $v$ a $u \in U$, con $U' = U - \{u\}$ y costo de paso $c = d(v,u)$. Hay que ver que $h(v,U) \le d(v,u) + h(u,U')$, comparando término a término:

- $\operatorname{MST}(U) \le \operatorname{MST}(U') + \min_{w\in U'} d(u,w)$. Al MST de $U'$ le pegamos $u$ con su arista más barata y obtenemos un árbol que conecta $U$. El MST de $U$ no puede ser más caro que ese árbol.
- $\min_{w\in U} d(v,w) \le d(v,u)$, porque $u \in U$.
- $\min_{w\in U} d(w,s) \le \min_{w\in U'} d(w,s)$, porque $U' \subseteq U$: tomar el mínimo sobre más ciudades nunca da más.

Al sumar las tres desigualdades sale $h(n) \le c + h(n')$. Para el último paso ($U'=\varnothing$) y para el cierre, la cota es exacta y la igualdad se cumple. Lo comprobamos además con código en todas las transiciones de casos pequeños, en C.8 (sección 13).

Nuestro A* **no depende** de la consistencia: reabre un estado si llega con mejor $g$ (`bestG`), como pide la sección 7.

**Un MST no es una ruta.** El MST no exige grado 2: una ciudad puede tener 3 ramas o más. Tampoco cierra un ciclo. En el microcaso, el MST de $\{B,C,D,E\}$ es $B{-}C$, $C{-}D$, $D{-}E$ y cuesta 7. Una ruta no puede "recorrerlo" gratis: para pasar de una rama a otra tiene que volver por aristas ya usadas, y eso cuesta. La relajación pierde justo eso: el **orden** y la obligación de **entrar y salir** de cada ciudad una sola vez.
#%% md
### C.5 Microcaso manual (sección 6.2)

Lo resolvimos primero a mano. La celda de código de más abajo solo **verifica** estas cuentas.

Matriz: A-B 4, A-C 6, A-D 7, A-E 3, B-C 2, B-D 5, B-E 6, C-D 3, C-E 4, D-E 2. Origen A.

**Raíz.** $U=\{B,C,D,E\}$. El MST es B-C (2), D-E (2) y C-D (3), y cuesta 7. Conexión desde A: $\min = 3$ (E). Regreso a A: $\min = 3$ (E otra vez). $h = 7+3+3 = 13$, $f = 13$.

**1. Hijos de la raíz:**

| Hijo | $g$ | $U$ | MST de $U$ | conexión desde el hijo | regreso a A | $h$ | $f$ |
|---|---:|---|---|---:|---:|---:|---:|
| A->B | 4 | C, D, E | C-D 3 + D-E 2 = 5 | B-C = 2 | E-A = 3 | 10 | **14** |
| A->C | 6 | B, D, E | D-E 2 + B-D 5 = 7 | C-B = 2 | E-A = 3 | 12 | 18 |
| A->D | 7 | B, C, E | B-C 2 + C-E 4 = 6 | D-E = 2 | E-A = 3 | 11 | 18 |
| A->E | 3 | B, C, D | B-C 2 + C-D 3 = 5 | E-D = 2 | B-A = 4 | 11 | **14** |

**2. Primer empate y regla de desempate.** El primer empate aparece en la frontera inicial: A->B y A->E tienen $f = 14$. Nuestra regla, que usan A* y RBFS, es:

1. menor $f$;
2. si empatan, el nodo **más profundo**, porque está más cerca de cerrar un ciclo;
3. si siguen empatados, el que se generó primero (orden creciente de ciudad).

Como A->B y A->E tienen la misma profundidad, gana **A->B** por orden de generación. Al expandir A->B aparecen sus hijos:

| Hijo de A->B | $g$ | $U$ | $h$ | $f$ |
|---|---:|---|---:|---:|
| A->B->C | 6 | D, E | MST 2 + C-D 3 + E-A 3 = 8 | **14** |
| A->B->D | 9 | C, E | MST 4 + D-E 2 + E-A 3 = 9 | 18 |
| A->B->E | 10 | C, D | MST 3 + E-D 2 + C-A 6 = 11 | 21 |

Ahora empatan A->E ($f=14$, profundidad 1) y A->B->C ($f=14$, profundidad 2). Gana A->B->C por ser más profundo. Siguiendo así, A* expande A, AB, ABC, ABCD y ABCDE, y saca el nodo cerrado con **costo 14**.

**3. Cota con un pendiente y sin pendientes.**

- Prefijo A->B->C->D ($g=9$), $U=\{E\}$: $h = 0 + d(D,E) + d(E,A) = 2+3 = 5$. Es exactamente lo que falta: $f = 14$.
- Prefijo A->B->C->D->E ($g=11$), sin pendientes pero sin cerrar: $h = d(E,A) = 3$, $f = 14$.
- Al cerrar: $g = 14$, $h = 0$.

**4. Primeros cambios de límite en RBFS.** Se llama RBFS(A, límite $=\infty$). Los hijos quedan con $f$ = máx($g+h$, 13): B 14, E 14, C 18, D 18.

- El mejor es B (14). La alternativa es E (14), así que se baja a B con límite $\min(\infty, 14) = 14$.
- En B, los hijos son C 14, D 18, E 21. El mejor es C (14) y la alternativa 18; el nuevo límite es $\min(14, 18) = 14$.
- En A->B->C, los hijos son D 14 y E 19. Para A->B->C->E: $g = 10$, $h = 0 + d(E,D) + d(D,A) = 2 + 7 = 9$, $f = 19$. Se baja a D con límite 14.
- Luego A->B->C->D->E (14) y el cierre (14 ≤ 14): **encontrado**.

El límite pasa de $\infty$ a 14 y se queda ahí. En el microcaso RBFS **no retrocede**, porque la cota es exacta en el camino óptimo. Si la $f$ hubiera subido por encima de 14, RBFS habría guardado ese valor en B y habría vuelto a E. En D.3 mostramos una traza de 6 ciudades donde sí retrocede.

**5. Swap contra 2-opt sobre la misma ruta** A-B-C-D-E-A (costo 14):

- **2-opt** con $i=0$, $j=2$: quita A-B y C-D, pone A-C y B-D, invierte el tramo B C. Queda **A-C-B-D-E**, con $\Delta = 6+5-4-3 = +4$, o sea 18.
- **Swap** de las posiciones 1 y 3 (B y D): queda **A-D-C-B-E**, con costo $7+3+2+6+3 = 21$. Si se mira bien, eso es invertir el tramo B C D, es decir, el 2-opt con $i=0$, $j=3$: $\Delta = d(A,D)+d(B,E)-d(A,B)-d(D,E) = 7+6-4-2 = +7$.

En un ciclo de 5 ciudades **todo swap coincide con algún 2-opt**. Las dos ciudades intercambiadas quedan a distancia 1 o 2 en el ciclo, contando por el lado más corto, y el swap equivale a invertir el tramo entre ellas. Con 6 ciudades o más ya no pasa siempre: un swap de posiciones lejanas cambia **4** aristas y un 2-opt cambia **2**. En E.1 lo comprobamos enumerando todos los swaps.
#%% code
MICRO = np.array([[0, 4, 6, 7, 3],
                  [4, 0, 2, 5, 6],
                  [6, 2, 0, 3, 4],
                  [7, 5, 3, 0, 2],
                  [3, 6, 4, 2, 0]])
micro = TSPInstance("micro", "EXPLICIT", "FULL_MATRIX", list("ABCDE"), MICRO)
LET = "ABCDE"
name_of = lambda path: "-".join(LET[p] for p in path)

H = MSTHeuristic(micro.W)
root = root_node(5)
assert H(root) == 13
rows = []
for child in successors(micro.W, root):
    rows.append((name_of(reconstruct(child)), child.g, H(child), child.g + H(child)))
    for grandchild in (successors(micro.W, child) if child.last == 1 else []):
        rows.append((name_of(reconstruct(grandchild)), grandchild.g, H(grandchild), grandchild.g + H(grandchild)))
table = pd.DataFrame(rows, columns=["prefijo", "g", "h", "f"])
display(table)
assert table.set_index("prefijo")["f"].to_dict() == {"A-B": 14, "A-B-C": 14, "A-B-D": 18, "A-B-E": 21,
                                                     "A-C": 18, "A-D": 18, "A-E": 14}
# one pending and no pending
n_abcd = successors(micro.W, successors(micro.W, successors(micro.W, root)[0])[0])[0]
assert name_of(reconstruct(n_abcd)) == "A-B-C-D" and H(n_abcd) == 5
n_abcde = successors(micro.W, n_abcd)[0]
assert H(n_abcde) == 3 and H(successors(micro.W, n_abcde)[0]) == 0
print("microcaso: g, h y f de la tabla manual verificados")
#%% md
### C.6 Oráculos exactos para pruebas pequeñas

Para probar A* y RBFS necesitamos conocer la respuesta correcta por otro camino. Usamos dos oráculos que no dependen de la búsqueda:

- **`brute_force`** prueba todas las permutaciones, $(k-1)!$ rutas. Lo usamos hasta $k=10$, que son 362 880 rutas.
- **`held_karp`** es programación dinámica sobre subconjuntos, $O(k^2 2^k)$. Calcula el óptimo de otra forma y llega hasta $k=12$ en poco tiempo.

Solo los usamos para probar, nunca dentro de la comparación. Con el microcaso listamos además sus 24 rutas (12 ciclos en 2 sentidos) con su costo. Esa tabla es el oráculo del microcaso para las pruebas de A* y RBFS.
#%% code
def brute_force(inst, start=0):
    others = [v for v in range(inst.n) if v != start]
    best_cost, best_tour = INF, None
    for perm in itertools.permutations(others):
        tour = [start, *perm]
        c = tour_cost(inst.W, tour)
        if c < best_cost:
            best_cost, best_tour = c, tour
    return best_cost, best_tour


def held_karp(inst, start=0):
    W, n = inst.W, inst.n
    others = [v for v in range(n) if v != start]
    best = {(1 << v, v): W[start][v] for v in others}
    for size in range(2, n):
        for subset in itertools.combinations(others, size):
            mask = sum(1 << v for v in subset)
            for v in subset:
                prev = mask & ~(1 << v)
                best[(mask, v)] = min(best[(prev, u)] + W[u][v] for u in subset if u != v)
    full = sum(1 << v for v in others)
    return min(best[(full, v)] + W[v][start] for v in others)


cost, tour = brute_force(micro)
assert cost == 14 == held_karp(micro)
print("microcaso: óptimo", cost, "con la ruta", name_of(tour), "(y su reversa A-E-D-C-B)")

# every tour of the microcase: (5-1)! = 24 = 12 cycles x 2 directions; this table is the oracle for D.3
tours = sorted(((tour_cost(micro.W, [0, *perm]), name_of([0, *perm])) for perm in itertools.permutations(range(1, 5))))
oracle = pd.DataFrame(tours, columns=["costo", "ruta"])
for c, g_ in oracle.groupby("costo"):
    print(f"costo {c}: {len(g_)} rutas  {', '.join(g_['ruta'])}")
assert oracle["costo"].value_counts().sort_index().to_dict() == {14: 2, 18: 2, 19: 4, 21: 8, 23: 4, 24: 2, 28: 2}
assert oracle["costo"].min() == cost and len(oracle) == 24
#%% md
### C.7 Dos rutas parciales que terminan en la misma ciudad (actividad de la sección 5)

Tomamos el subproblema de att48 con 6 ciudades. Comparamos dos prefijos que terminan en la misma ciudad y tienen la misma profundidad, pero distintas ciudades pendientes. Una regla que los fusione por "ciudad" (o por "ciudad y profundidad", parecida a la de TSP Solve) conserva el de menor $g$ y descarta el otro.

La celda busca un par así donde el prefijo descartado completa un ciclo óptimo y el conservado no.
#%% code
def all_prefixes(inst, start=0):
    stack, out = [root_node(inst.n, start)], []
    while stack:
        node = stack.pop()
        out.append(node)
        if node.remaining:
            stack.extend(successors(inst.W, node, start))
    return out


def best_completion(inst, node, start=0):
    rest = list(bits(node.remaining))
    if not rest:
        return inst.W[node.last][start]
    return min(sum(inst.W[a][b] for a, b in zip((node.last, *perm), perm)) + inst.W[perm[-1]][start]
               for perm in itertools.permutations(rest))


sub6 = INSTANCES["att48"].subproblem(6)
optimum6 = brute_force(sub6)[0]
example = None
prefixes = [p for p in all_prefixes(sub6) if 0 < p.depth < 5]
for a, b in itertools.combinations(prefixes, 2):
    if a.last == b.last and a.depth == b.depth and a.remaining != b.remaining:
        keep, drop = (a, b) if a.g <= b.g else (b, a)
        if drop.g + best_completion(sub6, drop) == optimum6 < keep.g + best_completion(sub6, keep):
            example = keep, drop
            break
ids = sub6.node_ids
for label, node in zip(["se conserva (menor g)", "se descarta"], example):
    print(f"{label:22s}: ruta {[ids[p] for p in reconstruct(node)]}, g = {node.g}, "
          f"faltan {[ids[p] for p in bits(node.remaining)]}, "
          f"mejor ciclo posible = {node.g + best_completion(sub6, node)}")
print("óptimo del subproblema:", optimum6)
#%% md
**Lo que encontramos (C.7):** los dos prefijos terminan en la ciudad 5 y están a la misma profundidad. El conservado es más barato **hasta ahora**, pero las ciudades que le faltan lo obligan a terminar caro: su mejor ciclo cuesta 5879. Al descartado le faltan otras ciudades, y con ellas cierra el ciclo óptimo de 5715. Fusionar por ciudad tira el prefijo bueno. Este prefijo no es el único camino al costo 5715, porque la ruta inversa también lo alcanza con otro prefijo. Aun así, en D.5 la búsqueda con esta regla termina en 5879 en esta instancia. Por eso la clave tiene que incluir el conjunto de pendientes.
#%% md
### C.8 Pruebas del MST y de la heurística (tabla de la sección 13)

- **MST:** casos de 0, 1 y 2 pendientes. Para conjuntos más grandes comparamos con un Kruskal propio (con unión-búsqueda) y verificamos que Prim devuelve un árbol válido: $|U|-1$ aristas que conectan todo y suman el costo reportado.
- **Heurística admisible:** para **todos** los prefijos de dos subproblemas de 8 ciudades (uno EUC_2D y uno EXPLICIT) enumeramos todas las continuaciones y verificamos que $h$ no supera el costo restante óptimo. Ese costo es el residual de cada prefijo, no el óptimo total.
- **Consistencia:** en esos mismos árboles revisamos $h(n) \le c(n,n') + h(n')$ en cada transición.
#%% code
def kruskal(W, nodes):
    nodes = list(nodes)
    parent = {v: v for v in nodes}

    def find(v):
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    total = 0
    for w, a, b in sorted((W[a][b], a, b) for a, b in itertools.combinations(nodes, 2)):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            total += w
    return total


def is_spanning_tree(nodes, edges):
    nodes = set(nodes)
    if len(edges) != len(nodes) - 1:
        return False
    reached, frontier = {next(iter(nodes))}, [next(iter(nodes))]
    while frontier:
        v = frontier.pop()
        for a, b in edges:
            for x, y in ((a, b), (b, a)):
                if x == v and y not in reached:
                    reached.add(y)
                    frontier.append(y)
    return reached == nodes


W = INSTANCES["berlin52"].W
assert prim(W, []) == (0, []) and prim(W, [7]) == (0, [])
assert prim(W, [3, 9]) == (W[3][9], [(3, 9)])
rng = random.Random(7)
for _ in range(300):
    nodes = rng.sample(range(52), rng.randint(2, 20))
    total, edges = prim(W, nodes)
    assert is_spanning_tree(nodes, edges) and total == sum(W[a][b] for a, b in edges) == kruskal(W, nodes)
print("MST: 0, 1 y 2 nodos OK; 300 conjuntos aleatorios iguales a Kruskal y con árbol válido")

for name in ["berlin52", "gr48"]:
    sub = INSTANCES[name].subproblem(8)
    H = MSTHeuristic(sub.W)
    nodes = all_prefixes(sub)
    ratios, depths, violations_h, violations_c = [], [], 0, 0
    for node in nodes:
        residual = best_completion(sub, node)
        h = H(node)
        violations_h += h > residual
        if residual > 0:
            ratios.append(h / residual)
            depths.append(node.depth)
        for child in successors(sub.W, node):
            violations_c += h > (child.g - node.g) + H(child)
    closing = [c for nd in nodes if nd.remaining == 0 for c in successors(sub.W, nd)]
    assert all(H(c) == 0 for c in closing)
    assert violations_h == 0 and violations_c == 0
    print(f"{name} k=8: {len(nodes)} prefijos, h <= residual en todos; consistencia en todas las transiciones; "
          f"h/residual medio = {np.mean(ratios):.3f} (mínimo {min(ratios):.3f}, en profundidad {depths[int(np.argmin(ratios))]})")
    by_depth = pd.Series(ratios).groupby(depths).agg(["count", "min", "mean"]).round(3)
    display(by_depth.rename_axis("profundidad").T)
#%% md
**Lo que encontramos (C.8):**

- La cota nunca falla y es consistente en todas las transiciones.
- El promedio de $h$/residual sale muy alto (0.977 en berlin52 y 0.974 en gr48). De los 13 700 prefijos, 10 080 tienen 1 o 0 pendientes, y ahí la cota es exacta (razón 1.0).
- Lo que importa es el **mínimo**: 0.763 en berlin52 y 0.640 en gr48, los dos en profundidad 5 (2 ciudades pendientes). Ahí la cota deja sin contar entre casi una cuarta parte y más de un tercio de lo que falta. En la raíz la razón es 0.824 en berlin52 y 0.723 en gr48, y sube con la profundidad. El mínimo no está en la raíz.
- Una posible causa es que el MST no exige grado 2 y los dos mínimos pueden escoger la misma ciudad. No medimos esa causa. Lo que sí medimos, en la tabla por profundidad, es que la razón promedio va de 0.72 a 0.92 entre la raíz y la profundidad 5.
