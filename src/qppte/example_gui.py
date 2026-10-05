import sys
from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMenu,
    QMenuBar,
    QVBoxLayout,
    QWidget,
)
from tree_sitter import Point

from qppte.qpythonplaintextsettings import QPythonPlainTextSettingsDialog
from qppte.qpythonplaintextwidget import QPythonPlainTextWidget


class TextEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QPythonPlainTextEdit Demo")
        self.setGeometry(100, 100, 800, 600)

        text_widget = QPythonPlainTextWidget()
        text_widget.editor.setHighlightStyle("Light")
        text_widget.editor.enableLineNumbers(True)
        search_action = QAction("Search", self)
        search_action.setShortcut(text_widget.editor.actionTriggers["search"].getQKeyCombination())
        search_action.triggered.connect(text_widget.editor.startSearch)
        self.addAction(search_action)

        root_panel = QWidget()
        layout = QVBoxLayout()
        root_panel.setLayout(layout)
        layout.addWidget(text_widget)

        self.setCentralWidget(root_panel)

        self.sample_text = """\"\"\" Module docstring \"\"\"

@property
def foo() -> None:
    pass
    
@property(x=7)
def moo() -> None:
    pass
    
for i in [1, 3, 5, 7, 11]:
    print(f"i -> {i}")
    
class A:
    \"\"\" Class A \"\"\"
    def __init__(self):
        self.x = 1 # initializing x to 1
    
    def __repr__(self, /) -> str:
        \"\"\" String representation of class A \"\"\"
        return f"Instance of class {self.__class__.__name__}({self.a})"
"""
        text_widget.editor.setPlainText(self.sample_text)

        menu_bar = QMenuBar()

        def open_file():
            file_name, _ = QFileDialog.getOpenFileName(
                self, caption="Import project from file", dir=str(Path.home()), filter="*.py"
            )
            if file_name != "":
                text_widget.editor.setPlainText(Path(file_name).read_text())

        file_menu = QMenu("&File", menu_bar)
        file_menu.addAction("&Open", open_file)
        file_menu.addSeparator()
        file_menu.addAction(
            "&Settings",
            lambda: QPythonPlainTextSettingsDialog(self, text_widget.editor.settings, text_widget.editor).exec(),
        )
        file_menu.addSeparator()
        file_menu.addAction("&Quit", self.close)
        menu_bar.addMenu(file_menu)

        edit_menu = QMenu("&Edit", menu_bar)
        edit_menu.addAction(
            "&Undo", lambda: text_widget.editor.keyPressEvent(text_widget.editor.actionTriggers["undo"].getQKeyEvent())
        ).setShortcut(text_widget.editor.actionTriggers["undo"].getQKeyCombination())
        edit_menu.addAction(
            "&Redo", lambda: text_widget.editor.keyPressEvent(text_widget.editor.actionTriggers["redo"].getQKeyEvent())
        ).setShortcut(text_widget.editor.actionTriggers["redo"].getQKeyCombination())
        edit_menu.addSeparator()
        menu_bar.addMenu(edit_menu)

        self.setMenuBar(menu_bar)


def pretty_print(node, input_source_bytes: bytes, indent="", show_matched_text: bool = False):
    # Named nodes represent actual syntax constructs (like 'function_definition')
    # Anonymous nodes are structural literal punctuation (like '{' or ';')
    node_type = node.type if node.is_named else f'"{node.type}"'

    # Print the current node name along with its character span
    matched_text = input_source_bytes[node.start_byte : node.end_byte].decode("utf-8")
    if show_matched_text:
        print(f"{indent}{node_type} [{node.start_byte} - {node.end_byte}] [{matched_text}]")
    else:
        print(f"{indent}{node_type} [{node.start_byte} - {node.end_byte}]")

    # Recursively format all children
    for child in node.children:
        pretty_print(child, input_source_bytes, indent + "  ")


def get_offset(lines: list[str], p: Point) -> int:
    return sum([len(line) for line in lines[0 : p.row]]) + p.column + p.row


def main():
    app = QApplication(sys.argv)
    window = TextEditorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
