from PySide6.QtGui import QColor, QFont, QTextCharFormat


class TextCharFormat(QTextCharFormat):
    def __init__(
        self,
        foreground_color: str | None = None,
        background_color: str | None = None,
        weight: QFont.Weight = QFont.Weight.Normal,
        italic=False,
        underline=False,
    ):
        super().__init__()
        if foreground_color is not None:
            self.setForeground(QColor(foreground_color))
        if background_color is not None:
            self.setBackground(QColor(background_color))
        self.setFontWeight(weight)
        self.setFontItalic(italic)
        self.setFontUnderline(underline)


DEFAULT_STYLES: dict[str, dict[str, TextCharFormat | str]] = {
    "default": {
        "function_definition": TextCharFormat(foreground_color="#00627A"),
        "special_function": TextCharFormat(foreground_color="#B200B2"),
        "keyword": TextCharFormat(foreground_color="#0033B3"),
        "decorator": TextCharFormat(foreground_color="#9E880D"),
        "keyword_argument": TextCharFormat(foreground_color="#660099"),
        "line_comment": TextCharFormat(foreground_color="#8C8C8C", italic=True),
        "number": TextCharFormat(foreground_color="#1750EB"),
        "function_call": TextCharFormat(),
        "string": TextCharFormat(foreground_color="#067D17"),
        "self": TextCharFormat(foreground_color="#94558D"),
        "type": TextCharFormat(foreground_color="#660099"),
        "class_definition_name": TextCharFormat(weight=QFont.Weight.Bold),
        "QPlainTextEdit_default_foreground_color": "#000000",
        "QPlainTextEdit_background_color": "#ffffff",
        "QPlainTextEdit_line_number_color": "#999999",
        "QPlainTextEdit_current_line_background_color": "#f5f8fe",
    },
    "light_bold": {
        "function_definition": TextCharFormat(foreground_color="#00627A", weight=QFont.Weight.Bold),
        "special_function": TextCharFormat(foreground_color="#B200B2", weight=QFont.Weight.Bold),
        "keyword": TextCharFormat(foreground_color="#0033B3", weight=QFont.Weight.Bold),
        "decorator": TextCharFormat(foreground_color="#9E880D", weight=QFont.Weight.Bold),
        "keyword_argument": TextCharFormat(foreground_color="#660099", weight=QFont.Weight.Bold),
        "line_comment": TextCharFormat(foreground_color="#8C8C8C", italic=True, weight=QFont.Weight.Bold),
        "number": TextCharFormat(foreground_color="#1750EB", weight=QFont.Weight.Bold),
        "function_call": TextCharFormat(weight=QFont.Weight.Bold),
        "string": TextCharFormat(foreground_color="#067D17", weight=QFont.Weight.Bold),
        "self": TextCharFormat(foreground_color="#94558D", weight=QFont.Weight.Bold),
        "type": TextCharFormat(foreground_color="#660099", weight=QFont.Weight.Bold),
        "class_definition_name": TextCharFormat(weight=QFont.Weight.Bold),
        "QPlainTextEdit_default_foreground_color": "#000000",
        "QPlainTextEdit_background_color": "#ffffff",
        "QPlainTextEdit_line_number_color": "#999999",
        "QPlainTextEdit_current_line_background_color": "#f5f8fe",
    },
    "warm_neon": {
        "function_definition": TextCharFormat(foreground_color="#FFC66D"),
        "special_function": TextCharFormat(foreground_color="#83D6F1"),
        "keyword": TextCharFormat(foreground_color="#CC9900"),
        "decorator": TextCharFormat(foreground_color="#6699FF"),
        "keyword_argument": TextCharFormat(foreground_color="#AA4926"),
        "line_comment": TextCharFormat(foreground_color="#FF6666", italic=True),
        "number": TextCharFormat(foreground_color="#F971BB"),
        "function_call": TextCharFormat(foreground_color="#9BC28E"),
        "string": TextCharFormat(foreground_color="#00B580"),
        "self": TextCharFormat(foreground_color="#94558D"),
        "type": TextCharFormat(foreground_color="#9BC28E"),
        "class_definition_name": TextCharFormat(foreground_color="#FFFFFF", weight=QFont.Weight.Bold),
        "QPlainTextEdit_default_foreground_color": "#FFFFFF",
        "QPlainTextEdit_background_color": "#282828",
        "QPlainTextEdit_line_number_color": "#546D54",
        "QPlainTextEdit_current_line_background_color": "#202020",
    },
}
