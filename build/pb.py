#%% md
Los archivos están en la carpeta `data/`. El script `data/download.sh` los vuelve a descargar del repositorio oficial de TSPLIB y los descomprime. Bajamos las 4 instancias obligatorias, las 3 de ampliación y las rutas óptimas oficiales (`.opt.tour`) que existen: att48, berlin52, gr48 y eil51. El servidor tiene `eil51.opt.tour` aunque el índice no lo lista. brazil58 no tiene `.opt.tour` publicado.

**Idea de la lectura.** `tsplib95` interpreta cada tipo de peso (ATT, EUC_2D, GEO y matrices EXPLICIT en varios formatos). Pedimos cada peso con `get_weight` y armamos una matriz `D` de posiciones `0..n-1`. La lista `node_ids` guarda qué identificador real de TSPLIB hay en cada posición, así que nunca suponemos que "nodo 1 = posición 1". El origen fijo es la posición 0, que es el identificador más pequeño. El lector lee `NAME`, `TYPE`, `DIMENSION`, `EDGE_WEIGHT_TYPE` y, si existe, `EDGE_WEIGHT_FORMAT`, y exige `TYPE = TSP` para no confundir el archivo con uno de VRP.
#%% code
OPTIMA = {"att48": 10628, "berlin52": 7542, "brazil58": 25395, "gr48": 5046,
          "gr17": 2085, "burma14": 3323, "eil51": 426}
MANDATORY = ["att48", "berlin52", "brazil58", "gr48"]


@dataclass
class TSPInstance:
    name: str
    weight_type: str
    weight_format: object
    node_ids: list
    D: np.ndarray
    coords: object = None          # array (n, 2) for drawing, or None
    optimum: object = None         # official optimum of the full cycle, if known
    subset: str = "full"
    comment: str = ""

    def __post_init__(self):
        self.n = len(self.node_ids)
        self.W = self.D.tolist()   # plain lists: faster than numpy for scalar lookups in the solvers

    def subproblem(self, k):
        """First k identifiers in sorted order with the original weights (induced subproblem)."""
        coords = None if self.coords is None else self.coords[:k]
        return TSPInstance(self.name, self.weight_type, self.weight_format, self.node_ids[:k],
                           self.D[:k, :k].copy(), coords, None, f"k={k}", self.comment)


def load_instance(name):
    problem = tsplib95.load(DATA / f"{name}.tsp")
    assert problem.type == "TSP", f"{name} is {problem.type}, not a TSP file"
    lib_ids = sorted(problem.get_nodes())
    # tsplib95 numbers EXPLICIT matrices from 0, while TSPLIB files (and .opt.tour) number cities from 1
    ids = [i + 1 for i in lib_ids] if lib_ids[0] == 0 else lib_ids
    D = np.array([[problem.get_weight(a, b) if a != b else 0 for b in lib_ids] for a in lib_ids], dtype=np.int64)
    assert D.shape == (problem.dimension, problem.dimension), "dimension mismatch"
    assert (D == D.T).all(), "matrix is not symmetric"
    assert (np.diag(D) == 0).all() and (D >= 0).all(), "bad diagonal or negative weight"
    assert ((D + np.eye(len(ids), dtype=np.int64)) > 0).all(), "two different cities at distance 0"
    coords = None
    if problem.node_coords:
        coords = np.array([problem.node_coords[i] for i in lib_ids], dtype=float)
    elif problem.display_data:
        coords = np.array([problem.display_data[i] for i in lib_ids], dtype=float)
    inst = TSPInstance(name, problem.edge_weight_type, problem.edge_weight_format or None, ids, D,
                       coords, OPTIMA.get(name), "full", problem.comment or "")
    inst.lib_ids = lib_ids
    inst.file_name, inst.file_type = problem.name, problem.type
    assert inst.file_name == name, f"NAME {inst.file_name} does not match file {name}"
    return inst


t0 = time.perf_counter()
INSTANCES = {name: load_instance(name) for name in MANDATORY + ["gr17", "burma14", "eil51"]}
print(f"carga y auditoría de las 7 instancias: {time.perf_counter() - t0:.2f} s (no entra en ningún tiempo medido)")

cards = pd.DataFrame([{
    "instancia": inst.name, "NAME": inst.file_name, "TYPE": inst.file_type, "ciudades": inst.n, "EDGE_WEIGHT_TYPE": inst.weight_type,
    "EDGE_WEIGHT_FORMAT": inst.weight_format or "-", "coordenadas": "sí" if inst.coords is not None else "no",
    "peso mín": int(inst.D[inst.D > 0].min()), "peso máx": int(inst.D.max()),
    "óptimo oficial": inst.optimum, "comentario": inst.comment,
} for inst in INSTANCES.values()])
cards
#%% md
**Una trampa de numeración.** En las instancias EXPLICIT (gr48, brazil58, gr17), `tsplib95` numera las ciudades **desde 0**. Los archivos de TSPLIB y los `.opt.tour` las numeran **desde 1**. Al principio pedimos `get_weight(1, 2)` en gr48 esperando el peso entre las ciudades 1 y 2 (593) y obtuvimos 258, que es el peso entre las ciudades **2 y 3**. Con la ruta oficial el error salta enseguida: `trace_tours` falla porque la ciudad 48 "no existe". Es lo que advierte la sección 3.1. Por eso el lector guarda dos listas: `node_ids`, con los identificadores oficiales de TSPLIB, y `lib_ids`, con los que usa la biblioteca.

**Fichas.** Las 4 instancias obligatorias pasan la auditoría del lector: `TYPE` igual a `TSP`, dimensión correcta, matriz simétrica, diagonal cero, sin pesos negativos y sin dos ciudades distintas a distancia 0. brazil58 y gr48 **no traen coordenadas**, solo la matriz. Por eso las dibujamos con un esquema circular y una matriz de calor (más abajo).

En burma14 (tipo GEO) encontramos un detalle: la fórmula GEO de TSPLIB da **1, no 0**, para la distancia de una ciudad a sí misma, por el `+ 1.0` del final de la fórmula. El lector pone la diagonal en 0 a mano. La diagonal nunca se usa en una ruta, pero sin ese ajuste fallaría la auditoría de "diagonal cero".
#%% md
### B.1 Pesos a mano (ejercicio de la sección 3.2)

**ATT, att48, ciudades 1 y 2.** Coordenadas $(6734, 1453)$ y $(2233, 10)$.

$$\Delta x = 4501,\quad \Delta y = 1443,\quad \Delta x^2 + \Delta y^2 = 20\,259\,001 + 2\,082\,249 = 22\,341\,250$$

$$r = \sqrt{22\,341\,250 / 10} = \sqrt{2\,234\,125} \approx 1494.699,\qquad t = \lfloor 1494.699 + 0.5 \rfloor = 1495$$

Como $t = 1495$ **no** es menor que $r = 1494.699$, entonces $d = t = 1495$.

**EUC_2D, berlin52, ciudades 1 y 2.** Coordenadas $(565, 575)$ y $(25, 185)$.

$$r = \sqrt{540^2 + 390^2} = \sqrt{291\,600 + 152\,100} = \sqrt{443\,700} \approx 666.108,\qquad d = \lfloor 666.108 + 0.5 \rfloor = 666$$

**EXPLICIT, gr48, ciudades 1 y 2.** El formato es `LOWER_DIAG_ROW`: el archivo da la mitad de abajo de la matriz, fila por fila, con la diagonal incluida. La fila 1 es solo `0`. La fila 2 es `593 0`. Por lo tanto $d(1,2) = 593$, sin ninguna fórmula: no se calcula nada a partir de coordenadas.

**ATT, att48, ciudades 1 y 5,** donde sí se suma el 1. Coordenadas $(6734, 1453)$ y $(3082, 1644)$: $r = \sqrt{(3652^2 + 191^2)/10} = \sqrt{1\,337\,358.5} \approx 1156.442$, $t = \lfloor 1156.942 \rfloor = 1156$. Como $1156 < 1156.442$, $d = t + 1 = 1157$. En resumen, ATT funciona como un **techo**: el +1 aparece cuando el redondeo baja, es decir, cuando la parte decimal de $r$ es menor que 0.5. En el par 1 y 2 la parte decimal era 0.699, el redondeo subió y no hubo +1.

La celda de abajo compara estos valores con el lector. Además:

- compara la matriz completa con nuestra propia implementación de las fórmulas ATT y EUC_2D;
- compara gr48, brazil58 y gr17 con un lector propio de los formatos `LOWER_DIAG_ROW` y `UPPER_ROW`, que no usa `tsplib95`;
- cuenta los pares donde `round(r)` de Python (que redondea los empates al par) difiere de `floor(r + 0.5)`. En estas instancias no hay empates, pero hay que comprobarlo.
#%% code
def att_distance(p, q):
    r = math.sqrt(((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) / 10.0)
    t = int(math.floor(r + 0.5))
    return t + 1 if t < r else t


def euc2d_distance(p, q):
    return int(math.floor(math.sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) + 0.5))


att, berlin, gr48 = INSTANCES["att48"], INSTANCES["berlin52"], INSTANCES["gr48"]
hand = pd.DataFrame([
    ("att48", "1-2", "ATT", 1495, att.D[0, 1]),
    ("att48", "1-5", "ATT", 1157, att.D[0, 4]),
    ("berlin52", "1-2", "EUC_2D", 666, berlin.D[0, 1]),
    ("gr48", "1-2", "EXPLICIT", 593, gr48.D[0, 1]),
], columns=["instancia", "par", "regla", "a mano", "lector"])
display(hand)
assert (hand["a mano"] == hand["lector"]).all()

for inst, formula in [(att, att_distance), (berlin, euc2d_distance), (INSTANCES["eil51"], euc2d_distance)]:
    mine = np.array([[formula(p, q) if i != j else 0 for j, q in enumerate(inst.coords)]
                     for i, p in enumerate(inst.coords)])
    assert (mine == inst.D).all(), inst.name
    print(f"{inst.name}: nuestra fórmula coincide con tsplib95 en los {inst.n * inst.n} pesos")


def parse_explicit(name):
    """Own reader for the two EXPLICIT formats we use; independent from tsplib95."""
    text = (DATA / f"{name}.tsp").read_text()
    header, _, body = text.partition("EDGE_WEIGHT_SECTION")
    n = int(header.split("DIMENSION")[1].split(":")[1].split()[0])
    fmt = header.split("EDGE_WEIGHT_FORMAT")[1].split(":")[1].split()[0]
    nums = iter(int(x) for x in body.replace("EOF", "").split())
    M = np.zeros((n, n), dtype=np.int64)
    for i in range(n):
        cols = range(i + 1) if fmt == "LOWER_DIAG_ROW" else range(i + 1, n)
        for j in cols:
            M[i, j] = M[j, i] = next(nums)
    assert next(nums, None) is None, "numbers left over"
    return M


for name in ["gr48", "brazil58", "gr17"]:
    assert (parse_explicit(name) == INSTANCES[name].D).all(), name
    print(f"{name}: nuestro lector de {INSTANCES[name].weight_format} coincide con tsplib95")

# When does ATT add the +1?  Count it over all pairs of att48.
plus_one = sum(1 for i in range(att.n) for j in range(i + 1, att.n)
               if att_distance(att.coords[i], att.coords[j]) != math.floor(math.sqrt(
                   ((att.coords[i] - att.coords[j]) ** 2).sum() / 10) + 0.5))
print(f"att48: el +1 de ATT se aplica en {plus_one} de {att.n * (att.n - 1) // 2} pares")

naive = sum(math.sqrt(((att.coords[i] - att.coords[j]) ** 2).sum()) for i in range(att.n) for j in range(i + 1, att.n))
print(f"att48 con distancia euclidiana común (sin /10) sería unas {naive / att.D[np.triu_indices(att.n, 1)].sum():.2f} veces más grande")

# round() in Python rounds ties to even; count pairs where it would differ from floor(r + 0.5)
for inst, scale in [(att, 10.0), (berlin, 1.0), (INSTANCES["eil51"], 1.0)]:
    rs = [math.sqrt(((inst.coords[i] - inst.coords[j]) ** 2).sum() / scale)
          for i in range(inst.n) for j in range(i + 1, inst.n)]
    ties = sum(round(r) != math.floor(r + 0.5) for r in rs)
    print(f"{inst.name}: pares donde round(r) difiere de floor(r + 0.5): {ties} de {inst.n * (inst.n - 1) // 2}")
#%% md
### B.2 Costo de una ruta y verificación independiente

Una ruta es una lista de **posiciones** que empieza en el origen (posición 0) y no lo repite al final: el regreso se suma aparte. `tour_cost` es la **única** función de costo del cuaderno. Todos los algoritmos la usan, o usan un delta que se valida contra ella.

Para verificarla de forma independiente usamos `problem.trace_tours` de `tsplib95`. Esa función recibe identificadores reales y calcula el costo con su propio código, sin pasar por nuestra matriz.
#%% code
def is_valid_tour(tour, n, start=0):
    return tour is not None and len(tour) == n and tour[0] == start and sorted(tour) == list(range(n))


def tour_cost(W, tour):
    total = W[tour[-1]][tour[0]]       # closing edge back to the origin
    for a, b in zip(tour, tour[1:]):
        total += W[a][b]
    return total


def read_opt_tour(inst):
    path = DATA / f"{inst.name}.opt.tour"
    if not path.exists():
        return None
    ids = tsplib95.load(path).tours[0]
    pos = {node: i for i, node in enumerate(inst.node_ids)}
    tour = [pos[node] for node in ids]
    k = tour.index(0)
    return tour[k:] + tour[:k]          # rotate so the fixed origin is first


rng = random.Random(2026)
rows = []
for name in MANDATORY + ["eil51"]:
    inst = INSTANCES[name]
    problem = tsplib95.load(DATA / f"{name}.tsp")
    opt = read_opt_tour(inst)
    if opt is not None:
        assert is_valid_tour(opt, inst.n)
        independent = problem.trace_tours([[inst.lib_ids[p] for p in opt]])[0]
        rows.append((name, ".opt.tour oficial", tour_cost(inst.W, opt), independent, inst.optimum))
    for t in range(3):
        tour = [0] + rng.sample(range(1, inst.n), inst.n - 1)
        independent = problem.trace_tours([[inst.lib_ids[p] for p in tour]])[0]
        rows.append((name, f"aleatoria {t + 1}", tour_cost(inst.W, tour), independent, None))
check = pd.DataFrame(rows, columns=["instancia", "ruta", "tour_cost", "tsplib95.trace_tours", "óptimo oficial"])
assert (check["tour_cost"] == check["tsplib95.trace_tours"]).all()
display(check)
#%% md
**Lo que encontramos (B.2):**

- Nuestro costo coincide con el de `tsplib95` en todas las rutas.
- Las rutas `.opt.tour` dan exactamente el óptimo oficial: **10628, 7542, 5046 y 426** (att48, berlin52, gr48 y eil51). Esto confirma que los pesos son los oficiales y que el ciclo se cierra bien.
- Usamos las rutas oficiales solo aquí, como prueba. Nunca las usamos como ruta inicial ni como población inicial.

**¿Por qué una ruta "mejor que el óptimo" obliga a revisar todo antes de celebrar?** El óptimo oficial está demostrado, así que nadie puede bajarlo. Si un algoritmo da menos, el error es nuestro. Hay tres sospechosos, y la FAQ oficial de TSPLIB describe errores de este tipo (distancias en punto flotante, cálculo GEO equivocado, coordenadas de dibujo usadas como si fueran las de las distancias).

1. **La distancia está mal.** Por ejemplo, usar en att48 la distancia euclidiana común: según B.1, las distancias salen unas 3.16 veces más grandes. Otro caso es redondear con `round()` de Python, que lleva los empates al par. En estas instancias no hay empates, pero lo comprobamos en B.1 porque otras podrían tenerlos.
2. **Falta el cierre del ciclo.** Si no se suma el regreso al origen, el "costo" es el de un camino abierto y sale más barato.
3. **La ruta no es válida.** Si omite una ciudad, puede salir más corta que el óptimo. Si repite una, el costo ya no es el de un ciclo del problema.

Por eso nuestro protocolo se detiene si un gap sale negativo (lo comprobamos en G).
#%% md
### B.3 Pruebas de la ruta (tabla de la sección 13)
#%% code
inst = INSTANCES["berlin52"]
good = list(range(inst.n))
assert is_valid_tour(good, inst.n)
assert not is_valid_tour(good[:-1] + [5], inst.n), "duplicated city must be rejected"
assert not is_valid_tour(good[:-1], inst.n), "missing city must be rejected"
assert not is_valid_tour(good[1:] + [0], inst.n), "tour must start at the origin"
# closing edge: the cost of 0-1-2 equals the sum of its three edges, including 2 -> 0
tiny = INSTANCES["gr17"]
assert tour_cost(tiny.W, [0, 1, 2]) == tiny.W[0][1] + tiny.W[1][2] + tiny.W[2][0]
# rotating or reversing a cycle does not change its cost
t = [0] + random.Random(1).sample(range(1, tiny.n), tiny.n - 1)
assert tour_cost(tiny.W, t) == tour_cost(tiny.W, [t[0]] + t[1:][::-1])
print("pruebas de ruta y costo: OK")
#%% md
### B.4 Cómo se ven las instancias

att48 y berlin52 tienen coordenadas y se dibujan en el plano. brazil58 y gr48 solo tienen matriz, así que usamos una **matriz de calor**. Más adelante dibujamos sus rutas en una **disposición circular esquemática**, que no representa la geografía real.
#%% code
fig, axes = plt.subplots(1, 4, figsize=(18, 4.2))
for ax, name in zip(axes[:2], ["att48", "berlin52"]):
    inst = INSTANCES[name]
    ax.scatter(inst.coords[:, 0], inst.coords[:, 1], s=14)
    ax.scatter(*inst.coords[0], s=60, c="red", label="origen (id %d)" % inst.node_ids[0])
    ax.set_title(f"{name} ({inst.weight_type}): coordenadas")
    ax.set_aspect("equal")
    ax.legend(fontsize=8)
for ax, name in zip(axes[2:], ["brazil58", "gr48"]):
    inst = INSTANCES[name]
    im = ax.imshow(inst.D, cmap="viridis")
    ax.set_title(f"{name} ({inst.weight_type}): matriz de pesos")
    ax.set_xlabel("posición")
    ax.set_ylabel("posición")
    fig.colorbar(im, ax=ax, fraction=0.046)
plt.tight_layout()
plt.show()
