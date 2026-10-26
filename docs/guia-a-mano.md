# Guia: lo que el taller pide hacer a mano o explicar con sus palabras

Todo esta resuelto en el cuaderno; aqui va en corto para copiarlo y explicarlo en la sustentacion.
Va en el orden del enunciado. Donde dice "Cuaderno:" esta la version completa.

## Seccion 1. Actividad de lectura (Cuaderno: C.1)

- Que codigo hace swap: en Hill Climbing de TSP Solve, la funcion `getNextSolution` intercambia dos
  ciudades: `tempNode = newTour(p1); newTour(p1) = newTour(p2); newTour(p2) = tempNode`. La pagina lo llama
  2-opt, pero es swap.
- Que cambiar para 2-opt: en lugar de intercambiar, invertir el tramo entre las dos posiciones:
  `newTour(p1+1:p2) = flip(newTour(p1+1:p2))`, y saltar los pares de aristas vecinas.
- Clave de estado de A*: (ultima ciudad, conjunto de pendientes, cerrado). La ciudad sola no basta: dos
  rutas que llegan a la misma ciudad con pendientes distintos tienen futuros distintos.

## Secciones 3.1 y 3.2. Pesos a mano (Cuaderno: B.1)

ATT, att48, ciudades 1 y 5: (6734, 1453) y (3082, 1644)

    dx = 3652   dy = 191
    r = sqrt((3652^2 + 191^2) / 10) = sqrt(1337358.5) = 1156.44
    t = redondeo(r) = 1156
    t < r  ->  d = t + 1 = 1157        (lector: 1157)

EUC_2D, berlin52, ciudades 1 y 2: (565, 575) y (25, 185)

    dx = 540   dy = 390
    r = sqrt(291600 + 152100) = sqrt(443700) = 666.11
    d = floor(r + 0.5) = 666            (lector: 666)

EXPLICIT, gr48, 1 y 2: se lee de la matriz del archivo = 593.

Explicar: una ruta mas barata que el optimo oficial es imposible, asi que el error es nuestro. Se revisa
primero la distancia (por ejemplo olvidar el +1 de ATT), despues que se cobre el regreso al origen, y por
ultimo que la ruta tenga todas las ciudades una sola vez.

## Seccion 5. Actividad: dos rutas parciales que terminan en la misma ciudad (Cuaderno: C.7 y D.5)

Subproblema de att48 con 6 ciudades (optimo 5715):

    ruta 1 -> 3 -> 5    g = 1159   faltan {2, 4, 6}   mejor ciclo posible = 5879
    ruta 1 -> 6 -> 5    g = 2676   faltan {2, 3, 4}   mejor ciclo posible = 5715 (optimo)

Las dos terminan en la ciudad 5. Si se fusionan "por ciudad", se queda la de menor g (1 -> 3 -> 5) y se
borra la otra, que era la que llevaba al optimo. En D.5 la busqueda con esa regla termina en 5879.
Por eso la clave debe incluir las pendientes.

## Seccion 6. Demostracion con sus palabras (Cuaderno: C.4)

Admisible:

> Para terminar una ruta hay que ir de la ciudad actual a una pendiente, recorrer todas las pendientes y
> volver a A. El tramo por las pendientes es un arbol que las une, asi que cuesta al menos MST(U). La primera
> arista cuesta al menos la conexion mas barata ciudad->U y la ultima al menos la mas barata U->A. Sumando,
> h nunca supera el costo real que falta. No hace falta la desigualdad triangular.

Consistente, h(n) <= c(n,n') + h(n'), al pasar de v a una pendiente u (U' = U sin u):

> MST(U) <= MST(U') + (arista mas barata de u a U'), porque asi se arma un arbol de U.
> min d(v,U) <= d(v,u), porque u esta en U.
> min d(U,A) <= min d(U',A), porque U' esta dentro de U.
> Sumando las tres sale h(n) <= d(v,u) + h(n'). En el ultimo paso y al cerrar se cumple con igualdad.

Ejemplo del microcaso: h(A-B) = 10 y h(A-B-C) = 8 con arista 2: 10 <= 2 + 8.

## Seccion 6.2. Microcaso (Cuaderno: C.5)

h = MST(pendientes) + arista mas barata actual->pendiente + arista mas barata pendiente->A

1) Hijos de A (la raiz tiene h = 13):

| Hijo | g | MST pendientes | ciudad->U | U->A | h | f |
|---|---|---|---|---|---|---|
| A-B | 4 | {C,D,E} = 5 | B-C 2 | E-A 3 | 10 | 14 |
| A-C | 6 | {B,D,E} = 7 | C-B 2 | E-A 3 | 12 | 18 |
| A-D | 7 | {B,C,E} = 6 | D-E 2 | E-A 3 | 11 | 18 |
| A-E | 3 | {B,C,D} = 5 | E-D 2 | B-A 4 | 11 | 14 |

2) Empate: A-B y A-E con f = 14. Regla: menor f, luego mas profundo, luego el generado primero. Gana A-B.

3) Un pendiente (A-B-C-D): g = 9, h = d(D,E) + d(E,A) = 5, f = 14 (exacta).
   Ninguno (A-B-C-D-E): g = 11, h = d(E,A) = 3, f = 14 = optimo.

4) RBFS:

| Llamada | Mejor hijo (f) | Alternativa | Nuevo limite |
|---|---|---|---|
| raiz, limite inf | B (14) | E 14 | 14 |
| A-B | C (14) | D 18 | 14 |
| A-B-C | D (14) | E 19 | 14 |
| A-B-C-D | E (14) | inf | 14 |
| A-B-C-D-E | cierra con 14 | | encontrado |

Sin retrocesos.

5) Swap vs 2-opt sobre A-B-C-D-E (costo 14):
- 2-opt (i=0, j=2): A-C-B-D-E = 18; delta = 6 + 5 - 4 - 3 = +4.
- Swap B y D: A-D-C-B-E = 21; cambia 2 aristas = 2-opt (i=0, j=3).
- Con 5 ciudades todo swap es un 2-opt. Desde 6, si hay 2 o mas ciudades entre las posiciones, el swap
  cambia 4 aristas; el 2-opt siempre 2.

Arbol de A*:

                        A (h=13)
            /        |        |        \
       B f=14     C f=18   D f=18    E f=14   <- empate, gana B
       /   |   \
     C 14 D 18 E 21
       |
     D 14   (E 19)
       |
     E 14
       |
     A  costo 14 = optimo

2-opt (idea general, no es el microcaso):

    antes (se cruzan)        despues (sin cruce)
    A       B                A ------- B
      \   /
        X
      /   \
    D       C                D ------- C
    quita A-C y B-D          pone A-B y D-C; el tramo entre ellas se recorre al reves

## Seccion 8.1. RBFS explicado (Cuaderno: D.2 y D.3)

- Regeneracion: guardamos aparte (solo para medir) cada ruta parcial ya expandida. Si RBFS vuelve a
  expandir la misma ruta, es una regeneracion. Ese registro gasta memoria, por eso solo se activa al medir.
- Por que el maximo en child.f: si el padre ya tiene un f respaldado mas alto, sabemos que todo lo que pasa
  por el cuesta al menos eso. El hijo hereda ese valor para no parecer mas barato de lo que es. Ejemplo
  (berlin52, 8 ciudades): un hijo con g+h = 2166 recibe f = 2202.
- Segunda alternativa: es el f del segundo mejor hijo. Sirve de limite: si la rama elegida pasa de ese
  valor, RBFS vuelve y prueba la otra.
- Rama que reaparece: cuando una rama falla, RBFS guarda su f. Si despues las otras ramas suben por encima,
  esa rama vuelve a ser la mejor y se expande de nuevo. En la traza de D.3: la rama 23-24 falla con 1878
  (limite 1789) y mas adelante se vuelve a expandir.

## Seccion 10. Sin cruces, es optima? (Cuaderno: E.2)

- En el plano: no. Una ruta sin cruces puede no ser optima. Ejemplo de 6 puntos A(0,0) B(10,0) C(10,10)
  D(0,10) E(5,3) F(5,7): A-B-C-D-F-E no tiene cruces y cuesta 45.66; el optimo A-D-F-C-B-E cuesta 43.32.
  No tener cruces es necesario para un optimo local de 2-opt, pero no basta.
- Con matriz explicita: no hay posiciones, asi que "cruce" no significa nada. Cualquier ruta se puede
  dibujar sin cruces poniendo las ciudades en circulo en su orden. Solo vale comparar el costo con el optimo.

## Seccion 11. Si no hay deltas positivos (Cuaderno: E.4)

Si en la calibracion ningun movimiento empeora, no se puede usar la mediana de deltas positivos. Usamos la
mediana de |delta| / -ln(p0). Si todos los deltas son 0, usamos T0 = 1.

## Seccion 11.1. Las cuatro preguntas (Cuaderno: respuesta bajo 11.1, tabla G.5)

- SA mejora siempre a HC? No siempre; gana en la gran mayoria de semillas (ver G.5).
- T0 demasiado baja: SA casi no acepta empeoramientos y se comporta como HC; empeoran sobre todo los peores casos.
- Enfriamiento: al bajar T la aceptacion de empeoramientos cae casi a 0 (figura 5).
- Compensa el trabajo extra? Depende: SA da mejor calidad pero tarda mas; hay que mirar tiempo, no solo
  evaluaciones.

(Las cifras exactas se actualizan con la ejecucion final; copienlas del cuaderno.)

## Seccion 12.1. OX a mano y representacion canonica (Cuaderno: F.1 y F.2)

p1 = [B,C,D,E,F,G], p2 = [E,B,G,C,F,D], segmento posiciones 2 a 4.

    pos:       1  2  3  4  5  6
    p1:        B [C  D  E] F  G
    hijo:      _  C  D  E  _  _      copiar segmento de p1
    huecos (circular desde la 5):  5, 6, 1
    leer p2 desde la pos 5:  F  D  E  B  G  C
    omitidas (ya estan):        D  E     C
    rellenar:  F->5   B->6   G->1
    hijo:      G  C  D  E  F  B

Conserva el tramo C-D-E de p1 y el orden F, B, G de p2.

Representacion canonica: una ruta y su reversa son el mismo ciclo. Para contar individuos unicos usamos la
menor de las dos (el origen ya esta fijo, no hace falta rotar). Solo se usa para contar; el costo se calcula
con el cromosoma tal cual, y en TSP simetrico la reversa cuesta lo mismo.

## Seccion 16. Las 12 preguntas

Se agregan aqui en corto cuando termine la ejecucion final, porque varias cifras cambian.
