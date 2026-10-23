"""Temas de color de la interfaz."""
import json
import os

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "themes.json")
DEFAULT = "Midnight Blue"  # el acento #3b9eff coincide con las barras de la app original

current = {}  # tema activo; lo leen los componentes pintados a mano (widgets.py)


def set_current(t):
    current.clear()
    current.update(t)


def load_themes():
    with open(DATA, encoding="utf-8") as f:
        raw = json.load(f)
    return {v["label"]: v for v in raw.values()}


def _mix(a, b, k):
    return tuple(round(x + (y - x) * k) for x, y in zip(a, b))


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _hex(c):
    return "#%02x%02x%02x" % tuple(c)


def _tint(h, c, k):
    """Quita el matiz propio del color (gris con su misma luminosidad) y lo tiñe con c."""
    g = round(sum(_rgb(h)) / 3)
    return _hex(_mix((g, g, g), c, k))


def with_accent(t, r, g, b):
    """Copia del tema con acento, fondos y textos teñidos con el color del preset."""
    c = (r, g, b)
    out = dict(t)
    out["kAccent"] = _hex(c)
    out["kAccentDim"] = "#33" + _hex(c)[1:]
    out["kAccentSoft"] = _hex(_mix(c, (0, 0, 0), 0.52))
    for key, k in (("kBg", 0.05), ("kSurface", 0.07), ("kCard", 0.08), ("kElevated", 0.10), ("kBorder", 0.14),
                   ("kDivider", 0.10), ("kTextSecondary", 0.18), ("kTextMuted", 0.18), ("kBgGradientMid", 0.05),
                   ("kBgGradientBottom", 0.03)):
        out[key] = _tint(t[key], c, k)
    out["kBgGradientTop"] = _tint(t["kBgGradientTop"], c, 0.22)
    return out


def stylesheet(t):
    return f"""
QWidget {{ background: {t['kBg']}; color: {t['kTextPrimary']}; }}
QWidget#root {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {t['kBgGradientTop']},
    stop:0.6 {t['kBgGradientMid']}, stop:1 {t['kBgGradientBottom']}); }}
QWidget#sidebar {{ background: {t['kSurface']}; }}
QWidget#panel {{ background: {t['kSurface']}; border-radius: 10px; }}
QPushButton#tab {{ background: transparent; border: none; border-radius: 6px; color: {t['kTextSecondary']}; padding: 8px; }}
QPushButton#tab:checked {{ background: {t['kAccentDim']}; color: {t['kAccent']}; }}
QComboBox#preset {{ background: {t['kSurface']}; border: none; border-radius: 8px; padding-left: 12px; font-weight: bold; }}
QComboBox#type {{ background: transparent; border: none; padding-left: 4px; font-weight: bold; }}
QComboBox QAbstractItemView {{ background: {t['kCard']}; border: 1px solid {t['kBorder']};
    selection-background-color: {t['kAccentDim']}; selection-color: {t['kAccent']}; outline: none; }}
QPushButton#seg {{ background: {t['kSurface']}; border: 1px solid transparent; border-radius: 6px;
    color: {t['kTextSecondary']}; padding: 9px 18px; min-width: 34px; }}
QPushButton#seg:checked {{ background: {t['kAccentDim']}; border-color: {t['kAccent']}; color: {t['kAccent']}; }}
QPushButton#power {{ background: {t['kCard']}; border: 2px solid {t['kBorder']}; border-radius: 30px;
    color: {t['kTextMuted']}; font-size: 22px; }}
QPushButton#power:checked {{ background: {t['kAccentDim']}; border-color: {t['kAccent']}; color: {t['kAccent']}; }}
QPushButton#playdrum {{ background: {t['kAccentDim']}; border: 1px solid {t['kAccent']}; border-radius: 6px;
    color: {t['kAccent']}; font-weight: bold; }}
QPushButton#playdrum:disabled {{ background: {t['kSurface']}; border-color: {t['kBorder']}; color: {t['kTextMuted']}; }}
QPushButton#tool {{ background: {t['kSurface']}; border: none; border-radius: 6px; padding: 9px 14px; }}
QPushButton#tool:hover {{ background: {t['kElevated']}; }}
QMainWindow, QMenuBar, QMenu {{ background: {t['kSurface']}; }}
QMenuBar::item:selected, QMenu::item:selected {{ background: {t['kAccentDim']}; }}
QTabWidget::pane {{ border: 1px solid {t['kBorder']}; }}
QTabBar::tab {{ background: {t['kSurface']}; color: {t['kTextSecondary']}; padding: 6px 14px;
               border: 1px solid {t['kBorder']}; border-bottom: none; }}
QTabBar::tab:selected {{ background: {t['kCard']}; color: {t['kAccent']}; }}
QTabBar::tab:disabled {{ color: {t['kTextMuted']}; }}
QListWidget, QTableWidget, QLineEdit, QSpinBox, QComboBox {{
    background: {t['kCard']}; border: 1px solid {t['kBorder']}; border-radius: 4px;
    selection-background-color: {t['kAccentDim']}; selection-color: {t['kTextPrimary']}; }}
QListWidget::item:selected {{ background: {t['kAccentDim']}; color: {t['kAccent']}; }}
QHeaderView::section {{ background: {t['kElevated']}; color: {t['kTextSecondary']}; border: none; padding: 2px; }}
QLabel {{ background: transparent; }}
QCheckBox {{ background: transparent; spacing: 6px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {t['kBorder']}; border-radius: 3px;
                       background: {t['kCard']}; }}
QCheckBox::indicator:checked {{ background: {t['kAccent']}; border-color: {t['kAccent']}; }}
QSplitter::handle {{ background: {t['kDivider']}; }}
QScrollBar {{ background: {t['kSurface']}; }}
QScrollBar::handle {{ background: {t['kElevated']}; border-radius: 4px; }}
QPushButton {{ background: {t['kElevated']}; border: 1px solid {t['kBorder']}; padding: 5px 12px; border-radius: 4px; }}
QPushButton:hover {{ border-color: {t['kAccent']}; }}
"""
