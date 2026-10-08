from PySide6.QtWidgets import QVBoxLayout, QWidget

from qppte import QPythonPlainTextEdit


class QPythonPlainTextWidget(QWidget):
    def __init__(self, parent=None, *, editor: QPythonPlainTextEdit | None = None):
        """
        Primary class for embedding Python code editor in your application.

        Args:
            parent: QWidget parent object if any.
            editor: instance of QPythonPlainTextEdit to be placed inside of this Widget. If None (default), then
                instance of QPythonPlainTextEdit class will be created automatically.
        """
        super().__init__(parent)
        self.editor = QPythonPlainTextEdit(self) if editor is None else editor
        self.editor.setParent(self)
        self.setContentsMargins(0, 0, 0, 0)
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor, stretch=1)
        layout.addWidget(self.editor.getInfoPanel())
