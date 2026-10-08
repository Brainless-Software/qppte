# Embedding code editor within larger application

To embed code editor into your application you will typically use `QPythonPlainTextWidget`.
This class extends `QWidget` and in its layout it has `QPythonPlainTextEdit` and right below 
associated info panel. This panel displays current cursor line and number column and a search field
when user presses `Ctrl-F`. Here is a simple example

```python
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout,QMenuBar, QMenu
from PySide6.QtGui import QAction
from qppte import QPythonPlainTextWidget, QPythonPlainTextSettingsDialog


class TextEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 800, 600)

        text_widget = QPythonPlainTextWidget()
        search_action = QAction("Search", self)

        # following triggers search even when editor widget does not have focus
        search_action.setShortcut(text_widget.editor.actionTriggers["search"].getQKeyCombination())
        search_action.triggered.connect(text_widget.editor.startSearch)
        self.addAction(search_action)

        root_panel = QWidget()
        root_panel.setLayout(QVBoxLayout())
        root_panel.layout().addWidget(text_widget)

        # setup File->Setting menu to open settings dialog
        menu_bar = QMenuBar()
        file_menu = QMenu("&File", menu_bar)
        file_menu.addAction(
            "&Settings",
            lambda: QPythonPlainTextSettingsDialog(
                self, 
                text_widget.editor.settings, # setting to display and chage 
                text_widget.editor # editor class to automatically apply new settings
            ).exec(),
        )
        menu_bar.addMenu(file_menu)
        
        self.setCentralWidget(root_panel)
```

