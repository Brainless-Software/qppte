# QPPTE - QPythonPlainTextEdit

A poor-main embeddable code editor for python. Written in Python with [PySide6](https://pypi.org/project/PySide6/)
it is created with intent to be used within larger applications where code editor is required. For example 
if you application supports plugins in Python and you want to give users ability to create and edit such plugins 
directly within the application, then you can make this library a dependency in your project and embed this editor.

It supports basic syntax highlighting using [tree-sitter](https://github.com/tree-sitter/py-tree-sitter) and keystrokes common to code editors. The styles and 
the keystrokes can be customized by the user.

To add this library to your project do

```shell
uv add qppte
```


