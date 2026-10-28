# Plan de captura: Import (DS / AMP / CAB / Preset)

**EN ESPERA: no ejecutar hasta que el usuario lo autorice y se haya decidido cómo restaurar un modelo importado.**

Objetivo: saber qué escribe la app oficial en la pedalera al importar un modelo (AMX/NAM), un CAB o un preset, para que
Linux pueda hacerlo. Hasta ahora todas las capturas fueron de solo observación. **Esta no lo es**: importar de verdad
escribe en la flash (borrado de sectores y escrituras `type=5/6`, ver `app_debug_log_2026-10-17.txt`).

## Antes de empezar (obligatorio)
1. Respaldar el banco con el clon de Linux (conectar y comprobar que se creó
   `~/.local/share/mk300-studio/backups/mk300_<fecha>.bin`) o con los volcados de `windows/dumps/`. Guardar una copia
   fuera de la carpeta sincronizada.
2. **No tocar `CLEAN NFDA` ni `DISTORSION NFDA`.** La importación escribe en la zona de modelos, no en esos presets,
   pero dejar la pedalera sobre un preset vacío "USER PRESET n" durante toda la prueba.
3. Usar solo archivos propios o de prueba (un AMX/NAM pequeño). Importar **un solo modelo por tipo**, en una ranura que
   se pueda sobrescribir sin pérdida (anotar cuál era el modelo anterior).
4. Tener a mano la forma de restaurar (otra importación del modelo original, o Factory Restore de la app). Si no se sabe
   restaurar, **no continuar**: avisar primero.

## Qué grabar
Con el spy Frida sobre la app ya abierta (`tools/midi_spy_attach.py`, local, no versionado):
- Una captura por operación, en archivos separados: `import_ds`, `import_amp`, `import_cab`, `import_preset`.
- Anotar en `windows/RESULTADOS_IMPORT.md`: archivo usado (nombre y tamaño), ranura de destino, hora de inicio/fin,
  mensajes que mostró la app, y si la pedalera reinició o cambió de preset.
- Capturar también la pantalla antes y después de "Save to Device".
- Tras cada importación, volcar de nuevo los bloques `0x80000000`, `0x90000000`, `0xA0000000` (nombres CAB/AMP/DS) y el
  banco, para comparar con el estado anterior.

## Qué se espera aprender
- Direcciones y tipos (`type=5/6`) de escritura, tamaño de bloque y orden (borrar, escribir, confirmar).
- Formato en que se envía el modelo (cabecera, longitud, checksum) y cómo se convierte AMX/NAM.
- Cómo se actualiza el nombre del modelo en las listas.

## No hacer
- No repetir importaciones "para ver"; una por tipo basta.
- No interrumpir una escritura (no desconectar ni cerrar la app a medias).
- No incluir el nombre de marca del fabricante en archivos ni notas.
