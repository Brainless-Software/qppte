# Adding new syntax highlighting styles

By default, syntax highlit colors and font rules are held in [DEFAULT_STYLES](https://github.com/Brainless-Software/qppte/blob/6a1ef0f9498bc31c977c6d4bf53d7f2a4fe48017/src/qppte/style.py#L23)
variable. You can add new style directly to this variable or make a copy of it, add new style to the copy 
and pass it around when instantiating editor and settings classes. Below we add new style `"Paper"` with changed 
background color and color of some other elements.

```python
from qppte import (
    DEFAULT_STYLES, TextCharFormat, QPythonPlainTextEdit, 
    QPythonPlainTextWidget, QPythonPlainTextSettingsDialog
)

styles = DEFAULT_STYLES.copy()
styles["Paper"] = {
    # text formats for various python syntax elements
    "function_definition": TextCharFormat(foreground_color="#00627A"),
    "special_function": TextCharFormat(foreground_color="#B200B2"),
    "keyword": TextCharFormat(foreground_color="#0033B3"),
    "decorator": TextCharFormat(foreground_color="#9E880D"),
    "keyword_argument": TextCharFormat(foreground_color="#660099"),
    "line_comment": TextCharFormat(foreground_color="#5C5C5C", italic=True),
    "number": TextCharFormat(foreground_color="#1750EB"),
    "function_call": TextCharFormat(),
    "string": TextCharFormat(foreground_color="#067D17"),
    "docstring": TextCharFormat(foreground_color="#5C5C5C", italic=True),
    "self": TextCharFormat(foreground_color="#94558D"),
    "type": TextCharFormat(foreground_color="#660099"),
    "class_definition_name": TextCharFormat(weight=QFont.Weight.Bold),
    
    # colors to be applied to the common elements of the editor
    # not python syntax specific
    "QPlainTextEdit_default_foreground_color": "#000000",
    "QPlainTextEdit_background_color": "#fff3e5",
    "QPlainTextEdit_line_number_color": "#999999",
    "QPlainTextEdit_current_line_background_color": "#f5f8fe",
}

text_widget = QPythonPlainTextWidget(editor = QPythonPlainTextEdit(None, syntaxHighlightStyles=styles))

file_menu = QMenu("&File", menu_bar)
file_menu.addAction("&Open", open_file)
file_menu.addSeparator()
file_menu.addAction(
    "&Settings",
    lambda: QPythonPlainTextSettingsDialog(
        self,
        text_widget.editor.settings,  # setting to display and chage
        text_widget.editor,  # editor class to which automatically apply new settings
        syntaxHighlightStyles=styles
    ).exec(),
)
```