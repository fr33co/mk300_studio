# Datos recogidos en Windows (2026-10-23): PROTOCOLO RESUELTO

Para la sesión de Linux. Nuestras herramientas solo **observaron** el tráfico de la app oficial (Frida sobre winmm);
no enviaron nada a la pedalera. Durante la captura la app escribió algunos valores al tocar controles, y
**todos volvieron a su valor original**. Fueron escrituras en RAM; no hubo borrado ni guardado en flash.

## 1. Transporte: USB-MIDI SysEx (no BLE)
- La app oficial para Windows (Flutter) habla con
  la MK300 por **USB MIDI** (`winmm`, mensajes largos SysEx). Consola de la app: `isBle=false ... USB MIDI 握手`.
- En Linux: usar el puerto ALSA rawmidi de la MK300 (`amidi -l`, p. ej. `hw:X,0,0`) o `mido`/`python-rtmidi`.
  Las pruebas BLE de antes no contestaban porque la consulta estaba mal codificada (ver 2).
- Firmware de esta pedalera: **v75** (identidad `MK300_075`; la app recomienda v72).

## 2. Formato (verificado byte a byte; implementación de referencia en `../tools/mk300_sysex.py`)
```
SysEx = F0 + pack7(paquete) + F7
pack7: flujo de 7 bits, bit menos significativo primero (cada byte MIDI lleva 7 bits; el último se rellena con 0)
paquete = 00 59 <cmd> <len_lo> <len_hi> 00 <payload (len bytes)> <chk>      chk = ~sum(payload) & 0xFF
```
El `F0 00 32 ...` del principio **no** es un ID de fabricante: es `00 59` ya empaquetado.
La cabecera `00 B2 22 ...` del HANDOFF estaba mal leída (0xB2 = 0x59 desplazado).

| cmd | qué | payload petición | respuesta |
|---|---|---|---|
| `0x11` | identidad | vacío | cmd 0x11, payload `"MK300_075"` + ceros (27 bytes) |
| `0x23` | leer | `type(1) addr(4 LE) len(2 LE) 00` | cmd 0x23, mismo payload + `len` bytes de datos |
| `0x22` | escribir (RAM) | `type(1) addr(4 LE) len(2 LE) 00 datos` | cmd 0x00 (ACK), payload `00` = ok |
| `0x15` | mensaje MIDI envuelto | 3 bytes MIDI (p. ej. `b0 16 7f`) | ACK `00` |
| `0x00` | ACK | `00` ok / `01` error | — |

Ejemplos reales:
```
consulta        F0 00 32 45 00 00 00 40 7F F7                       (paquete 00 59 11 00 00 00 FF)
leer 0x70600000 F0 00 32 0D 41 00 00 00 02 00 00 00 03 27 01 00 00 21 00 F7
```
- Las lecturas largas se trocean en bloques de **1015 bytes** (0x3F7), con la dirección avanzando.
- Hay un `type` (4 o 5) delante de la dirección: 4 = memoria de config/presets, 5 = listas de modelos.
- `read type=5 0xd0000000 len=32` devuelve ACK `01` (no soportado en este firmware; la app sigue igual).

## 3. Secuencia al conectar (captura `midi_capture_20261023_161249*.txt`)
1. `QUERY` (x2) → `MK300_075`
2. `read t5 0xd0000000 32` → ACK 01
3. `read t4 0x20000000 86` → globales
4. `read t4 0x70600000 10` → tipo DS/AMP activo (`"AM2\0" "AM2\0" 00 chk`)
5. `read t5 0x80000000 1400` → 100 nombres de **CAB/IR** (registros de 14 bytes: `"1EAGLProV30s"`...)
6. `read t5 0x90000000 1680` → 120 nombres de **AMP** (14 bytes)
7. `read t5 0xa0000000 560` → 40 nombres de **DS** (14 bytes)
8. `read t4 0x70200000 2720` → **160 nombres de preset** × 17 bytes
9. `read t4 0x10000000 448` → **preset actual** (448 bytes, mismo formato que el banco)
10. Después, cada segundo: `read 0x20000000 86` + `read 0x70600000 10` (sondeo).

## 4. Escrituras observadas (útiles para mapear; todas revertidas por el usuario)
Offset dentro del bloque = dirección - base. Falta confirmar qué control de la UI era cada una.
```
t=10.3  0x20000038 len1  01→00→01      (global +0x38)
t=30.5  0x2000002a len2  100→90→81→90→100  (global +0x2A, perilla 0-100)
t=35.2  0x2000003c len1  01→00→01      (global +0x3C)
t=36.9  0x2000003d len1  00→01→00      (global +0x3D)
t=58.7  0x20000036 len2  1→0→1         (global +0x36)
t=60.9  0x2000000b len1  00→01→00      (global +0x0B)
t=64.3  MIDI b0 16 7f / b0 16 00       (CC#22 por el canal de control)
t=100.2 0x10000032 len1  00→01→00      (preset actual +0x32)
t=107.9 0x10000035 len1  01→00→01      (preset actual +0x35)
```
Del log antiguo (uso real): cambiar de preset = `write 0x70300000 len1`; parámetros del preset =
`write 0x10000xxx`; guardar en flash usa borrado + `write type=5/6` (NO usar hasta validar).

## 5. Archivos
- `dumps/*.bin`: volcados binarios reales de la pedalera (nombre = `t<type>_<addr>_<len>.bin`).
- `midi_capture_20261023_161249.txt`: captura cruda (conexión completa + pestañas). `*_decoded.txt`: decodificada.
- `midi_capture_drv_*.txt`: capturas cortas previas (solo sondeo).
- `app_debug_log_2026-10-17.txt`: log interno de la app (17-18/oct) con el mapa lógico de lecturas,
  escrituras y borrados (incluye flasheo de presets: `erase` + `write type=5/6`).

## 6. Herramientas (`../tools/`)
- `mk300_sysex.py`: pack7/unpack7, `query()`, `read_req()`, `write_req()`, `parse()`;
  `python mk300_sysex.py decode <captura> --dumps DIR`.
- `midi_spy.py` + `midi_spy_drv.js`: lanza la app oficial bajo Frida y graba el SysEx (Windows).
- `midi_spy_attach.py`: lo mismo sobre una app oficial ya abierta.

## Siguiente paso sugerido (Linux)
Solo lectura: abrir el rawmidi de la MK300, enviar `query()` y esperar `MK300_075`; luego `read_req(0x10000000, 448)`
y comparar con `dumps/t4_10000000_448.bin`. Mantener la regla de no escribir hasta validar.
