# MK300 Studio — estado y traspaso

Configurador no oficial de la pedalera MK300 (Jieli 3654:7756) para Linux. Ver `README.md` para qué hace y cómo usarlo.
Este archivo sirve para retomar el trabajo en otra sesión: qué hay, cómo se probó, qué falta y las reglas acordadas.

## Reglas acordadas con el usuario
- **Pruebas de escritura solo en presets vacíos "USER PRESET n".** Nunca con `CLEAN NFDA` ni `DISTORSION NFDA`
  (ni seleccionarlos con código: una vez una app de pruebas se conectó sola y los seleccionó; por eso existe
  `MK300_NO_PEDAL=1`. Hoy la app ya no conecta sola: hay que pulsar la tarjeta del dispositivo).
- Antes de escribir en flash, respaldo del banco. La app guarda uno en `~/.local/share/mk300-studio/backups/` al conectar.
- **Nada de referencias al fabricante, a su app ni a su socio de servicios** en lo que se sube a GitHub (nombres, logos, rutas,
  código o recursos). Los nombres de modelo (ampli/pantalla/distorsión) se leen de la propia pedalera.
- Repositorio **privado**: `git@github.com:fr33co/mk300_studio.git` (rama `main`). Licencia GPL-3.0 o posterior.
- Antes de cada subida, ejecutar `sh tools/check_refs.sh` (debe decir 0 archivos). El `.gitignore` deja fuera
  `original/`, `reference/`, `analysis/asm`, capturas y backups.

## Cómo ejecutar
```
cd mk300-linux && python3 run.py                          # PyQt5, con la pedalera por USB
MK300_NO_PEDAL=1 QT_QPA_PLATFORM=offscreen python3 ...    # pruebas/capturas sin tocar la pedalera
```
La app arranca en la pantalla **Connect**: busca la MK300 (cada 1,5 s) y hay que pulsar la tarjeta para sincronizar.
Sin pedalera solo se ven presets si se abre un archivo a propósito (Archivo → Abrir / bancos de fábrica).
Si se desconecta, vuelve sola a Connect. El puerto ALSA es exclusivo: cerrar otras apps que lo usen.

## Protocolo (resuelto y verificado)
USB-MIDI SysEx: paquete `00 59 <cmd> <len16> 00 <payload> <chk>` empaquetado a 7 bits en `F0..F7`, `chk = ~sum(payload)`.
Comandos: `0x11` identidad, `0x23` leer, `0x22` escribir (RAM). Implementación: `mk300cfg/protocol.py`,
`mk300cfg/device.py` (y `tools/mk300_sysex.py`, `tools/mk300_read.py` para línea de comandos).

| Dirección | Contenido |
|---|---|
| `0x0` (71688 B) | Banco: 160 presets × 448 + `PATCHEND`. Preset n en `n*448`. |
| `0x10000000` (448 B) | Preset activo, RAM. Escribir aquí cambia el sonido sin guardar. |
| `0x20000000` (86 B) | Globales; bytes 0..1 = índice del preset activo (desde 0). |
| `0xE0000000+n` | Escribir 1 byte (0) selecciona el preset n. |
| Guardar preset | escribir 448 B en `n*448` y luego escribir `0xF0000000` vacío (sin borrado). |
| `0x70200000` | Nombres de preset (160 × 17). |
| `0x80000000` / `0x90000000` / `0xA0000000` | Nombres CAB / AMP / DS, registros de 14 B `<id><nombre>` (type 5). |
| `0x70600000` | Tipo AMP/DS activo; la app oficial lo sondea cada 1 s. |

Mapa de globales (RAM, sin comando de guardado, como hace la app oficial): `mk300cfg/settings.py` (`RAW_FIELDS`).
Verificado contra capturas de pantalla de la app oficial (EQ, Looper, Glob coinciden con los valores reales).
Tail Delay/Reverb = bits del byte `0x4b` (máscaras 1/4 y 2/8: OFF/Auto/Force): deducido del código, sin verificar.
Detalle del log de la app oficial: `analysis/log_windows.md`; capturas y volcados: `windows/` (`dumps/` y `screens/` no se suben).

## Qué funciona (probado con la pedalera, firmware v75)
- Lectura de banco, preset activo, globales y nombres de modelo (probado en modo AM3).
- Sincronización en vivo en ambos sentidos (preset, perillas, interruptores) con mensajes en la barra de estado.
  Los globales en vivo están implementados pero no probados con la pedalera.
- Save / Save to en flash con confirmación y verificación por relectura (probado en presets vacíos).
- Pantalla de conexión y regreso a ella al desconectar (el desenchufe con cable real solo se simuló).
- Interfaz: ventana maximizada y escalada, selector de presets con lista dentro de la ventana (en Wayland la nativa se
  cerraba al soltar el ratón), color de la interfaz según el color del preset, 8 temas, iconos propios, `app_icon.svg`.

## Pendiente
1. Probar globales en vivo en ambos sentidos con la pedalera en un preset vacío, y ver si sobreviven a apagarla.
2. Verificar Tail Delay/Reverb (captura en la app oficial de Windows cambiándolos).
3. Detectar cambios de banco hechos desde la pedalera (hoy solo sigue el preset activo y sus ajustes).
4. Banco completo hacia la pedalera (Import all, Swap preset, Factory Restore): probablemente borrado de sectores y
   escrituras type 5/6 grandes. El borrado de 3 MB en `0x20000000..` del log parece firmware/IR: **no tocarlo**.
5. Modo AM3/AM4 (escritura en `0x70300000`): sin entender. Nombres de modelo en AM4 sin comprobar.
6. Snapshots (`0x70400000`, 36864 B, cabecera "SnapShot"), Sounds/Import (IR) y Community: sin implementar.
7. Fidelidad: rangos estimados (Pan, BPM, Auto Gate, LC/HC del CAB, EQ); Bass EQ 7 y Whammy sin nombre; barra de título.
8. Antes de hacer público el repo: decidir qué hacer con `factory_am3.bin`, `factory_am4.bin` y `catalog.json` (datos
   del fabricante), el autor del commit (nombre y correo reales) y sacar `.git` de Syncthing (`.stignore`).
9. Opcional: reconexión automática sin pulsar la tarjeta; podar `~/.local/share/mk300-studio/backups/`.

## Notas
- La carpeta vive en Syncthing; `.git` también se sincroniza (riesgo de conflictos).
- Locales y no versionados: `tools/pylibs`, `tools/blutter`, `tools/midi_spy*.py`, `window_shots.ps1`, `original/`
  (descargas sin verificar: no ejecutar) y `analysis/asm`. No hace falta sincronizarlos.
- GNOME/Wayland con pantalla útil de 1366×768: por eso el tamaño mínimo de la ventana es 900×560.
- Las conversaciones de Claude Code van ligadas a la ruta de la carpeta: al moverla, retomar leyendo este archivo.
