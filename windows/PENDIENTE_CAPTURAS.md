# Pendiente para la sesión en Windows

> **Actualizado:** gran parte de los rangos y nombres ya se obtuvo del código de la app oficial sin usar la interfaz.
> Leer primero `windows/ANALISIS_RANGOS.md`. Aquí solo queda lo que se resuelve con la app (ver "Qué falta de verdad").

Para cerrar la fidelidad de la app de Linux hacen falta datos de la app oficial. Guardar las capturas en
`windows/screens/parte3/` (carpeta nueva, una imagen por punto, nombre con el número del punto: `01_pan_min.png`...).
**IMPORTANTE: no hacer pruebas en los presets `CLEAN NFDA` ni `DISTORSION NFDA`** (ni seleccionarlos). Si hace falta
mover controles, hacerlo antes en un preset vacío "USER PRESET n". Solo se observa: no guardar nada en flash. Al terminar cada control, devolverlo a su valor original.

## Qué falta de verdad (resto de la lista, ya resuelta en ANALISIS_RANGOS.md, no repetir)
- **BPM máximo del preset** (Effect): se asume 240; confirmar arrastrando al máximo.
- **Whammy**: qué pasa con `Mix` en cada `Mode` (MBody, Oct1, Oct2).
- **CAB**: LC/HC y demás perillas del módulo (el código no las define).
- **Puntos 7 y 8**: AI Tone, Audio separation, Import.

Ya resueltos por análisis (no capturar): Pan (-100..100), Drum BPM (40..240), Auto Gate (máx. 100), EQ paramétrico
(LC, HC, Freq, Q, Gain), nombre y bandas de Bass EQ 7.

## Rangos (lista original; arrastrar al mínimo y al máximo y capturar; el valor se ve en la barra o perilla)
1. **Pan** (Effect): mínimo y máximo.
2. **BPM** del preset (Effect) y **Drum BPM** (Drum): mínimo y máximo.
3. **Auto Gate** (Looper): máximo.
4. **EQ**: LC y HC en los extremos; Freq y Q de P1..P4 en los extremos; Gain en el máximo y el mínimo.
5. **CAB**: LC/HC y demás perillas del módulo, en los extremos.

Alternativa: grabar con el spy Frida (`tools/midi_spy*.py`, locales, no versionados) mientras se mueve cada control a
sus extremos; el valor escrito da el rango real.

## Nombres sin identificar
6. **Bass EQ 7** y **Whammy**: abrir el módulo donde aparecen y capturar con el nombre que muestra la app.

## Secciones que Linux no tiene (solo ver qué son)
7. **AI Tone** y **Audio separation** (barra lateral): captura de cada pantalla abierta y otra tras pulsar lo que ofrezcan.
   Anotar si piden internet o cuenta.
8. **Import**: una captura por sub-pestaña (DS, AMP, CAB, Preset) y del botón "Load AMX/NAM File to List".

## Ya hecho en Linux (no repetir)
- Título de ventana con la versión: `MK300 v75 — <banco>` (con pedalera conectada; sin pedalera `MK300 Studio`).
- No incluir nombre de marca del fabricante en nombres de archivo ni notas que se suban al repositorio.
