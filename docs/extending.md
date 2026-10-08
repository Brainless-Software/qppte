# Extending editor

To extend functionality of the editor you create a new class that inherits from `QPythonPlainTextEdit`.
For example, let say we want to add functionality when pressing `Shift+Enter` inserts new line right below the 
current line where the current cursor is without breaking apart current line and move cursor to that new line.
We can do that like so:

```python
from typing import override
from PySide6 import QtCore
from PySide6.QtGui import QKeyEvent, Qt, QTextCursor
from qppte import QPythonPlainTextEdit, QPythonPlainTextWidget

class MyTextEditor(QPythonPlainTextEdit):
    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if (
            not self.isReadOnly()
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and event.modifiers() == QtCore.Qt.KeyboardModifier.ShiftModifier
        ):
            # pressing Shift+Enter will insert new line without breaking current one
            cursor = self.textCursor()
            self.recordStateForUndoOperation() # important or undo will not work later
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.MoveAnchor)
            cursor.insertText("\n")
            self.setTextCursor(cursor)
        else:
            super().keyPressEvent(event)

text_widget = QPythonPlainTextWidget(editor=MyTextEditor())
...
```