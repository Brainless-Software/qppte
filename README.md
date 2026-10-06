QPPTE - QPythonPlainTextEdit
============================

A poor-main embeddable code editor for python. Written in Python with [PySide6](https://pypi.org/project/PySide6/)
it is created with intent to be used within larger application where code editor is required. For example 
if you application supports plugins in Python and you want to give users ability to create and edit such plugins, then
you can make this library a dependency in your project and embed this editor. 

More information can be found [here](https://brainless-software.github.io/qppte/).

A poor-main text editor for editing and viewing Python code to be used with [PySide6](https://pypi.org/project/PySide6/)
library. It supports basic syntax highlighting using [tree-sitter](https://github.com/tree-sitter/py-tree-sitter) and
keystrokes common to code editors. Highlighting styles can be customized and expanded. Likewise, keystrokes can be
customized by the user.

When syntax highlighting is enabled we synchronously reparse the whole source code tree and re-highlight entire text.
This is suboptimal and could result in slowing down of the text update but is adequate for relatively small files.

## Adding qptte to your code

```shell
uv add git+https://github.com/priimak/qppte.git@v0.5.0
```

## Running demo GUI

```shell
uv tool run --from git+https://github.com/priimak/qppte.git@v0.5.0 qppte_demo
```

## Supported additional editor operations

* Line or block indent
    * Press `Tab` to indent a line or a selected block by a Tab width number of spaces. Tab is always converted into
      space (default 4).
* Undo and Redo
    * `Ctrl-Z` and `Ctrl-R` for undo and redo respectively.
* Unindent line or block
    * Press `Shift-Tab` to unindent a line or a selected block by a Tab width number of spaces.
* Delete line or block.
    * `Ctrl-Y` will delete a line or all lines in a selected block.
* Duplicate line
    * `Ctrl-D` will duplicate current line and move cursor down.
* Move line up and down
    * `Ctrl-Shift-ArrowUp` and `Ctrl-Shift-ArrowDown` will move current line up and down respectively.
* Toggle commenting line or block.
    * `Ctrl-/` will toggle commenting out a line or all lines included in the selected block.
* Increment/decrement font size
    * `Ctrl-+` will increase font size. `Ctrl+_` decrease.

## Using QPythonPlainTextEdit in your code.

```python
from qppte import QPythonPlainTextEdit
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget


class TextEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        root_panel = QWidget()

        layout = QVBoxLayout()
        root_panel.setLayout(layout)

        code_editor = QPythonPlainTextEdit()
        layout.addWidget(code_editor)

        self.setCentralWidget(root_panel)

        ...
```

## Methods specific to QPythonPlainTextEdit

* `getTabWidth() -> int` - returns number of spaces to be used when Tab is pressed on the keyboard
* `setTabWidth(tabWidthSpaces: int)` - sets number of spaces to be used when Tab is pressed on the keyboard. Will not
  affect already entered text/code in the editor.
* `getHighlightStyle() -> str` - returns current name of highlight style.
* `setHighlightStyle(highlightStyle: str)` - sets highlight style to a new one.
* `listAvailableHighlightStyles() -> list[str]` - returns list of available highlight styles.
* `setEnableSyntaxHighlighting(enableSyntaxHighlighting: bool)` - enables or disables syntax highlighting.
* `recordStateForUndoOperation()` - method to be used when extending `QPythonPlainTextEdit`

## Adding and modifying new custom highlight styles.

TBD

## Changing keyboard shortcuts

TBD