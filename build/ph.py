#%% md
### H.1 Resumen para la discusión

Antes de responder juntamos en una tabla lo que más usan las preguntas 7, 9 y 10: gap mediano, dispersión y tiempo mediano de cada método local en las cuatro instancias, con el presupuesto principal (200 000 evaluaciones). Sale de `df_b` (G.4), no de números copiados a mano. Las columnas de orden dicen qué puesto ocupa cada método en esa instancia por gap mediano y por tiempo mediano.
#%% code
main = df_b[df_b["presupuesto"] == 200_000]
discussion = (main.groupby(["instance", "algorithm"], sort=False)
              .agg(gap_mediano=("gap_percent", "median"), gap_desv=("gap_percent", "std"),
                   gap_max=("gap_percent", "max"), s_mediano=("elapsed_seconds", "median"),
                   llega_al_optimo=("gap_percent", lambda g: int((g == 0).sum())))
              .round(2))
discussion["orden por gap"] = discussion.groupby(level=0)["gap_mediano"].rank(method="min").astype(int)
discussion["orden por tiempo"] = discussion.groupby(level=0)["s_mediano"].rank(method="min").astype(int)
display(discussion)
print("puesto medio por gap:", discussion.groupby(level=1, sort=False)["orden por gap"].mean().to_dict())
print("puesto medio por tiempo:", discussion.groupby(level=1, sort=False)["orden por tiempo"].mean().to_dict())
#%% md
### H.2 Las 12 preguntas de la sección 16

Cada respuesta dice de dónde sale: el apartado (por ejemplo, G.4) y la tabla, figura, prueba o traza.

**1. ¿Por qué A\* y RBFS trabajan con rutas parciales y HC, SA y GA con rutas completas?** Porque hacen preguntas distintas. A\* y RBFS **construyen** la ruta ciudad por ciudad y necesitan saber, antes de terminarla, si vale la pena seguir: eso lo da $f = g + h$, donde $g$ es lo ya recorrido y $h$ una cota de lo que falta (C.2, C.3). Sobre una ruta completa no queda nada por acotar. HC, SA y GA **mejoran** rutas que ya existen: necesitan un costo completo para comparar, y sus operadores (2-opt, OX, inversión) solo tienen sentido sobre una permutación entera (E.1, F.1). Por eso los exactos pueden certificar el óptimo cuando terminan (D.4) y los locales siempre tienen una ruta para devolver, aunque sea mala (G.4, 30 000 evaluaciones).

**2. ¿Por qué el MST da una cota y no una solución? ¿Qué pierde la relajación?** Lo que falta de una ruta parcial es un camino que pasa por todas las pendientes y vuelve. Si a ese camino le quitamos las dos aristas de conexión, queda un árbol que une las pendientes, y ningún árbol es más barato que el MST. Por eso la suma no se pasa del costo real (C.4). Pero el MST no exige **grado 2** ni que sea un solo camino: puede ramificarse, y las dos aristas de conexión pueden salir hacia la misma ciudad. Eso es lo que pierde. En C.8 lo medimos sobre los 13 700 prefijos de dos subproblemas de 8 ciudades: la cota nunca falla, pero cerca de la raíz deja sin contar entre una cuarta y una tercera parte de lo que falta (mínimo $h$/residual 0.76 en berlin52 y 0.64 en gr48). Ese hueco hace crecer la búsqueda: con 48 ciudades ni A\* ni RBFS terminan en 30 s (G.4).

**3. ¿Qué sucede si A\* cierra estados usando solamente la última ciudad?** Dos rutas parciales que terminan en la misma ciudad se tratan como el mismo estado, aunque les falten ciudades distintas. En D.5 A\* no devuelve **ninguna** ruta en los 5 casos (`EXHAUSTED`): el primer prefijo que llega a cada ciudad es el directo desde el origen y tiene el menor $g$, así que todo prefijo más largo se descarta. Si además se usa la profundidad (la regla de TSP Solve, C.1), aparecen rutas, pero no óptimas: 5879 contra 5715 en att48 con $k=6$. En C.7 está el par concreto: el prefijo descartado era el único que llevaba al óptimo.

**4. ¿Por qué devolver el primer nodo con pendientes vacíos, sin cobrar el retorno, puede fallar?** Porque ese nodo es el mejor **camino** abierto, no el mejor ciclo. En D.5, en att48 con $k=6$, el camino cuesta 4151, pero al cerrarlo el ciclo cuesta 6163, un 7.8 % por encima del óptimo 5715. El camino más barato puede terminar lejos del origen y el regreso se paga después. Nuestro A\* evita el error con el estado "cerrado": la meta se reconoce al sacar de la frontera un nodo que ya pagó el regreso (D.1).

**5. ¿En qué casos RBFS redujo memoria y aumentó recomputación?** En todos los subproblemas de la escala A (G.3, tabla y figura 4). En $k = 12$, RBFS nunca tiene más de 68 registros vivos ni pasa de 0.02 MiB, mientras A\* guarda entre 1296 y 4204 nodos en la frontera y usa hasta 2.35 MiB: entre 3 y 130 veces menos memoria. El precio: en berlin52 con $k=12$, de 80 651 expansiones, 80 214 son regeneraciones (99.5 %), y tarda unos 18 s contra 0.09 s de A\*. En brazil58 con $k = 10$ y $k = 12$, y en burma14 y gr17 completas (D.8), RBFS se corta por presupuesto, mientras A\* termina. La traza del caso de 6 ciudades de berlin52 (D.3) muestra el mecanismo en pequeño: la rama 23-24 falla con límite 1789, guarda el valor respaldado 1878, se olvida, y después **reaparece** y se expande otra vez.

**6. ¿Qué diferencias hay entre att48 y gr48, las dos con 48 ciudades?** No es el mismo problema con otro nombre.
- **Datos:** att48 tiene coordenadas y la distancia pseudo-euclidiana ATT; gr48 es una matriz explícita, sin coordenadas (B, fichas). En gr48 no hay "cruces" ni plano: su figura 1 es un círculo esquemático (E.2, G.6).
- **Exactos:** gr48 es mucho más fácil. En $k = 12$, A\* hace 38 expansiones en gr48 y 376 en att48; RBFS, 79 contra 32 375 (G.3). En los primeros 12 nodos de gr48 la cota MST se ajusta mejor.
- **Locales:** las dos tienen gaps de pocos puntos a 200 000 evaluaciones (H.1). gr48 es donde SA y HC con reinicios quedan más cerca: SA pierde en 3 de 10 semillas y la diferencia mediana es solo de 38 unidades, un 0.75 % (G.5). SA llega al óptimo de gr48 en 1 semilla y al de att48 en ninguna (G.4).
- **Escala del costo:** el óptimo de att48 es 10 628 y el de gr48 5046 (B.2), así que una misma diferencia absoluta pesa distinto. Por eso comparamos con el gap y no con el costo.

**7. ¿Cuánto aportaron los reinicios frente a aceptar empeoramientos?** Mirando la distribución de las 10 semillas (H.1, figura 3, G.5):
- Con 30 000 evaluaciones, los reinicios no aportan **nada**: HC nunca llega a su primer óptimo local, así que HC con reinicios da exactamente lo mismo que HC de una ruta (G.4).
- Con 200 000, los reinicios bajan el gap mediano de 4.5-8.1 % a 1.7-5.7 %. Aceptar empeoramientos (SA) lo baja más: 0.3-2.9 %. SA le gana a HC con reinicios en 35 de 40 pares con la misma ruta inicial (G.5), y es el único que llega al óptimo oficial (6 de 40 corridas).
- La dispersión está en la figura 3 y en las columnas `gap_desv` y `gap_max` de H.1: la comparación es de medianas y peores casos sobre las 10 semillas, no de la mejor corrida.

**8. ¿Qué signos de convergencia prematura hubo en el GA? ¿Cómo se relacionan con la diversidad?** En la corrida de berlin52 con el presupuesto principal (figura 6), las aristas distintas por ciudad bajan de 24.4 al inicio a 2.4 al final: casi toda la población usa las mismas aristas. Desde la generación 300 la mediana de la población es igual al mejor, y desde la 550 el mejor no vuelve a bajar en las casi 2000 generaciones que quedan. La fracción de rutas únicas sigue alta más tiempo, pero engaña: son variantes de la misma ruta que difieren en unas pocas inversiones. Con poca diversidad de aristas, el OX ya no tiene nada nuevo que combinar, y solo la mutación trae aristas nuevas. Por eso en la calibración gana la mutación alta, $p_m = 0.3$ (G.2). En las 10 semillas el GA queda cerca de HC de una ruta (gap mediano 3.6-5.5 %, H.1), lejos de SA.

**9. ¿Cambió el ranking al comparar tiempo en lugar de evaluaciones?** Sí. Por **calidad con las mismas evaluaciones**, el orden es SA, HC con reinicios, GA y al final HC de una ruta (H.1, puesto medio por gap: 1.0, 2.25, 3.0 y 3.75), aunque el GA y HC de una ruta cambian de lugar según la instancia. Por **tiempo**, HC de una ruta y HC con reinicios terminan en menos de 0.3 s, SA tarda unas 10 veces más que HC con reinicios y el GA es por mucho el más lento, 17-19 s (G.4, G.5, H.1, puesto medio por tiempo). En la figura 2 en segundos se ve que el orden de calidad **depende del corte**: a los 0.2 s el mejor es HC con reinicios, porque SA todavía no empezó a enfriarse; desde 1.5 s el mejor es SA. Dos matices: `tracemalloc` hace a SA unas 9 veces más lento y a HC casi nada (G.7), así que parte de esa diferencia es la medición; y las corridas compartían la máquina (G.1). No medimos qué pasa si HC con reinicios recibe los mismos **segundos** que SA (pregunta 12).

**10. Dos segundos para devolver una ruta, ¿qué elegimos? ¿Y para demostrar optimalidad?**
- **Dos segundos:** SA con 200 000 evaluaciones. Con medición y 8 corridas en paralelo tardó unos 1.5 s (G.4), y sin `tracemalloc` es unas 9 veces más rápido (G.7), así que cabe con margen y es el que mejor gap da (H.1). Como en otra ejecución de prueba SA tardó hasta el doble, sin margen elegiríamos HC con reinicios: termina en menos de 0.3 s con gap mediano 1.7-5.7 %. El GA no sirve aquí. Ojo: no corrimos un presupuesto de 2 s; lo deducimos de los tiempos medidos.
- **Demostrar optimalidad:** A\* con MST, que certificó todos los subproblemas de hasta 12 ciudades y burma14 y gr17 completas (G.3, D.8). En las instancias de 48 a 58 ciudades no terminó en 30 s (G.4), así que con nuestros recursos **no** podemos demostrar el óptimo ahí. Los locales nunca demuestran nada: aunque SA dé el óptimo oficial, solo lo sabemos porque TSPLIB lo publica. RBFS no es la opción: usa menos memoria pero se corta antes que A\* (D.8).

**11. ¿Qué afirmaciones de la página de referencia requieren matices?** Hay que separar lo que es del algoritmo de lo que es de su código (C.1):
- **"A\* da el óptimo".** Es verdad para A\* con una heurística admisible y el estado correcto. El código de la página usa como estado solo la ciudad (y la profundidad), y con esa regla A\* deja de ser exacto: lo reproducimos en D.5. Que la página encuentre el óptimo solo desde 8 de 48 orígenes es un síntoma de su implementación, no de A\*.
- **"RBFS usa memoria lineal".** Es una propiedad del algoritmo y la vimos: los registros vivos crecen como $k^2/2$ (G.3). Pero no implica menos tiempo: con 12 ciudades ya regenera el 99.5 % de sus expansiones (G.3). Además, en el código de la página la $f$ resta la profundidad y el `max` con la $f$ del padre se aplica a una copia, así que su RBFS no es el de la sección 8.
- **"Hill Climbing con 2-opt".** El código hace swap, no 2-opt (C.1). Son vecindades distintas: desde 6 ciudades hay swaps que cambian 4 aristas y no equivalen a ningún 2-opt (E.1).
- **Tiempos publicados.** Son de otro lenguaje, otra máquina y otro código. No sirven como meta (C.1), y nuestros propios tiempos dependen de la medición (G.7).

**12. ¿Qué conclusión no podemos sostener?**
- **"El GA es peor que SA" en general.** Probamos un GA básico (OX, inversión, torneo), calibrado en dos instancias con 5 semillas. Otro operador o una búsqueda local dentro del GA podrían cambiarlo.
- **Diferencias pequeñas entre configuraciones.** En la calibración de SA, las seis configuraciones quedan entre 1.2 % y 1.8 % (G.2); con 5 semillas y 2 instancias eso no es concluyente.
- **Significancia estadística.** Con 10 semillas contamos pares mejor/igual/peor (G.5), pero no hicimos una prueba formal. "SA gana 35 de 40" es una tendencia clara, no una probabilidad.
- **Tiempos absolutos.** Están inflados por `tracemalloc` y por correr 8 procesos a la vez (G.1, G.7). Sirven para ordenar de forma gruesa, no para afirmar "SA tarda 3 s".
- **Comportamiento de los exactos en las instancias completas.** Tenemos un solo ensayo de 30 s por instancia y algoritmo (G.4). No sabemos cuánto tardarían en terminar.
- **Instancias más grandes.** Todas tienen entre 48 y 58 ciudades. No podemos extrapolar el orden de los métodos a 500 ciudades.
- **Primera mejora contra mejor mejora en las instancias completas.** Solo lo medimos con 20 ciudades (E.3).
#%% md
### H.3 Conclusiones

1. **Un A\* bien formulado es exacto, y uno mal formulado no.** El estado tiene que ser (ciudad actual, pendientes, cerrado), y la meta se reconoce después de cobrar el regreso. Con esas reglas, A\* certificó los 16 subproblemas y dos instancias completas pequeñas (D.4, G.3, D.8). Con la regla de la última ciudad, o sin cobrar el regreso, da respuestas incorrectas (D.5).
2. **La cota MST es correcta pero floja cerca de la raíz** (C.8), y eso limita los exactos a unas 12-17 ciudades con nuestro presupuesto (G.3, G.4, D.8).
3. **RBFS cambia memoria por tiempo:** usa hasta 130 veces menos memoria que A\*, pero regenera casi todo lo que expande y se corta donde A\* termina (G.3, D.8).
4. **Entre los locales, aceptar empeoramientos es lo que más aporta.** Con el mismo presupuesto y la misma ruta inicial, SA tiene el mejor gap mediano en las cuatro instancias y es el único que llega al óptimo oficial (G.4, G.5, figura 3). Los reinicios ayudan a HC, pero menos.
5. **El presupuesto decide la comparación.** Con las 30 000 evaluaciones del enunciado, HC no alcanza a terminar su primer descenso y los reinicios no se usan (G.4). Medir con un presupuesto que no deja terminar a un método mide el corte, no el método.
6. **El GA básico pierde diversidad de aristas muy rápido** (F, figura 6) y queda al nivel de HC de una ruta, con mucho más tiempo (H.1).
7. **El tiempo y la memoria hay que leerlos con su instrumento.** `tracemalloc` cambia los tiempos de forma distinta para cada algoritmo (G.7), y la memoria del proceso es casi toda del entorno, no del solver.
#%% md
### H.4 Referencias

Consulta de fuentes: 17 de octubre de 2026.

1. Hamdi Altaheri. [TSP Solve](https://sites.google.com/view/tsp-solve/homepage), páginas de [A\*](https://sites.google.com/view/tsp-solve/tsp-a-algorithm), [Hill Climbing](https://sites.google.com/view/tsp-solve/tsp-hill-climbing-algorithm) y [RBFS](https://sites.google.com/view/tsp-solve/tsp-rbfs-algorithm). Objeto de la lectura crítica de C.1; no usamos sus resultados como nuestros.
2. Gerhard Reinelt. [TSPLIB95](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/), su [documentación](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp95.pdf) (fórmulas ATT, GEO y EUC_2D) y la tabla de [óptimos](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/TSP-BEST.html). Datos, distancias y valores de referencia.
3. Stuart Russell y Peter Norvig. *Artificial Intelligence: A Modern Approach*, 4.ª edición. Capítulo 3 (A\*, heurísticas admisibles y consistentes, RBFS) y capítulo 4 (búsqueda local, Simulated Annealing, algoritmos genéticos).
4. AIMA Code. [Recursive Best First Search](https://github.com/aimacode/aima-pseudocode/blob/master/md/Recursive-Best-First-Search.md), pseudocódigo de AIMA3e. Base de nuestro RBFS (D.2).
5. Desarrolladores de `tsplib95`. [Guía de uso](https://tsplib95.readthedocs.io/en/stable/pages/usage.html). Solo para leer las instancias y comparar pesos (B).
6. Peter Norvig. [The Traveling Salesperson Problem](https://github.com/norvig/pytudes/blob/main/ipynb/TSP.ipynb) (pytudes). Lo consultamos como ejemplo de 2-opt y de cómo dibujar rutas; no copiamos su código.
7. Claude (Anthropic). Lo usamos como herramienta de apoyo para consultar conceptos y documentación, y como apoyo en la implementación, la depuración y la redacción. Revisamos y ejecutamos todo el código, y los números del cuaderno salen de nuestras corridas.
#%% md
### H.5 Bitácora: lo que salió mal y cómo lo arreglamos

- **Los índices de `tsplib95` en matrices explícitas.** En gr48, brazil58 y gr17, `tsplib95` numera las ciudades desde 0, pero los archivos TSPLIB y las rutas óptimas las numeran desde 1. Pedimos `get_weight(1, 2)` en gr48 esperando 593 y salió 258, el peso entre las ciudades 2 y 3. Lo arreglamos guardando las dos numeraciones (`node_ids` oficiales y `lib_ids` de la biblioteca) y comparando con pesos calculados a mano (B).
- **La diagonal de burma14 (GEO).** La fórmula GEO da 1, no 0, de una ciudad a sí misma, por el `+ 1.0` final. Ninguna ruta usa esa arista, pero la auditoría de "diagonal cero" fallaba, así que la fijamos en 0 (B).
- **Fusionar por la última ciudad.** Lo probamos esperando una ruta peor y no salió **ninguna**: A\* agotaba la frontera (D.5). Entender por qué nos llevó al par de C.7.
- **El presupuesto de 30 000 evaluaciones.** Al medir HC vimos que no le alcanzaba para su primer óptimo local (E.2). Subimos el presupuesto principal a 200 000 evaluaciones para todos y dejamos el del enunciado como segunda comparación (G.1).
- **El GA y el tiempo.** Con 60 s el GA se cortaba por tiempo en gr48; subimos el límite a 120 s para que el corte fuera siempre por evaluaciones (G.1).
- **El costo de medir la memoria.** Esperábamos que `tracemalloc` hiciera todo un poco más lento por igual. Hace a SA unas 9 veces más lento y a HC casi nada (G.7), y eso cambió cómo leemos los tiempos (pregunta 9).
