# Qué falta y qué necesita la sesión de Linux (estado 2026-10-28)

Complementa `FALTA_PARA_OTRA_PC.md` (lista de tareas para Windows) y `ANALISIS_RANGOS.md` (datos ya obtenidos).

## Lo que necesita de Windows (bloqueante para cerrar la fidelidad)
Hasta el 2026-10-28 12:25 `windows/screens/parte3/` solo tenía las plantillas `LEEME.md` y `NOTAS.md`, sin imágenes ni
`RESULTADOS_PARTE3.md`. Falta:
1. **BPM máximo del preset** (Effect): `01_bpm_min.png`, `01_bpm_max.png` (se asume 240).
2. **Whammy**: `Mix` y `Bend` en cada Mode (MBody, Oct1, Oct2): visible, oculto o deshabilitado, y su rango.
3. **CAB**: nombre y rango de cada perilla del módulo (LC/HC si existen, selector de tipo o micrófono).
4. **AI Tone** y **Audio separation**: capturas de la pantalla abierta y tras pulsar; anotar si piden internet o cuenta.
5. **Import**: sub-pestañas DS, AMP, CAB, Preset y el botón "Load AMX/NAM File to List".
6. Resultados escritos en `windows/RESULTADOS_PARTE3.md` (un apartado por punto, con el valor tal como lo muestra la app).

Reglas: no tocar `CLEAN NFDA` ni `DISTORSION NFDA`; trabajar en un preset vacío "USER PRESET n"; solo observar, sin guardar
en flash; devolver cada control a su valor original; sin nombre de marca del fabricante en nombres ni notas.

## Lo que se hace en Linux sin esperar a Windows
1. **Aplicar los rangos confirmados al código** (hoy son estimados):
   - Pan: −100..100 (ahora −50..50 en `mk300cfg/app.py`).
   - Auto Gate: máx. 100 (ahora 0..60 en `mk300cfg/screens.py`).
   - Drum BPM: 40..240 (ahora 30..300); BPM del preset mín. 40.
   - EQ paramétrico: LC 19..200 (OFF bajo 20), HC 4000..20500 (OFF sobre 20000), Freq 20..20000, Q 0.1..16.0, Gain −18..+18.
   - EQ gráficos de módulos: bandas −24..+24 dB.
2. **Revisar el diff de `mk300-linux/data/catalog.json` y `tools/finalize_catalog.py`** (Whammy con Mode/Bend/Mix y nombres
   de banda de Bass EQ 7, hechos por la otra sesión). `catalog.json` es dato del fabricante: decidir antes de publicar el repo.
3. **Confirmar la etiqueta de `optRch`** (`Nor` / `Dry` / `NoCAB`): el código no la muestra.
4. Commit de lo anterior (nada está commiteado todavía: `app.py` con el título de ventana, `catalog.json`,
   `finalize_catalog.py`, notas en `windows/`).

## Pruebas con la pedalera real (requieren que el usuario la conecte)
Siempre en un preset vacío "USER PRESET n", nunca en `CLEAN NFDA` ni `DISTORSION NFDA`; no llamar a `connect_pedal` si la
pedalera no está en uno vacío.
- Título de ventana con versión: `MK300 v75 — <banco>` (solo probado simulando la conexión).
- Globales en vivo en ambos sentidos y si sobreviven al apagado (HANDOFF, pendiente 1).
- Tail Delay/Reverb (HANDOFF, pendiente 2): captura en Windows cambiando Off/Auto/Force (`09_tail_*.png`) y compararla con
  el byte `0x4b`.

## Fuera de alcance por ahora (alto riesgo o sin entender)
Import all, Swap preset, Factory Restore (borrado de flash), Snapshots, Sounds/IR, modo AM3/AM4 (`0x70300000`),
Community, AI Tone y Audio separation (hasta saber qué son).
