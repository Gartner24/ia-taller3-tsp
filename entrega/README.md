# Taller IA: TSP (A*, RBFS, HC, SA, GA)

Santiago Valencia León (C.C. 1032797866) y Juan Manuel Galvis (C.C. 1004520611).

El cuaderno `Taller_IA_TSP_AStar_MST_HC_SA_GA_RBFS.ipynb` ya está ejecutado: para revisarlo basta abrirlo,
no hace falta ejecutar nada. Nuestra solución está debajo de cada sección del enunciado, después de una
celda **SOLUCIÓN · sección N**.

Contenido: el cuaderno, `data/` (instancias TSPLIB; `download.sh` las vuelve a bajar),
`resultados/ejecuciones.csv` (una fila por ejecución) y `ejercicios_a_mano/` (Excalidraw: se abre en
https://excalidraw.com o en Obsidian).

## Ejecutarlo

Abrir el cuaderno desde esta carpeta (lee `data/` con rutas relativas) y usar
**Kernel > Restart Kernel and Run All Cells**.

### Linux

```
python3 -m venv .venv
source .venv/bin/activate
pip install jupyterlab numpy pandas matplotlib tsplib95==0.7.1
jupyter lab
```

Tarda unos 7 minutos con 8 procesos en paralelo.

### Windows

1. Instalar Python 3.12 o más nuevo desde https://www.python.org/downloads/ marcando
   **"Add python.exe to PATH"**.
2. En esta carpeta: clic derecho > **Abrir en Terminal**.
3. Ejecutar:
   ```
   py -m pip install jupyterlab numpy pandas matplotlib tsplib95==0.7.1
   py -m jupyter lab
   ```
   (si `py` no existe, usar `python`).

En Windows las ejecuciones corren una tras otra (no hay `fork`), así que tarda más (estimado 20 a 40
minutos, no medido). Los costos y gaps salen iguales; cambian los tiempos, las expansiones de las búsquedas
cortadas por tiempo, y la fila de memoria RSS de G.7 aparece como `NaN`.
