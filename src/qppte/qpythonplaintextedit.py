import re
from collections import deque
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from threading import Lock
from typing import Callable, NamedTuple, override

from PySide6 import QtCore, QtGui
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QKeyEvent,
    QPalette,
    Qt,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from tree_sitter import Node, QueryCursor

from qppte.action_trigger import DEFAULT_ACTION_TRIGGERS, ActionTrigger
from qppte.line_number_panel import LineNumberPanel
from qppte.qppte_tree_sitter import HIGHLIGHTER_QUERY, PYTHON_PARSER
from qppte.style import DEFAULT_STYLES, TextCharFormat

COMMENT_REGEX = re.compile(r"^(\s*)#\s?")
NO_COMMENT_REGEX = re.compile(r"^(\s*)")
LEADING_SPACE = re.compile(r"""^(\s*).*""")
LINE_NUM_AND_COLUMN_REGEX = re.compile(r"^\s*(\d+)(:(\d+))?\s*$")


class UndoOp(NamedTuple):
    text: str
    cursor_position: int


class SearchField(QLineEdit):
    def __init__(
        self, editor_parent: QPlainTextEdit, hide: Callable[[], None], cc_label_appearance: Callable[[], None]
    ):
        super().__init__()
        self.editor_parent: QPythonPlainTextEdit = editor_parent
        self.hide = hide
        self.setContentsMargins(0, 0, 0, 0)
        self.setMinimumWidth(40 * QFontMetrics(self.font()).horizontalAdvance("9"))

        # place "find" icon on the left side of search text field.
        self.addAction(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.EditFind), QLineEdit.ActionPosition.LeadingPosition)

        self.textChanged.connect(self.doSearch)
        self.starting_offset = -1
        self.last_found_offset = -1
        self.follow_up_offset = -1
        self.follow_down_offset = -1
        self.case_sensitive = True
        self.cc_label_appearance = cc_label_appearance

    @override
    def focusInEvent(self, event: QtGui.QFocusEvent, /) -> None:
        super().focusInEvent(event)
        self.selectAll()

    @override
    def focusOutEvent(self, event: QtGui.QFocusEvent, /) -> None:
        super().focusOutEvent(event)
        self.hide()

    def doSearch(self, _: str) -> None:
        search_string = self.text().strip()
        code = self.editor_parent.toPlainText() if self.case_sensitive else self.editor_parent._lowerCaseCode
        if self.starting_offset == -1:
            self.starting_offset = self.editor_parent.textCursor().position()
        found_offset = code.find(search_string if self.case_sensitive else search_string.lower(), self.starting_offset)
        self.selectFoundText(found_offset, search_string)

    def selectFoundText(self, found_offset: int, search_string: str) -> None:
        if search_string == "":
            return
        palette = self.palette()
        if found_offset >= 0:
            c = self.editor_parent.textCursor()
            c.setPosition(found_offset, QTextCursor.MoveMode.MoveAnchor)
            c.setPosition(found_offset + len(search_string), QTextCursor.MoveMode.KeepAnchor)
            self.editor_parent.setTextCursor(c)
            self.last_found_offset = found_offset
            self.follow_down_offset = found_offset + 1
            self.follow_up_offset = found_offset - 1
            palette.setColor(QPalette.ColorRole.Text, "#000000")
        else:
            palette.setColor(QPalette.ColorRole.Text, "#FF0000")
        self.setPalette(palette)

    def nextDownSearch(self) -> None:
        search_string = self.text().strip()
        code = self.editor_parent.toPlainText() if self.case_sensitive else self.editor_parent._lowerCaseCode
        found_offset = code.find(
            search_string if self.case_sensitive else search_string.lower(), self.follow_down_offset
        )
        self.selectFoundText(found_offset, search_string)

    def nextUpSearch(self) -> None:
        search_string = self.text().strip()
        code = self.editor_parent.toPlainText() if self.case_sensitive else self.editor_parent._lowerCaseCode
        found_offset = code.rfind(
            search_string if self.case_sensitive else search_string.lower(), 0, self.follow_up_offset
        )
        self.selectFoundText(found_offset, search_string)

    def keyPressEvent(self, event: QKeyEvent, /) -> None:
        if event.type() == QtCore.QEvent.Type.KeyPress:
            modifiers = event.modifiers()
            key = event.key()
            if key == QtCore.Qt.Key.Key_Escape:
                self.hide()
                self.editor_parent.setFocus()
                if self.last_found_offset >= 0:
                    c = self.editor_parent.textCursor()
                    c.setPosition(self.last_found_offset, QTextCursor.MoveMode.MoveAnchor)
                    self.editor_parent.setTextCursor(c)
                return
            elif (
                key in (QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Return)
                and modifiers == QtCore.Qt.KeyboardModifier.NoModifier
            ):
                self.nextDownSearch()
                return
            elif key == QtCore.Qt.Key.Key_Down:
                self.nextDownSearch()
            elif key == QtCore.Qt.Key.Key_Up:
                self.nextUpSearch()
            elif key == QtCore.Qt.Key.Key_C and modifiers == QtCore.Qt.KeyboardModifier.AltModifier:
                self.case_sensitive = not self.case_sensitive
                self.cc_label_appearance()
                return
            elif key == QtCore.Qt.Key.Key_F and modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
                self.selectAll()
            elif (
                key in (QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Return)
                and modifiers == QtCore.Qt.KeyboardModifier.ControlModifier
            ):
                self.hide()
                self.editor_parent.setFocus()
                if self.last_found_offset >= 0:
                    c = self.editor_parent.textCursor()
                    c.setPosition(self.last_found_offset, QTextCursor.MoveMode.MoveAnchor)
                    self.editor_parent.setTextCursor(c)
                return

        super().keyPressEvent(event)


class SearchFieldPanel(QWidget):
    def __init__(self, editor_parent: QPlainTextEdit):
        super().__init__()
        layout = QHBoxLayout()
        self.setLayout(layout)
        self.setContentsMargins(0, 0, 0, 0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setVisible(False)

        cc_label = QLabel("Cc")

        self.search_field: SearchField

        def set_cc_label_appearance():
            if self.search_field.case_sensitive:
                cc_label.setStyleSheet("QLabel { background-color: lightblue; }")
            else:
                cc_label.setStyleSheet("QLabel { }")

        self.search_field = SearchField(
            editor_parent, hide=lambda: self.setVisible(False), cc_label_appearance=set_cc_label_appearance
        )
        set_cc_label_appearance()
        layout.addWidget(self.search_field, alignment=Qt.AlignmentFlag.AlignLeft)

        cc_label.setContentsMargins(5, 1, 5, 1)
        cc_label.setToolTip("Match case [Alt+C]")

        def toggle_cc_search(_):
            self.search_field.case_sensitive = not self.search_field.case_sensitive
            set_cc_label_appearance()

        cc_label.mousePressEvent = toggle_cc_search

        layout.addWidget(cc_label, alignment=Qt.AlignmentFlag.AlignLeft)

        up_label = QLabel("↑")
        up_label.setMouseTracking(True)
        up_label.enterEvent = lambda _: up_label.setStyleSheet(
            "QLabel { border: 1px solid gray; background-color: gray; color: white; }"
        )
        up_label.leaveEvent = lambda _: up_label.setStyleSheet("QLabel { border: 1px solid gray; }")
        up_label.mousePressEvent = lambda _: self.search_field.nextUpSearch()
        up_label.setStyleSheet("QLabel { border: 1px solid gray; }")
        up_label.setToolTip("Previous Occurrence")
        layout.addWidget(up_label, alignment=Qt.AlignmentFlag.AlignLeft)
        down_label = QLabel("↓")
        down_label.enterEvent = lambda _: down_label.setStyleSheet(
            "QLabel { border: 1px solid gray; background-color: gray; color: white; }"
        )
        down_label.leaveEvent = lambda _: down_label.setStyleSheet("QLabel { border: 1px solid gray; }")
        down_label.mousePressEvent = lambda s: self.search_field.nextDownSearch()

        down_label.setStyleSheet("QLabel { border: 1px solid gray; }")
        down_label.setToolTip("Next Occurrence")
        layout.addWidget(down_label, alignment=Qt.AlignmentFlag.AlignLeft)

    @override
    def setVisible(self, visible: bool, /) -> None:
        super().setVisible(visible)
        if visible:
            self.search_field.last_found_offset = -1

    def resetSearchOffsets(self, starting_offset: int) -> None:
        self.search_field.starting_offset = starting_offset
        self.search_field.last_found_offset = -1
        self.search_field.follow_up_offset = -1
        self.search_field.follow_down_offset = -1


class QPythonPlainTextEditInfoPanel(QWidget):
    def __init__(self, editor_parent: QPlainTextEdit):
        super().__init__()
        self.search_field_panel = SearchFieldPanel(editor_parent)
        self.line_num_label = QLabel()
        self.setContentsMargins(0, 0, 0, 0)

        def onCursorPositionChanged():
            c = editor_parent.textCursor()
            self.line_num_label.setText(f"{c.block().blockNumber() + 1}:{c.columnNumber() + 1}   ")

        editor_parent.cursorPositionChanged.connect(onCursorPositionChanged)

        layout = QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.search_field_panel, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(QWidget(), stretch=1)
        layout.addWidget(self.line_num_label, alignment=Qt.AlignmentFlag.AlignRight)


class GotoLineDialog(QDialog):
    def __init__(self, parent, initial_text: Callable[[str | None], str]):
        super().__init__(parent)
        self.setWindowTitle("Go to Line:Column")
        text_edit: QPythonPlainTextEdit = parent

        layout = QVBoxLayout()

        topPanel = QWidget()
        topPanelLayout = QHBoxLayout()
        topPanel.setLayout(topPanelLayout)
        topPanelLayout.addWidget(QLabel("[Line] [:Column]"))
        line_num_input = QLineEdit(initial_text(None))
        line_num_input.selectAll()
        topPanelLayout.addWidget(line_num_input)

        layout.addWidget(topPanel)

        buttonPanel = QWidget()
        buttonPanelLayout = QHBoxLayout()
        buttonPanel.setLayout(buttonPanelLayout)
        buttonPanelLayout.addWidget(QLabel(), stretch=1)

        def ok():

            input_text = line_num_input.text()
            match = LINE_NUM_AND_COLUMN_REGEX.match(input_text)
            if match:
                line_num = int(match.group(1)) - 1
                column_text = match.group(3)
                b = text_edit.document().findBlockByLineNumber(min(line_num, text_edit.blockCount() - 1))
                text_edit.setTextCursor(QTextCursor(b))

                if column_text is None:
                    # move to the beginning of the line
                    c = text_edit.textCursor()
                    c.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor)
                    text_edit.setTextCursor(c)
                else:
                    # move to the requested column
                    c = text_edit.textCursor()
                    c.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.MoveAnchor)
                    text_edit.setTextCursor(c)

                    c = text_edit.textCursor()
                    max_column_num = c.columnNumber()
                    if column_text is not None:
                        column = int(column_text) - 1
                        c.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor)
                        c.movePosition(
                            QTextCursor.MoveOperation.NextCharacter,
                            QTextCursor.MoveMode.MoveAnchor,
                            min(column, max_column_num),
                        )
                        text_edit.setTextCursor(c)
                initial_text(input_text)
                self.close()

        ok_button = QPushButton("Ok", autoDefault=True)
        ok_button.clicked.connect(ok)
        buttonPanelLayout.addWidget(ok_button, stretch=1)

        cancel_button = QPushButton("Cancel")
        buttonPanelLayout.addWidget(cancel_button, stretch=1)
        cancel_button.clicked.connect(self.close)
        layout.addWidget(buttonPanel)

        self.setLayout(layout)


@dataclass
class Settings:
    """
    Settings for QPythonPlainTextEdit

    Attributes:
        highlightStyle: Name of a style to be picked from `syntaxHighlightStyles` argument.
        enableLineNumbers: Indicates if we show line numbers in the editor or not.
        enableSyntaxHighlighting: Enable or disable syntax highlighting.
        tabWidthSpaces: When Tab key is pressed it is always converted into a number of space defined by this field.
        fontFamily: font family to be used with this widget.
        fontSizePt: font point size.
    """

    highlightStyle: str
    enableLineNumbers: bool
    enableSyntaxHighlighting: bool
    tabWidthSpaces: int
    fontFamily: str
    fontSizePt: int

    def apply(self, editor: "QPythonPlainTextEdit") -> None:
        editor.setHighlightStyle(self.highlightStyle)
        editor.enableLineNumbers(self.enableLineNumbers)
        editor.setEnableSyntaxHighlighting(self.enableSyntaxHighlighting)
        editor.setTabWidth(self.tabWidthSpaces)
        editor.setFont(QFont(self.fontFamily, self.fontSizePt))

    @staticmethod
    def default() -> "Settings":
        return Settings(
            highlightStyle="Light",
            enableLineNumbers=True,
            enableSyntaxHighlighting=True,
            tabWidthSpaces=4,
            fontFamily="Monospace",
            fontSizePt=12,
        )


class DefaultLastUsedGotoLineText(Callable[[str | None], str]):
    def __init__(self):
        self.last_used_text: str = ""

    def __call__(self, text: str | None) -> str:
        if text is not None:
            self.last_used_text = text
        return self.last_used_text


DEFAULT_LAST_USED_GOTO_LINE_TEXT = DefaultLastUsedGotoLineText()


class QPythonPlainTextEdit(QPlainTextEdit):
    # Emitted whenever the cursor enters a different line
    # Currently handled by LineNumberPanel
    # Note that the new line number (0‑based)
    signalCursorMovedLine = QtCore.Signal(int)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        settings: Settings = Settings.default(),
        syntaxHighlightStyles: dict[str, dict[str, TextCharFormat | str]] | None = None,
        actionTriggers: dict[str, ActionTrigger] | None = None,
        initial_goto_line_text: Callable[[str | None], str] = DEFAULT_LAST_USED_GOTO_LINE_TEXT,
    ):
        """
        QPythonPlainTextEdit constructor. Intended to be used for displaying or editing Python code in place
        of QPLainTextEdit.

        Args:
            parent: QWidget parent class if any
            settings: Settings to be applied to this widget.
            syntaxHighlightStyles: dict containing highlight rules for various highlight styles. If None (default),
                then it is resolved to `qptte.style.DEFAULT_STYLES`.
            actionTriggers: dictionary containing keystroke definitions for all custom actions used in this class.
                If None (default), then `DEFAULT_ACTION_TRIGGERS` is used.
            initial_goto_line_text: Callback used to set and retrieve initial value in `GotoLineDialog`. Default
                is a callback that sets and uses global shared value remembering last used entered text.

        """
        super().__init__(parent)
        self.settings = settings
        self.__line_numbers_enabled = settings.enableLineNumbers
        self.__syntax_highlighting_enabled = settings.enableSyntaxHighlighting
        self.__working = False
        self.__styles = DEFAULT_STYLES if syntaxHighlightStyles is None else syntaxHighlightStyles
        if settings.highlightStyle not in self.__styles:
            raise ValueError(
                f"Highlight style [{settings.highlightStyle}] is not present in the list of available styles"
            )

        self.__tab_width_num_spaces = settings.tabWidthSpaces
        self.__tab_spaces = " " * self.__tab_width_num_spaces

        self.actionTriggers = DEFAULT_ACTION_TRIGGERS if actionTriggers is None else actionTriggers

        self.setAutoFillBackground(True)
        self.__highlightStyle = settings.highlightStyle
        self.__highlightStyleDict = self.__styles[settings.highlightStyle]
        self.__background_color = QColor(self.__highlightStyleDict["QPlainTextEdit_background_color"])
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, self.__background_color)
        palette.setColor(
            QPalette.ColorRole.Text, QColor(self.__highlightStyleDict["QPlainTextEdit_default_foreground_color"])
        )
        self.setPalette(palette)

        self.__line_number_color = QColor(self.__highlightStyleDict["QPlainTextEdit_line_number_color"])
        self.__current_line_background_color = QColor(
            self.__highlightStyleDict["QPlainTextEdit_current_line_background_color"]
        )

        self.__lock = Lock()
        self.__highlight_done_once = False
        self.__signal_connected = False
        self.__undo_queue = deque[UndoOp](maxlen=200)
        self.__redo_queue = deque[UndoOp](maxlen=200)

        self.__initial_goto_line_text = initial_goto_line_text

        self.current_font_horizontal_advance = QFontMetrics(self.font()).horizontalAdvance("9")
        self.__lineNumberPanel = LineNumberPanel(self) if settings.enableLineNumbers else None
        self.__lineNumberPanelConnections = self.__configure_line_numbers_panel() if settings.enableLineNumbers else []
        self._lineNumberPanelWidth = self.__calc_line_number_panel_width()
        self.__last_block_number = -1

        self.setFont(QFont(settings.fontFamily, settings.fontSizePt))
        self.current_font_horizontal_advance = QFontMetrics(self.font()).horizontalAdvance("9")

        self.__info_panel: QPythonPlainTextEditInfoPanel | None = None
        self._lowerCaseCode = self.toPlainText().lower()

        def updateLowerCaseCode():
            self._lowerCaseCode = self.toPlainText().lower()

        self.textChanged.connect(updateLowerCaseCode)
        self.cursorPositionChanged.connect(self.__signal_handler_cursor_position_changed)

    def __configure_line_numbers_panel(self) -> list[QtCore.QMetaObject.Connection]:
        c1 = self.blockCountChanged.connect(self.__signal_handler_block_count_changed)
        c2 = self.updateRequest.connect(self.__signal_handler_update_request)

        self.__signal_handler_block_count_changed(0)
        return [c1, c2]

    def __unconfigure_line_numbers_panel(self) -> None:
        self.blockCountChanged.disconnect(self.__lineNumberPanelConnections[0])
        self.updateRequest.disconnect(self.__lineNumberPanelConnections[1])
        self.__lineNumberPanelConnections.clear()
        self.__lineNumberPanel.setParent(None)
        self.__lineNumberPanel = None
        self.setViewportMargins(0, 0, 0, 0)

    def getCurrentLineBackgroundColor(self) -> QColor:
        """Background color for current line"""
        return self.__current_line_background_color

    def getBackgroundColor(self) -> QColor:
        """Background color for the whole editor"""
        return self.__background_color

    def getLineNumberColor(self) -> QColor:
        """
        If line number column is present (enabled), then this is a color for the vertical line
        that separates line number column from the code.
        """
        return self.__line_number_color

    def getContextManu(self) -> QMenu:
        """Returns context menu. Override this method alter content of the context menu"""
        menu = QMenu(self)
        if not self.isReadOnly():
            menu.addAction(
                "&Undo",
                self.actionTriggers["undo"].getQKeyCombination(),
                lambda: self.keyPressEvent(self.actionTriggers["undo"].getQKeyEvent()),
            ).setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.EditUndo))
            menu.addAction(
                "&Redo",
                self.actionTriggers["redo"].getQKeyCombination(),
                lambda: self.keyPressEvent(self.actionTriggers["redo"].getQKeyEvent()),
            ).setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.EditRedo))
            menu.addSeparator()
            menu.addAction(
                "Cu&t",
                self.actionTriggers["cut"].getQKeyCombination(),
                lambda: self.keyPressEvent(self.actionTriggers["cut"].getQKeyEvent()),
            ).setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.EditCut))

        menu.addAction(
            "&Copy",
            self.actionTriggers["copy"].getQKeyCombination(),
            lambda: self.keyPressEvent(self.actionTriggers["copy"].getQKeyEvent()),
        ).setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.EditCopy))
        if not self.isReadOnly():
            menu.addAction(
                "&Paste",
                self.actionTriggers["paste"].getQKeyCombination(),
                lambda: self.keyPressEvent(self.actionTriggers["paste"].getQKeyEvent()),
            ).setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.EditPaste))
            menu.addSeparator()
        menu.addAction(
            "&Select All",
            self.actionTriggers["select_all"].getQKeyCombination(),
            lambda: self.keyPressEvent(self.actionTriggers["select_all"].getQKeyEvent()),
        ).setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.EditSelectAll))
        return menu

    @override
    def contextMenuEvent(self, event: QtGui.QContextMenuEvent, /) -> None:
        menu = self.getContextManu()
        menu.exec_(self.mapToGlobal(event.pos()))
        del menu

    @override
    def resizeEvent(self, event: QtGui.QResizeEvent, /) -> None:
        super().resizeEvent(event)
        if self.__lineNumberPanel is not None:
            self.__lineNumberPanel.resizeEvent(event)

    def getInfoPanel(self) -> QWidget:
        """
        Returns info panel to be used at the bottom of the larger widget for embedding. Do not override this method.
        """
        if self.__info_panel is None:
            self.__info_panel = QPythonPlainTextEditInfoPanel(self)

        assert self.__info_panel is not None
        return self.__info_panel

    def __calc_line_number_panel_width(self) -> int:
        return (len(str(self.blockCount())) + 3) * self.current_font_horizontal_advance

    def __signal_handler_block_count_changed(self, _: int) -> None:
        self._lineNumberPanelWidth = 0 if self.__lineNumberPanel is None else self.__calc_line_number_panel_width()
        self.setViewportMargins(self._lineNumberPanelWidth, 0, 0, 0)
        if self.__lineNumberPanel is not None:
            self.__lineNumberPanel.update()

    def __signal_handler_update_request(self, _: QtCore.QRect, dy: int) -> None:
        if dy > 0:
            self.__lineNumberPanel.scroll(0, dy)

    def __signal_handler_cursor_position_changed(self) -> None:
        # Highlight the current line
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(self.__current_line_background_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            self.setExtraSelections([selection])

            # repaint line highlight in number line column only if block number actually changed
            current_block_number = self.textCursor().blockNumber()
            if self.__last_block_number != current_block_number:
                self.signalCursorMovedLine.emit(current_block_number)
                self.__last_block_number = current_block_number

    def setTabWidth(self, tabWidthSpaces: int) -> None:
        """
        Tabs are always transformed into spaces when typing. This functions defines into how many spaces it is
        transformed. By default, TAB is converted into 4 empty space characters.
        """
        self.__tab_width_num_spaces = tabWidthSpaces
        self.__tab_spaces = " " * self.__tab_width_num_spaces

    def getTabWidth(self) -> int:
        """Returns number of spaces to be inserted when user presses TAB on the keyboard."""
        return self.__tab_width_num_spaces

    def recordStateForUndoOperation(self) -> None:
        """To be called when extending custom commands."""
        self.__undo_queue.append(UndoOp(self.toPlainText(), self.textCursor().position()))

    @override
    def setFont(self, font: QFont | str | Sequence[str]) -> None:
        super().setFont(font)
        self.current_font_horizontal_advance = QFontMetrics(self.font()).horizontalAdvance("9")
        self._lineNumberPanelWidth = self.__calc_line_number_panel_width()
        self.__signal_handler_block_count_changed(1)

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.isReadOnly():
            super().keyPressEvent(event)
            return

        if event.type() == QtCore.QEvent.Type.KeyPress:
            if self.actionTriggers["select_all"].match(event):
                self.selectAll()
                return

            if self.actionTriggers["cut"].match(event):
                c = self.textCursor()
                self.__undo_queue.append(UndoOp(self.toPlainText(), c.position()))
                if c.hasSelection():
                    QtGui.QGuiApplication.clipboard().setText(c.selectedText())
                    c.removeSelectedText()
                else:
                    c.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor)
                    c.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
                    QtGui.QGuiApplication.clipboard().setText(c.selectedText())
                    c.removeSelectedText()
                    c.deleteChar()
                self.setTextCursor(c)
                return

            if self.actionTriggers["copy"].match(event):
                c = self.textCursor()
                if c.hasSelection():
                    QtGui.QGuiApplication.clipboard().setText(c.selectedText())
                else:
                    c.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor)
                    c.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
                    self.setTextCursor(c)
                    QtGui.QGuiApplication.clipboard().setText(c.selectedText() + "\n")
                return

            if self.actionTriggers["paste"].match(event):
                c = self.textCursor()
                self.__undo_queue.append(UndoOp(self.toPlainText(), c.position()))
                c.insertText(QtGui.QGuiApplication.clipboard().text())
                return

            if self.actionTriggers["unindent"].match(event):
                c = self.textCursor()
                self.__undo_queue.append(UndoOp(self.toPlainText(), c.position()))
                if c.hasSelection():
                    # we will be moving entire block
                    selection_start = c.selectionStart()
                    selection_end = c.selectionEnd()
                    c.setPosition(selection_start)
                    c.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor)
                    superblock_start = c.position()
                    c.setPosition(selection_end, QTextCursor.MoveMode.KeepAnchor)
                    c.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
                    lines = c.selection().toPlainText().splitlines()
                    c.removeSelectedText()

                    end_offset = 0
                    start_offset = -1
                    new_lines = []
                    for line in lines:
                        new_line = line.lstrip()
                        new_num_spaces = len(line) - len(new_line) - self.__tab_width_num_spaces
                        if new_num_spaces > 0:
                            new_line = (" " * new_num_spaces) + new_line
                        if start_offset == -1:
                            start_offset = len(line) - len(new_line)
                        end_offset += len(line) - len(new_line)
                        new_lines.append(new_line)
                    c.insertText("\n".join(new_lines))
                    c = self.textCursor()
                    c.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor)
                    superbloc_end_min_limit = c.position()
                    c.setPosition(
                        max(selection_start - start_offset, superblock_start), QTextCursor.MoveMode.MoveAnchor
                    )
                    c.setPosition(
                        max(selection_end - end_offset, superbloc_end_min_limit), QTextCursor.MoveMode.KeepAnchor
                    )
                    self.setTextCursor(c)
                else:
                    pos = c.position()
                    column = c.columnNumber()
                    c.select(QTextCursor.SelectionType.LineUnderCursor)
                    text = c.selection().toPlainText()
                    m = LEADING_SPACE.match(text)
                    if m:
                        sp = m.group(1)
                        len_sp = len(sp)
                        if len_sp > 0:
                            new_text = (
                                text.lstrip()
                                if len_sp < self.__tab_width_num_spaces
                                else text.removeprefix(self.__tab_spaces)
                            )
                            new_len_sp = len_sp - (len(text) - len(new_text))
                            c.removeSelectedText()
                            c.insertText(new_text)
                            if column <= new_len_sp:
                                c.setPosition(pos)
                            else:
                                if column > len_sp:
                                    c.setPosition(pos - self.__tab_width_num_spaces)
                                else:
                                    c.movePosition(
                                        QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor
                                    )
                                    c.setPosition(c.position() + new_len_sp)
                            self.setTextCursor(c)
                return

            if event.text().isprintable() and event.modifiers() in (
                QtCore.Qt.KeyboardModifier.NoModifier,
                QtCore.Qt.KeyboardModifier.ShiftModifier,
            ):
                self.__redo_queue.clear()
                c = self.textCursor()
                self.__undo_queue.append(UndoOp(self.toPlainText(), c.position()))
                key = event.key()
                if key == QtCore.Qt.Key.Key_QuoteDbl and c.hasSelection():
                    new_text = '"' + c.selectedText() + '"'
                    c.removeSelectedText()
                    c.insertText(new_text)
                    self.setTextCursor(c)
                    return
                if key == QtCore.Qt.Key.Key_Apostrophe and c.hasSelection():
                    new_text = "'" + c.selectedText() + "'"
                    c.removeSelectedText()
                    c.insertText(new_text)
                    self.setTextCursor(c)
                    return
                if key == QtCore.Qt.Key.Key_ParenLeft and c.hasSelection():
                    new_text = "(" + c.selectedText() + ")"
                    c.removeSelectedText()
                    c.insertText(new_text)
                    self.setTextCursor(c)
                    return
                if key == QtCore.Qt.Key.Key_BracketLeft and c.hasSelection():
                    new_text = "[" + c.selectedText() + "]"
                    c.removeSelectedText()
                    c.insertText(new_text)
                    self.setTextCursor(c)
                    return
                if key == QtCore.Qt.Key.Key_BraceLeft and c.hasSelection():
                    new_text = "{" + c.selectedText() + "}"
                    c.removeSelectedText()
                    c.insertText(new_text)
                    self.setTextCursor(c)
                    return

                super().keyPressEvent(event)
                return

            if self.actionTriggers["join_two_lines"].match(event):
                c = self.textCursor()
                c.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor)
                start_block_position = c.position()
                c.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
                saved_position = c.position()
                current_line = c.selection().toPlainText().rstrip() + " "

                c.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor)
                next_line_position = c.position()
                if next_line_position != saved_position:
                    self.__undo_queue.append(UndoOp(self.toPlainText(), c.position()))
                    c.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor)
                    c.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
                    next_line = c.selection().toPlainText().lstrip()
                    end_block_position = c.position()
                    c.setPosition(start_block_position, QTextCursor.MoveMode.MoveAnchor)
                    c.setPosition(end_block_position, QTextCursor.MoveMode.KeepAnchor)
                    c.removeSelectedText()
                    c.insertText(current_line + next_line)
                    self.setTextCursor(c)
                return

            if self.actionTriggers["clear_selection"].match(event):
                c = self.textCursor()
                c.clearSelection()
                self.setTextCursor(c)
                return

            if self.actionTriggers["delete_lines"].match(event):
                c = self.textCursor()
                self.__undo_queue.append(UndoOp(self.toPlainText(), c.position()))
                if c.hasSelection():
                    # delete all lines for this block
                    selection_start = c.selectionStart()
                    selection_end = c.selectionEnd()
                    c.setPosition(selection_start)
                    c.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor)
                    c.setPosition(selection_end, QTextCursor.MoveMode.KeepAnchor)
                    c.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
                else:
                    c.select(QTextCursor.SelectionType.LineUnderCursor)

                c.removeSelectedText()
                c.deleteChar()
                self.setTextCursor(c)
                return

            if self.actionTriggers["goto_line"].match(event):
                GotoLineDialog(self, self.__initial_goto_line_text).exec()
                return

            if self.actionTriggers["indent_block"].match(event):
                c = self.textCursor()
                self.__undo_queue.append(UndoOp(self.toPlainText(), c.position()))
                if c.hasSelection():
                    # we will be moving entire block
                    selection_start = c.selectionStart()
                    selection_end = c.selectionEnd()
                    c.setPosition(selection_start)
                    c.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor)
                    c.setPosition(selection_end, QTextCursor.MoveMode.KeepAnchor)
                    c.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
                    num_lines = len(c.selection().toPlainText().splitlines())
                    c.setPosition(selection_start, QTextCursor.MoveMode.MoveAnchor)
                    c.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor)
                    c.insertText(self.__tab_spaces)
                    for _ in range(num_lines - 1):
                        c.movePosition(QTextCursor.MoveOperation.Down)
                        c.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor)
                        c.insertText(self.__tab_spaces)
                    c.setPosition(selection_start + self.__tab_width_num_spaces, QTextCursor.MoveMode.MoveAnchor)
                    c.setPosition(
                        selection_end + self.__tab_width_num_spaces * num_lines, QTextCursor.MoveMode.KeepAnchor
                    )
                    self.setTextCursor(c)
                else:
                    pos = c.position()
                    column = c.columnNumber()
                    c.select(QTextCursor.SelectionType.LineUnderCursor)
                    text = c.selection().toPlainText()
                    m = LEADING_SPACE.match(text)
                    if m:
                        leading_space = m.group(1)
                        if column <= len(leading_space):
                            new_line = self.__tab_spaces + text
                            c.removeSelectedText()
                            c.insertText(new_line)
                        else:
                            c.setPosition(pos, QTextCursor.MoveMode.MoveAnchor)
                            c.insertText(self.__tab_spaces)
                        c.setPosition(pos + self.__tab_width_num_spaces)
                        self.setTextCursor(c)

                return

            if self.actionTriggers["backspace"].match(event):
                c = self.textCursor()
                if c.hasSelection():
                    super().keyPressEvent(event)
                    return
                self.__undo_queue.append(UndoOp(self.toPlainText(), c.position()))
                column = c.columnNumber()
                c.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.KeepAnchor)
                selected_text = c.selectedText()
                if selected_text.strip() == "":
                    # cursor is placed in the leading whitespace
                    spaces_to_remove = column % self.__tab_width_num_spaces
                    if spaces_to_remove > 0:
                        c.removeSelectedText()
                        c.insertText(self.__tab_spaces * int(column / self.__tab_width_num_spaces))
                        self.setTextCursor(c)
                    elif selected_text != "":
                        c.removeSelectedText()
                        c.insertText(self.__tab_spaces * int(column / self.__tab_width_num_spaces - 1))
                    else:
                        super().keyPressEvent(event)
                else:
                    super().keyPressEvent(event)
                return

            if self.actionTriggers["new_line_enter"].match(event) or self.actionTriggers["new_line_return"].match(
                event
            ):
                # pressing Enter or Return
                c = self.textCursor()
                self.__undo_queue.append(UndoOp(self.toPlainText(), c.position()))
                column = c.columnNumber()
                c.select(QTextCursor.SelectionType.LineUnderCursor)
                text = c.selectedText()
                m = LEADING_SPACE.match(text)
                if m:
                    sp = m.group(1)
                    if len(sp) <= column:
                        super().keyPressEvent(event)
                        self.textCursor().insertText("    " * int(len(sp) / 4))
                        return

                c = self.textCursor()
                pos = c.position()
                c.movePosition(QTextCursor.MoveOperation.StartOfLine)
                self.setTextCursor(c)
                super().keyPressEvent(event)
                c = self.textCursor()
                c.setPosition(pos + 1)
                self.setTextCursor(c)
                return

            if self.actionTriggers["move_line_up"].match(event):
                c = self.textCursor()
                self.__undo_queue.append(UndoOp(self.toPlainText(), c.position()))
                at_column = c.columnNumber()
                c.select(QTextCursor.SelectionType.LineUnderCursor)
                line_to_move = c.selection().toPlainText()
                c.removeSelectedText()
                c.deleteChar()
                c.movePosition(QTextCursor.MoveOperation.Up)
                c.movePosition(QTextCursor.MoveOperation.StartOfLine)
                c.insertText(line_to_move + "\n")
                c.movePosition(QTextCursor.MoveOperation.Up)
                c.movePosition(QTextCursor.MoveOperation.StartOfLine)
                c.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, at_column)
                self.setTextCursor(c)
                return

            if self.actionTriggers["move_line_down"].match(event):
                c = self.textCursor()
                self.__undo_queue.append(UndoOp(self.toPlainText(), c.position()))
                at_column = c.columnNumber()
                c.select(QTextCursor.SelectionType.LineUnderCursor)
                line_to_move = c.selection().toPlainText()
                c.removeSelectedText()
                c.deleteChar()
                c.movePosition(QTextCursor.MoveOperation.Down)
                c.movePosition(QTextCursor.MoveOperation.StartOfLine)
                c.insertText(line_to_move + "\n")
                c.movePosition(QTextCursor.MoveOperation.Up)
                c.movePosition(QTextCursor.MoveOperation.StartOfLine)
                c.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, at_column)
                self.setTextCursor(c)
                return

            if self.actionTriggers["duplicate_line"].match(event):
                c = self.textCursor()
                self.__undo_queue.append(UndoOp(self.toPlainText(), c.position()))
                at_column = c.columnNumber()
                c.select(QTextCursor.SelectionType.LineUnderCursor)
                line_str = c.selection().toPlainText()
                c.movePosition(QTextCursor.MoveOperation.EndOfLine)
                c.insertText(f"\n{line_str}")
                c.movePosition(QTextCursor.MoveOperation.StartOfLine)
                c.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, at_column)
                self.setTextCursor(c)
                return

            if self.actionTriggers["toggle_comment_block"].match(event):
                # (Un)Comment line or a selection of lines on Ctrl-/
                c = self.textCursor()
                self.__undo_queue.append(UndoOp(self.toPlainText(), c.position()))
                one_line_comment = False
                if not c.hasSelection():
                    c.select(QTextCursor.SelectionType.LineUnderCursor)
                    one_line_comment = True

                selection_start = c.selectionStart()
                selection_end = c.selectionEnd()

                c.setPosition(selection_start)
                c.movePosition(QTextCursor.MoveOperation.StartOfLine)
                start_position = c.position()
                c.setPosition(selection_end)
                c.movePosition(QTextCursor.MoveOperation.EndOfLine)
                end_position = c.position()
                c.setPosition(start_position)
                c.setPosition(end_position, QTextCursor.MoveMode.KeepAnchor)

                lines: list[str] = c.selectedText().splitlines()
                new_lines = []
                for line in lines:
                    comment_match = COMMENT_REGEX.match(line)
                    if comment_match:
                        new_lines.append(re.sub(COMMENT_REGEX, r"\1", line))
                    else:
                        new_lines.append(re.sub(NO_COMMENT_REGEX, r"\1# ", line))

                new_text_block = "\n".join(new_lines)
                c.beginEditBlock()
                c.removeSelectedText()
                c.insertText(new_text_block)
                c.endEditBlock()

                if one_line_comment:
                    c.movePosition(QTextCursor.MoveOperation.Down)
                else:
                    # try to keep selection; it will be distorted a bit most of the time though
                    c.setPosition(start_position)
                    c.setPosition(
                        min(start_position + len(new_text_block), self.document().characterCount() - 1),
                        QTextCursor.MoveMode.KeepAnchor,
                    )

                self.setTextCursor(c)
                return

            if self.actionTriggers["search"].match(event):
                self.startSearch()
                return

            if self.actionTriggers["undo"].match(event):
                with suppress(IndexError):
                    op: UndoOp = self.__undo_queue.pop()
                    self.__redo_queue.append(UndoOp(self.toPlainText(), self.textCursor().position()))
                    self.clear()
                    self.setPlainText(op.text)
                    c = self.textCursor()
                    c.setPosition(op.cursor_position)
                    self.setTextCursor(c)
                    return

            if self.actionTriggers["redo"].match(event):
                with suppress(IndexError):
                    self.__undo_queue.append(UndoOp(self.toPlainText(), self.textCursor().position()))
                    op: UndoOp = self.__redo_queue.pop()
                    self.__undo_queue.append(op)
                    self.clear()
                    self.setPlainText(op.text)
                    c = self.textCursor()
                    c.setPosition(op.cursor_position)
                    self.setTextCursor(c)
                    return

            if event.text() != "":
                self.__undo_queue.append(UndoOp(self.toPlainText(), self.textCursor().position()))

        super().keyPressEvent(event)

    def __highlight(self) -> None:
        if not self.__syntax_highlighting_enabled:
            return

        cursor: QTextCursor = self.textCursor()

        text = self.toPlainText()
        lines = text.splitlines()

        input_text = text.encode()
        tree = PYTHON_PARSER.parse(input_text)
        query_cursor = QueryCursor(HIGHLIGHTER_QUERY)

        matches: list[tuple[int, dict[str, list[Node]]]] = query_cursor.matches(tree.root_node)
        matches.sort(key=lambda m: m[0])
        for _, m in matches:
            for capture_name, nodes in m.items():
                for node in nodes:
                    cursor.setPosition(
                        sum([len(line) for line in lines[0 : node.start_point.row]])
                        + node.start_point.column
                        + node.start_point.row
                    )
                    cursor.setPosition(
                        sum([len(line1) for line1 in lines[0 : node.end_point.row]])
                        + node.end_point.column
                        + node.end_point.row,
                        QTextCursor.MoveMode.KeepAnchor,
                    )
                    cursor.setCharFormat(self.__highlightStyleDict[capture_name])

        self.__highlight_done_once = True

    def __rehighlight(self):
        with self.__lock:
            if self.__working:
                return
            else:
                self.__working = True

        try:
            if self.isReadOnly() and self.__highlight_done_once:
                return

            # clear all formatting first
            cursor: QTextCursor = self.textCursor()
            cursor.setPosition(0)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
            cursor.setCharFormat(QTextCharFormat())

            self.__highlight()
            self.__highlight_done_once = True
        finally:
            self.__working = False

    @override
    def setPlainText(self, text: str, /) -> None:
        self.__highlight_done_once = False
        super().setPlainText(text)
        self.__rehighlight()
        if not self.__signal_connected:
            self.textChanged.connect(self.__rehighlight)
            self.__signal_connected = True

    def startSearch(self):
        """Programmatically trigger appearing search field into the info panel."""
        if self.__info_panel is not None:
            self.__info_panel.search_field_panel.resetSearchOffsets(self.textCursor().position())
            self.__info_panel.search_field_panel.setVisible(True)
            self.__info_panel.search_field_panel.search_field.setFocus()

    def setHighlightStyle(self, highlightStyle: str) -> None:
        """
        Sets new highlight style. This will trigger re-rendering of text if new style is different from currently
        selected. Note that this is a NO-OP if syntax highlighting is disabled.
        """
        if self.__highlightStyle != highlightStyle:
            saved_position = self.textCursor().position()
            self.__highlightStyle = highlightStyle
            self.__highlightStyleDict = self.__styles[highlightStyle]
            self.__background_color = QColor(self.__highlightStyleDict["QPlainTextEdit_background_color"])
            palette = self.palette()
            palette.setColor(QPalette.ColorRole.Base, self.__background_color)
            palette.setColor(
                QPalette.ColorRole.Text,
                QColor(self.__highlightStyleDict["QPlainTextEdit_default_foreground_color"]),
            )
            self.setPalette(palette)

            self.__line_number_color = QColor(self.__highlightStyleDict["QPlainTextEdit_line_number_color"])
            self.__current_line_background_color = QColor(
                self.__highlightStyleDict["QPlainTextEdit_current_line_background_color"]
            )
            self.setPlainText(self.toPlainText())
            cursor = self.textCursor()
            cursor.setPosition(saved_position)
            self.setTextCursor(cursor)

    def getHighlightStyle(self) -> str:
        """Returns highlight style currently in use"""
        return self.__highlightStyle

    def setEnableSyntaxHighlighting(self, enableSyntaxHighlighting: bool) -> None:
        """
        Following will trigger clearing of existing highlighting style and application of new style if any.
        Note that if you are disabling syntax highlighting and previous style affected background color,
        then this operation will not affect background color.
        """
        if self.__syntax_highlighting_enabled != enableSyntaxHighlighting:
            self.__syntax_highlighting_enabled = enableSyntaxHighlighting
            self.setPlainText(self.toPlainText())

    def enableLineNumbers(self, enableLineNumbers: bool) -> None:
        """Enables or disables presence of line number column in the left edge of the editor."""
        if enableLineNumbers != self.__line_numbers_enabled:
            if enableLineNumbers:
                self.__line_numbers_enabled = True
                self.__lineNumberPanel = LineNumberPanel(self)
                self.__lineNumberPanelConnections = self.__configure_line_numbers_panel()
                self.__lineNumberPanel.show()
            else:
                self.__line_numbers_enabled = False
                self.__unconfigure_line_numbers_panel()

    def lineNumbersEnabled(self) -> bool:
        """Returns true if line numbers column is enabled, false otherwise"""
        return self.__line_numbers_enabled

    def listAvailableHighlightStyles(self) -> list[str]:
        """
        Returns list of available highlight styles that can be used with this instance of QPythonPlainTextEdit class.
        """
        return list(self.__styles.keys())
