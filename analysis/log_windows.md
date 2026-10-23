# Análisis de windows/app_debug_log_2026-10-17.txt (la app oficial en Windows, 279k líneas)

El log NO trae bytes crudos de los paquetes (solo longitudes), pero sí el modelo de acceso de la app:
**memoria direccionada** con comandos leer / escribir / borrar. Transporte no indicado en el log.

## Primitivas (cola `CmdQ`)
- `read type=4|5 addr len`, `write type=4|5 addr len`, `erase addr` (sectores de 0x1000), `_sendWithRetry` (3 intentos).
- Respuesta de lectura = datos + ~15 bytes de sobrecarga (10 -> 25, 448 -> 463, 86 -> 101). Lecturas grandes llegan en
  trozos de 1030 bytes (1024 de datos + 6 de cabecera). `type=5` parece el modo "bloque grande"; `type=4` el normal.
- Escrituras grandes se envían en paquetes de 1030 bytes (el último más corto). Escritura de 1 byte = paquete de 16 bytes.

## Mapa de direcciones
| Dirección | Tam. | Uso |
|---|---|---|
| `0x00000000` | 71688 | **Banco completo** = 160 x 448 + 8 (`PATCHEND`). Coincide con el formato ya verificado. Parche n en `n*448` (ej. `0x8c00`=n80, `0x8dc0`=n81, escritura de 448 bytes). |
| `0x10000000` | 448 | Parche actual (edición en vivo). Campos sueltos: enables en `+0x2c..0x2f` (eid 3 -> `0x2e`, eid 4 -> `0x2f`), parámetros de 2 bytes desde `+0x5a/0x62/0x8a.../0xa2...` |
| `0x20000000` | 86 | Ajustes globales (se lee al conectar; se escriben campos como `0x2000002a`, `0x20000034`) |
| `0x70200000` | 2720 | Tabla leída al conectar (type 4) |
| `0x70400000` | 36864 | Lectura/escritura (10 escrituras): probable datos de usuario (IR/cab?) |
| `0x70600000` | 10 | Tipo AMP/DS: `[DS 4B ascii][AMP 4B ascii][0x00][checksum]`, sondeado **cada 1 s**. Ej. `41 4d 32 00 41 4d 32 00 00 7f` = "AM2". checksum válido = ~suma? (0x7f) |
| `0x80000000` / `0x90000000` / `0xa0000000` | 1400 / 1680 / 560 | Tablas type 5 leídas al conectar (listas DS/AMP/CAB o nombres) |
| `0x70300000` | 1 | escritura 1 byte (cambio de modo/banco?) |
| `0xe0000000..0xe0000052` | 1 | escrituras de 1 byte (footswitch/controles; `0xe0000050/51` muy frecuentes) |
| `0xf0000000` | 0 | escritura vacía (73 veces): "commit/aplicar/guardar" |

## Secuencia típica
- Conexión: leer `0x20000000`, `0x70600000`, `0x80000000`, `0x90000000`, `0xa0000000`, `0x70200000`, `0x10000000`.
- Cambiar enable de efecto: write 1 byte en `0x10000000 + offset` (`sendEffectEnable`).
- Mover perilla: write 2 bytes en `0x10000000 + offset` (`sendEffectParam eid pid val`).
- Guardar/volcar banco: `erase` de sectores 0x1000 consecutivos + `write type=5 addr=0x0 len=7936` por tandas.

## Siguiente paso
Falta ver los BYTES del paquete (cabecera/cmd). Hipótesis a probar con `tools/bz_query.py`: la pedalera no contestó
a `00 B2 22 ...` quizá porque el protocolo real es lectura por dirección. Pedir al usuario una captura HCI/USBPcap
para ver la cabecera de una lectura (`read type=4 addr=0x70600000 len=10`, respuesta 25 bytes).
