#%% md
### Lista de entrega revisada

- [x] **Se ejecuta desde un kernel reiniciado con datos locales.** El cuaderno guardado se ejecutó completo, de arriba abajo, con un kernel nuevo (`jupyter nbconvert --execute`). Los datos se leen de `data/` y `data/download.sh` los vuelve a bajar (B).
- [x] **Las cuatro instancias están auditadas y los pesos son oficiales.** Fichas, pesos a mano, fórmulas propias contra `tsplib95` y las rutas `.opt.tour` que dan 10628, 7542 y 5046 (B, B.1, B.2).
- [x] **Los cinco algoritmos son propios y tienen pruebas.** A\* y RBFS (D.1, D.2, D.4, D.6), HC y SA (E.2, E.4), GA (F.2). `tsplib95` solo lee archivos.
- [x] **El costo incluye el cierre y todas las rutas son permutaciones válidas.** Una sola función `tour_cost` con la arista de regreso (B.2, B.3); G.4 comprueba las 320 rutas de la escala B, y F prueba cada hijo del GA.
- [x] **Hay pruebas pequeñas de optimalidad para A\* y RBFS.** Microcaso a mano (C.5, D.3). A\* certifica los 16 subproblemas y burma14 y gr17 completas (D.4, D.8). RBFS coincide con el oráculo en los 14 subproblemas que termina (D.4) y no termina burma14 ni gr17 (D.8).
- [x] **Se distinguen swap, 2-opt e inversión.** C.1 (el swap de TSP Solve), C.5 (5 ciudades), E.1 (conteo de aristas) y F (inversión como mutación).
- [x] **Los registros incluyen semillas, parámetros, presupuestos y causas de parada.** El contrato `RunResult` (A.1) y las tablas de G.2, G.3 y G.4. G.4 guarda cada ejecución de las dos escalas en `resultados/ejecuciones.csv` con `seed`, `parameters` (presupuesto en evaluaciones y segundos), `stop_reason` y `optimality_status`, y cuenta los motivos de parada.
- [x] **Las comparaciones incluyen las diez semillas y los resultados censurados.** Tablas por instancia con válidas/previstas y censuradas (G.4), comparación por pares (G.5), cajas con cada semilla (figura 3).
- [x] **Las gráficas salen de los registros y las conclusiones remiten a evidencia.** Las figuras 1 a 6 leen `history`, `levels`, `gen_log` y las tablas (G.6); cada respuesta de H.2 y cada conclusión de H.3 dice de qué apartado sale.
- [x] **Se entrega el cuaderno con salidas guardadas y los datos o instrucciones de descarga.** Este cuaderno con salidas, la carpeta `data/` con `download.sh`, la tabla `resultados/ejecuciones.csv`, y la animación incrustada en el cuaderno (G.8; al ejecutar se guarda también en `figuras/`).
- [x] **Los integrantes pueden explicar cualquier fragmento.** Cada apartado empieza con la idea en palabras simples y termina con lo que encontramos. Las trazas a mano (C.5, D.3, F.1) son las que usaremos en la sustentación.
