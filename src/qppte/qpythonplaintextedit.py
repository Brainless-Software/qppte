import re
from collections import deque
from collections.abc import Sequence
from contextlib import suppress
from functools import cache, reduce
from threading import Lock
from typing import NamedTuple, override

import tree_sitter_python
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
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget
from tree_sitter import Language, Node, Parser, Query, QueryCursor

from qppte.line_number_panel import LineNumberPanel
from qppte.style import DEFAULT_STYLES, TextCharFormat

PY_LANGUAGE = Language(tree_sitter_python.language())
PYTHON_PARSER = Parser(PY_LANGUAGE)
HIGHLIGHTER_QUERY = Query(
    PY_LANGUAGE,
    """
        (function_definition
          name: (identifier) @function_definition)

        (function_definition (identifier) @special_function (#any-of? @special_function 
                                                                        "__init__" "__new__" "__setattr__" 
                                                                        "__delattr__" "__eq__" "__ne__" 
                                                                        "__str__" "__hash__" "__format__" 
                                                                        "__getattribute__" "__sizeof__" "__dir__" 
                                                                        "__repr__"))
        ("." (identifier) @special_function (#any-of? @special_function 
                                                        "__init__" "__new__" "__setattr__" "__delattr__" "__eq__" 
                                                        "__ne__" "__str__" "__hash__" "__format__" "__getattribute__" 
                                                        "__sizeof__" "__dir__" "__repr__"))

        (type) @type

        (class_definition
          name: (identifier) @class_definition_name)

        (call (identifier) @function_call)
        (decorator "@" (identifier)) @decorator 
        (decorator "@" (call (identifier) @decorator))  
        (decorator ("@" @decorator))

        (string_start) @string
        (string_content) @string
        (string_end) @string

        ["def" "return" "if" "else" "class" "assert" "async" "await" "break" "continue" "del" "elif" 
         "else" "except" "finally" "for" "global" "lambda" "pass" "raise" "nonlocal" "return" "try" 
         "while" "yield" "as" "with" "import" "from" "match" "case" "in"] @keyword

        (true) @keyword
        (false) @keyword

        (integer) @number
        (float) @number

        (keyword_argument (identifier) @keyword_argument) 

        ((identifier) @self (#eq? @self "self"))

        (comment) @line_comment
    """,
)

COMMENT_REGEX = re.compile(r"^(\s*)#\s?")
NO_COMMENT_REGEX = re.compile(r"^(\s*)")
LEADING_SPACE = re.compile(r"""^(\s*).*""")


class ActionTrigger(NamedTuple):
    keys: tuple[int]
    modifiers: tuple[int]

    @cache
    def get_modifiers(self) -> int:
        return reduce(lambda acc, m: acc | m, self.modifiers, QtCore.Qt.KeyboardModifier.NoModifier)

    def match(self, event: QKeyEvent) -> bool:
        if event.key() in self.keys and (self.modifiers == [] or self.get_modifiers() == event.modifiers()):
            return True
        else:
            return False


class UndoOp(NamedTuple):
    text: str
    cursor_position: int


DEFAULT_ACTION_TRIGGERS: dict[str, ActionTrigger] = {
    "indent_block": ActionTrigger((Qt.Key.Key_Tab,), tuple()),
    "clear_selection": ActionTrigger((Qt.Key.Key_Escape,), tuple()),
    "backspace": ActionTrigger((Qt.Key.Key_Backspace,), tuple()),
    "new_line": ActionTrigger(
        (
            Qt.Key.Key_Enter,
            Qt.Key.Key_Return,
        ),
        tuple(),
    ),
    "undo": ActionTrigger((Qt.Key.Key_Z,), (QtCore.Qt.KeyboardModifier.ControlModifier,)),
    "redo": ActionTrigger((Qt.Key.Key_R,), (QtCore.Qt.KeyboardModifier.ControlModifier,)),
    "unindent": ActionTrigger((Qt.Key.Key_Backtab,), (QtCore.Qt.KeyboardModifier.ShiftModifier,)),
    "delete_lines": ActionTrigger((Qt.Key.Key_Y,), (QtCore.Qt.KeyboardModifier.ControlModifier,)),
    "move_line_up": ActionTrigger(
        (Qt.Key.Key_Up,), (QtCore.Qt.KeyboardModifier.ControlModifier, QtCore.Qt.KeyboardModifier.ShiftModifier)
    ),
    "move_line_down": ActionTrigger(
        (Qt.Key.Key_Down,), (QtCore.Qt.KeyboardModifier.ControlModifier, QtCore.Qt.KeyboardModifier.ShiftModifier)
    ),
    "duplicate_line": ActionTrigger((Qt.Key.Key_D,), (QtCore.Qt.KeyboardModifier.ControlModifier,)),
    "toggle_comment_block": ActionTrigger((Qt.Key.Key_Slash,), (QtCore.Qt.KeyboardModifier.ControlModifier,)),
    "increase_font_size": ActionTrigger(
        (Qt.Key.Key_Plus,), (QtCore.Qt.KeyboardModifier.ControlModifier, QtCore.Qt.KeyboardModifier.ShiftModifier)
    ),
    "decrease_font_size": ActionTrigger(
        (Qt.Key.Key_Underscore,), (QtCore.Qt.KeyboardModifier.ControlModifier, QtCore.Qt.KeyboardModifier.ShiftModifier)
    ),
}


class QPythonPlainTextEdit(QPlainTextEdit):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        highlightStyle: str = "default",
        enableLineNumbers: bool = False,
        enableSyntaxHighlighting: bool = True,
        syntaxHighlightStyles: dict[str, dict[str, TextCharFormat | str]] | None = None,
        tabWidthSpaces: int = 4,
        actionTriggers: dict[str, ActionTrigger] | None = None,
        font: QFont = QFont("Monospace"),
    ):
        """
        QPythonPlainTextEdit constructor. Intented to be used is for displaying or edit Python code in place
        of QPLainTextEdit.

        :param parent: QWidget parent class if any
        :param highlightStyle: Name of a style to be picked by from `syntaxHighlightStyles`. Default is `default`.
        :param enableLineNumbers: Indicates if we show line numbers in the editor or not. Default is `False`.
        :param enableSyntaxHighlighting: Enable or disable syntax highlighting. Default is True.11
        :param syntaxHighlightStyles: dict containing highlight rules for various highlight styles. If None (default),
            then it is resolved to `qptte.style.DEFAULT_STYLES`.
        :param tabWidthSpaces: When Tab key is pressed it is always converted into a number of space defined by this
            argument. Default is 4 spaces.
        :param actionTriggers: dictionary containing keystroke definitions for all custom actions used in this class.
            If None (default), then `DEFAULT_ACTION_TRIGGERS` is used.
        :param font: font to be used with this widget. Default is `QFont("Monospace")`.
        """
        super().__init__(parent)
        self.__line_numbers_enabled = enableLineNumbers
        self.__syntax_highlighting_enabled = enableSyntaxHighlighting
        self.__working = False
        self.__styles = DEFAULT_STYLES if syntaxHighlightStyles is None else syntaxHighlightStyles
        if highlightStyle not in self.__styles:
            raise ValueError(f"Highlight style [{highlightStyle}] is not present in the list of available styles")

        self.__tab_width_num_spaces = tabWidthSpaces
        self.__tab_spaces = " " * self.__tab_width_num_spaces

        self.actionTriggers = DEFAULT_ACTION_TRIGGERS if actionTriggers is None else actionTriggers

        self.setAutoFillBackground(True)
        self.__highlightStyle = highlightStyle
        self.__highlightStyleDict = self.__styles[highlightStyle]
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

        self.setFont(font)
        self.current_font_horizontal_advance = QFontMetrics(self.font()).horizontalAdvance("9")

        self.__lineNumberPanel = LineNumberPanel(self) if enableLineNumbers else None
        self.__lineNumberPanelConnections = self.__configure_line_numbers_panel() if enableLineNumbers else []
        self._lineNumberPanelWidth = self.calc_line_number_panel_width()

    def __configure_line_numbers_panel(self) -> list[QtCore.QMetaObject.Connection]:
        c1 = self.blockCountChanged.connect(self.__signal_handler_block_count_changed)
        c2 = self.updateRequest.connect(self.__signal_handler_update_request)
        c3 = self.cursorPositionChanged.connect(self.__signal_handler_cursor_position_changed)

        self.__signal_handler_block_count_changed(0)
        return [c1, c2, c3]

    def __unconfigure_line_numbers_panel(self) -> None:
        self.blockCountChanged.disconnect(self.__lineNumberPanelConnections[0])
        self.updateRequest.disconnect(self.__lineNumberPanelConnections[1])
        self.cursorPositionChanged.disconnect(self.__lineNumberPanelConnections[2])
        self.__lineNumberPanelConnections.clear()
        self.__lineNumberPanel.setParent(None)
        self.__lineNumberPanel = None
        self.setViewportMargins(0, 0, 0, 0)

    def getBackgroundColor(self) -> QColor:
        return self.__background_color

    def getLineNumberColor(self) -> QColor:
        return self.__line_number_color

    @override
    def resizeEvent(self, e: QtGui.QResizeEvent, /) -> None:
        super().resizeEvent(e)
        if self.__lineNumberPanel is not None:
            self.__lineNumberPanel.resizeEvent(e)

    def calc_line_number_panel_width(self) -> int:
        return len(str(self.blockCount())) * self.current_font_horizontal_advance

    def __signal_handler_block_count_changed(self, newBlockCount: int) -> None:
        self._lineNumberPanelWidth = self.calc_line_number_panel_width()
        self.setViewportMargins(self._lineNumberPanelWidth + self.current_font_horizontal_advance * 2, 0, 0, 0)

    def __signal_handler_update_request(self, rect: QtCore.QRect, dy: int) -> None:
        # Update the line number panel in response to an update in the editor
        if dy > 0:
            self.__lineNumberPanel.scroll(0, dy)
        else:
            self.__lineNumberPanel.update(0, rect.y(), self.__lineNumberPanel.width(), rect.height())

    def __signal_handler_cursor_position_changed(self) -> None:
        # Highlight the current line
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(self.__current_line_background_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            self.setExtraSelections([selection])

    def setTabWidth(self, tabWidthSpaces: int) -> None:
        """
        Tabs are always transformed into spaces when typing. This functions sets into how many spaces it is
        transformed. By default, a TAB is converted into 4 empty space characters.
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

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.type() == QtCore.QEvent.Type.KeyPress:
            if event.text().isprintable() and event.modifiers() in (
                QtCore.Qt.KeyboardModifier.NoModifier,
                QtCore.Qt.KeyboardModifier.ShiftModifier,
            ):
                self.__redo_queue.clear()
                c = self.textCursor()
                self.__undo_queue.append(UndoOp(self.toPlainText(), c.position()))
                super().keyPressEvent(event)
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
                            new_line = (self.__tab_spaces) + text
                            c.removeSelectedText()
                            c.insertText(new_line)
                        else:
                            c.setPosition(pos, QTextCursor.MoveMode.MoveAnchor)
                            c.insertText(self.__tab_spaces)
                        c.setPosition(pos + self.__tab_width_num_spaces)
                        self.setTextCursor(c)

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
                                    c.position() + new_len_sp
                                    c.setPosition(c.position() + new_len_sp)
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
                    # cursor is placed in the leading white space
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

            if self.actionTriggers["new_line"].match(event):
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
                # (Un)Comment out line or selection of lines on Ctrl-/
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

            if self.actionTriggers["increase_font_size"].match(event):
                font = self.font()
                font.setPointSize(font.pointSize() + 1)
                self.setFont(font)
                self._lineNumberPanelWidth = self.calc_line_number_panel_width()
                self.__signal_handler_block_count_changed(1)
                return

            if self.actionTriggers["decrease_font_size"].match(event):
                font = self.font()
                font.setPointSize(font.pointSize() - 1)
                self.setFont(font)
                self._lineNumberPanelWidth = self.calc_line_number_panel_width()
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

    def setHighlightStyle(self, highlightStyle: str) -> None:
        """
        Sets new highlight style. This will trigger re-rendering of text.
        Note that this is a NO-OP if syntax highlighting is disabled
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
        if enableLineNumbers:
            self.__line_numbers_enabled = True
            self.__lineNumberPanel = LineNumberPanel(self)
            self.__lineNumberPanelConnections = self.__configure_line_numbers_panel()
            self.__lineNumberPanel.show()
        else:
            self.__line_numbers_enabled = False
            self.__unconfigure_line_numbers_panel()

    def lineNumbersEnabled(self) -> bool:
        return self.__line_numbers_enabled

    def listAvailableHighlightStyles(self) -> list[str]:
        """
        Returns list of available highlight styles that can be used with this instance of QPythonPlainTextEdit class.
        """
        return list(self.__styles.keys())
