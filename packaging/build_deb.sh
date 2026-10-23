#!/bin/sh
# Construye dist/mk300-studio_<versión>_all.deb. Uso: sh packaging/build_deb.sh [versión]
set -e
cd "$(dirname "$0")/.."
VER="${1:-0.1.0}"
PKG=mk300-studio
STAGE="$(mktemp -d)"
ROOT="$STAGE/$PKG"
LIB="$ROOT/usr/lib/$PKG"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$LIB" "$ROOT/usr/bin" "$ROOT/usr/share/applications" "$ROOT/usr/share/doc/$PKG" \
         "$ROOT/usr/share/icons/hicolor/scalable/apps" "$ROOT/DEBIAN"

# aplicación (sin cachés ni datos de usuario)
cp -r mk300-linux/mk300cfg mk300-linux/data mk300-linux/assets mk300-linux/run.py "$LIB/"
find "$LIB" -name __pycache__ -prune -exec rm -rf {} +

printf '#!/bin/sh\nexec python3 /usr/lib/%s/run.py "$@"\n' "$PKG" > "$ROOT/usr/bin/$PKG"
cp packaging/mk300-studio.desktop "$ROOT/usr/share/applications/"
cp mk300-linux/assets/app_icon.svg "$ROOT/usr/share/icons/hicolor/scalable/apps/$PKG.svg"
cp README.md "$ROOT/usr/share/doc/$PKG/README.md"
cat > "$ROOT/usr/share/doc/$PKG/copyright" <<C
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: MK300 Studio

Files: *
Copyright: 2026 MK300 Studio contributors
License: GPL-3+

License: GPL-3+
 Este programa es software libre: puede redistribuirlo y/o modificarlo bajo los
 términos de la Licencia Pública General de GNU publicada por la Free Software
 Foundation, ya sea la versión 3 de la Licencia o (a su elección) cualquier
 versión posterior.
 .
 En Debian, el texto completo está en /usr/share/common-licenses/GPL-3.
C

find "$ROOT" -type d -exec chmod 755 {} +
find "$ROOT" -type f -exec chmod 644 {} +
chmod 755 "$ROOT/usr/bin/$PKG"

cat > "$ROOT/DEBIAN/postinst" <<'C'
#!/bin/sh
set -e
python3 -m compileall -q /usr/lib/mk300-studio >/dev/null 2>&1 || true
exit 0
C
cat > "$ROOT/DEBIAN/postrm" <<'C'
#!/bin/sh
set -e
if [ "$1" = remove ] || [ "$1" = purge ]; then
    rm -rf /usr/lib/mk300-studio
fi
exit 0
C
chmod 755 "$ROOT/DEBIAN/postinst" "$ROOT/DEBIAN/postrm"

SIZE=$(du -sk "$ROOT" | cut -f1)
cat > "$ROOT/DEBIAN/control" <<C
Package: $PKG
Version: $VER
Section: sound
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-pyqt5, alsa-utils
Installed-Size: $SIZE
Maintainer: MK300 Studio contributors <noreply@users.noreply.github.com>
Description: Configurador no oficial de la pedalera MK300 para Linux
 Lee y edita los presets de la pedalera MK300 por USB-MIDI, con sincronización
 en vivo entre la pedalera y la aplicación, ajustes globales (EQ, Looper,
 Drum) y guardado de presets en la pedalera.
 .
 Proyecto no oficial y sin relación con el fabricante.
C

mkdir -p dist
dpkg-deb --build --root-owner-group "$ROOT" "dist/${PKG}_${VER}_all.deb" >/dev/null
echo "dist/${PKG}_${VER}_all.deb"
