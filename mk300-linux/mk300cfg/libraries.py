"""Páginas Import, AI Tone, Audio separation y Community del menú lateral (disposición de la app oficial).

Import (DS, AMP, CAB y Preset) y Audio separation mantienen una lista local de archivos (se recuerda entre sesiones). Las
acciones que necesitan la pedalera (Save to Device, Audition, Use) están desactivadas.
"""
import os

from PyQt5 import QtCore, QtGui, QtWidgets

from . import theme
from . import widgets as W

NEEDS_DEVICE = "Requiere conexión con la pedalera"


def muted(text):
    lab = QtWidgets.QLabel(text)
    lab.setWordWrap(True)
    lab.setStyleSheet(f"color: {theme.current.get('kTextMuted', '#666')}; background: transparent;")
    return lab


class RangeBar(QtWidgets.QWidget):
    """Barra con dos tiradores (Gain 30–60 en la app original)."""
    changed = QtCore.pyqtSignal(int, int)

    def __init__(self, label, lo=0, hi=100, parent=None):
        super().__init__(parent)
        self.label, self.lo_lim, self.hi_lim = label, lo, hi
        self.lo, self.hi = 30, 60
        self.drag = None
        self.setFixedHeight(30)
        self.setStyleSheet("background: transparent;")

    def _x(self, v):
        return 70 + (v - self.lo_lim) / (self.hi_lim - self.lo_lim) * (self.width() - 140)

    def _v(self, x):
        f = max(0.0, min(1.0, (x - 70) / max(1, self.width() - 140)))
        return int(round(self.lo_lim + f * (self.hi_lim - self.lo_lim)))

    def mousePressEvent(self, e):
        self.drag = "lo" if abs(e.x() - self._x(self.lo)) <= abs(e.x() - self._x(self.hi)) else "hi"
        self.mouseMoveEvent(e)

    def mouseMoveEvent(self, e):
        if self.drag is None:
            return
        v = self._v(e.x())
        if self.drag == "lo":
            self.lo = min(v, self.hi - 1)
        else:
            self.hi = max(v, self.lo + 1)
        self.update()
        self.changed.emit(self.lo, self.hi)

    def mouseReleaseEvent(self, e):
        self.drag = None

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(W.col("kCard"))
        p.drawRoundedRect(QtCore.QRectF(0, 0, self.width(), self.height()), 6, 6)
        x0, x1 = self._x(self.lo), self._x(self.hi)
        c = W.col("kAccent")
        c.setAlpha(110)
        p.setBrush(c)
        p.drawRect(QtCore.QRectF(x0, 0, x1 - x0, self.height()))
        p.setBrush(W.col("kAccent"))
        for x in (x0, x1):
            p.drawRoundedRect(QtCore.QRectF(x - 3, 2, 6, self.height() - 4), 2, 2)
        f = p.font()
        f.setPointSizeF(9)
        p.setFont(f)
        p.setPen(W.col("kTextSecondary"))
        p.drawText(QtCore.QRectF(10, 0, 60, self.height()), QtCore.Qt.AlignVCenter, self.label)
        p.setPen(W.col("kTextPrimary"))
        p.drawText(QtCore.QRectF(0, 0, self.width() - 10, self.height()),
                   QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight, f"{self.lo}–{self.hi}")


class FileList(QtWidgets.QWidget):
    """Buscador + botón Edit + lista de archivos con un botón de acción desactivado por fila."""
    changed = QtCore.pyqtSignal()

    def __init__(self, action_text, tag=None, action_tip=NEEDS_DEVICE, empty_text=None, parent=None):
        super().__init__(parent)
        self.action_text, self.tag, self.action_tip = action_text, tag, action_tip
        self.empty_text = empty_text or "Sin archivos. Usa el botón «Load … File to List» para añadir."
        self.paths, self.editing = [], False
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        top = QtWidgets.QHBoxLayout()
        self.search = QtWidgets.QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("🔍  Search")
        self.search.setMinimumHeight(32)
        self.search.textChanged.connect(self.rebuild)
        self.edit_btn = QtWidgets.QPushButton("✎  Edit")
        self.edit_btn.setObjectName("tool")
        self.edit_btn.setCheckable(True)
        self.edit_btn.toggled.connect(self.set_editing)
        top.addWidget(self.search, 1)
        top.addWidget(self.edit_btn)
        lay.addLayout(top)
        self.info = QtWidgets.QLabel()
        self.info.setStyleSheet(f"color: {theme.current.get('kAccent', '#3b9eff')}; background: {theme.current.get('kSurface', '#111')};"
                                " padding: 8px 12px; border-radius: 6px;")
        self.info.hide()
        lay.addWidget(self.info)
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.body = QtWidgets.QWidget()
        self.body.setStyleSheet("background: transparent;")
        self.rows = QtWidgets.QVBoxLayout(self.body)
        self.rows.setContentsMargins(0, 0, 0, 0)
        self.rows.setSpacing(2)
        self.scroll.setWidget(self.body)
        self.scroll.viewport().setStyleSheet("background: transparent;")
        lay.addWidget(self.scroll, 1)

    def set_info(self, text):
        self.info.setText("ⓘ  " + text)
        self.info.show()

    def set_paths(self, paths):
        self.paths = list(paths)
        self.rebuild()

    def add_paths(self, new):
        for p in new:
            if p not in self.paths:
                self.paths.append(p)
        self.rebuild()
        self.changed.emit()

    def set_editing(self, on):
        self.editing = on
        self.rebuild()

    def remove(self, path):
        self.paths.remove(path)
        self.rebuild()
        self.changed.emit()

    def rebuild(self):
        while self.rows.count():
            w = self.rows.takeAt(0).widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        q = self.search.text().strip().lower()
        shown = [p for p in self.paths if q in os.path.basename(p).lower()]
        for p in shown:
            self.rows.addWidget(self.make_row(p))
        if not shown:
            self.rows.addWidget(muted(self.empty_text))
        self.rows.addStretch(1)

    def make_row(self, path):
        w = QtWidgets.QWidget()
        w.setStyleSheet("background: transparent;")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(8, 6, 8, 6)
        icon = QtWidgets.QLabel("▤")
        icon.setStyleSheet(f"color: {theme.current.get('kAccent', '#3b9eff')}; background: transparent;")
        icon.setFixedWidth(24)
        h.addWidget(icon)
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(2)
        name = QtWidgets.QLabel(os.path.basename(path))
        name.setToolTip(path)
        name.setStyleSheet("background: transparent;")
        col.addWidget(name, 0, QtCore.Qt.AlignLeft)
        if self.tag:
            tag = QtWidgets.QLabel(self.tag)
            tag.setStyleSheet("color: #f59e0b; background: rgba(245,158,11,40); border-radius: 3px; padding: 0 6px; font-size: 8pt;")
            tag.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
            col.addWidget(tag, 0, QtCore.Qt.AlignLeft)
        h.addLayout(col, 1)
        if self.editing:
            rm = QtWidgets.QPushButton("✕")
            rm.setObjectName("tool")
            rm.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
            rm.setToolTip("Quitar de la lista (no borra el archivo)")
            rm.clicked.connect(lambda _, p=path: self.remove(p))
            h.addWidget(rm)
        act = QtWidgets.QPushButton(self.action_text)
        act.setObjectName("tool")
        act.setEnabled(False)
        act.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        act.setToolTip(self.action_tip)
        h.addWidget(act)
        return w


def store():
    return QtCore.QSettings("mk300cfg", "libraries")


class SoundsPanel(QtWidgets.QWidget):
    """Contenido de una pestaña de Sounds (DS, AMP o CAB)."""

    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(10)
        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)
        load = QtWidgets.QPushButton(f"▢  Load {kind} File to List")
        load.setObjectName("tool")
        load.clicked.connect(self.load_files)
        save = QtWidgets.QPushButton("▣  Save to Device")
        save.setObjectName("tool")
        save.setEnabled(False)
        save.setToolTip(NEEDS_DEVICE)
        row.addWidget(load)
        row.addWidget(save)
        row.addStretch(1)
        v.addLayout(row)
        self.level = W.ParamBar("CAB Level" if kind == "CAB" else "Level", 0, 100)
        self.level.setValue(50 if kind == "CAB" else 100)
        v.addWidget(self.level)
        if kind != "CAB":
            v.addWidget(RangeBar("Gain"))
        self.files = FileList("Audition")
        self.files.set_paths(store().value(f"sounds/{kind}", [], type=list))
        self.files.changed.connect(lambda: store().setValue(f"sounds/{kind}", self.files.paths))
        v.addWidget(self.files, 1)

    def load_files(self):
        flt = "Audio (*.wav)" if self.kind == "CAB" else f"{self.kind} (*.am3Data *.am4Data *.dsData);;Todos (*)"
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(self, f"Cargar archivos {self.kind}", "", flt)
        if paths:
            self.files.add_paths(paths)


class ImportPage(QtWidgets.QWidget):
    """Import: sub-pestañas DS, AMP, CAB y Preset, como la app oficial."""
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        bar = QtWidgets.QWidget()
        bar.setObjectName("panel")
        bl = QtWidgets.QHBoxLayout(bar)
        bl.setContentsMargins(4, 4, 4, 4)
        self.group = QtWidgets.QButtonGroup(self)
        self.stack = QtWidgets.QStackedWidget()
        for i, kind in enumerate(("DS", "AMP", "CAB", "Preset")):
            b = QtWidgets.QPushButton(kind)
            b.setObjectName("tab")
            b.setCheckable(True)
            b.setChecked(i == 0)
            self.group.addButton(b, i)
            bl.addWidget(b, 1)
            self.stack.addWidget(PresetPanel() if kind == "Preset" else SoundsPanel(kind))
        self.group.buttonClicked[int].connect(self.stack.setCurrentIndex)
        v.addWidget(bar)
        v.addWidget(self.stack, 1)


class PresetPanel(QtWidgets.QWidget):
    """Pestaña Preset de Import (snapshots)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(10)
        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)
        load = QtWidgets.QPushButton("▢  Load  File to List")
        load.setObjectName("tool")
        load.clicked.connect(self.load_files)
        row.addWidget(load)
        row.addStretch(1)
        v.addLayout(row)
        self.files = FileList("Use", tag="Snapshot")
        self.files.set_info("Currently supports importing snapshots to the device")
        self.files.set_paths(store().value("import/files", [], type=list))
        self.files.changed.connect(lambda: store().setValue("import/files", self.files.paths))
        v.addWidget(self.files, 1)

    def load_files(self):
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Cargar snapshots", "", "Snapshots (*.kz300);;Todos (*)")
        if paths:
            self.files.add_paths(paths)


class AiTonePage(QtWidgets.QWidget):
    """En la app oficial esta sección aún no existe: solo muestra "Coming Soon"."""
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QtWidgets.QVBoxLayout(self)
        v.addStretch(1)
        t = QtWidgets.QLabel("Coming Soon")
        t.setAlignment(QtCore.Qt.AlignCenter)
        f = t.font()
        f.setPointSizeF(18)
        f.setBold(True)
        t.setFont(f)
        v.addWidget(t)
        v.addStretch(1)


class AudioSeparationPage(QtWidgets.QWidget):
    """Biblioteca local de audio. La separación de pistas todavía no está disponible."""
    EXTS = "*.wav *.mp3 *.flac *.ogg *.mp4 *.mov"

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)
        top = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Audio Library")
        f = title.font()
        f.setPointSizeF(16)
        f.setBold(True)
        title.setFont(f)
        top.addWidget(title)
        top.addStretch(1)
        add = QtWidgets.QPushButton("+  Import")
        add.setObjectName("tool")
        add.clicked.connect(self.load_files)
        top.addWidget(add)
        v.addLayout(top)
        v.addWidget(muted("Importa un archivo de audio o vídeo (WAV / MP3 / FLAC / OGG / MP4 / MOV). La separación de "
                          "pistas todavía no está disponible en esta versión: por ahora solo se guarda la lista."))
        self.files = FileList("Separate", action_tip="Separación de pistas no disponible en esta versión",
                              empty_text="La biblioteca está vacía. Pulsa «+ Import» para añadir un archivo de audio o vídeo.")
        self.files.set_paths(store().value("audio/files", [], type=list))
        self.files.changed.connect(lambda: store().setValue("audio/files", self.files.paths))
        v.addWidget(self.files, 1)

    def load_files(self):
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Importar audio", "", f"Audio y vídeo ({self.EXTS});;Todos (*)")
        if paths:
            self.files.add_paths(paths)


class CommunityPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QtWidgets.QVBoxLayout(self)
        v.addStretch(1)
        t = QtWidgets.QLabel("Community")
        t.setAlignment(QtCore.Qt.AlignCenter)
        f = t.font()
        f.setPointSizeF(18)
        f.setBold(True)
        t.setFont(f)
        v.addWidget(t)
        m = muted("La comunidad (descarga y publicación de presets, amplis y cabinets) necesita conexión a internet "
                  "y una cuenta del servicio. No está disponible en esta versión.")
        m.setAlignment(QtCore.Qt.AlignCenter)
        m.setMaximumWidth(520)
        v.addWidget(m, 0, QtCore.Qt.AlignHCenter)
        v.addStretch(2)


class ConnectPage(QtWidgets.QWidget):
    """Pantalla inicial: busca la pedalera por USB y deja entrar a los presets con un clic."""
    connectRequested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QtWidgets.QVBoxLayout(self)
        v.addStretch(2)
        self.title = QtWidgets.QLabel("Buscando dispositivos…")
        self.title.setAlignment(QtCore.Qt.AlignCenter)
        f = self.title.font()
        f.setPointSizeF(20)
        f.setBold(True)
        self.title.setFont(f)
        v.addWidget(self.title)
        self.sub = muted("")
        self.sub.setAlignment(QtCore.Qt.AlignCenter)
        v.addWidget(self.sub)
        self.card = QtWidgets.QPushButton()
        self.card.setObjectName("devcard")
        self.card.setCursor(QtCore.Qt.PointingHandCursor)
        self.card.setFixedSize(520, 84)
        self.card.clicked.connect(self.connectRequested)
        v.addWidget(self.card, 0, QtCore.Qt.AlignHCenter)
        self.notice = muted("")
        self.notice.setAlignment(QtCore.Qt.AlignCenter)
        v.addWidget(self.notice)
        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)
        self.refresh_btn = QtWidgets.QPushButton("↻  Buscar de nuevo")
        self.refresh_btn.setObjectName("tool")
        self.refresh_btn.clicked.connect(self.scan)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        v.addLayout(row)
        v.addStretch(3)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.scan)
        self.scan()

    def set_notice(self, text):
        self.notice.setText(text)

    def scan(self):
        from . import device
        try:
            path = device.find_device()
        except device.DeviceError:
            path = None
        if path:
            self.title.setText("Dispositivo encontrado")
            self.sub.setText("Pulsa el dispositivo para sincronizar y entrar a tus presets.")
            self.card.setText(f"MK300\nUSB · {path}      ›")
        else:
            self.title.setText("Ningún dispositivo")
            self.sub.setText("Conecta la MK300 por USB. Se detectará sola.")
        self.card.setVisible(bool(path))

    def showEvent(self, e):
        super().showEvent(e)
        self.scan()
        self.timer.start(1500)

    def hideEvent(self, e):
        super().hideEvent(e)
        self.timer.stop()
