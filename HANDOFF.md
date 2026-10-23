# Clon de la app oficial para la MK300 (Linux) — estado y traspaso

> **ACTUALIZACIÓN 2026-10-23 (sesión Windows): protocolo resuelto.** La app oficial de Windows usa
> **USB-MIDI SysEx**, no BLE. Detalles, secuencia de conexión, volcados reales y mapa de escrituras en
> `windows/README.md`; codificador/decodificador de referencia en `tools/mk300_sysex.py`.
> La sección "Protocolo reconstruido" de abajo queda obsoleta en la cabecera (`00 B2 22` era `00 59` mal leído).

Objetivo: una app nativa de Linux (Ubuntu) equivalente a la app oficial del fabricante, para configurar la
pedalera MK300 (Jieli 3654:7756). Regla del usuario: **no escribir nada en la pedalera**
hasta que el protocolo esté validado; la app solo edita archivos.

## Cómo ejecutar la app
```
cd mk300-linux && python3 run.py        # PyQt5; datos en data/, iconos en assets/
```

## Qué hay hecho (carpeta `mk300-linux/`)
- Interfaz con la disposición de la app oficial: menú lateral (Param, Sounds, Import, Community),
  pestañas Effect/Glob/EQ/Looper/Drum, cadena de 11 efectos reordenable, perillas, 8 temas.
- Formato de banco verificado: 160 parches x 448 bytes + `PATCHEND` (8 bytes). Mapa del parche
  en `mk300cfg/bank.py`. Nombres de modelos DS/AMP/CAB en `data/models.json` (valor de tipo = id - 1).
- Catálogo de efectos (`data/catalog.json`) extraído del ensamblador con `tools/extract_catalog.py`
  y completado con `tools/finalize_catalog.py` (DLY 27 tipos, FX 16).
- Ajustes globales (Glob/EQ/Looper/Drum): NO están en los bancos; se guardan en `<banco>.glob.json`.

## Protocolo (RESUELTO, ver windows/README.md)
- Transporte real: **USB-MIDI SysEx** (no BLE). Paquete `00 59 <cmd> <len16> 00 <payload> <chk>`, empaquetado a 7 bits
  dentro de `F0..F7`. Comandos: 0x11 identidad, 0x23 leer, 0x22 escribir (RAM). Implementación: `tools/mk300_sysex.py`
  (verificada contra la captura) y cliente solo-lectura `tools/mk300_read.py`.
- Mapa de memoria: `analysis/log_windows.md`. Banco = leer `0x0` x 71688; preset actual `0x10000000` x 448;
  globales `0x20000000` x 86; nombres de preset `0x70200000` (160 x 17); modelos CAB/AMP/DS en type 5 `0x80/90/a0000000`.
- Validado en Linux (2026-10-23), siempre en presets vacíos "USER PRESET": lectura de banco, preset activo = bytes 0..1 de
  `0x20000000` (desde 0), RAM del preset activo `0x10000000`, selección = escribir 0 en `0xe0000000+n`, guardado en flash =
  escribir 448 bytes en `n*448` + escribir `0xf0000000` vacío (sin erase). Todo en `mk300cfg/device.py`.
- App: al abrir lee la pedalera y salta al preset activo; Archivo > "Sincronizar con la pedalera (USB)" (sondeo 400 ms):
  preset y ajustes se reflejan en ambos sentidos; Save / Save to guardan en flash (con confirmación y verificación).
  No se prueba con CLEAN NFDA / DISTORSION NFDA (regla del usuario). Respaldos automáticos en `mk300-linux/backups/`.
  Globales (`0x20000000`, 86 bytes): mapa en `mk300cfg/settings.py` (RAW_FIELDS), sacado de los cierres de GlobFields y
  contrastado con las capturas de pantalla de la app oficial (`windows/screens`): EQ, Looper y Glob coinciden con los valores reales.
  Tail Delay/Reverb = bits del byte 0x4b (máscaras 1/4 y 2/8: OFF/Auto/Force) -> deducido del código, sin verificar en la pedalera.
  Los globales se escriben en RAM sin comando de guardado (como la app oficial). Pendiente: probar globales en vivo en un preset vacío
  y comprobar si la pedalera los conserva al apagarla.

## Lo que falta y se puede recoger en Windows (partición con la app oficial)
Guardar todo en `mk300/windows/` (el proyecto está en Syncthing):
1. **Capturas de pantalla a resolución completa** de: Param (Effect con AMP, CAB, DLY, MOD, FX, GATE, REV y WAH
   abiertos), Glob, EQ, Looper, Drum, Sounds (DS/AMP/CAB), Import, Community, menú More, y sobre todo
   **la pantalla/diálogo de conexión** (¿lista de dispositivos? ¿USB o Bluetooth? ¿qué nombre muestra?).
2. **Exportaciones de la app con la pedalera conectada:** More -> "Share all presets" (banco completo),
   "Share current preset", Export Snapshot, Share EQ. Con esos archivos se valida el formato real.
3. **Dato clave:** cómo se conecta la app oficial en Windows (USB o Bluetooth) y si funciona con la pedalera
   conectada solo por USB.
4. Opcional, captura USB: Wireshark con USBPcap sobre el bus de la MK300 mientras la app lee presets.
   Si la app conecta por Bluetooth, la captura USB no mostrará configuración (también sirve como prueba).
5. Bluetooth: en Android, activar "Registro de rastreo HCI de Bluetooth", usar `original/apk/la app oficial.apk`
   leyendo presets y copiar `btsnoop_hci.log` aquí. Es la forma más corta de ver los bytes reales.

## Notas
- No ejecutar nada de `original/` (descargas sin verificar); no hace falta sincronizar `original/` ni
  `reference/video/` (unos 300 MB).
- La app oficial no arranca bajo Wine 9 (falta `combase.RoFailFastWithErrorContext`).
- Herramientas locales sin sudo: `tools/pylibs` (bleak, pyusb, yt-dlp, pyelftools). Análisis de la app:
  `analysis/` (blutter sobre `libapp.so`). Referencia visual: `reference/` (fotogramas del vídeo de la guía).
- Pendiente de fidelidad visual: barra de título, tipografía y colores exactos; rangos estimados (Pan, BPM,
  Auto Gate, LC/HC, CAB Low/High Cut, EQ); parámetros de Bass EQ 7 y Whammy sin nombre.
