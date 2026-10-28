# MK300 Studio — estado y traspaso

Configurador no oficial de la pedalera MK300 (Jieli 3654:7756) para Linux. Ver `README.md` para qué hace y cómo usarlo.
Este archivo sirve para retomar el trabajo en otra sesión: qué hay, cómo se probó, qué falta y las reglas acordadas.

## Reglas acordadas con el usuario
- **Pruebas de escritura solo en presets vacíos "USER PRESET n".** Nunca con `CLEAN NFDA` ni `DISTORSION NFDA`
  (ni seleccionarlos con código: una vez una app de pruebas se conectó sola y los seleccionó. Hoy la app ya no
  conecta sola: hay que pulsar la tarjeta del dispositivo; en pruebas con código, no llamar a `connect_pedal`
  salvo con la pedalera en un preset vacío).
- Antes de escribir en flash, respaldo del banco. La app guarda uno en `~/.local/share/mk300-studio/backups/` al conectar.
- **Nada de referencias al fabricante, a su app ni a su socio de servicios** en lo que se sube a GitHub (nombres, logos, rutas,
  código o recursos). Los nombres de modelo (ampli/pantalla/distorsión) se leen de la propia pedalera.
- Repositorio **privado**: `git@github.com:fr33co/mk300_studio.git` (rama `main`). Licencia GPL-3.0 o posterior.
- Antes de cada subida, ejecutar `sh tools/check_refs.sh` (debe decir 0 archivos). El `.gitignore` deja fuera
  `original/`, `reference/`, `analysis/asm`, capturas y backups.

## Cómo ejecutar
```
cd mk300-linux && python3 run.py                          # PyQt5, con la pedalera por USB
QT_QPA_PLATFORM=offscreen python3 ...                     # pruebas/capturas (la app no conecta sola)
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
- Sincronización en vivo en ambos sentidos (preset, perillas, interruptores, globales) con mensajes en la barra de estado.
- Rangos de la app oficial aplicados (Pan, BPM, Auto Gate, EQ) y título con la versión (`MK300 v75`): probados con la pedalera.
  Los rangos salen del análisis del código de la app oficial (`windows/ANALISIS_RANGOS.md`); el BPM máximo del preset (240) es supuesto.
- Save / Save to en flash con confirmación y verificación por relectura (probado en presets vacíos).
- Pantalla de conexión y regreso a ella al desconectar (el desenchufe con cable real solo se simuló).
- Interfaz: ventana maximizada y escalada, selector de presets con lista dentro de la ventana (en Wayland la nativa se
  cerraba al soltar el ratón), color de la interfaz según el color del preset, 8 temas, iconos propios, `app_icon.svg`.

## Pendiente
1. ~~Probar globales en vivo en ambos sentidos~~: probado por el usuario con la pedalera (2026-10-28): los cambios
   llegan y se guardan.
2. Tail Delay/Reverb: la app oficial muestra Delay y Reverb con OFF/Auto/Force (`windows/RESULTADOS_PARTE3.md`), igual
   que el clon, pero las capturas no prueban el mapeo de bits del byte `0x4b`. Verificarlo con la pedalera: cambiar Tail
   en el clon (preset vacío) y comprobar el resultado en la pedalera o en la app oficial.
3. ~~Detectar cambios de banco hechos desde la pedalera~~: hecho (cada ~2 s lee los nombres de preset y la flash del
   activo; si cambian, relee el banco y actualiza la app sin pisar presets que el usuario editó en la app). Limitación: un
   cambio de contenido sin cambio de nombre en un preset no activo no se ve hasta que se active o cambie algún nombre.
   Probado solo con pedalera simulada: falta probarlo con la real (renombrar/guardar un preset desde la pedalera, en un
   preset vacío).
4. Banco completo hacia la pedalera (Import all, Swap preset, Factory Restore): probablemente borrado de sectores y
   escrituras type 5/6 grandes. El borrado de 3 MB en `0x20000000..` del log parece firmware/IR: **no tocarlo**.
5. Modo AM3/AM4 (escritura en `0x70300000`): sin entender. Nombres de modelo en AM4 sin comprobar.
6. Snapshots (`0x70400000`, 36864 B, cabecera "SnapShot"), Import real a la pedalera (DS/AMP/CAB/Preset) y Community: sin
   implementar. La barra lateral ya sigue a la app oficial (Param, Import con DS/AMP/CAB/Preset, AI Tone "Coming Soon",
   Audio separation como biblioteca local sin separación de pistas, Community); sin pedalera solo están activas Connect,
   Audio separation y Community.
7. Fidelidad: hecho (rangos de Pan, BPM, Auto Gate, EQ y CAB, Bass EQ 7, Whammy con Mix solo en MBody, título con
   versión, arco invertido de High Cut en CAB). Falta: rango de Bend de Whammy en MBody/Oct2 (se asume 0–100), y que la
   app oficial llama NAM al slot AMP en un preset vacío. Hipótesis sin verificar: el modelo AMP nº 1 de la pedalera es un
   modelo importado por el usuario (su registro `unboosted her…` no lleva el número delante, a diferencia de los demás) y
   la app etiqueta NAM cuando el slot usa un modelo importado. Para confirmarlo: ver en la app oficial qué modelo es el
   nº 1 de la lista AMP y si la etiqueta cambia a AMP al elegir otro.
   En la app oficial AI Tone solo muestra "Coming Soon" (no hay nada que replicar); Audio separation es una biblioteca
   local de audio (Import de WAV/MP3/MP4...), sin internet ni cuenta hasta donde se vio.
8. Antes de hacer público el repo: decidir qué hacer con `factory_am3.bin`, `factory_am4.bin` y `catalog.json` (datos
   del fabricante), el autor del commit (nombre y correo reales) y sacar `.git` de Syncthing (`.stignore`).
9. ~~Reconexión automática y poda de backups~~: hecho. Solo reconecta tras perder la conexión por sorpresa (nunca al
   arrancar ni tras desactivar la sincronización a mano) y sin cambios sin guardar; conectar solo lee. Se conservan los
   30 backups más recientes. Probado con pedalera simulada; falta el desenchufe real.

## Notas
- La carpeta vive en Syncthing; `.git` también se sincroniza (riesgo de conflictos).
- Locales y no versionados: `tools/pylibs`, `tools/blutter`, `tools/midi_spy*.py`, `window_shots.ps1`, `original/`
  (descargas sin verificar: no ejecutar) y `analysis/asm`. No hace falta sincronizarlos.
- GNOME/Wayland con pantalla útil de 1366×768: por eso el tamaño mínimo de la ventana es 900×560.
- Las conversaciones de Claude Code van ligadas a la ruta de la carpeta: al moverla, retomar leyendo este archivo.
