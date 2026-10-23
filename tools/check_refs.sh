#!/bin/sh
# Comprueba que lo versionado no menciona al fabricante, a su app, a su socio de servicios ni al usuario local.
# Los términos se arman por partes para que este script no se detecte a sí mismo.
a='m-?v''ave'; b='m-?w''ave'; c='tone ?30''00'; d='ef''cs'; e='aguada''rrama'
n=$(git grep -I -i -c -E "$a|$b|$c|$d|$e" HEAD -- . ':!LICENSE' | wc -l)
echo "archivos con referencias en HEAD: $n"
[ "$n" -eq 0 ]
