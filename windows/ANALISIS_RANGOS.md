# Rangos y nombres obtenidos del análisis de la app oficial (sin usar la interfaz)

Fuente: volcado descompilado en `analysis/asm/` (local, no versionado) (solo lectura; no se tocó la pedalera ni la app).
Cubre los puntos 1 a 6 de `PENDIENTE_CAPTURAS.md`. Los puntos 7 y 8 (AI Tone, Audio separation, Import) y las capturas
siguen requiriendo la interfaz.

Leyenda: **[confirmado]** = constante leída directamente del código del control; **[inferido]** = valor que aparece en el
código del editor pero cuya asignación a un control concreto hay que verificar con la app.

## 1. Pan (Effect) — [confirmado]
- Mínimo `-100`, máximo `100` (slider "Pan", `product_patch_controls.dart`).

## 2. BPM y Drum BPM
- **Drum BPM** (Drum): `40` a `240` — [confirmado] (`mk300_view.dart`, `BpmSlider`).
- **BPM** del preset (Effect): mínimo `40` — [confirmado]. Máximo: no aparece como constante en el control; el ajuste de
  tempo global usa `40`–`240`, así que se asume `240` — [inferido].

## 3. Auto Gate (Looper) — [confirmado]
- Máximo `100` (`product_looper_editor.dart`, `ParamSlider` "Auto Gate"). Mínimo no explícito (por defecto 0).

## 4. EQ paramétrico (`product_eq_editor.dart`) — [confirmado]
| Control | Valor crudo | Cómo lo muestra la app |
|---|---|---|
| LC | `19` a `200` | por debajo de 20 muestra `OFF`; si no, Hz |
| HC | `4000` a `20500` | por encima de 20000 es apagado (OFF); si no, kHz (`valor/1000`, sufijo `K`) |
| Freq (P1..P4) | `20` a `20000` Hz | desde 1000 muestra `x.xk`; por debajo, Hz |
| Q (P1..P4) | `1` a `160` | `valor/10` → **0.1 a 16.0** |
| Gain (P1..P4) | `-18` a `18` | entero en dB, con `+` si es positivo y sufijo `dB` |

EQ gráficos de los módulos (`effect_params.dart`, `_eqParam`) — [confirmado]: cada banda va de `-48` a `48` en
pasos de 0.5, es decir **-24 dB a +24 dB**.

## 5. CAB
- En la definición de módulos (`effect_params.dart`) el módulo CAB no tiene tipos hijos ni perillas propias: es un
  módulo sin lista de parámetros de efecto. [confirmado]
- **CAB Level** (importar CAB): `0` a `127` [confirmado]. LC/HC y demás perillas del CAB no aparecen como constantes
  en el código; siguen pendientes de captura con la app.

## Otros controles de la interfaz (útiles para el clon) — [confirmado]
Sliders con su rango, extraídos de `ui/` (solo los de MK300):

| Control | Rango |
|---|---|
| VOL (maestro) | 0–100 |
| BT&USB VOL | 0–100 |
| USB REC VOL | 0–100 |
| Preset Vol | 0–100 |
| Rec Vol / Play Vol (Looper) | 0–100 |
| Reference (afinador, Hz) | 430–450 |
| Bypass Vol | 0–100 |
| Tempo global (BPM) | 40–240 |
| Importar AMP/DS (ganancia) | 0–255 |

Selector **RCH** (clave `optRch`), junto a "USB Audio" en la vista MK300: opciones `Nor` / `Dry` / `NoCAB`
[confirmado]. Justo antes hay otro selector `A:B` (`optAB`) junto a "Pedal State".

## 6. Nombres sin identificar — [confirmado]
- **Bass EQ 7**: EQ gráfico de **7 bandas**: 50 Hz, 120 Hz, 400 Hz, 500 Hz, 800 Hz, 4.5 kHz, 10 kHz.
  Los otros tipos de EQ gráfico son *Guitar EQ 6* (100 Hz, 200 Hz, 400 Hz, 800 Hz, 1.6 kHz, 3.2 kHz) y *Normal EQ 10*
  (31.25 Hz, 62.5 Hz, 125 Hz, 250 Hz, 500 Hz, 1 kHz, 2 kHz, 4 kHz, 8 kHz, 16 kHz).
- **Whammy**: tipo del módulo FX (`buildMk300WhammyChildType`), con 3 parámetros [confirmado]:
  1. **Mode**: `0` a `2` → `MBody`, `Oct1`, `Oct2`.
  2. **Bend**: rango por defecto (como el resto de parámetros sin límites explícitos).
  3. **Mix**: rango por defecto. Se oculta o deshabilita según el valor de Mode (con Mode = 0, `MBody`, cambia su
     estado) — [inferido]; confirmar en la app qué pasa con Mix en cada modo.
  Ya aplicado en `mk300-linux/data/catalog.json` (vía `tools/finalize_catalog.py`): Whammy con Mode (0-2), Bend y Mix, y
  nombres de banda de Bass EQ 7 (antes sin nombre).

## Nota sobre el registro de depuración de la app
`debug_log` registra los valores que se enviaron en una sesión (`sendEffectParam eid pid val`), pero no sirve para
obtener rangos: solo contiene los valores que se usaron, no los extremos.

## Ya cubierto por el clon
`mk300-linux/data/catalog.json` ya incluye `minVal`/`maxVal` de los parámetros de efectos (WAH, FX, GATE, EQ, MOD, DLY,
REV), así que ahí no hace falta más extracción.

## Sigue pendiente (requiere la app)
- Capturas para confirmar lo marcado como [inferido]: BPM máximo del preset y comportamiento de Mix en Whammy; y las perillas del CAB.
- Puntos 7 y 8: AI Tone, Audio separation, Import.
