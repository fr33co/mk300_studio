"""Componentes visuales de la pantalla principal (perilla, barra, interruptor, cadena).

Aspecto propio, de línea similar a la app oficial: perillas con arco de 270°, barras azules con -/+,
interruptor tipo píldora y botones de cadena con icono tintado por categoría.
Los colores salen del tema activo (theme.current).
"""
import math
import os

from PyQt5 import QtCore, QtGui, QtWidgets

from . import theme

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

# Color de cada categoría, tomado de los fotogramas de la app original.
CATEGORY_COLORS = {
    "WAH": "#ff2d6f", "FX": "#c026d3", "GATE": "#14b8a6", "DS": "#f97316", "AMP": "#10b981",
    "CAB": "#60a5fa", "EQ": "#22d3ee", "MOD": "#d946ef", "DLY": "#eab308", "REV": "#38bdf8",
    "VOL": "#84cc16",
}
ICON_FILES = {"WAH": "WAH", "FX": "FX", "GATE": "GATE", "DS": "DS", "AMP": "AMP", "CAB": "CAB",
              "EQ": "EQ", "MOD": "MOD", "DLY": "DLY", "REV": "REV", "VOL": "VOL"}


def col(key):
    return QtGui.QColor(theme.current.get(key, "#888888"))


_icon_cache = {}


def tinted_icon(name, color, size):
    """Carga assets/icon/<name>.svg y lo tiñe del color dado."""
    key = (name, color, size)
    if key in _icon_cache:
        return _icon_cache[key]
    src = QtGui.QPixmap(os.path.join(ASSETS, "icon", f"{name}.svg"))
    if src.isNull():
        return None
    dpr = 2
    src = src.scaled(size * dpr, size * dpr, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
    out = QtGui.QPixmap(src.size())
    out.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(out)
    p.drawPixmap(0, 0, src)
    p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
    p.fillRect(out.rect(), QtGui.QColor(color))
    p.end()
    out.setDevicePixelRatio(dpr)
    _icon_cache[key] = out
    return out


UI_SCALE = 1.0  # sube al agrandar la ventana; lo fija MainWindow.resizeEvent


class Knob(QtWidgets.QWidget):
    """Perilla con arco de 270° (empieza abajo a la izquierda, sentido horario)."""
    valueChanged = QtCore.pyqtSignal(int)

    def __init__(self, label, vmin=0, vmax=100, color="#10b981", fmt=None, log=False, parent=None):
        super().__init__(parent)
        self.label, self.vmin, self.vmax, self.color = label, vmin, vmax, color
        self.log = log  # escala logarítmica (frecuencias)
        self.fmt = fmt or str
        self._v = vmin
        self._drag = None
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(round(86 * UI_SCALE), round(112 * UI_SCALE))
        self.setCursor(QtCore.Qt.SizeVerCursor)

    def value(self):
        return self._v

    def setValue(self, v, emit=False):
        v = max(self.vmin, min(self.vmax, int(v)))
        if v != self._v:
            self._v = v
            self.update()
            if emit:
                self.valueChanged.emit(v)

    def _frac(self, v):
        if self.log:
            return (math.log(max(v, self.vmin)) - math.log(self.vmin)) / (math.log(self.vmax) - math.log(self.vmin))
        return (v - self.vmin) / max(1, self.vmax - self.vmin)

    def _from_frac(self, f):
        f = max(0.0, min(1.0, f))
        if self.log:
            return math.exp(math.log(self.vmin) + f * (math.log(self.vmax) - math.log(self.vmin)))
        return self.vmin + f * (self.vmax - self.vmin)

    def mousePressEvent(self, e):
        self._drag = (e.y(), self._frac(self._v))

    def mouseMoveEvent(self, e):
        if self._drag:
            self.setValue(round(self._from_frac(self._drag[1] + (self._drag[0] - e.y()) / 150.0)), emit=True)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def wheelEvent(self, e):
        up = e.angleDelta().y() > 0
        if self.log:
            self.setValue(max(self._v + (1 if up else -1), round(self._v * (1.03 if up else 0.97))) if up
                          else min(self._v - 1, round(self._v * 0.97)), emit=True)
        else:
            self.setValue(self._v + (1 if up else -1), emit=True)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        sc = self.width() / 86
        p.scale(sc, sc)
        d = 56
        r = QtCore.QRectF((86 - d) / 2, 8, d, d)
        pen = QtGui.QPen(col("kElevated"), 4, cap=QtCore.Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(r, int(-135 * 16), int(-270 * 16))
        frac = self._frac(self._v)
        p.setPen(QtGui.QPen(QtGui.QColor(self.color), 4, cap=QtCore.Qt.RoundCap))
        if frac > 0:
            p.drawArc(r, int(-135 * 16), int(-270 * frac * 16))
        else:  # punto inicial como en la app original
            a = math.radians(225)
            p.setBrush(QtGui.QColor(self.color))
            p.drawEllipse(QtCore.QPointF(r.center().x() + d / 2 * math.cos(a),
                                         r.center().y() - d / 2 * math.sin(a)), 2, 2)
        p.setPen(col("kTextPrimary"))
        f = p.font()
        f.setPointSizeF(10)
        p.setFont(f)
        p.drawText(r, QtCore.Qt.AlignCenter, self.fmt(self._v))
        p.setPen(col("kTextSecondary"))
        f.setPointSizeF(9.5)
        p.setFont(f)
        p.drawText(QtCore.QRectF(0, 72, 86, 34), QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop,
                   self.label)


class ParamBar(QtWidgets.QWidget):
    """Barra horizontal con fill, etiqueta, valor y botones −/+ (Preset Vol, Pan, BPM)."""
    valueChanged = QtCore.pyqtSignal(int)

    def __init__(self, label, vmin, vmax, fmt=None, parent=None):
        super().__init__(parent)
        self.label, self.vmin, self.vmax = label, vmin, vmax
        self.fmt = fmt or str
        self._v = vmin
        self.setStyleSheet("background: transparent;")
        self.setFixedHeight(30)
        self.setCursor(QtCore.Qt.PointingHandCursor)

    def value(self):
        return self._v

    def setValue(self, v, emit=False):
        v = max(self.vmin, min(self.vmax, int(v)))
        if v != self._v:
            self._v = v
            self.update()
            if emit:
                self.valueChanged.emit(v)

    def _track(self):
        return QtCore.QRectF(28, 0, self.width() - 56 - self.right_margin(), self.height())

    def right_margin(self):
        return 0

    def _set_from_x(self, x):
        t = self._track()
        self.setValue(self.vmin + (x - t.left()) / max(1, t.width()) * (self.vmax - self.vmin) + 0.5, emit=True)

    def mousePressEvent(self, e):
        if e.x() < 28:
            self.setValue(self._v - 1, emit=True)
        elif e.x() > self.width() - 28 - self.right_margin() and e.x() < self.width() - self.right_margin():
            self.setValue(self._v + 1, emit=True)
        else:
            self._set_from_x(e.x())

    def mouseMoveEvent(self, e):
        if e.buttons() & QtCore.Qt.LeftButton and 28 <= e.x() <= self.width() - 28 - self.right_margin():
            self._set_from_x(e.x())

    def wheelEvent(self, e):
        self.setValue(self._v + (1 if e.angleDelta().y() > 0 else -1), emit=True)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w = self.width() - self.right_margin()
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(col("kCard"))
        p.drawRoundedRect(QtCore.QRectF(0, 0, w, self.height()), 6, 6)
        t = self._track()
        frac = (self._v - self.vmin) / max(1, self.vmax - self.vmin)
        p.setBrush(col("kAccent"))
        p.drawRoundedRect(QtCore.QRectF(t.left(), 0, t.width() * frac, t.height()), 5, 5)
        f = p.font()
        f.setPointSizeF(9.5)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QtGui.QColor("#ffffff"))
        p.drawText(t.adjusted(8, 0, 0, 0), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, self.label)
        f.setBold(False)
        p.setFont(f)
        p.setPen(col("kTextPrimary"))
        p.drawText(t.adjusted(0, 0, -6, 0), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight, self.fmt(self._v))
        p.setPen(col("kAccent"))
        f.setPointSizeF(13)
        p.setFont(f)
        p.drawText(QtCore.QRectF(0, 0, 28, self.height()), QtCore.Qt.AlignCenter, "−")
        p.drawText(QtCore.QRectF(w - 28, 0, 28, self.height()), QtCore.Qt.AlignCenter, "+")


class BpmBar(ParamBar):
    """Barra de BPM: deja sitio a la derecha para el botón TAP."""
    def right_margin(self):
        return 76


class Toggle(QtWidgets.QWidget):
    toggled = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._on = False
        self.color = "#10b981"
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(50, 28)
        self.setCursor(QtCore.Qt.PointingHandCursor)

    def isChecked(self):
        return self._on

    def setChecked(self, v, emit=False):
        if v != self._on:
            self._on = bool(v)
            self.update()
            if emit:
                self.toggled.emit(self._on)

    def mousePressEvent(self, e):
        self.setChecked(not self._on, emit=True)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(self.color) if self._on else col("kElevated"))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 13, 13)
        p.setBrush(QtGui.QColor("#ffffff") if self._on else col("kTextMuted"))
        x = self.width() - 25 if self._on else 3
        p.drawEllipse(QtCore.QRectF(x, 3, 22, 22))


class ChainButton(QtWidgets.QWidget):
    """Icono de un slot de la cadena: gris si está apagado, del color de su categoría si activo."""
    clicked = QtCore.pyqtSignal(int)

    def __init__(self, slot, category, parent=None):
        super().__init__(parent)
        self.slot, self.category = slot, category
        self.enabled_fx = False
        self.selected = False
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(round(76 * UI_SCALE), round(96 * UI_SCALE))
        self.setCursor(QtCore.Qt.PointingHandCursor)

    def set_state(self, enabled, selected):
        self.enabled_fx, self.selected = enabled, selected
        self.update()

    def mousePressEvent(self, e):
        self._press = e.pos()
        self.clicked.emit(self.slot)

    def mouseMoveEvent(self, e):
        if not (e.buttons() & QtCore.Qt.LeftButton) or \
                (e.pos() - self._press).manhattanLength() < QtWidgets.QApplication.startDragDistance():
            return
        drag = QtGui.QDrag(self)
        mime = QtCore.QMimeData()
        mime.setText(str(self.slot))
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.setHotSpot(e.pos())
        drag.exec_(QtCore.Qt.MoveAction)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        sc = self.width() / 76
        p.scale(sc, sc)
        color = CATEGORY_COLORS[self.category]
        box = QtCore.QRectF(6, 4, 64, 64)
        p.setPen(QtGui.QPen(QtGui.QColor(color), 1.5) if self.selected else QtCore.Qt.NoPen)
        bg = QtGui.QColor(color)
        bg.setAlpha(46 if self.enabled_fx else 0)
        p.setBrush(bg if self.enabled_fx else col("kCard"))
        p.drawRoundedRect(box, 12, 12)
        ic = tinted_icon(ICON_FILES[self.category], color if self.enabled_fx else theme.current.get("kTextMuted", "#666"), 30)
        if ic:
            s = ic.size() / ic.devicePixelRatio()
            p.drawPixmap(int(box.center().x() - s.width() / 2), int(box.center().y() - s.height() / 2), ic)
        f = p.font()
        f.setPointSizeF(9)
        f.setBold(self.enabled_fx or self.selected)
        p.setFont(f)
        p.setPen(QtGui.QColor(color) if (self.enabled_fx or self.selected) else col("kTextMuted"))
        p.drawText(QtCore.QRectF(0, 72, 76, 20), QtCore.Qt.AlignCenter, self.category)


class ChainRow(QtWidgets.QWidget):
    """Fila de ChainButton que acepta soltar un icono para reordenar la cadena."""
    moved = QtCore.pyqtSignal(int, int)  # slot, posición de destino

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setStyleSheet("background: transparent;")

    def dragEnterEvent(self, e):
        if e.mimeData().hasText():
            e.acceptProposedAction()

    def dropEvent(self, e):
        try:
            slot = int(e.mimeData().text())
        except ValueError:
            return
        x = e.pos().x()
        buttons = sorted((b for b in self.findChildren(ChainButton) if b.isVisible()), key=lambda b: b.x())
        target = sum(1 for b in buttons if b.slot != slot and b.x() + b.width() / 2 < x)
        e.acceptProposedAction()
        self.moved.emit(slot, target)


class SideButton(QtWidgets.QAbstractButton):
    """Elemento del menú lateral (Param, Sounds, Import, Community)."""
    def __init__(self, text, glyph, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.glyph = glyph
        self.setCheckable(True)
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(86, 78)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        if self.isChecked():
            p.setPen(QtCore.Qt.NoPen)
            c = col("kAccent")
            c.setAlpha(36)
            p.setBrush(c)
            p.drawRoundedRect(QtCore.QRectF(6, 4, self.width() - 12, self.height() - 8), 10, 10)
        color = col("kAccent") if self.isChecked() else (col("kTextSecondary") if self.isEnabled() else col("kTextMuted"))
        p.setPen(color)
        f = p.font()
        f.setPointSizeF(17)
        p.setFont(f)
        p.drawText(QtCore.QRectF(0, 12, self.width(), 30), QtCore.Qt.AlignCenter, self.glyph)
        f.setPointSizeF(9)
        p.setFont(f)
        p.drawText(QtCore.QRectF(0, 46, self.width(), 20), QtCore.Qt.AlignCenter, self.text())


class OverlayCombo(QtWidgets.QComboBox):
    """Combo cuya lista se abre DENTRO de la ventana: un clic la abre y se queda abierta.

    El desplegable nativo de Qt (ventana emergente) en Wayland se cierra al soltar el botón del ratón,
    obligando a mantenerlo pulsado. Aquí la lista es un widget hijo de la ventana: se elige con un clic,
    con las flechas + Enter, y se cierra con Esc o haciendo clic fuera.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._list = None

    def _ensure_list(self):
        if self._list is None:
            lst = QtWidgets.QListWidget(self.window())
            lst.setObjectName("overlaylist")
            lst.setFrameShape(QtWidgets.QFrame.NoFrame)
            lst.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
            lst.itemClicked.connect(self._picked)
            lst.itemActivated.connect(self._picked)
            lst.hide()
            self._list = lst
        return self._list

    def showPopup(self):
        lst = self._ensure_list()
        if lst.isVisible():
            return self.hidePopup()
        lst.clear()
        for i in range(self.count()):
            it = QtWidgets.QListWidgetItem(self.itemIcon(i), self.itemText(i))
            lst.addItem(it)
        win = self.window()
        top_left = self.mapTo(win, QtCore.QPoint(0, self.height() + 2))
        h = max(120, min(460, win.height() - top_left.y() - 30))
        lst.setGeometry(top_left.x(), top_left.y(), self.width(), h)
        t = theme.current
        lst.setStyleSheet(
            f"QListWidget#overlaylist {{ background: {t.get('kCard', '#222')}; border: 1px solid {t.get('kAccent', '#3b9eff')};"
            f" border-radius: 6px; outline: none; }}"
            f"QListWidget#overlaylist::item {{ padding: 6px 8px; }}"
            f"QListWidget#overlaylist::item:hover {{ background: {t.get('kElevated', '#333')}; }}"
            f"QListWidget#overlaylist::item:selected {{ background: {t.get('kAccentDim', '#333')}; color: {t.get('kAccent', '#fff')}; }}")
        lst.setCurrentRow(self.currentIndex())
        lst.scrollToItem(lst.currentItem(), QtWidgets.QAbstractItemView.PositionAtCenter)
        lst.raise_()
        lst.show()
        lst.setFocus()
        QtWidgets.QApplication.instance().installEventFilter(self)

    def hidePopup(self):
        if self._list is not None and self._list.isVisible():
            self._list.hide()
            QtWidgets.QApplication.instance().removeEventFilter(self)

    def _picked(self, item):
        row = self._list.row(item)
        self.hidePopup()
        self.setCurrentIndex(row)

    def eventFilter(self, obj, e):
        if self._list is not None and self._list.isVisible():
            if e.type() == QtCore.QEvent.MouseButtonPress:
                w = QtWidgets.QApplication.widgetAt(e.globalPos())
                inside = w is not None and (w is self._list or self._list.isAncestorOf(w))
                if not inside and w is not self:
                    self.hidePopup()
            elif e.type() == QtCore.QEvent.KeyPress and e.key() == QtCore.Qt.Key_Escape:
                self.hidePopup()
                return True
        return super().eventFilter(obj, e)
