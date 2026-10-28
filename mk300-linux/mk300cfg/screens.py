"""Pantallas Glob, EQ, Looper y Drum de la app (disposición de la app oficial).

Editan un GlobalSettings en memoria; no se comunican con la pedalera.
"""
import cmath
import json
import math
import time

from PyQt5 import QtCore, QtGui, QtWidgets

from . import theme
from . import widgets as W

NOTE = "Ajustes globales: con la pedalera sincronizada se leen y se envían a ella; sin conexión se guardan junto al banco (.glob.json)."
BAND_COLORS = ["#d946ef", "#3b9eff", "#4ade80", "#facc15"]
FS = 48000.0


class SectionHeader(QtWidgets.QWidget):
    """Título de sección: barra de acento a la izquierda, texto en mayúsculas y línea."""

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text.upper()
        self.setFixedHeight(30)
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(W.col("kAccent"))
        p.drawRect(0, 6, 3, 18)
        f = p.font()
        f.setPointSizeF(9)
        f.setBold(True)
        f.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 1.2)
        p.setFont(f)
        p.setPen(W.col("kTextSecondary"))
        p.drawText(QtCore.QRectF(10, 0, 400, self.height()), QtCore.Qt.AlignVCenter, self.text)
        p.setPen(QtGui.QPen(W.col("kDivider"), 1))
        y = self.height() - 2
        p.drawLine(0, y, min(self.width(), 590), y)


class Segmented(QtWidgets.QWidget):
    """Fila de botones excluyentes (OFF/ON, A/B, Nor/Dry/NoCAB…)."""
    valueChanged = QtCore.pyqtSignal(int)

    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.group = QtWidgets.QButtonGroup(self)
        self.group.setExclusive(True)
        for i, text in enumerate(options):
            b = QtWidgets.QPushButton(text)
            b.setObjectName("seg")
            b.setCheckable(True)
            self.group.addButton(b, i)
            lay.addWidget(b)
        lay.addStretch(1)
        self.group.buttonClicked[int].connect(self.valueChanged)

    def setValue(self, v):
        b = self.group.button(v)
        if b:
            b.setChecked(True)


def row(label, widget):
    w = QtWidgets.QWidget()
    w.setStyleSheet("background: transparent;")
    lay = QtWidgets.QHBoxLayout(w)
    lay.setContentsMargins(0, 2, 0, 2)
    lab = QtWidgets.QLabel(label)
    f = lab.font()
    f.setBold(True)
    lab.setFont(f)
    lab.setFixedWidth(130)
    lay.addWidget(lab)
    if isinstance(widget, W.Toggle):  # los interruptores van pegados a la derecha, como en la original
        lay.addStretch(1)
        lay.addWidget(widget)
    else:
        lay.addWidget(widget, 1)
    return w


def note_label():
    lab = QtWidgets.QLabel(NOTE)
    lab.setWordWrap(True)
    lab.setStyleSheet(f"color: {theme.current.get('kTextMuted', '#666')}; background: transparent;")
    return lab


class Page(QtWidgets.QWidget):
    """Base: contenido con márgenes y nota al pie."""

    def __init__(self, settings, on_change, parent=None):
        super().__init__(parent)
        self.s, self.on_change = settings, on_change
        self._loading = False
        self.lay = QtWidgets.QVBoxLayout(self)
        self.lay.setContentsMargins(4, 4, 4, 4)
        self.lay.setSpacing(8)

    def changed(self, attr, v, index=None):
        if self._loading:
            return
        if index is None:
            setattr(self.s, attr, v)
        else:
            getattr(self.s, attr)[index] = v
        self.on_change()

    def set_settings(self, s):
        self.s = s
        self.refresh()

    def refresh(self):
        pass


class GlobPage(Page):
    def __init__(self, settings, on_change, parent=None):
        super().__init__(settings, on_change, parent)
        L = self.lay
        L.addWidget(SectionHeader("Pedal-1"))
        self.conv = Segmented(["OFF", "ON"])
        self.sync = Segmented(["OFF", "ON"])
        self.state0 = Segmented(["A", "B"])
        L.addWidget(row("A/B Convert", self.conv))
        L.addWidget(row("Sync", self.sync))
        L.addWidget(row("Pedal State", self.state0))
        L.addWidget(SectionHeader("Pedal-2"))
        self.state1 = Segmented(["A", "B"])
        L.addWidget(row("Pedal State", self.state1))
        L.addWidget(SectionHeader("Tail"))
        self.tail_delay = Segmented(["OFF", "Auto", "Force"])
        self.tail_reverb = Segmented(["OFF", "Auto", "Force"])
        L.addWidget(row("Delay", self.tail_delay))
        L.addWidget(row("Reverb", self.tail_reverb))
        L.addWidget(SectionHeader("Other"))
        self.rch = Segmented(["Nor", "Dry", "NoCAB"])
        self.usb = Segmented(["NOR", "NO", "RESAMPLE", "DRY"])
        L.addWidget(row("RCH", self.rch))
        L.addWidget(row("USB Audio", self.usb))
        self.bt = W.ParamBar("BT&USB VOL", 0, 100)
        self.rec = W.ParamBar("USB REC VOL", 0, 100)
        L.addWidget(self.bt)
        L.addWidget(self.rec)
        self.toe0 = Segmented(["None", "Resume", "Disable"])
        self.toe1 = Segmented(["None", "Resume", "Disable"])
        L.addWidget(row("P1 Toe Switch", self.toe0))
        L.addWidget(row("P2 Toe Switch", self.toe1))
        L.addStretch(1)
        L.addWidget(note_label())
        self.conv.valueChanged.connect(lambda v: self.changed("pedal_conv0", v))
        self.sync.valueChanged.connect(lambda v: self.changed("pedal_sync0", v))
        self.state0.valueChanged.connect(lambda v: self.changed("pedal_state", v, 0))
        self.state1.valueChanged.connect(lambda v: self.changed("pedal_state", v, 1))
        self.tail_delay.valueChanged.connect(lambda v: self.changed("tail_delay", v))
        self.tail_reverb.valueChanged.connect(lambda v: self.changed("tail_reverb", v))
        self.rch.valueChanged.connect(lambda v: self.changed("right_output_mode", v))
        self.usb.valueChanged.connect(lambda v: self.changed("usb_rec_type", v))
        self.bt.valueChanged.connect(lambda v: self.changed("music_vol", v))
        self.rec.valueChanged.connect(lambda v: self.changed("usb_rec_vol", v))
        self.toe0.valueChanged.connect(lambda v: self.changed("pedal_toe_switch", v, 0))
        self.toe1.valueChanged.connect(lambda v: self.changed("pedal_toe_switch", v, 1))
        self.refresh()

    def refresh(self):
        s = self.s
        self._loading = True
        self.conv.setValue(s.pedal_conv0)
        self.sync.setValue(s.pedal_sync0)
        self.state0.setValue(s.pedal_state[0])
        self.state1.setValue(s.pedal_state[1])
        self.tail_delay.setValue(s.tail_delay)
        self.tail_reverb.setValue(s.tail_reverb)
        self.rch.setValue(s.right_output_mode)
        self.usb.setValue(s.usb_rec_type)
        self.bt.setValue(s.music_vol)
        self.rec.setValue(s.usb_rec_vol)
        self.toe0.setValue(s.pedal_toe_switch[0])
        self.toe1.setValue(s.pedal_toe_switch[1])
        self._loading = False


def _biquad_db(b, a, f):
    w = 2 * math.pi * f / FS
    z1 = cmath.exp(-1j * w)
    z2 = z1 * z1
    h = (b[0] + b[1] * z1 + b[2] * z2) / (a[0] + a[1] * z1 + a[2] * z2)
    return 20 * math.log10(max(abs(h), 1e-6))


def _peak(f0, q, gain_db):
    A = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * f0 / FS
    al = math.sin(w0) / (2 * max(q, 0.1))
    c = math.cos(w0)
    return [1 + al * A, -2 * c, 1 - al * A], [1 + al / A, -2 * c, 1 - al / A]


def _pass(f0, high):
    w0 = 2 * math.pi * f0 / FS
    al = math.sin(w0) / (2 * 0.7071)
    c = math.cos(w0)
    if high:
        b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]
    else:
        b = [(1 - c) / 2, 1 - c, (1 - c) / 2]
    return b, [1 + al, -2 * c, 1 - al]


def eq_response_db(s, f):
    """Respuesta del ecualizador (dB) a la frecuencia f: pasa-altos LC, pasa-bajos HC y 4 picos."""
    if not s.eq_enable:
        return 0.0
    tot = 0.0
    if s.eq_lc >= 20:  # por debajo de 20 el pasa-altos está apagado
        tot += _biquad_db(*_pass(s.eq_lc, True), f)
    if s.eq_hc <= 20000:  # por encima de 20000 el pasa-bajos está apagado
        tot += _biquad_db(*_pass(s.eq_hc, False), f)
    for i in range(4):
        tot += _biquad_db(*_peak(s.eq_peak_freq[i], s.eq_quality_factor[i] / 10, s.eq_peak_gain[i]), f)
    return tot


class EqGraph(QtWidgets.QWidget):
    """Curva de respuesta con los 4 puntos de banda (se arrastran para cambiar frecuencia y ganancia)."""
    bandMoved = QtCore.pyqtSignal(int, int, int)  # banda, frecuencia, ganancia

    FMIN, FMAX, DB = 20.0, 20000.0, 20.0

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.s = settings
        self.drag = None
        self.setMinimumHeight(170)
        self.setStyleSheet("background: transparent;")

    def _x(self, f):
        return 30 + (math.log(f / self.FMIN) / math.log(self.FMAX / self.FMIN)) * (self.width() - 40)

    def _y(self, db):
        db = max(-self.DB, min(self.DB, db))
        return 8 + (1 - (db + self.DB) / (2 * self.DB)) * (self.height() - 28)

    def _from_xy(self, x, y):
        f = self.FMIN * math.exp(max(0.0, min(1.0, (x - 30) / (self.width() - 40))) * math.log(self.FMAX / self.FMIN))
        db = (1 - (y - 8) / (self.height() - 28)) * 2 * self.DB - self.DB
        return int(round(f)), int(round(max(-18, min(18, db))))

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        left, right = 30, self.width() - 10
        grid = QtGui.QPen(W.col("kDivider"), 1)
        f = p.font()
        f.setPointSizeF(7)
        p.setFont(f)
        for db in (-20, -10, 0, 10, 20):
            y = self._y(db)
            p.setPen(grid)
            p.drawLine(int(left), int(y), int(right), int(y))
            p.setPen(W.col("kTextMuted"))
            p.drawText(QtCore.QRectF(0, y - 8, 26, 16), QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, f"{db:+d}" if db else "0")
        for fr, lab in ((50, "50"), (100, "100"), (200, "200"), (500, "500"), (1000, "1k"), (2000, "2k"),
                        (5000, "5k"), (10000, "10k"), (20000, "20k")):
            x = self._x(fr)
            p.setPen(W.col("kTextMuted"))
            p.drawText(QtCore.QRectF(x - 20, self.height() - 16, 40, 14), QtCore.Qt.AlignCenter, lab)
        pts = [QtCore.QPointF(self._x(fr), self._y(eq_response_db(self.s, fr)))
               for fr in [self.FMIN * (self.FMAX / self.FMIN) ** (i / 240) for i in range(241)]]
        path = QtGui.QPainterPath(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)
        fill = QtGui.QPainterPath(path)
        fill.lineTo(pts[-1].x(), self._y(0))
        fill.lineTo(pts[0].x(), self._y(0))
        c = W.col("kAccent")
        c.setAlpha(30)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(c)
        p.drawPath(fill)
        p.setBrush(QtCore.Qt.NoBrush)
        p.setPen(QtGui.QPen(W.col("kAccent"), 1.6))
        p.drawPath(path)
        for i in range(4):
            x, y = self._x(self.s.eq_peak_freq[i]), self._y(self.s.eq_peak_gain[i])
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QColor(BAND_COLORS[i]))
            p.drawEllipse(QtCore.QPointF(x, y), 5, 5)
            p.setPen(QtGui.QColor(BAND_COLORS[i]))
            p.drawText(QtCore.QRectF(x - 8, y - 20, 16, 12), QtCore.Qt.AlignCenter, str(i + 1))

    def mousePressEvent(self, e):
        best = min(range(4), key=lambda i: (self._x(self.s.eq_peak_freq[i]) - e.x()) ** 2 +
                   (self._y(self.s.eq_peak_gain[i]) - e.y()) ** 2)
        d2 = (self._x(self.s.eq_peak_freq[best]) - e.x()) ** 2 + (self._y(self.s.eq_peak_gain[best]) - e.y()) ** 2
        self.drag = best if d2 < 18 ** 2 else None

    def mouseMoveEvent(self, e):
        if self.drag is not None:
            f, g = self._from_xy(e.x(), e.y())
            self.bandMoved.emit(self.drag, max(20, min(20000, f)), g)

    def mouseReleaseEvent(self, e):
        self.drag = None


def fmt_freq(v):
    return f"{v / 1000:.1f}k" if v >= 1000 else str(v)


def fmt_q(v):
    return f"{v / 10:.1f}"


def fmt_db(v):
    return "0dB" if v == 0 else f"{v:+d}dB"


class EqPage(Page):
    def __init__(self, settings, on_change, parent=None):
        super().__init__(settings, on_change, parent)
        L = self.lay
        top = QtWidgets.QHBoxLayout()
        for text, slot in (("⭱  Share EQ", self.share), ("⭳  Import EQ", self.import_eq)):
            b = QtWidgets.QPushButton(text)
            b.setObjectName("tool")
            b.clicked.connect(slot)
            top.addWidget(b)
        top.addStretch(1)
        L.addLayout(top)

        head = QtWidgets.QHBoxLayout()
        head.addStretch(1)
        self.power = QtWidgets.QPushButton("⏻")
        self.power.setObjectName("power")
        self.power.setCheckable(True)
        self.power.setFixedSize(60, 60)
        self.lc = W.Knob("LC", 19, 200, "#3b9eff", fmt=lambda v: "OFF" if v < 20 else str(v), log=True)
        self.hc = W.Knob("HC", 4000, 20500, "#3b9eff", fmt=lambda v: "OFF" if v > 20000 else f"{v / 1000:.1f}K", log=True)
        for label, widget in (("EQ", self.power), (None, self.lc), (None, self.hc)):
            col = QtWidgets.QVBoxLayout()
            col.addWidget(widget, 0, QtCore.Qt.AlignHCenter)
            if label:
                lab = QtWidgets.QLabel(label)
                lab.setAlignment(QtCore.Qt.AlignHCenter)
                lab.setStyleSheet("background: transparent;")
                col.addWidget(lab)
                col.addStretch(1)
            head.addLayout(col)
        head.addStretch(1)
        L.addLayout(head)

        self.graph = EqGraph(self.s)
        self.graph.bandMoved.connect(self.band_moved)
        L.addWidget(self.graph, 1)

        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(0)
        self.knobs = {"freq": [], "q": [], "gain": []}
        for r, (key, name) in enumerate((("freq", "Freq"), ("q", "Q"), ("gain", "Gain"))):
            lab = QtWidgets.QLabel(name)
            lab.setStyleSheet(f"color: {theme.current.get('kTextSecondary', '#999')}; background: transparent;")
            grid.addWidget(lab, r + 1, 0)
        for i in range(4):
            hdr = QtWidgets.QLabel(f"P{i + 1}")
            hdr.setAlignment(QtCore.Qt.AlignHCenter)
            hdr.setStyleSheet(f"color: {BAND_COLORS[i]}; background: transparent; font-weight: bold;")
            grid.addWidget(hdr, 0, i + 1)
            specs = (("freq", 20, 20000, fmt_freq, True), ("q", 1, 160, fmt_q, False), ("gain", -18, 18, fmt_db, False))
            for r, (key, lo, hi, fmt, log) in enumerate(specs):
                k = W.Knob("", lo, hi, BAND_COLORS[i], fmt=fmt, log=log)
                k.setFixedSize(86, 78)
                k.valueChanged.connect(lambda v, key=key, i=i: self.knob_changed(key, i, v))
                grid.addWidget(k, r + 1, i + 1, QtCore.Qt.AlignHCenter)
                self.knobs[key].append(k)
        for c in range(1, 5):
            grid.setColumnStretch(c, 1)
        grid.setColumnMinimumWidth(0, 50)
        L.addLayout(grid)
        L.addWidget(note_label())
        self.power.toggled.connect(lambda v: (self.changed("eq_enable", int(v)), self.graph.update()))
        self.lc.valueChanged.connect(lambda v: (self.changed("eq_lc", v), self.graph.update()))
        self.hc.valueChanged.connect(lambda v: (self.changed("eq_hc", v), self.graph.update()))
        self.refresh()

    def knob_changed(self, key, i, v):
        attr = {"freq": "eq_peak_freq", "q": "eq_quality_factor", "gain": "eq_peak_gain"}[key]
        self.changed(attr, v, i)
        self.graph.update()

    def band_moved(self, i, f, g):
        self.knobs["freq"][i].setValue(f, emit=True)
        self.knobs["gain"][i].setValue(g, emit=True)

    def refresh(self):
        s = self.s
        self.graph.s = s
        self._loading = True
        self.power.setChecked(bool(s.eq_enable))
        self.lc.setValue(s.eq_lc)
        self.hc.setValue(s.eq_hc)
        for i in range(4):
            self.knobs["freq"][i].setValue(s.eq_peak_freq[i])
            self.knobs["q"][i].setValue(s.eq_quality_factor[i])
            self.knobs["gain"][i].setValue(s.eq_peak_gain[i])
        self._loading = False
        self.graph.update()

    def share(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Compartir EQ", "eq.mkeq", "EQ (*.mkeq)")
        if path:
            d = {k: getattr(self.s, k) for k in ("eq_enable", "eq_lc", "eq_hc", "eq_peak_freq",
                                                  "eq_quality_factor", "eq_peak_gain")}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(d, f, indent=1)

    def import_eq(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Importar EQ", "", "EQ (*.mkeq);;Todos (*)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError) as e:
            QtWidgets.QMessageBox.critical(self, "EQ inválido", str(e))
            return
        for k in ("eq_enable", "eq_lc", "eq_hc", "eq_peak_freq", "eq_quality_factor", "eq_peak_gain"):
            if k in d and isinstance(d[k], type(getattr(self.s, k))):
                setattr(self.s, k, d[k])
        self.refresh()
        self.on_change()


class LooperPage(Page):
    def __init__(self, settings, on_change, parent=None):
        super().__init__(settings, on_change, parent)
        L = self.lay
        L.addWidget(SectionHeader("Looper"))
        self.rec = W.ParamBar("Rec Vol", 0, 100)
        self.play = W.ParamBar("Play Vol", 0, 100)
        self.auto = Segmented(["OFF", "ONCE", "HOLD"])
        self.gate = W.ParamBar("Auto Gate", 0, 100)
        self.pos = Segmented(["HEAD", "TAIL"])
        self.dsync = Segmented(["OFF", "ON-1", "ON-2"])
        L.addWidget(self.rec)
        L.addWidget(self.play)
        L.addWidget(row("Auto Rec", self.auto))
        L.addWidget(self.gate)
        L.addWidget(row("POS", self.pos))
        L.addWidget(row("Drum Sync", self.dsync))
        L.addStretch(1)
        L.addWidget(note_label())
        self.rec.valueChanged.connect(lambda v: self.changed("looper_rec_vol", v))
        self.play.valueChanged.connect(lambda v: self.changed("looper_play_vol", v))
        self.auto.valueChanged.connect(lambda v: self.changed("looper_auto_rec", v))
        self.gate.valueChanged.connect(lambda v: self.changed("looper_auto_rec_db", v))
        self.pos.valueChanged.connect(lambda v: self.changed("looper_position", v))
        self.dsync.valueChanged.connect(lambda v: self.changed("looper_drum_sync", v))
        self.refresh()

    def refresh(self):
        s = self.s
        self._loading = True
        self.rec.setValue(s.looper_rec_vol)
        self.play.setValue(s.looper_play_vol)
        self.auto.setValue(s.looper_auto_rec)
        self.gate.setValue(s.looper_auto_rec_db)
        self.pos.setValue(s.looper_position)
        self.dsync.setValue(s.looper_drum_sync)
        self._loading = False


class DrumPage(Page):
    def __init__(self, settings, on_change, parent=None):
        super().__init__(settings, on_change, parent)
        L = self.lay
        play = QtWidgets.QPushButton("▶  Play Drum")
        play.setObjectName("playdrum")
        play.setMinimumHeight(44)
        play.setEnabled(False)
        play.setToolTip("Requiere conexión con la pedalera")
        L.addWidget(play)
        L.addWidget(SectionHeader("Drum Machine"))
        self.vol = W.ParamBar("VOL", 0, 100)
        self.bpm = W.BpmBar("Drum BPM", 40, 240)
        self.taps = []
        L.addWidget(self.vol)
        brow = QtWidgets.QHBoxLayout()
        brow.setSpacing(0)
        brow.addWidget(self.bpm, 1)
        tap = QtWidgets.QPushButton("TAP")
        tap.setObjectName("tool")
        tap.setFixedSize(70, 30)
        tap.clicked.connect(self.tap_tempo)
        brow.addWidget(tap)
        L.addLayout(brow)
        self.sync = W.Toggle()
        self.sync.color = theme.current.get("kAccent", "#3b9eff")
        L.addWidget(row("Bpm Sync", self.sync))
        L.addStretch(1)
        L.addWidget(note_label())
        self.vol.valueChanged.connect(lambda v: self.changed("drum_vol", v))
        self.bpm.valueChanged.connect(lambda v: self.changed("drum_tempo", v))
        self.sync.toggled.connect(lambda v: self.changed("drum_sync", int(v)))
        self.refresh()

    def tap_tempo(self):
        now = time.time()
        self.taps = [t for t in self.taps if now - t < 2.5] + [now]
        if len(self.taps) >= 2:
            gaps = [b - a for a, b in zip(self.taps, self.taps[1:])]
            self.bpm.setValue(round(60 / (sum(gaps) / len(gaps))), emit=True)

    def refresh(self):
        s = self.s
        self._loading = True
        self.vol.setValue(s.drum_vol)
        self.bpm.setValue(s.drum_tempo)
        self.sync.color = theme.current.get("kAccent", "#3b9eff")
        self.sync.setChecked(bool(s.drum_sync))
        self._loading = False
