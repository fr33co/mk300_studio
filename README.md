# MK300 Studio

**MK300 Studio** es un configurador de escritorio de la pedalera **MK300** (USB 3654:7756) para Linux. Hace lo que la app
oficial del fabricante hace en Windows: editar presets, ajustes globales, EQ, Looper y Drum, con la pedalera conectada por USB
y sincronizada en los dos sentidos.

> Proyecto no oficial y sin relación con el fabricante. Se hizo por ingeniería inversa del tráfico USB-MIDI y de la
> app original. **Úsalo bajo tu responsabilidad**: escribe en la memoria de la pedalera.

## Qué hace

- Lee el banco completo (160 presets) y abre la app en el preset que tenga activo la pedalera.
- **Sincronización en vivo** (Archivo → Sincronizar con la pedalera): el preset activo y los ajustes se reflejan
  en ambos sentidos; la barra de estado indica qué cambió y de dónde.
- **Save / Save to** guardan el preset en la flash de la pedalera, con confirmación y verificación por relectura.
- Pestañas Effect, Glob, EQ, Looper y Drum con la disposición de la app oficial, cadena de 11 efectos reordenable,
  perillas, 8 temas y color de la interfaz según el color del preset.
- Los nombres de los modelos de ampli, pantalla y distorsión se leen de la propia pedalera al conectar, así que
  siempre coinciden con lo que ella muestra (sin pedalera se usa una lista de respaldo).
- Funciona también sin pedalera: edita bancos `.bin` como archivos.

## Estado

| Función | Estado |
|---|---|
| Lectura de banco, preset activo y globales | Probado con la pedalera |
| Edición en vivo y guardado de presets | Probado (firmware v75, solo en presets vacíos) |
| Ajustes globales (Glob, EQ, Looper, Drum) | Mapa verificado contra capturas de la app oficial; sincronización en vivo sin probar del todo |
| Tail Delay/Reverb | Deducido del código, sin verificar en la pedalera |
| Import/Swap de banco completo, Factory Restore, Snapshots, IR/Sounds | No implementado (no escribe nada de esto) |

Solo se ha probado con el firmware **v75**.

## Requisitos

- Linux con ALSA (`amidi`) y Python 3.10+
- `PyQt5` (`pip install PyQt5` o el paquete `python3-pyqt5` de tu distribución)
- La MK300 conectada por USB. Tu usuario debe poder abrir `/dev/snd/midiC*D*` (grupo `audio`); en Ubuntu suele
  bastar con tener la sesión iniciada. Hay una regla udev opcional en `tools/99-mk300.rules`.

## Instalación (paquete .deb)

```
sh packaging/build_deb.sh            # genera dist/mk300-studio_0.1.0_all.deb
sudo apt install ./dist/mk300-studio_0.1.0_all.deb
mk300-studio                         # o desde el menú de aplicaciones
```

Instala la app en `/usr/lib/mk300-studio` y depende de `python3-pyqt5` y `alsa-utils`. Los respaldos se guardan en
`~/.local/share/mk300-studio/backups/`. Para quitarla: `sudo apt remove mk300-studio`.

## Uso

```
cd mk300-linux
python3 run.py
```

Al abrir, si la pedalera está conectada se lee su banco y se guarda una copia en `~/.local/share/mk300-studio/backups/`.
Cierra otras aplicaciones que usen la pedalera (como un editor MIDI): el puerto es exclusivo.

Para pruebas sin tocar la pedalera: `MK300_NO_PEDAL=1 python3 run.py`.

## Protocolo (resumen)

USB-MIDI SysEx. Paquete `00 59 <cmd> <len16> 00 <payload> <chk>`, empaquetado a 7 bits dentro de `F0 … F7`,
con `chk = ~sum(payload)`. Comandos: `0x11` identidad, `0x23` leer, `0x22` escribir (RAM).

| Dirección | Contenido |
|---|---|
| `0x00000000` | Banco: 160 presets × 448 bytes + `PATCHEND` (flash) |
| `0x10000000` | Preset activo (RAM, 448 bytes) |
| `0x20000000` | Ajustes globales (86 bytes); bytes 0–1 = índice del preset activo |
| `0xE0000000 + n` | Escribir 1 byte (0) selecciona el preset n |
| `0xF0000000` | Escritura vacía tras escribir un preset: lo confirma en flash |
| `0x70200000` | Nombres de preset |
| `0x80000000` / `0x90000000` / `0xA0000000` | Nombres de modelo CAB / AMP / DS (registros de 14 bytes `<id><nombre>`) |

Detalle y mapa completo: `analysis/log_windows.md`, `windows/README.md` y `mk300-linux/mk300cfg/`
(`protocol.py`, `device.py`, `bank.py`, `settings.py`).

## Estructura

```
mk300-linux/   la app (PyQt5)
tools/         utilidades: decodificador de capturas SysEx, lector de línea de comandos, extractores de catálogo
windows/       capturas MIDI y notas tomadas con la app oficial en Windows
analysis/      notas de la ingeniería inversa
HANDOFF.md     estado del proyecto y pendientes
```

## Seguridad

- La app escribe solo en el preset activo (RAM), en posiciones de preset que tú confirmas y en los ajustes
  globales. No borra sectores ni toca firmware.
- Antes de guardar presets importantes, conserva un respaldo (`~/.local/share/mk300-studio/backups/` se genera solo al conectar).
- Usa solo software que hayas obtenido de forma legítima.

## Licencia

[GPL-3.0 o posterior](LICENSE). Los iconos de `mk300-linux/assets/` son originales de este proyecto.
"MK300" es el nombre del producto de su propietario y se cita solo para indicar con qué hardware es compatible.
