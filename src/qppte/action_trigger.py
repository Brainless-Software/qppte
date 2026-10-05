from functools import cache, reduce
from typing import NamedTuple

from PySide6 import QtCore
from PySide6.QtGui import QKeyEvent, Qt


class ActionTrigger(NamedTuple):
    key: int
    modifiers: tuple[int]

    @cache
    def get_modifiers(self) -> int:
        return reduce(lambda acc, m: acc | m, self.modifiers, QtCore.Qt.KeyboardModifier.NoModifier)

    def match(self, event: QKeyEvent) -> bool:
        if event.key() == self.key and (self.modifiers == [] or self.get_modifiers() == event.modifiers()):
            return True
        else:
            return False

    @cache
    def getQKeyCombination(self) -> QtCore.QKeyCombination:
        return QtCore.QKeyCombination(self.get_modifiers(), self.key)

    @cache
    def getQKeyEvent(self) -> QKeyEvent:
        c = self.getQKeyCombination()
        return QKeyEvent(QtCore.QEvent.Type.KeyPress, c.key(), c.keyboardModifiers())


DEFAULT_ACTION_TRIGGERS: dict[str, ActionTrigger] = {
    "indent_block": ActionTrigger(Qt.Key.Key_Tab, tuple()),
    "clear_selection": ActionTrigger(Qt.Key.Key_Escape, tuple()),
    "backspace": ActionTrigger(Qt.Key.Key_Backspace, tuple()),
    "new_line_enter": ActionTrigger(Qt.Key.Key_Enter, tuple()),
    "new_line_return": ActionTrigger(Qt.Key.Key_Return, tuple()),
    "select_all": ActionTrigger(Qt.Key.Key_A, (QtCore.Qt.KeyboardModifier.ControlModifier,)),
    "cut": ActionTrigger(Qt.Key.Key_X, (QtCore.Qt.KeyboardModifier.ControlModifier,)),
    "copy": ActionTrigger(Qt.Key.Key_C, (QtCore.Qt.KeyboardModifier.ControlModifier,)),
    "paste": ActionTrigger(Qt.Key.Key_V, (QtCore.Qt.KeyboardModifier.ControlModifier,)),
    "undo": ActionTrigger(Qt.Key.Key_Z, (QtCore.Qt.KeyboardModifier.ControlModifier,)),
    "redo": ActionTrigger(Qt.Key.Key_R, (QtCore.Qt.KeyboardModifier.ControlModifier,)),
    "unindent": ActionTrigger(Qt.Key.Key_Backtab, (QtCore.Qt.KeyboardModifier.ShiftModifier,)),
    "delete_lines": ActionTrigger(Qt.Key.Key_Y, (QtCore.Qt.KeyboardModifier.ControlModifier,)),
    "goto_line": ActionTrigger(Qt.Key.Key_G, (QtCore.Qt.KeyboardModifier.ControlModifier,)),
    "move_line_up": ActionTrigger(
        Qt.Key.Key_Up, (QtCore.Qt.KeyboardModifier.ControlModifier, QtCore.Qt.KeyboardModifier.ShiftModifier)
    ),
    "move_line_down": ActionTrigger(
        Qt.Key.Key_Down, (QtCore.Qt.KeyboardModifier.ControlModifier, QtCore.Qt.KeyboardModifier.ShiftModifier)
    ),
    "duplicate_line": ActionTrigger(Qt.Key.Key_D, (QtCore.Qt.KeyboardModifier.ControlModifier,)),
    "toggle_comment_block": ActionTrigger(Qt.Key.Key_Slash, (QtCore.Qt.KeyboardModifier.ControlModifier,)),
    "join_two_lines": ActionTrigger(
        Qt.Key.Key_J, (QtCore.Qt.KeyboardModifier.ControlModifier, QtCore.Qt.KeyboardModifier.ShiftModifier)
    ),
    "search": ActionTrigger(Qt.Key.Key_F, (QtCore.Qt.KeyboardModifier.ControlModifier,)),
}
