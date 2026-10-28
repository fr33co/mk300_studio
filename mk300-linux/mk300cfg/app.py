"""MK300 Studio: configurador de la pedalera MK300 para Linux (PyQt5). Edita bancos de presets como archivos.

Con la pedalera solo LEE (Archivo > Leer banco de la pedalera); nunca escribe en ella
hasta que se valide la escritura. La disposición sigue la de la app oficial.
"""
import json
import os
import sys
import time

from PyQt5 import QtCore, QtGui, QtWidgets

from . import theme as themes
from . import widgets as W
from . import screens
from . import libraries
from .settings import GlobalSettings
from . import device
from .bank import (Bank, NAME_LEN, PATCH_SIZE, PATCH_COUNT, PARAMS, SLOTS, OFF_COLOR, OFF_VOL, OFF_TEMPO, OFF_PAN,
                   OFF_CHAIN, OFF_EFFON, OFF_EFFUNIT, OFF_EFFPARA)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Orden de slots confirmado por buildMk300EffectParams de la app original.
SLOT_NAMES = ["WAH", "FX", "GATE", "DS", "AMP", "CAB", "EQ", "MOD", "DLY", "REV", "VOL"]
MODEL_SLOTS = {3: "DS", 4: "AMP", 5: "CAB"}  # slot -> lista de modelos en data/models.json
# Categorías con catálogo de tipos (índice de tipo = valor de effunit; parámetros en el
# orden del catálogo). Orden de tipos contrastado con las listas de la app original.
CATALOG_VALIDATED = {"WAH", "FX", "GATE", "EQ", "MOD", "DLY", "REV"}

AMP_DS_PARAMS = ["Gain", "Level", "Bass", "Middle", "Treble", "Reso", "Pres", "Bright"]
CAB_PARAMS = ["Level", "Low\nCut", "High\nCut"]
EQ6_PARAMS = ["100Hz", "200Hz", "400Hz", "800Hz", "1.6kHz", "3.2kHz"]

def color_icon(patch):
    """Cuadrito con el color del preset (bytes 0x14..0x16 del parche)."""
    r, g, b, _ = patch.color
    pm = QtGui.QPixmap(16, 16)
    pm.fill(QtGui.QColor(r, g, b))
    return QtGui.QIcon(pm)


TAB_NAMES = ["Effect", "Glob", "EQ", "Looper", "Drum"]


MAX_BACKUPS = 30  # copias de la pedalera que se conservan (se crea una en cada conexión)


def user_data_dir():
    """Carpeta de datos del usuario (escribible aunque la app esté instalada en /usr)."""
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "mk300-studio")


def load_json(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def fmt_tenths(v):
    return f"{v / 10:.1f}"


def fmt_khz(v):
    return f"{v / 10:.1f}K"


def fmt_seconds(v):
    return f"{v / 1000:.1f}"


def param_format(cat, name):
    """Formato de visualización de la app original para algunos parámetros."""
    if name == "Time" and cat == "DLY":
        return fmt_seconds
    if name == "Speed" and cat == "MOD":
        return fmt_tenths
    return None


WHAMMY_MODES = ("MBody", "Oct1", "Oct2")


def fmt_whammy_mode(v):
    return WHAMMY_MODES[v] if 0 <= v < len(WHAMMY_MODES) else str(v)


def fw_label(ident):
    """'MK300_075' -> 'v75' (sin la versión, cadena vacía)."""
    digits = ident.rpartition("_")[2]
    return f"v{int(digits)}" if digits.isdigit() else ""


def fmt_pan(v):
    return "C" if v == 0 else (f"R{v}" if v > 0 else f"L{-v}")


class HexDialog(QtWidgets.QDialog):
    """Editor de los 448 bytes de un parche (para campos aún sin mapear)."""

    def __init__(self, patch, on_change, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Bytes del parche — {patch.name}")
        self.resize(780, 560)
        self.patch, self.on_change, self._loading = patch, on_change, True
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel(f"{PATCH_SIZE} bytes en hexadecimal (offset a la izquierda)."))
        self.table = QtWidgets.QTableWidget(PATCH_SIZE // 16, 16)
        self.table.setHorizontalHeaderLabels([f"{i:X}" for i in range(16)])
        self.table.setVerticalHeaderLabels([f"{r * 16:03X}" for r in range(PATCH_SIZE // 16)])
        self.table.horizontalHeader().setDefaultSectionSize(38)
        self.table.verticalHeader().setDefaultSectionSize(22)
        for i, b in enumerate(patch.raw):
            self.table.setItem(i // 16, i % 16, QtWidgets.QTableWidgetItem(f"{b:02X}"))
        self.table.cellChanged.connect(self.edit_byte)
        lay.addWidget(self.table)
        self._loading = False

    def edit_byte(self, r, c):
        if self._loading:
            return
        item = self.table.item(r, c)
        try:
            v = int(item.text(), 16)
            if not 0 <= v <= 255:
                raise ValueError
        except ValueError:
            self._loading = True
            item.setText(f"{self.patch.raw[r * 16 + c]:02X}")
            self._loading = False
            return
        self.patch.raw[r * 16 + c] = v
        self.on_change()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1180, 700)
        # Mínimo explícito y bajo: el del contenido (781 px de alto) no cabe en pantallas de 768 px y Wayland
        # se negaba a maximizar la ventana.
        self.setMinimumSize(900, 560)
        self.bank = None
        self.mode = "am3"
        self.path = None
        self.dirty = False
        self._loading = False
        self.slot = 4  # slot seleccionado (AMP, como en el vídeo de la app)
        self.catalog = load_json("catalog.json")
        self.models = load_json("models.json")
        self.themes = themes.load_themes()
        self.taps = []
        self.glob = GlobalSettings()
        self.use_preset_color = QtCore.QSettings("mk300cfg", "app").value("preset_color", True, type=bool)
        self.base_theme = {"label": ""}
        self._style_key = None
        self._base_pt = QtWidgets.QApplication.instance().font().pointSize()
        self._scale_timer = QtCore.QTimer(self)
        self._scale_timer.setSingleShot(True)
        self._scale_timer.timeout.connect(self._apply_scale)
        self.pedal = None  # conexión USB abierta (sincronización activa)
        self.fw = None  # versión de firmware de la pedalera conectada ("v75")
        self.pedal_idx = None  # último preset activo visto en la pedalera
        self.live_sent = None  # copia del preset activo tal como está en la RAM de la pedalera
        self._from_pedal = False
        self._glob_loading = False
        self.offline = False  # el usuario abrió un archivo a propósito: se ven los presets sin pedalera
        self.pedal_models = None  # nombres de DS/AMP/CAB leídos de la pedalera (mandan sobre models.json)
        self.glob_raw = None  # copia de los 86 bytes de globales tal como están en la pedalera
        self.flash_bank = None  # último banco leído de la flash de la pedalera (para detectar cambios hechos en ella)
        self.flash_names = None  # y su lista de nombres de preset
        self._bank_tick = 0
        self._auto_reconnect = False  # solo tras perder la conexión por sorpresa, nunca al arrancar
        self._mix_knob = None  # perilla Mix de Whammy (se oculta fuera del modo MBody)
        self.sync_timer = QtCore.QTimer(self)
        self.sync_timer.timeout.connect(self.poll_pedal)
        self.reconnect_timer = QtCore.QTimer(self)
        self.reconnect_timer.timeout.connect(self._try_reconnect)
        self.reconnect_timer.start(1500)
        self.push_timer = QtCore.QTimer(self)
        self.push_timer.setSingleShot(True)
        self.push_timer.timeout.connect(lambda: self._sync_call(self._push_all))

        self.build_ui()
        self.link_label = QtWidgets.QLabel()
        self.statusBar().addPermanentWidget(self.link_label)
        self._set_link_state()
        self.build_menus()
        saved = QtCore.QSettings("mk300cfg", "app").value("theme", themes.DEFAULT)
        self.apply_theme(saved if saved in self.themes else themes.DEFAULT)
        self.open_path(os.path.join(DATA_DIR, "factory_am3.bin"))

    # --- construcción de la interfaz ---------------------------------------
    def build_ui(self):
        root = QtWidgets.QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        h = QtWidgets.QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        side = QtWidgets.QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(90)
        sl = QtWidgets.QVBoxLayout(side)
        sl.setContentsMargins(2, 10, 2, 10)
        sl.setSpacing(6)
        self.side_group = QtWidgets.QButtonGroup(self)
        b = W.SideButton("Connect", "⇄")  # pantalla de conexión: id 4 (el último de la pila)
        b.setChecked(True)
        self.side_group.addButton(b, 4)
        sl.addWidget(b)
        for i, (text, glyph) in enumerate((("Param", "☰"), ("Sounds", "▤"), ("Import", "⤓"), ("Community", "▦"))):
            b = W.SideButton(text, glyph)
            self.side_group.addButton(b, i)
            sl.addWidget(b)
        sl.addStretch(1)
        h.addWidget(side)

        main = QtWidgets.QVBoxLayout()
        main.setContentsMargins(16, 12, 16, 12)
        main.setSpacing(10)
        h.addLayout(main, 1)

        self.top_stack = QtWidgets.QStackedWidget()
        main.addWidget(self.top_stack, 1)

        # Param: pestañas Effect / Glob / EQ / Looper / Drum
        param = QtWidgets.QWidget()
        pv = QtWidgets.QVBoxLayout(param)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(10)
        tabs = QtWidgets.QWidget()
        tabs.setObjectName("panel")
        tl = QtWidgets.QHBoxLayout(tabs)
        tl.setContentsMargins(4, 4, 4, 4)
        self.tab_group = QtWidgets.QButtonGroup(self)
        self.stack = QtWidgets.QStackedWidget()
        for i, name in enumerate(TAB_NAMES):
            b = QtWidgets.QPushButton(name)
            b.setObjectName("tab")
            b.setCheckable(True)
            b.setChecked(i == 0)
            self.tab_group.addButton(b, i)
            tl.addWidget(b, 1)
        pv.addWidget(tabs)
        pv.addWidget(self.stack, 1)

        self.stack.addWidget(self.build_effect_page())
        self.pages = [screens.GlobPage(self.glob, self.glob_changed), screens.EqPage(self.glob, self.glob_changed),
                      screens.LooperPage(self.glob, self.glob_changed), screens.DrumPage(self.glob, self.glob_changed)]
        for page in self.pages:  # con barra de desplazamiento si no caben (Glob tiene más filas que alto)
            sa = QtWidgets.QScrollArea()
            sa.setWidgetResizable(True)
            sa.setFrameShape(QtWidgets.QFrame.NoFrame)
            sa.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")
            sa.setWidget(page)
            self.stack.addWidget(sa)
        self.tab_group.buttonClicked[int].connect(self.stack.setCurrentIndex)

        self.connect_page = libraries.ConnectPage()
        self.connect_page.connectRequested.connect(lambda: self.connect_pedal(silent=False))
        for page in (param, libraries.SoundsPage(), libraries.ImportPage(), libraries.CommunityPage(), self.connect_page):
            self.top_stack.addWidget(page)
        self.top_stack.setCurrentIndex(4)
        self.side_group.buttonClicked[int].connect(self.top_stack.setCurrentIndex)

    def build_effect_page(self):
        page = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        # selector de preset + editar nombre
        row = QtWidgets.QHBoxLayout()
        self.preset_combo = W.OverlayCombo()
        self.preset_combo.setObjectName("preset")
        self.preset_combo.setMinimumHeight(40)
        self.preset_combo.setMaxVisibleItems(18)
        self.preset_combo.currentIndexChanged.connect(self.select_patch)
        edit = QtWidgets.QPushButton("✎")
        edit.setObjectName("tool")
        edit.setFixedSize(44, 40)
        edit.setToolTip("Renombrar preset")
        edit.clicked.connect(self.rename_dialog)
        row.addWidget(self.preset_combo, 1)
        row.addWidget(edit)
        v.addLayout(row)

        # Save / Save to / More
        row = QtWidgets.QHBoxLayout()
        for text, slot in (("Save", self.save_clicked), ("Save to", self.save_to_clicked)):
            b = QtWidgets.QPushButton(text)
            b.setObjectName("tool")
            b.clicked.connect(slot)
            row.addWidget(b)
        more = QtWidgets.QPushButton("More")
        more.setObjectName("tool")
        menu = QtWidgets.QMenu(more)
        for text, slot in (
            ("Share current preset", self.share_current), ("Import current preset", self.import_current),
            ("Swap preset", self.swap_preset), (None, None),
            ("Share all presets", self.save_as), ("Import all presets", self.open_dialog),
            ("Export Snapshot", None), (None, None),
            ("Color", self.pick_color), ("Factory Restore", self.factory_restore),
        ):
            if text is None:
                menu.addSeparator()
                continue
            a = menu.addAction(text)
            if slot:
                a.triggered.connect(slot)
            else:
                a.setEnabled(False)
                a.setToolTip("Requiere conexión con la pedalera")
        more.setMenu(menu)
        row.addWidget(more)
        row.addStretch(1)
        v.addLayout(row)

        # barras Preset Vol / Pan / BPM
        self.bar_vol = W.ParamBar("Preset Vol", 0, 100)
        self.bar_pan = W.ParamBar("Pan", -100, 100, fmt=fmt_pan)
        self.bar_bpm = W.BpmBar("BPM", 40, 240)
        for bar, attr in ((self.bar_vol, "vol"), (self.bar_pan, "pan"), (self.bar_bpm, "tempo")):
            bar.valueChanged.connect(lambda val, a=attr: self.set_header(a, val))
        v.addWidget(self.bar_vol)
        v.addWidget(self.bar_pan)
        bpm_row = QtWidgets.QHBoxLayout()
        bpm_row.setSpacing(0)
        bpm_row.addWidget(self.bar_bpm, 1)
        tap = QtWidgets.QPushButton("TAP")
        tap.setObjectName("tool")
        tap.setFixedSize(70, 30)
        tap.clicked.connect(self.tap_tempo)
        bpm_row.addWidget(tap)
        v.addLayout(bpm_row)

        # cadena de efectos
        self.chain_box = W.ChainRow()
        self.chain_box.moved.connect(self.move_slot)
        self.chain_row = QtWidgets.QHBoxLayout(self.chain_box)
        self.chain_row.setContentsMargins(0, 0, 0, 0)
        self.chain_row.setSpacing(2)
        self.chain_buttons = {}
        for slot in range(SLOTS):
            b = W.ChainButton(slot, SLOT_NAMES[slot])
            b.clicked.connect(self.select_slot)
            self.chain_buttons[slot] = b
        v.addWidget(self.chain_box)

        # panel del efecto seleccionado
        panel = QtWidgets.QWidget()
        panel.setObjectName("panel")
        pl = QtWidgets.QVBoxLayout(panel)
        pl.setContentsMargins(16, 12, 16, 14)
        head = QtWidgets.QHBoxLayout()
        self.panel_icon = QtWidgets.QLabel()
        self.panel_cat = QtWidgets.QLabel()
        f = self.panel_cat.font()
        f.setBold(True)
        f.setPointSizeF(12)
        self.panel_cat.setFont(f)
        self.type_combo = W.OverlayCombo()
        self.type_combo.setObjectName("type")
        self.type_combo.setMinimumHeight(32)
        self.type_combo.setMaxVisibleItems(20)
        self.type_combo.currentIndexChanged.connect(self.change_type)
        self.toggle = W.Toggle()
        self.toggle.toggled.connect(self.toggle_slot)
        head.addWidget(self.panel_icon)
        head.addWidget(self.panel_cat)
        head.addSpacing(8)
        head.addWidget(self.type_combo, 1)
        head.addSpacing(8)
        head.addWidget(self.toggle)
        pl.addLayout(head)
        self.knob_row = QtWidgets.QHBoxLayout()
        self.knob_row.setSpacing(4)
        pl.addSpacing(6)
        pl.addLayout(self.knob_row)
        self.hint = QtWidgets.QLabel()
        self.hint.setWordWrap(True)
        pl.addWidget(self.hint)
        pl.addStretch(1)
        v.addWidget(panel, 1)
        return page

    def build_menus(self):
        m = self.menuBar().addMenu("&Archivo")
        for text, slot, key in (
            ("Banco de fábrica AM3", lambda: self.open_file(os.path.join(DATA_DIR, "factory_am3.bin")), None),
            ("Banco de fábrica AM4", lambda: self.open_file(os.path.join(DATA_DIR, "factory_am4.bin")), None),
            ("&Abrir…", self.open_dialog, "Ctrl+O"),
            ("&Guardar", self.save, "Ctrl+S"),
            ("Guardar &como…", self.save_as, "Ctrl+Shift+S"),
        ):
            a = m.addAction(text)
            a.triggered.connect(slot)
            if key:
                a.setShortcut(key)
        self.sync_action = m.addAction("Sincronizar con la &pedalera (USB)")
        self.sync_action.setCheckable(True)
        self.sync_action.toggled.connect(self.toggle_sync)
        vm = self.menuBar().addMenu("&Ver")
        vm.addAction("Editor de bytes del parche…").triggered.connect(self.open_hex)

        mm = self.menuBar().addMenu("&Modo")
        mgrp = QtWidgets.QActionGroup(self)
        self.mode_actions = {}
        for key, text in (("am3", "AM3"), ("am4", "AM4")):
            a = mm.addAction(text)
            a.setCheckable(True)
            a.setActionGroup(mgrp)
            a.setChecked(key == self.mode)
            a.triggered.connect(lambda _, k=key: self.set_mode(k))
            self.mode_actions[key] = a

        tm = self.menuBar().addMenu("&Tema")
        pc = tm.addAction("Color del preset")
        pc.setCheckable(True)
        pc.setChecked(self.use_preset_color)
        pc.toggled.connect(self.toggle_preset_color)
        tm.addSeparator()
        grp = QtWidgets.QActionGroup(self)
        self.theme_actions = {}
        saved = QtCore.QSettings("mk300cfg", "app").value("theme", themes.DEFAULT)
        for label in self.themes:
            a = tm.addAction(label)
            a.setCheckable(True)
            a.setActionGroup(grp)
            a.setChecked(label == saved)
            a.triggered.connect(lambda _, l=label: self.apply_theme(l))
            self.theme_actions[label] = a

    # --- estado actual -------------------------------------------------------
    GLOB_LABELS = {
        "music_vol": "BT&USB VOL", "usb_rec_vol": "USB REC VOL", "usb_rec_type": "USB Audio", "right_output_mode": "RCH",
        "pedal_conv0": "A/B Convert", "pedal_sync0": "Sync", "pedal_toe_switch": "Toe Switch", "pedal_state": "Pedal State", "tail_delay": "Tail Delay", "tail_reverb": "Tail Reverb",
        "eq_enable": "EQ on/off", "eq_lc": "EQ LC", "eq_hc": "EQ HC", "eq_peak_freq": "EQ frecuencia",
        "eq_quality_factor": "EQ Q", "eq_peak_gain": "EQ ganancia", "looper_rec_vol": "Looper REC vol",
        "looper_play_vol": "Looper PLAY vol", "looper_auto_rec": "Looper Auto REC", "looper_auto_rec_db": "Looper Auto Gate",
        "looper_position": "Looper Position", "looper_drum_sync": "Looper Drum Sync", "drum_vol": "Drum vol",
        "drum_tempo": "Drum BPM", "drum_sync": "Drum Sync"}

    def glob_changed(self):
        self.set_dirty(True)
        if self.pedal and not self._glob_loading:
            self.push_timer.start(40)

    def set_glob(self, g):
        self.glob = g
        self._glob_loading = True
        try:
            for page in self.pages:
                page.set_settings(g)
        finally:
            self._glob_loading = False

    def push_globals(self):
        """Envía a la RAM de la pedalera los ajustes globales que cambiaron en la app."""
        if self.glob_raw is None:
            return
        new = self.glob.to_raw(self.glob_raw)
        diff = [i for i in range(len(new)) if new[i] != self.glob_raw[i]]
        if diff:
            runs = []
            for i in diff:
                if runs and i == runs[-1][1]:
                    runs[-1] = (runs[-1][0], i + 1)
                else:
                    runs.append((i, i + 1))
            for a, b in runs:
                self.pedal.write_global(a, new[a:b])
            names = ", ".join(self.GLOB_LABELS[n] for n in GlobalSettings.from_raw(self.glob_raw).changed_fields(self.glob))
            self.statusBar().showMessage(f"App → pedalera: {names}", 5000)
            self.glob_raw = new
        # Pedal State no está en los globales: es un campo del parche (0x1e..0x1f)
        p = self._cur()
        if p is not None and bytes(p.raw[0x1E:0x20]) != bytes(self.glob.pedal_state):
            p.raw[0x1E:0x20] = bytes(self.glob.pedal_state)

    def _cur(self):
        i = self.preset_combo.currentIndex()
        return None if self._loading or i < 0 or not self.bank else self.bank.patches[i]

    def _update_title(self):
        base = os.path.basename(self.path) if self.path else "banco de fábrica"
        head = f"MK300 {self.fw}" if self.pedal and self.fw else "MK300 Studio"
        self.setWindowTitle(f"{head} — {base}{' *' if self.dirty else ''}")

    def set_dirty(self, v):
        self.dirty = v
        self._update_title()
        if v and self.pedal and not self._loading:
            self.push_timer.start(40)

    def apply_theme(self, label):
        self.base_theme = self.themes[label]
        self._style_key = None
        QtCore.QSettings("mk300cfg", "app").setValue("theme", label)
        if label in getattr(self, "theme_actions", {}):
            self.theme_actions[label].setChecked(True)
        if self.bank:
            self.refresh_all()
        else:
            self._restyle()

    def _restyle(self):
        """Aplica el tema base; si está activo, con el acento del color del preset actual."""
        t, key = self.base_theme, self.base_theme["label"]
        p = self._cur() if self.bank else None
        if p is not None and self.use_preset_color:
            r, g, b, _ = p.color
            t, key = themes.with_accent(t, r, g, b), (key, r, g, b)
        if key == self._style_key:
            return
        self._style_key = key
        themes.set_current(t)
        W._icon_cache.clear()
        QtWidgets.QApplication.instance().setStyleSheet(themes.stylesheet(t))
        for w in self.findChildren(QtWidgets.QWidget):
            w.update()

    def toggle_preset_color(self, on):
        self.use_preset_color = on
        QtCore.QSettings("mk300cfg", "app").setValue("preset_color", on)
        self._style_key = None
        self.refresh_all()

    def set_mode(self, key):
        self.mode = key
        self.mode_actions[key].setChecked(True)
        if self.bank:
            self.refresh_all()

    # --- carga / guardado -----------------------------------------------------
    def maybe_discard(self):
        if not self.dirty:
            return True
        r = QtWidgets.QMessageBox.question(self, "Cambios sin guardar", "Hay cambios sin guardar. ¿Descartarlos?")
        return r == QtWidgets.QMessageBox.Yes

    def open_dialog(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Abrir banco", "", "Bancos (*.bin);;Todos (*)")
        if p:
            self.open_file(p)

    # --- sincronización con la pedalera (USB) -------------------------------------
    def toggle_sync(self, on):
        if on and self.pedal is None:
            if not self.connect_pedal():
                self.sync_action.blockSignals(True)
                self.sync_action.setChecked(False)
                self.sync_action.blockSignals(False)
        elif not on and self.pedal is not None:
            self._unlink("Sincronización desactivada")

    def describe_change(self, old, new):
        """Texto legible de lo que cambió entre dos copias del preset, y el slot afectado (o None)."""
        names, slot_hit, seen = [], None, set()
        from .bank import Patch
        po, pn = Patch(bytearray(old)), Patch(bytearray(new))
        for off in (i for i in range(PATCH_SIZE) if old[i] != new[i]):
            if OFF_EFFPARA <= off < OFF_EFFPARA + SLOTS * PARAMS * 2:
                slot, i = divmod((off - OFF_EFFPARA) // 2, PARAMS)
                key, slot_hit = ("par", slot, i), slot if slot_hit is None else slot_hit
                if key in seen:
                    continue
                seen.add(key)
                label = next((sp[1] for sp in self.knob_specs(slot, pn.unit(slot), pn)[0] if sp[0] == i), f"P{i + 1}")
                names.append(f"{SLOT_NAMES[slot]} {label.replace(chr(10), ' ')}: {po.param(slot, i)} → {pn.param(slot, i)}")
            elif OFF_EFFON <= off < OFF_EFFON + SLOTS:
                slot = off - OFF_EFFON
                slot_hit = slot if slot_hit is None else slot_hit
                names.append(f"{SLOT_NAMES[slot]} {'activado' if pn.enabled(slot) else 'desactivado'}")
            elif OFF_EFFUNIT <= off < OFF_EFFUNIT + SLOTS:
                slot = off - OFF_EFFUNIT
                slot_hit = slot if slot_hit is None else slot_hit
                names.append(f"{SLOT_NAMES[slot]}: tipo cambiado")
            elif OFF_CHAIN <= off < OFF_CHAIN + SLOTS:
                if "chain" not in seen:
                    seen.add("chain")
                    names.append("orden de la cadena")
            elif off in (OFF_VOL, OFF_VOL + 1):
                if "vol" not in seen:
                    seen.add("vol")
                    names.append(f"Preset Vol: {po.vol} → {pn.vol}")
            elif off in (OFF_PAN, OFF_PAN + 1):
                if "pan" not in seen:
                    seen.add("pan")
                    names.append(f"Pan: {po.pan} → {pn.pan}")
            elif off in (OFF_TEMPO, OFF_TEMPO + 1):
                if "bpm" not in seen:
                    seen.add("bpm")
                    names.append(f"BPM: {po.tempo} → {pn.tempo}")
            elif OFF_COLOR <= off < OFF_COLOR + 4:
                if "color" not in seen:
                    seen.add("color")
                    names.append("color")
            elif off < NAME_LEN:
                if "name" not in seen:
                    seen.add("name")
                    names.append(f"nombre: {pn.name}")
            elif "otro" not in seen:
                seen.add("otro")
                names.append(f"byte 0x{off:02x}")
        return ", ".join(names[:4]) + (" …" if len(names) > 4 else ""), slot_hit

    def _set_link_state(self):
        if self.pedal is not None:
            self.link_label.setText("● Pedalera sincronizada")
            self.link_label.setStyleSheet("color: #22c55e; background: transparent; padding: 0 8px;")
        else:
            self.link_label.setText("○ Sin pedalera")
            self.link_label.setStyleSheet("color: #9a9a9a; background: transparent; padding: 0 8px;")
        self._update_title()
        self._update_view()

    def _unlink(self, why=None, auto=False):
        self._auto_reconnect = auto  # solo si la conexión se perdió sola
        self.sync_timer.stop()
        self.push_timer.stop()
        if self.pedal:
            try:
                self.pedal.close()
            except OSError:
                pass
        self.pedal = None
        self.pedal_models = None
        self.fw = None
        self.flash_bank = self.flash_names = None
        self._set_link_state()
        self.sync_action.blockSignals(True)
        self.sync_action.setChecked(False)
        self.sync_action.blockSignals(False)
        if why:
            self.statusBar().showMessage(why, 8000)
            self.connect_page.set_notice("Se perdió la conexión con la pedalera." if "desconectada" in why else why)

    def _sync_call(self, fn):
        try:
            fn()
        except (device.DeviceError, OSError) as e:
            self._unlink(f"Pedalera desconectada: {e}", auto=True)

    def show_page(self, idx):
        self.side_group.button(idx).setChecked(True)
        self.top_stack.setCurrentIndex(idx)

    def _update_view(self):
        """Sin pedalera (y sin archivo abierto a propósito) solo se ve la pantalla de conexión."""
        online = self.pedal is not None or self.offline
        for i in (0, 1, 2):
            self.side_group.button(i).setEnabled(online)
        cur = self.top_stack.currentIndex()
        if online and cur == 4:
            self.show_page(0)
        elif not online and cur != 3:
            self.show_page(4)

    def open_file(self, path):
        """Abrir un banco de archivo a propósito: permite ver los presets sin pedalera."""
        self.open_path(path)
        if self.pedal is None and self.bank is not None:
            self.offline = True
        self._update_view()

    def connect_pedal(self, silent=False):
        """Lee el banco de la pedalera, lo abre en su preset activo y empieza a sincronizar."""
        if self.pedal is not None or not self.maybe_discard():
            return self.pedal is not None
        try:
            pedal = device.Pedal()
            try:
                data, idx, live, graw = pedal.read_bank(), pedal.current_index(), pedal.read_live(), pedal.read_globals()
                models = pedal.read_model_names()
                fw = fw_label(pedal.identity())
                names = pedal.read_names()
            except Exception:
                pedal.close()
                raise
        except device.DeviceError as e:
            if silent:
                self.statusBar().showMessage(f"Sin pedalera: {e}", 6000)
            else:
                QtWidgets.QMessageBox.critical(self, "Pedalera", str(e))
            return False
        # Copia automática de lo leído: <datos de usuario>/mk300-studio/backups/mk300_<fecha>.bin
        folder = os.path.join(user_data_dir(), "backups")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, time.strftime("mk300_%Y%m%d_%H%M%S.bin"))
        with open(path, "wb") as f:
            f.write(data)
        for old in sorted(f for f in os.listdir(folder) if f.startswith("mk300_") and f.endswith(".bin"))[:-MAX_BACKUPS]:
            os.remove(os.path.join(folder, old))
        self.dirty = False
        self.open_path(path)
        self.bank.patches[idx].raw[:] = live  # la RAM de la pedalera manda sobre la flash
        self.offline = False
        self.connect_page.set_notice("")
        self.pedal, self.pedal_idx, self.live_sent = pedal, idx, bytes(live)
        self.pedal_models = models
        self.fw = fw
        self.flash_bank, self.flash_names, self._bank_tick = bytes(data), names, 0
        self.glob_raw = bytes(graw)
        g = GlobalSettings.from_raw(graw)
        g.pedal_state = list(live[0x1E:0x20])
        self.set_glob(g)
        self._from_pedal = True
        try:
            self.preset_combo.setCurrentIndex(idx)
        finally:
            self._from_pedal = False
        self.refresh_presets()
        self.refresh_all()
        self.set_dirty(False)
        self.sync_action.blockSignals(True)
        self.sync_action.setChecked(True)
        self.sync_action.blockSignals(False)
        self.sync_timer.start(400)
        self._set_link_state()
        self.statusBar().showMessage(f"Sincronizado con la pedalera (preset {idx + 1})", 6000)
        return True

    def poll_pedal(self):
        if self.push_timer.isActive():
            return
        self._sync_call(self._poll_pedal)

    def _poll_globals(self):
        graw = self.pedal.read_globals()
        if graw != self.glob_raw:  # ajuste global cambiado en la pedalera
            old = GlobalSettings.from_raw(self.glob_raw)
            g = GlobalSettings.from_raw(graw)
            g.pedal_state = list(self.glob.pedal_state)
            names = ", ".join(self.GLOB_LABELS[n] for n in old.changed_fields(g)) or "globales"
            self.glob_raw = bytes(graw)
            self.set_glob(g)
            self.statusBar().showMessage(f"Pedalera → app: {names}", 5000)

    def _try_reconnect(self):
        """Tras perder la conexión por sorpresa, vuelve a conectar sola cuando reaparece (solo lee; sin cambios pendientes)."""
        if self.pedal is None and self._auto_reconnect and not self.dirty and device.pedal_present():
            self.connect_pedal(silent=True)

    def _poll_bank(self):
        """Detecta cambios de banco hechos desde la pedalera (guardar, renombrar, copiar) y los trae a la app."""
        idx = self.pedal_idx
        names = self.pedal.read_names()
        flash = self.pedal.read(idx * PATCH_SIZE, PATCH_SIZE)
        if names == self.flash_names and flash == self.flash_bank[idx * PATCH_SIZE:(idx + 1) * PATCH_SIZE]:
            return
        new, old = self.pedal.read_bank(), self.flash_bank
        updated, kept = [], []
        for i in range(PATCH_COUNT):
            a, b = i * PATCH_SIZE, (i + 1) * PATCH_SIZE
            if new[a:b] == old[a:b]:
                continue
            p = self.bank.patches[i]
            if i == idx:  # el activo ya va por la RAM
                updated.append(i)
            elif bytes(p.raw) == old[a:b]:
                p.raw[:] = new[a:b]
                updated.append(i)
            else:  # el usuario lo editó en la app: no se pisa
                kept.append(i)
        self.flash_bank, self.flash_names = bytes(new), names
        self.refresh_presets()
        msg = f"Pedalera → app: banco actualizado ({len(updated)} presets)"
        if kept:
            msg += f"; {len(kept)} con cambios tuyos sin tocar"
        self.statusBar().showMessage(msg, 8000)

    def _poll_pedal(self):
        self._poll_globals()
        self._bank_tick += 1
        if self._bank_tick % 5 == 0 and self.flash_bank is not None and self.pedal_idx is not None:  # cada ~2 s
            self._poll_bank()
        idx, live = self.pedal.current_index(), self.pedal.read_live()
        changed = False
        if idx != self.pedal_idx:  # cambio de preset hecho en la pedalera
            self.pedal_idx = idx
            self._from_pedal = True
            try:
                self.preset_combo.setCurrentIndex(idx)
            finally:
                self._from_pedal = False
            changed = True
        if live != self.live_sent or changed:  # ajuste girado en la pedalera
            was_dirty = self.dirty
            if changed:
                msg, hit = f"Pedalera → app: preset {idx + 1} «{self.bank.patches[idx].name}»", None
            else:
                msg, hit = self.describe_change(self.live_sent, live)
                msg = f"Pedalera → app: {msg}"
            self.bank.patches[idx].raw[:] = live
            if list(live[0x1E:0x20]) != self.glob.pedal_state:
                self.glob.pedal_state = list(live[0x1E:0x20])
                self.set_glob(self.glob)
            if hit is not None and hit != self.slot:
                self.slot = hit  # muestra el efecto que se tocó en la pedalera
            self.statusBar().showMessage(msg, 5000)
            self.live_sent = bytes(live)
            self.refresh_presets()
            self.refresh_all()
            self.set_dirty(was_dirty)
            self.push_timer.stop()

    def _select_on_pedal(self):
        idx = self.preset_combo.currentIndex()
        self.pedal.select_preset(idx)
        self.pedal_idx = idx
        self.live_sent = self.pedal.read_live()
        self.push_live()  # si el banco de la app difiere, la pedalera suena como la app

    def _push_all(self):
        self.push_globals()
        self.push_live()

    def push_live(self):
        """Envía a la RAM de la pedalera solo los bytes que cambiaron en el preset activo."""
        p = self._cur()
        if not self.pedal or self.live_sent is None or p is None or self.preset_combo.currentIndex() != self.pedal_idx:
            return
        new, old = bytes(p.raw), self.live_sent
        diff = [i for i in range(PATCH_SIZE) if new[i] != old[i]]
        if not diff:
            return
        if len(diff) > 32:
            runs = [(diff[0], diff[-1] + 1)]
        else:
            runs = []
            for i in diff:
                if runs and i == runs[-1][1]:
                    runs[-1] = (runs[-1][0], i + 1)
                else:
                    runs.append((i, i + 1))
        for a, b in runs:
            self.pedal.write_live(a, new[a:b])
        self.statusBar().showMessage(f"App → pedalera: {self.describe_change(old, new)[0]}", 5000)
        self.live_sent = new

    def save_to_pedal(self, idx):
        """Guarda el preset activo de la app en la flash de la pedalera (con confirmación)."""
        p = self._cur()
        if p is None:
            return
        r = QtWidgets.QMessageBox.question(
            self, "Guardar en la pedalera", f"¿Guardar «{p.name}» en la posición {idx + 1} de la pedalera?\n"
            f"Sustituye lo que haya ahí ({self.bank.patches[idx].name if idx != self.preset_combo.currentIndex() else 'versión guardada'}).")
        if r != QtWidgets.QMessageBox.Yes:
            return
        def run():
            self.pedal.save_preset(idx, bytes(p.raw))
            self.flash_bank = self.flash_bank[:idx * PATCH_SIZE] + bytes(p.raw) + self.flash_bank[(idx + 1) * PATCH_SIZE:]
            self.flash_names = self.pedal.read_names()  # lo guardado desde la app no cuenta como cambio de la pedalera
            if idx != self.preset_combo.currentIndex():
                self.bank.patches[idx].raw[:] = p.raw
                self.refresh_presets()
            self.statusBar().showMessage(f"Guardado en la pedalera: preset {idx + 1}", 6000)
        self._sync_call(run)

    def save_clicked(self):
        if self.pedal:
            self.save_to_pedal(self.preset_combo.currentIndex())
            if self.path:
                self.save()
        else:
            self.save()

    def save_to_clicked(self):
        if not self.pedal:
            return self.save_as()
        n, ok = QtWidgets.QInputDialog.getInt(self, "Save to", f"Guardar en la posición (1-{PATCH_COUNT}):",
                                              self.preset_combo.currentIndex() + 1, 1, PATCH_COUNT)
        if ok:
            self.save_to_pedal(n - 1)

    def open_path(self, path):
        if not self.maybe_discard():
            return
        try:
            self.bank = Bank.load(path)
        except (OSError, ValueError) as e:
            QtWidgets.QMessageBox.critical(self, "No se pudo abrir", str(e))
            return
        # Los bancos de fábrica son de solo lectura: se guardan siempre "como…".
        self.path = None if path.startswith(DATA_DIR) else path
        if "factory_am4" in path:
            self.mode = "am4"
            self.mode_actions["am4"].setChecked(True)
        elif "factory_am3" in path:
            self.mode = "am3"
            self.mode_actions["am3"].setChecked(True)
        self.set_glob(GlobalSettings.load_for(path) if self.path else GlobalSettings())
        self.set_dirty(False)
        self._loading = True
        self.preset_combo.clear()
        for i, p in enumerate(self.bank.patches):
            self.preset_combo.addItem(color_icon(p), f"[{i + 1:03d}] {p.name}")
        self._loading = False
        self.preset_combo.setCurrentIndex(0)
        self.refresh_all()

    def save(self):
        if not self.bank:
            return
        if not self.path:
            return self.save_as()
        self.bank.save(self.path)
        self.glob.save_for(self.path)
        self.set_dirty(False)

    def save_as(self):
        if not self.bank:
            return
        p, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Guardar banco", "mi_banco.bin", "Bancos (*.bin)")
        if p:
            self.path = p
            self.save()

    def factory_restore(self):
        r = QtWidgets.QMessageBox.question(
            self, "Factory Restore",
            f"Se recargará el banco de fábrica {self.mode.upper()} y se perderán los cambios no guardados. ¿Continuar?")
        if r == QtWidgets.QMessageBox.Yes:
            self.dirty = False
            self.open_path(os.path.join(DATA_DIR, f"factory_{self.mode}.bin"))

    # --- acciones del menú More -----------------------------------------------
    def share_current(self):
        p = self._cur()
        if not p:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Compartir preset", f"{p.name or 'preset'}.mkpreset")
        if path:
            with open(path, "wb") as f:
                f.write(bytes(p.raw))

    def import_current(self):
        p = self._cur()
        if not p:
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Importar preset", "", "Presets (*.mkpreset);;Todos (*)")
        if not path:
            return
        data = open(path, "rb").read()
        if len(data) != PATCH_SIZE:
            QtWidgets.QMessageBox.critical(self, "Preset inválido", f"Se esperaban {PATCH_SIZE} bytes y tiene {len(data)}.")
            return
        p.raw[:] = data
        self.set_dirty(True)
        self.refresh_presets()
        self.refresh_all()

    def swap_preset(self):
        i = self.preset_combo.currentIndex()
        n, ok = QtWidgets.QInputDialog.getInt(self, "Swap preset", f"Intercambiar con el preset (1-{PATCH_COUNT}):",
                                              i + 1, 1, PATCH_COUNT)
        if ok and n - 1 != i:
            ps = self.bank.patches
            ps[i], ps[n - 1] = ps[n - 1], ps[i]
            self.set_dirty(True)
            self.refresh_presets()
            self.refresh_all()
            self.refresh_all()

    def pick_color(self):
        p = self._cur()
        if not p:
            return
        r, g, b, _ = p.color
        c = QtWidgets.QColorDialog.getColor(QtGui.QColor(r, g, b), self, "Color del preset")
        if c.isValid():
            p.set_color(c.red(), c.green(), c.blue())
            self.set_dirty(True)
            self.refresh_presets()
            self.refresh_all()

    def open_hex(self):
        p = self._cur()
        if p:
            HexDialog(p, lambda: (self.set_dirty(True), self.refresh_presets(), self.refresh_all()), self).exec_()

    # --- selección y edición ---------------------------------------------------
    def refresh_presets(self):
        self._loading = True
        i = self.preset_combo.currentIndex()
        for k, p in enumerate(self.bank.patches):
            self.preset_combo.setItemText(k, f"[{k + 1:03d}] {p.name}")
            self.preset_combo.setItemIcon(k, color_icon(p))
        self.preset_combo.setCurrentIndex(i)
        self._loading = False

    def select_patch(self, _):
        if not self._loading and self.bank:
            self.refresh_all()
            if self.pedal and not self._from_pedal:
                self.push_timer.stop()
                self._sync_call(self._select_on_pedal)

    def rename_dialog(self):
        p = self._cur()
        if not p:
            return
        text, ok = QtWidgets.QInputDialog.getText(self, "Renombrar preset", f"Nombre (máx. {NAME_LEN}):", text=p.name)
        if ok:
            p.name = text
            self.set_dirty(True)
            self.refresh_presets()

    def set_header(self, attr, v):
        if self._loading:
            return
        if (p := self._cur()):
            setattr(p, attr, v)
            self.set_dirty(True)

    def tap_tempo(self):
        now = time.time()
        self.taps = [t for t in self.taps if now - t < 2.5] + [now]
        if len(self.taps) >= 2:
            gaps = [b - a for a, b in zip(self.taps, self.taps[1:])]
            self.bar_bpm.setValue(round(60 / (sum(gaps) / len(gaps))), emit=True)

    def select_slot(self, slot):
        self.slot = slot
        self.refresh_panel()
        self.refresh_chain()

    def move_slot(self, slot, pos):
        """Mueve un efecto a la posición `pos` de la cadena (arrastrar y soltar)."""
        p = self._cur()
        if p is None:
            return
        order = p.chain()
        if slot not in order:
            return
        order.remove(slot)
        order.insert(max(0, min(pos, len(order))), slot)
        if order != p.chain():
            p.set_chain(order)
            self.set_dirty(True)
            self.refresh_chain()

    def toggle_slot(self, on):
        if self._loading:
            return
        if (p := self._cur()):
            p.set_enabled(self.slot, on)
            self.set_dirty(True)
            self.refresh_chain()

    def change_type(self, idx):
        p = self._cur()
        if p is None or idx < 0:
            return
        unit = self.type_combo.itemData(idx)
        if unit is not None and unit != p.unit(self.slot):
            p.set_unit(self.slot, unit)
            self.set_dirty(True)
            self.refresh_knobs()

    def _is_whammy(self, p):
        cat = SLOT_NAMES[self.slot]
        return cat == "FX" and cat in CATALOG_VALIDATED and p.unit(self.slot) < len(self.catalog[cat]) \
            and self.catalog[cat][p.unit(self.slot)]["name"] == "Whammy"

    def set_param(self, i, v):
        if (p := self._cur()):
            p.set_param(self.slot, i, v)
            if i == 0 and self._mix_knob is not None and self._is_whammy(p):
                self._mix_knob.setVisible(v == 0)  # Mix solo existe con Mode = MBody
            self.set_dirty(True)

    # --- refresco de la interfaz -----------------------------------------------
    def refresh_all(self):
        p = self._cur()
        if p is None:
            return
        self._restyle()
        self._loading = True
        self.bar_vol.setValue(p.vol)
        self.bar_pan.setValue(p.pan)
        self.bar_bpm.setValue(p.tempo)
        self._loading = False
        self.refresh_chain()
        self.refresh_panel()

    def refresh_chain(self):
        p = self._cur()
        if p is None:
            return
        while self.chain_row.count():
            it = self.chain_row.takeAt(0)
            w = it.widget()
            if w is not None and not isinstance(w, W.ChainButton):
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self.chain_row.addStretch(1)
        order = [s for s in p.chain() if 0 <= s < SLOTS]
        for pos, slot in enumerate(order):
            b = self.chain_buttons[slot]
            b.set_state(p.enabled(slot), slot == self.slot)
            self.chain_row.addWidget(b)
            b.show()
            if pos < len(order) - 1:
                arrow = QtWidgets.QLabel("›")
                arrow.setStyleSheet(f"color: {themes.current.get('kTextMuted', '#666')}; background: transparent;")
                self.chain_row.addWidget(arrow)
        self.chain_row.addStretch(1)

    def type_items(self, slot):
        """(texto, valor de effunit) de cada tipo disponible, o [] si no hay lista fiable."""
        cat = SLOT_NAMES[slot]
        if slot in MODEL_SLOTS:
            names = self.models[self.mode][MODEL_SLOTS[slot]]  # respaldo sin pedalera
            pm = (self.pedal_models or {}).get(MODEL_SLOTS[slot])
            ids = range(1, max(pm) + 1) if pm else sorted(int(k) for k in names)
            return [(f"{i}{(pm or {}).get(i) or names.get(str(i)) or 'modelo'}", i - 1) for i in ids]
        if cat in CATALOG_VALIDATED:
            return [(c["name"], i) for i, c in enumerate(self.catalog[cat])]
        return []

    def refresh_panel(self):
        p = self._cur()
        if p is None:
            return
        slot, cat = self.slot, SLOT_NAMES[self.slot]
        color = W.CATEGORY_COLORS[cat]
        self._loading = True
        ic = W.tinted_icon(W.ICON_FILES[cat], color, 22)
        self.panel_icon.setPixmap(ic if ic else QtGui.QPixmap())
        self.panel_cat.setText(cat)
        self.panel_cat.setStyleSheet(f"color: {color}; background: transparent;")
        self.toggle.color = color
        self.toggle.setChecked(p.enabled(slot))

        items = self.type_items(slot)
        unit = p.unit(slot)
        self.type_combo.clear()
        if cat == "VOL":
            self.type_combo.addItem("VOL", unit)
        else:
            if not items:
                items = [(f"Tipo {u}", u) for u in range(max(unit, 12) + 1)]
            if all(v != unit for _, v in items):
                items = items + [(f"Tipo {unit}" if slot not in MODEL_SLOTS else f"modelo {unit + 1}", unit)]
            for text, val in items:
                self.type_combo.addItem(text, val)
            self.type_combo.setCurrentIndex(next(i for i, (_, v) in enumerate(items) if v == unit))
        self.type_combo.setEnabled(cat != "VOL")
        self._loading = False
        self.refresh_knobs()

    def knob_specs(self, slot, unit, patch):
        """Lista de (índice, etiqueta, mín, máx, formato) de las perillas y si los nombres están verificados."""
        cat = SLOT_NAMES[slot]
        if cat in ("AMP", "DS"):
            return [(i, n, 0, 100, None) for i, n in enumerate(AMP_DS_PARAMS)], True
        if cat == "CAB":
            return [(0, CAB_PARAMS[0], 0, 100, None), (1, CAB_PARAMS[1], 20, 300, None),
                    (2, CAB_PARAMS[2], 50, 180, fmt_khz)], True
        if cat == "VOL":
            return [(0, "VOL", 0, 100, None)], True
        if cat in CATALOG_VALIDATED:
            child = self.catalog[cat][unit] if unit < len(self.catalog[cat]) else None
            if child and child["params"]:
                names = [(prm.get("name") or "").replace("\\n", "\n") for prm in child["params"]]
                sync_on = "Sync" in names and patch.param(slot, names.index("Sync")) > 0
                out = []
                for i, prm in enumerate(child["params"]):
                    name = names[i]
                    if not name or (name == "Sync\nBpm" and not sync_on):
                        continue  # parámetros sin nombre u ocultos, como en la app original
                    fmt = fmt_whammy_mode if child["name"] == "Whammy" and name == "Mode" else param_format(cat, name)
                    out.append((i, name, prm.get("minVal", 0), prm.get("maxVal", 100), fmt))
                return out, True
        n = max(3, 1 + max([i for i in range(PARAMS) if patch.param(slot, i) != 0], default=-1))
        out = []
        for i in range(min(n, PARAMS)):
            v = patch.param(slot, i)
            out.append((i, f"P{i + 1}", min(0, v), max(100, v), None))
        return out, False

    def refresh_knobs(self):
        p = self._cur()
        if p is None:
            return
        while self.knob_row.count():
            w = self.knob_row.takeAt(0).widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        specs, known = self.knob_specs(self.slot, p.unit(self.slot), p)
        color = W.CATEGORY_COLORS[SLOT_NAMES[self.slot]]
        self.knob_row.addStretch(1)
        self._mix_knob = None
        for i, label, lo, hi, fmt in specs:
            k = W.Knob(label, lo, hi, color, fmt)
            k.setValue(p.param(self.slot, i))
            k.valueChanged.connect(lambda v, i=i: self.set_param(i, v))
            self.knob_row.addWidget(k)
            if self._is_whammy(p) and label == "Mix":
                self._mix_knob = k
                k.setVisible(p.param(self.slot, 0) == 0)  # solo con Mode = MBody, como la app original
        self.knob_row.addStretch(1)
        self.hint.setText("" if known else
                          "Nombres de parámetros de este tipo aún no verificados con la app original (P1…Pn).")
        self.hint.setStyleSheet(f"color: {themes.current.get('kTextMuted', '#666')}; background: transparent;")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._scale_timer.start(60)

    def _apply_scale(self):
        """Agranda perillas, iconos de la cadena, barras y letra cuando la ventana crece (maximizar)."""
        s = max(1.0, min(2.6, min((self.width() - 90) / 1090, (self.height() - 30) / 600)))
        if abs(s - W.UI_SCALE) < 0.03:
            return
        W.UI_SCALE = s
        app = QtWidgets.QApplication.instance()
        app.setFont(QtGui.QFont(app.font().family(), round(self._base_pt * min(s, 1.6)))) \
            if self._base_pt else None
        for bar in (self.bar_vol, self.bar_pan, self.bar_bpm):
            bar.setFixedHeight(round(30 * s))
        for b in self.chain_buttons.values():
            b.setFixedSize(round(76 * s), round(96 * s))
            b.update()
        if self.bank:
            self.refresh_chain()
            self.refresh_knobs()

    def closeEvent(self, e):
        if self.maybe_discard():
            self._unlink()
            e.accept()
        else:
            e.ignore()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("MK300 Studio")
    app.setDesktopFileName("mk300-studio")
    app.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(DATA_DIR), "assets", "app_icon.svg")))
    w = MainWindow()
    w.showMaximized()  # ocupa todo el monitor; el contenido se amplía con la ventana
    sys.exit(app.exec_())
