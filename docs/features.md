# Features

This library provides several classes.

* [QPythonPlainTextEdit](https://github.com/Brainless-Software/qppte/blob/d18d65b4e8f5c1a3932472deb2a2702fe3e38b93/src/qppte/qpythonplaintextedit.py#L380) -
  actual code editor class.
  Extends [QPlainTextEdit](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QPlainTextEdit.html).
* [QPythonPlainTextWidget](https://github.com/Brainless-Software/qppte/blob/d18d65b4e8f5c1a3932472deb2a2702fe3e38b93/src/qppte/qpythonplaintextwidget.py#L6) -
  QWidget container that holds editor class and bottom info panel. This is a primary class for embedding editor into
  your application.
* [QPythonPlainTextSettings](https://github.com/Brainless-Software/qppte/blob/d18d65b4e8f5c1a3932472deb2a2702fe3e38b93/src/qppte/qpythonplaintextsettings.py#L21) -
  QWidget panel that displays commonly modifiable editor settings.
* [QPythonPlainTextSettingsDialog](https://github.com/Brainless-Software/qppte/blob/d18d65b4e8f5c1a3932472deb2a2702fe3e38b93/src/qppte/qpythonplaintextsettings.py#L180) -
  Immediately usable settings dialog if you wish to use default settings widget.

Below we outline features of the above classes .

### QPythonPlainTextEdit

* Python syntax highlighting
* Line numbers column
* Color schemes: `"Light"`, `"Light [Bold]"` and `"Warm Neon"`
* Common code editor key combinations:
    * `Tab` - indent block
    * `Shift+Tab` - unindent block
    * `Ctrl+A` - select all
    * `Ctrl+X` - cut line or selected block and save it into clipboard
    * `Ctrl+C` - copy line or selected block into clipboard
    * `Ctrl+V` - paste text from clipboard
    * `Ctrl+Z` - undo
    * `Ctrl+R` - redo
    * `Ctrl+Y` - delete current line or all lines in a block
    * `Ctrl+G` - goto line and optionally column
    * `Ctrl+Shift+⬆` - move current line up
    * `Ctrl+Shift+⬇` - move current line down
    * `Ctrl+D` - duplicate current line
    * `Ctrl+/` - toggle commenting current line or a block
    * `Ctrl+Shift+J` - join current and next line
    * Selecting text and pressing `"`, `'`, `[`, `(`, `{` or backtick will wrap selected text into relevant characters.
    * `Ctrl+F` - search
        * Arrows `⬆` and `⬇` to go to previous and next matches.
        * `Alt+C` - to toggle case (in)sensitive search.
        * `Ctrl+Enter` - to close search and move focus to the editor

### QPythonPlainTextSettings

These allow you to modify following settings.

* Color scheme
* If syntax highlighting is enabled or not
* Show line numbers column or not
* Number of spaces to be used instead of `Tab`
* Fixed font family and size