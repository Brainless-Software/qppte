import sys
from pathlib import Path

from PySide6 import QtCore
from PySide6.QtGui import QAction, QFontDatabase, QKeyEvent, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from tree_sitter import Point

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
        search_action.setShortcut(text_widget.editor.actionTriggers["search"].get_q_key_combintation())
        search_action.triggered.connect(text_widget.editor.startSearch)
        self.addAction(search_action)

        root_panel = QWidget()
        layout = QVBoxLayout()
        root_panel.setLayout(layout)

        styles_selector = QComboBox()
        styles_selector.addItems(text_widget.editor.listAvailableHighlightStyles())
        styles_selector.setCurrentText(text_widget.editor.getHighlightStyle())

        styles_selector.currentTextChanged.connect(text_widget.editor.setHighlightStyle)

        tools_panel_1 = QWidget()
        tools_layout_1 = QHBoxLayout()
        tools_panel_1.setLayout(tools_layout_1)
        tools_layout_1.addWidget(QLabel("Highlighting Style"))
        tools_layout_1.addWidget(styles_selector)
        tools_layout_1.addWidget(QLabel("        "))

        highlighting_enabled_cb = QCheckBox("Highlighting Enabled")
        tools_layout_1.addWidget(highlighting_enabled_cb)
        highlighting_enabled_cb.setChecked(True)

        def toggle_highlighting(enabled: bool):
            text_widget.editor.setEnableSyntaxHighlighting(enabled)

        highlighting_enabled_cb.toggled.connect(toggle_highlighting)

        tools_layout_1.addWidget(QLabel(""), stretch=1)

        exit_button = QPushButton("Exit")
        tools_layout_1.addWidget(exit_button)
        exit_button.clicked.connect(self.close)

        tools_panel_2 = QWidget()
        tools_layout_2 = QHBoxLayout()
        tools_panel_2.setLayout(tools_layout_2)

        font_families = QFontDatabase.families()
        fixed_font_families = [f for f in font_families if QFontDatabase.isFixedPitch(f)]
        font_families_selector = QComboBox()
        font_families_selector.addItems(fixed_font_families)
        font_families_selector.setCurrentText(text_widget.editor.font().family())
        font_families_selector.currentTextChanged.connect(text_widget.editor.setFont)
        tools_layout_2.addWidget(QLabel("Font"))
        tools_layout_2.addWidget(font_families_selector)
        tools_layout_2.addWidget(QLabel("    "))
        linenum_enabled_cb = QCheckBox("Line Numbers Enabled")
        tools_layout_2.addWidget(linenum_enabled_cb)
        tools_layout_2.addWidget(QWidget(), stretch=1)
        linenum_enabled_cb.setChecked(text_widget.editor.lineNumbersEnabled())

        linenum_enabled_cb.toggled.connect(text_widget.editor.enableLineNumbers)

        layout.addWidget(tools_panel_1)
        layout.addWidget(tools_panel_2)

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
        file_menu.addAction("&Quit", self.close)
        menu_bar.addMenu(file_menu)

        edit_menu = QMenu("&Edit", menu_bar)
        edit_menu.addAction(
            "&Undo [Ctrl-Z]",
            lambda: text_widget.editor.keyPressEvent(
                QKeyEvent(QtCore.QEvent.Type.KeyPress, Qt.Key.Key_Z, QtCore.Qt.KeyboardModifier.ControlModifier, "z")
            ),
        )
        edit_menu.addAction(
            "&Redo [Ctrl-R]",
            lambda: text_widget.editor.keyPressEvent(
                QKeyEvent(QtCore.QEvent.Type.KeyPress, Qt.Key.Key_R, QtCore.Qt.KeyboardModifier.ControlModifier, "z")
            ),
        )
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
