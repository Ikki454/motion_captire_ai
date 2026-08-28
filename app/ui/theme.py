"""Dark visual theme for the desktop UI.

A single Qt style sheet plus a helper to apply it. Keeping the theme in
one module means the widgets stay free of styling code and the look can
be changed in one place.
"""

from PySide6.QtWidgets import QApplication, QWidget

# Palette (kept here so the values are named once).
_BACKGROUND = "#1e1e1e"
_SURFACE = "#252526"
_SURFACE_RAISED = "#2d2d30"
_BORDER = "#3a3a3a"
_BORDER_STRONG = "#4a4a4a"
_TEXT = "#d4d4d4"
_TEXT_MUTED = "#9a9a9a"
_TEXT_DISABLED = "#6a6a6a"
_ACCENT = "#4d9fff"
_ACCENT_PRESSED = "#3d7fd0"
_ACCENT_INK = "#10233d"
_DONE = "#3fb950"
_DONE_INK = "#0c2912"

DARK_STYLESHEET = f"""
QMainWindow, QDialog {{ background-color: {_BACKGROUND}; }}
QWidget {{ color: {_TEXT}; font-size: 13px; }}
QAbstractScrollArea {{ background-color: {_BACKGROUND}; border: none; }}
/* the widget a QScrollArea scrolls must not paint its own light background */
QScrollArea > QWidget > QWidget {{ background: transparent; }}

QLabel {{ background: transparent; }}
QLabel#appHint {{ color: {_TEXT_MUTED}; }}
QLabel#videoInfo {{ color: {_TEXT_MUTED}; }}

QPushButton {{
    background-color: {_SURFACE_RAISED};
    border: 1px solid {_BORDER_STRONG};
    border-radius: 5px;
    padding: 5px 12px;
}}
QPushButton:hover {{ border-color: {_ACCENT}; }}
QPushButton:pressed {{ background-color: {_BORDER}; }}
QPushButton:checked {{
    background-color: {_ACCENT};
    border-color: {_ACCENT};
    color: {_ACCENT_INK};
}}
QPushButton:disabled {{
    color: {_TEXT_DISABLED};
    border-color: {_BORDER};
    background-color: {_SURFACE};
}}

QComboBox, QSpinBox {{
    background-color: {_SURFACE_RAISED};
    border: 1px solid {_BORDER_STRONG};
    border-radius: 5px;
    padding: 4px 8px;
}}
QComboBox:hover, QSpinBox:hover {{ border-color: {_ACCENT}; }}
QComboBox:disabled, QSpinBox:disabled {{ color: {_TEXT_DISABLED}; }}
QComboBox QAbstractItemView {{
    background-color: {_SURFACE_RAISED};
    border: 1px solid {_BORDER_STRONG};
    selection-background-color: {_ACCENT};
    selection-color: {_ACCENT_INK};
}}

QCheckBox {{ spacing: 6px; background: transparent; }}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {_BORDER_STRONG};
    border-radius: 3px;
    background-color: {_SURFACE_RAISED};
}}
QCheckBox::indicator:checked {{
    background-color: {_ACCENT};
    border-color: {_ACCENT};
}}
QCheckBox:disabled {{ color: {_TEXT_DISABLED}; }}

QProgressBar {{
    background-color: {_SURFACE_RAISED};
    border: 1px solid {_BORDER};
    border-radius: 5px;
    text-align: center;
    color: {_TEXT};
}}
QProgressBar::chunk {{ background-color: {_ACCENT}; border-radius: 4px; }}

QSlider::groove:horizontal {{
    height: 4px;
    background: {_BORDER};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{ background: {_ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {_TEXT};
    width: 12px;
    margin: -5px 0;
    border-radius: 6px;
}}
QSlider::handle:horizontal:hover {{ background: {_ACCENT}; }}
QSlider:disabled {{ }}
QSlider::sub-page:horizontal:disabled {{ background: {_BORDER_STRONG}; }}
QSlider::handle:horizontal:disabled {{ background: {_BORDER_STRONG}; }}

QScrollBar:vertical {{ background: {_BACKGROUND}; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{
    background: {_BORDER_STRONG};
    border-radius: 6px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {_TEXT_MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

QMenuBar {{ background-color: {_BACKGROUND}; }}
QMenuBar::item:selected {{ background-color: {_SURFACE_RAISED}; }}
QMenu {{ background-color: {_SURFACE_RAISED}; border: 1px solid {_BORDER_STRONG}; }}
QMenu::item:selected {{ background-color: {_ACCENT}; color: {_ACCENT_INK}; }}
QMenu::item:disabled {{ color: {_TEXT_DISABLED}; }}

QStatusBar {{ background-color: {_SURFACE}; color: {_TEXT_MUTED}; }}
QStatusBar::item {{ border: none; }}

QToolTip {{
    background-color: {_SURFACE_RAISED};
    color: {_TEXT};
    border: 1px solid {_BORDER_STRONG};
}}

QSplitter::handle {{ background-color: {_BORDER}; }}
QSplitter::handle:horizontal {{ width: 4px; }}
QSplitter::handle:hover {{ background-color: {_ACCENT}; }}

PipelineSection {{
    background-color: {_SURFACE};
    border: 1px solid {_BORDER};
    border-radius: 8px;
}}
PipelineSection[state="active"] {{ border-color: {_ACCENT}; }}

QLabel#sectionBadge {{
    background-color: {_BORDER_STRONG};
    color: {_TEXT};
    border-radius: 10px;
    font-weight: bold;
}}
QLabel#sectionTitle {{ font-weight: bold; }}
QLabel#sectionHint {{ color: {_ACCENT}; font-weight: bold; }}
PipelineSection[state="active"] QLabel#sectionBadge {{
    background-color: {_ACCENT};
    color: {_ACCENT_INK};
}}
PipelineSection[state="done"] QLabel#sectionBadge {{
    background-color: {_DONE};
    color: {_DONE_INK};
}}
"""


def apply_dark_theme(target: QWidget | QApplication) -> None:
    """Apply the dark style sheet to a widget tree or the whole application."""

    target.setStyleSheet(DARK_STYLESHEET)
