from typing import Callable

from PySide6.QtCore import Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from qppte.qpythonplaintextedit import QPythonPlainTextEdit, Settings
from qppte.style import DEFAULT_STYLES_PROVIDER, TextCharFormat


class QPythonPlainTextSettings(QWidget):
    settings_changed = Signal(Settings)
    ok_called = Signal()
    cancel_called = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        /,
        settings: Settings | None = None,
        syntaxHighlightStyles: Callable[[], dict[str, dict[str, TextCharFormat | str]]] = DEFAULT_STYLES_PROVIDER,
    ) -> None:
        super().__init__(parent)
        if settings is None:
            raise ValueError("settings cannot be None")
        self.settings = settings
        self.syntaxHighlightStyles = syntaxHighlightStyles
        layout = QVBoxLayout()
        self.setLayout(layout)

        def mkRow(*widget: QWidget) -> QWidget:
            row = QWidget()
            row.setContentsMargins(0, 0, 0, 0)
            layout = QHBoxLayout()
            row.setLayout(layout)
            for w in widget:
                layout.addWidget(w)
            layout.addWidget(QLabel(""), stretch=1)
            return row

        styles_selector = QComboBox()
        styles_selector.addItems(list(syntaxHighlightStyles().keys()))
        styles_selector.setCurrentText(settings.highlightStyle)
        layout.addWidget(mkRow(QLabel("Highlight Style:"), styles_selector))

        enable_syntax_highlighting_cb = QCheckBox("Enable Syntax Highlighting")
        enable_syntax_highlighting_cb.setChecked(settings.enableSyntaxHighlighting)
        layout.addWidget(mkRow(enable_syntax_highlighting_cb))

        show_line_numbers_cb = QCheckBox("Show Line Numbers")
        show_line_numbers_cb.setChecked(settings.enableLineNumbers)
        layout.addWidget(mkRow(show_line_numbers_cb))

        tab_width_spaces_selector = QSpinBox()
        tab_width_spaces_selector.setMinimumWidth(50)
        tab_width_spaces_selector.setRange(min(1, settings.tabWidthSpaces), max(8, settings.tabWidthSpaces))
        tab_width_spaces_selector.setValue(settings.tabWidthSpaces)
        layout.addWidget(mkRow(QLabel("Tab Width Spaces:"), tab_width_spaces_selector))

        font_styles_selector = QComboBox()
        fixed_font_families = [f for f in (QFontDatabase.families()) if QFontDatabase.isFixedPitch(f)]
        font_styles_selector.addItems(fixed_font_families)
        font_styles_selector.setCurrentText(settings.fontFamily)
        font_size_selector = QSpinBox()
        font_size_selector.setMinimumWidth(50)
        font_size_selector.setRange(min(7, settings.fontSizePt), max(42, settings.fontSizePt))
        font_size_selector.setValue(settings.fontSizePt)
        layout.addWidget(mkRow(QLabel("Font Style:"), font_styles_selector, QLabel(" Size:"), font_size_selector))

        layout.addWidget(QWidget(), stretch=1)

        row = QWidget()
        row.setContentsMargins(0, 0, 0, 0)
        row.setLayout(QHBoxLayout())
        row.layout().addWidget(QLabel(""), stretch=1)
        ok_button = QPushButton("Ok")

        def ok():
            new_settings = Settings(
                highlightStyle=styles_selector.currentText(),
                enableLineNumbers=show_line_numbers_cb.isChecked(),
                enableSyntaxHighlighting=enable_syntax_highlighting_cb.isChecked(),
                tabWidthSpaces=tab_width_spaces_selector.value(),
                fontFamily=font_styles_selector.currentText(),
                fontSizePt=font_size_selector.value(),
            )
            if settings != new_settings:
                # setting have changed; mutate them in place and emit settings_changed signal
                settings.highlightStyle = new_settings.highlightStyle
                settings.enableLineNumbers = new_settings.enableLineNumbers
                settings.enableSyntaxHighlighting = new_settings.enableSyntaxHighlighting
                settings.tabWidthSpaces = new_settings.tabWidthSpaces
                settings.fontFamily = new_settings.fontFamily
                settings.fontSizePt = new_settings.fontSizePt
                self.settings_changed.emit(settings)
            self.ok_called.emit()

        ok_button.clicked.connect(ok)
        row.layout().addWidget(ok_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(lambda: self.cancel_called.emit())
        row.layout().addWidget(cancel_button)

        layout.addWidget(row)


class QPythonPlainTextSettingsDialog(QDialog):
    def __init__(self, parent, /, settings: Settings, editor: QPythonPlainTextEdit | None = None):
        super().__init__(parent)
        self.setWindowTitle("Editor Settings")
        self.setModal(True)
        layout = QVBoxLayout()
        self.setLayout(layout)
        settings_panel = QPythonPlainTextSettings(self, settings)
        layout.addWidget(settings_panel)
        settings_panel.cancel_called.connect(self.close)
        settings_panel.ok_called.connect(self.close)
        self.editor = editor
        settings_panel.settings_changed.connect(self.settingsChanged)

    def settingsChanged(self, new_settings: Settings) -> None:
        """Override this method to be notified where settings change."""
        if self.editor is not None:
            new_settings.apply(self.editor)
