from PySide6.QtCore import QRect, QRectF
from PySide6.QtGui import QFontMetrics, QPainter, QPaintEvent, QResizeEvent, Qt
from PySide6.QtWidgets import QWidget


class LineNumberPanel(QWidget):
    def __init__(self, editor_parent):
        super().__init__(editor_parent)
        self.editor_parent = editor_parent

    def sizeHint(self):
        return self.editor_parent.sizeHint()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        r: QRect = self.editor_parent.geometry()
        r.setWidth(
            self.editor_parent._lineNumberPanelWidth + int(self.editor_parent.current_font_horizontal_advance * 1.5)
        )
        r.setLeft(cr.left() + 1)
        r.setTop(cr.top() + 1)
        self.setGeometry(r)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.editor_parent.getBackgroundColor())
        block = self.editor_parent.firstVisibleBlock()
        block_number = block.blockNumber()
        bounding_rect_of_block: QRectF = self.editor_parent.blockBoundingGeometry(block)
        translated_bounding_rect_of_block: QRectF = bounding_rect_of_block.translated(
            self.editor_parent.contentOffset()
        )
        top = translated_bounding_rect_of_block.top()
        bottom = top + self.editor_parent.blockBoundingRect(block).height()

        height = QFontMetrics(self.font()).height()
        while block.isValid() and (top <= event.rect().bottom()):
            if block.isVisible() and (bottom >= event.rect().top()):
                painter.setPen(self.editor_parent.getLineNumberColor())
                painter.drawText(
                    0,
                    int(top),
                    self.width(),
                    height,
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    f"{block_number + 1}  ",
                )
            block = block.next()
            top = bottom
            bottom = top + self.editor_parent.blockBoundingRect(block).height()
            block_number += 1
