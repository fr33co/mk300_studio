# Resultados parte 3 (actualizado 2026-10-28)

Fuente: pasada en vivo con la app oficial abierta y la pedalera conectada (2026-10-28, solo observación), más las
capturas anteriores de `screens/` y `screens/parte2/`. Las capturas nuevas están en `screens/parte3/`.

Condiciones de la pasada:
- Se trabajó solo en el preset vacío **[160] USER PRESET 160** (módulos apagados salvo VOL; Preset Vol = 60, Pan = C,
  BPM = 80). No se seleccionó ni se tocó ninguno de los dos presets protegidos.
- No se pulsó ningún "Save", "Save to" ni "Save to Device"; no se cargó ningún archivo. Los selectores de archivos
  se cancelaron sin elegir nada.
- Cada control se devolvió a su valor original (BPM 80, FX Wah-Wah, CAB Level 80 / Low Cut 20 / High Cut 18.0K,
  Tail Delay y Reverb en OFF).
- Al empezar, la app tenía seleccionado el preset protegido [001]. Para cumplir la regla de no tocarlo, el preset
  activo **se dejó en [160] USER PRESET 160**. No se volvió a [001].
- Los números se leen como los muestra la app. Las perillas responden al arrastre vertical y a la rueda del ratón
  (un paso por evento de rueda).

## 1. BPM máximo del preset (Effect) — HECHO
- Mínimo: **40**. Máximo: **240**. Confirma lo esperado.
- Valor inicial en este preset: 80.
- Archivos: `01_bpm_min.png`, `01_bpm_max.png`.
- Pan (de paso): el centro se muestra como `C`, no como `0`.

## 2. Whammy — HECHO
Al elegir **Whammy** en el módulo FX aparecen tres perillas: **Mode**, **Bend**, **Mix**.
Valores por defecto al elegirlo: Mode = `MBody`, Bend = 50, Mix = 50.

| Mode | Mix | Bend |
|------|-----|------|
| `MBody` | Visible. Rango **0–100** | Visible (50 por defecto) |
| `Oct1` | **Oculto** (la perilla no aparece; no está deshabilitada, el panel solo muestra Mode y Bend) | Visible. Rango **0–100** (medido aquí) |
| `Oct2` | **Oculto** (igual que Oct1) | Visible (50 por defecto) |

- El rango de Bend (0–100) se midió en `Oct1`. En `MBody` y `Oct2` solo se vio el valor por defecto 50.
- El orden de Mode, de abajo hacia arriba al arrastrar, es `MBody`, `Oct1`, `Oct2`.
- Archivos: `02_whammy_mbody.png`, `02_whammy_oct1.png`, `02_whammy_oct2.png`,
  `02_whammy_mbody_mix_max.png` (Mix = 100), `02_whammy_mbody_mix_min.png` (Mix = 0).
- El tipo de FX se restauró a Wah-Wah.

## 3. CAB — HECHO
El módulo CAB tiene un selector de modelo y tres perillas.
- **Selector de modelo**: lista numerada de cabinas (por ejemplo `1EAGLProV30s`, `2Sperimental`, `3Juice4x12V30`,
  `4Mess Bog`, `5FdChamp`, `6FdPrJunir`, `7Mar960BV30`, `8DizzlV30`, `9Elctrovoice`, `10MessRectV30`…). No se cambió
  el modelo: la lista se abrió y se cerró con Escape.
- Perillas:

| Perilla (nombre exacto) | Rango observado | Valor original |
|-------------------------|-----------------|----------------|
| `Level` | **0 – 100** | 80 |
| `Low Cut` | **20 – 300** | 20 |
| `High Cut` | **5.0K – 18.0K** | 18.0K |

- `High Cut` muestra el arco **invertido**: arco lleno en 5.0K y vacío en 18.0K. Los valores se muestran con sufijo `K`.
- Low Cut y High Cut no tienen valor `OFF` en este módulo.
- Archivos: `03_cab_vista.png`, `03_cab_lista_modelos.png`, `03_cab_level_min.png`, `03_cab_level_max.png`,
  `03_cab_lowcut_min.png`, `03_cab_lowcut_max.png`, `03_cab_highcut_min.png` (5.0K), `03_cab_highcut_max.png` (18.0K).

## 4. AI Tone — HECHO
- Al abrirla desde la barra lateral muestra solo el texto **"Coming Soon"**. No hay botones ni nada que pulsar.
- No pide internet, cuenta ni inicio de sesión: la función aún no existe en esta versión.
- Archivos: `04_ai_tone_1.png` y `04_ai_tone_2.png` (son iguales, porque no hay nada que pulsar).

## 5. Audio separation — HECHO
- Se abre una pantalla **"Audio Library"** con la biblioteca vacía: texto "Library is empty" e "Import an audio or
  video file to get started (WAV / MP3 / MP4 / MOV, audio auto-extracted)". Hay un botón **Import** al centro y
  otro **+ Import** arriba a la derecha.
- Al pulsar Import abre un **selector de archivos local** ("File Picker") con filtro de audio (`*.wav, *.mp3,
  *.flac, *.ogg…`). Se canceló sin elegir archivo.
- Hasta ese punto no pidió internet, cuenta ni descargas. Funciona sin necesidad de iniciar sesión. No se importó
  ningún archivo, así que no se vio qué ocurre después (procesado o descarga de modelos).
- Archivos: `05_audio_sep_1.png` (biblioteca vacía), `05_audio_sep_2.png` (pantalla completa con el selector abierto).

## 6. Import — HECHO
Sub-pestañas, en este orden: **DS, AMP, CAB, Preset**.
- **DS** y **AMP**: botones `Load AMX/NAM File to List` y `Save to Device`; slider `Level` = 100; slider doble `Gain`
  = 30–60; buscador `Search`; botón `Edit`; lista vacía.
- **CAB**: botones `Load CAB File to List` y `Save to Device`; slider `CAB Level` = 50; `Search`; `Edit`; lista vacía.
- **Preset**: un solo botón `Load  File to List` (sin `Save to Device`); `Search`; `Edit`; aviso en una franja
  naranja: **"Currently supports importing snapshots to the device."**; lista vacía.
- `Load AMX/NAM File to List` abre un selector de archivos local con filtro de extensiones `*.am2, *.am3,
  *.am2data, …` (el filtro aparece cortado en pantalla). Se canceló sin cargar nada.
- No se pulsó ningún `Save to Device`.
- Archivos: `06_import_ds.png`, `06_import_amp.png`, `06_import_cab.png`, `06_import_preset.png`,
  `06_import_load_list.png` (pantalla completa con el selector abierto).

## 7. Tail Delay / Reverb (pestaña Glob) — HECHO
- La sección **TAIL** tiene **Delay** y **Reverb**, cada uno con tres botones: **OFF / Auto / Force**.
- Estado inicial de ambos: **OFF**. Se probaron los tres estados de cada uno por separado y ambos se devolvieron a OFF.
- Archivos: `09_tail_delay_off.png`, `09_tail_delay_auto.png`, `09_tail_delay_force.png`,
  `09_tail_reverb_off.png`, `09_tail_reverb_auto.png`, `09_tail_reverb_force.png`.
- Pendiente para quien compare con el byte `0x4b`: estas capturas muestran lo que dice la app, no el tráfico MIDI.

## Datos extra vistos en las capturas anteriores (útiles para el clon)
Pestaña Glob (`screens/015_161941.png`):
- **PEDAL-1**: A/B Convert (OFF/ON; en la captura ON), Sync (OFF/ON; OFF), Pedal State (A/B; A).
- **PEDAL-2**: Pedal State (A/B; A).
- **OTHER**: **RCH** con opciones `Nor` / `Dry` / `NoCAB` (en la captura: **Dry**), **USB Audio** con opciones
  `NOR` / `NO` / `RESAMPLE` / `DRY` (en la captura: NOR), BT&USB VOL = 100 y USB REC VOL = 50.
- Esto resuelve la etiqueta de `optRch` pedida en `FALTA_DE_LINUX.md`, punto 3 de "Lo que se hace en Linux".

Pestaña Effect:
- Barras superiores: Preset Vol, Pan (`C`), BPM con TAP; botones Save, Save to, More; selector de preset
  (`[001] ...`) con botón de sincronizar y de renombrar.
- Menú de GATE: AI Gate, Soft Gate, Hard Gate, Pro Gate, Compress, Compress Pro, F Compress, AI Ms Gate.
- Perillas de GATE (AI Gate): Gate 50, Bias 50, Detect = `Input` (selector).
- Perillas de AMP: Gain, Level, Bass, Middle, Treble, Reso, Pres, Bright. DS: mismas ocho. FX Compress Pro: Ratio, Gain,
  Knee, Thd, Attack, Level, Blend.
- Perillas de FX Wah-Wah: Speed (2.5), Q (50), Mix (80), Width (25), Level (50) y botón Sync.
- Menú de FX (parcial): Wah-Wah, Lofi, Sense-Wah, Boost, A Boost, E Boost, B Boost, Boost ED, Compress, Compress Pro,
  F Compress, Pitch, Octave, Ring, Pitch shifter, Whammy.
- Los nombres de modelo siguen el patrón `<n><CL|OD|DS>-<nombre>` (p. ej. `59CL-Pey6534`, `66CL-DieV4C2`).
- La cadena de módulos en un preset vacío es: WAH, FX, GATE, DS, **NAM** (en lugar de AMP), CAB, EQ, MOD, DLY, REV, VOL.
- En la lista de presets, del [149] al [160] se llaman "USER PRESET n".

## Qué queda pendiente
- Rango de Bend en `MBody` y `Oct2` (solo se midió en `Oct1`).
- Qué ocurre en Audio separation después de importar un archivo (no se hizo: exigiría cargar un archivo).
- `PLAN_CAPTURA_IMPORT.md` sigue en espera (escribe en flash): no ejecutar.
