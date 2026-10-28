# Lo que falta y debe hacerse en la PC con la app oficial y la pedalera

Contexto: el clon de Linux ya tiene todo lo que se pudo sacar del código de la app oficial (ver `ANALISIS_RANGOS.md`).
Esta lista es lo que **solo se resuelve usando la app**. Es la lista corta y vigente; `PENDIENTE_CAPTURAS.md` es la lista
original con el contexto.

## Reglas (obligatorias)
- No seleccionar ni probar nada en los presets `CLEAN NFDA` ni `DISTORSION NFDA`.
- Trabajar en un preset vacío "USER PRESET n". Solo observar: **no guardar nada en flash**.
- Al terminar cada control, devolverlo a su valor original.
- No incluir el nombre de marca del fabricante en nombres de archivo ni en notas que se suban al repositorio.
- Guardar las capturas en `windows/screens/parte3/` (carpeta nueva), con el número del punto en el nombre.
- Anotar los resultados en `windows/RESULTADOS_PARTE3.md` (crearlo), un apartado por punto, con el valor leído tal como
  lo muestra la app.

## 1. BPM máximo del preset (módulo Effect)
- Arrastrar el control BPM del preset al mínimo y al máximo; capturar cada extremo.
- Se espera mín. 40 (confirmado) y máx. 240 (asumido). Anotar el valor real del máximo.
- Archivos: `01_bpm_min.png`, `01_bpm_max.png`.

## 2. Whammy: comportamiento de Mix según Mode
- Seleccionar el tipo Whammy en el módulo FX.
- Para cada Mode (`MBody`, `Oct1`, `Oct2`): capturar el panel completo y anotar si `Mix` aparece, está oculto o está
  deshabilitado, y su rango (mín./máx.) cuando es visible. Anotar también el rango de `Bend`.
- Archivos: `02_whammy_mbody.png`, `02_whammy_oct1.png`, `02_whammy_oct2.png`.

## 3. CAB: perillas del módulo
- Abrir el módulo CAB y capturar la pantalla completa.
- Listar cada perilla/slider con su nombre exacto y su rango real (arrastrar a mínimo y máximo, una captura por
  extremo). Incluir LC y HC si existen, y cualquier selector de tipo o de micrófono.
- Archivos: `03_cab_vista.png`, `03_cab_<perilla>_min.png`, `03_cab_<perilla>_max.png`.

## 4. AI Tone
- Capturar la pantalla al abrirla desde la barra lateral y otra tras pulsar lo que ofrezca (sin completar acciones que
  suban, compren o borren datos).
- Anotar si pide internet, cuenta o inicio de sesión.
- Archivos: `04_ai_tone_1.png`, `04_ai_tone_2.png`.

## 5. Audio separation
- Igual que el punto 4: captura de la pantalla abierta y otra tras pulsar lo que ofrezca; anotar si requiere internet,
  cuenta o descargas.
- Archivos: `05_audio_sep_1.png`, `05_audio_sep_2.png`.

## 6. Import
- Una captura por sub-pestaña: DS, AMP, CAB y Preset.
- Captura del botón "Load AMX/NAM File to List" y de lo que muestra al pulsarlo (no cargar archivos en la pedalera).
- Archivos: `06_import_ds.png`, `06_import_amp.png`, `06_import_cab.png`, `06_import_preset.png`,
  `06_import_load_list.png`.

## 7. Tail Delay / Reverb (lo pide la sesión de Linux, ver `FALTA_DE_LINUX.md`)
- En los ajustes de Tail, cambiar entre Off / Auto / Force y capturar cada estado; anotar el valor que muestra la app.
- Archivos: `09_tail_off.png`, `09_tail_auto.png`, `09_tail_force.png`. Devolver el ajuste a su valor original.

## 8. (Opcional) Comprobaciones del clon
- Con la pedalera conectada, abrir el clon de Linux (o describir lo observado en la app oficial) y confirmar que el
  título de la ventana muestra la versión, p. ej. `MK300 v75 — <banco>`. No se probó con hardware real.
- Revisar que Whammy muestra Mode, Bend y Mix, y que Bass EQ 7 muestra sus 7 bandas con nombre.

## Verificación rápida de lo ya deducido por análisis (si hay tiempo)
Datos marcados como [confirmado] en `ANALISIS_RANGOS.md` se leyeron de ensamblador descompilado y no se compararon con la
app. Si se quiere comprobar, bastan estas capturas de los extremos: EQ paramétrico (LC, HC, Freq, Q, Gain) y Pan.
Esperado: LC 19–200 (OFF bajo 20), HC 4000–20500 (OFF sobre 20000), Freq 20–20000, Q 0.1–16.0, Gain −18 a +18 dB,
Pan −100 a 100.
