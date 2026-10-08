from typing import Callable

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics
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
    """ Called when `Ok` button is clicked and settings did change. """

    ok_called = Signal()
    """ Called when `Ok` button is clicked. """

    cancel_called = Signal()
    """ Called when `Cancel` button is clicked. """

    def __init__(
        self,
        parent: QWidget | None = None,
        settings: Settings | None = None,
        syntaxHighlightStyles: Callable[[], dict[str, dict[str, TextCharFormat | str]]] = DEFAULT_STYLES_PROVIDER,
        displayButtons: bool = True,
    ) -> None:
        """
        Default settings dialog for QPythonPlainTextEdit. It picks up available settings from `settings` argument
        and updates it when user clicks on `Ok` button and new settings are different from originally provided.

        Args:
            parent: parent QObject
            settings: settings object which is to be used by this widget
            syntaxHighlightStyles: all highlight styles; used to display drop down box with available styles.
            displayButtons: to display Ok and Cancel buttons or not. If False, then you can access these buttons
                by calling `.ok_button()` and `.cancel_button()` to place them elsewhere in your application.
        """
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
        font_row = mkRow(QLabel("Font Style:"), font_styles_selector, QLabel(" Size:"), font_size_selector)
        layout.addWidget(font_row)

        sample_text_edit = QPythonPlainTextEdit(
            self,
            readOnly=True,
            settings=settings,
            syntaxHighlightStyles=syntaxHighlightStyles(),
            text="""class A:
    def __init__(self):
        self.x = 1 # initializing x to 1
    
    def __repr__(self, /) -> str:
        \"\"\" String representation of class A \"\"\"
        return f"Instance of A({self.a})\"""",
        )
        sample_text_edit.setMinimumHeight(10 * QFontMetrics(self.font()).height())
        sample_text_edit.setMinimumWidth(65 * QFontMetrics(self.font()).horizontalAdvance("9"))
        layout.addWidget(sample_text_edit)

        def update_sample_font():
            sample_text_edit.setFont(QFont(font_styles_selector.currentText(), font_size_selector.value()))

        font_styles_selector.currentTextChanged.connect(update_sample_font)
        font_size_selector.valueChanged.connect(update_sample_font)
        styles_selector.currentTextChanged.connect(sample_text_edit.setHighlightStyle)
        enable_syntax_highlighting_cb.toggled.connect(sample_text_edit.setEnableSyntaxHighlighting)
        show_line_numbers_cb.toggled.connect(sample_text_edit.enableLineNumbers)

        layout.addWidget(QWidget(), stretch=1)

        self.__ok_button = QPushButton("Ok")

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

        self.__ok_button.clicked.connect(ok)
        self.__cancel_button = QPushButton("Cancel")
        self.__cancel_button.clicked.connect(lambda: self.cancel_called.emit())

        if displayButtons:
            row = QWidget()
            row.setContentsMargins(0, 0, 0, 0)
            row.setLayout(QHBoxLayout())
            row.layout().addWidget(QLabel(""), stretch=1)
            row.layout().addWidget(self.__ok_button)
            row.layout().addWidget(self.__cancel_button)

            layout.addWidget(row)

    def ok_button(self) -> QPushButton:
        """
        Access `Ok` button created for this QPythonPlainTextSettings object.
        You do that if displayButtons=False. In this case Ok and Cancel buttons are still created but are not placed
        inside this widget. You can then access them by calling this function and place them within some other
        context.
        """
        return self.__ok_button

    def cancel_button(self) -> QPushButton:
        """
        Access `Cancel` button created for this QPythonPlainTextSettings object.
        You do that if displayButtons=False. In this case Ok and Cancel buttons are still created but are not placed
        inside this widget. You can then access them by calling this function and place them within some other
        context.
        """
        return self.__cancel_button


class QPythonPlainTextSettingsDialog(QDialog):
    def __init__(
        self,
        parent,
        /,
        settings: Settings,
        editor: QPythonPlainTextEdit | None = None,
        syntaxHighlightStyles: dict[str, dict[str, TextCharFormat | str]] | None = None,
    ):
        """
        Standalone settings dialog widget to be used when you do not need any customization within you application.

        Args:
            parent: parent QObject
            settings: linked settings object; it will be updated when user clicks Ok button.
            editor: optional linked editor. If not Null then when user clicks Ok, new settings are applied to it.
            syntaxHighlightStyles: dict containing highlight rules for various highlight styles. If None (default),
                then it is resolved to `qptte.style.DEFAULT_STYLES`.
        """
        super().__init__(parent)
        self.setWindowTitle("Editor Settings")
        self.setModal(True)
        layout = QVBoxLayout()
        self.setLayout(layout)
        settings_panel = QPythonPlainTextSettings(
            self,
            settings,
            syntaxHighlightStyles=DEFAULT_STYLES_PROVIDER
            if syntaxHighlightStyles is None
            else (lambda: syntaxHighlightStyles),
        )
        layout.addWidget(settings_panel)
        settings_panel.cancel_called.connect(self.close)
        settings_panel.ok_called.connect(self.close)
        self.editor = editor
        settings_panel.settings_changed.connect(self.settingsChanged)

    def settingsChanged(self, new_settings: Settings) -> None:
        """Override this method to be notified where settings change."""
        if self.editor is not None:
            new_settings.apply(self.editor)
