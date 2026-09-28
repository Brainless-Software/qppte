from PySide6.QtCore import QLine, QRect, QRectF
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPaintEvent, QResizeEvent, Qt
from PySide6.QtWidgets import QWidget


class LineNumberPanel(QWidget):
    def __init__(self, editor_parent):
        super().__init__(editor_parent)
        self.editor_parent = editor_parent
        self.setContentsMargins(0, 0, 0, 0)

    def sizeHint(self):
        return self.editor_parent.sizeHint()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        r: QRect = self.editor_parent.geometry()
        r.setLeft(1)
        r.setTop(1)
        r.setWidth(self.editor_parent._lineNumberPanelWidth)
        r.setHeight(self.editor_parent.viewport().geometry().height())
        self.setGeometry(r)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        event_rect = event.rect()
        painter.fillRect(event_rect, self.editor_parent.getBackgroundColor())
        line_color = QColor(self.editor_parent.getLineNumberColor())
        line_color.setAlpha(80)
        painter.setPen(line_color)
        painter.drawLine(
            QLine(
                self.editor_parent._lineNumberPanelWidth - 2,
                0,
                self.editor_parent._lineNumberPanelWidth - 2,
                event_rect.height(),
            )
        )
        painter.setPen(self.editor_parent.getLineNumberColor())
        block = self.editor_parent.firstVisibleBlock()
        block_number = block.blockNumber()
        bounding_rect_of_block: QRectF = self.editor_parent.blockBoundingGeometry(block)
        translated_bounding_rect_of_block: QRectF = bounding_rect_of_block.translated(
            self.editor_parent.contentOffset()
        )
        top = translated_bounding_rect_of_block.top()
        bottom = top + self.editor_parent.blockBoundingRect(block).height()

        height = QFontMetrics(self.font()).height()
        while block.isValid() and (top <= event_rect.bottom()):
            if block.isVisible() and (bottom >= event_rect.top()):
                painter.drawText(
                    5,
                    int(top),
                    self.width(),
                    height,
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    f"{block_number + 1}   ",
                )
            block = block.next()
            top = bottom
            bottom = top + self.editor_parent.blockBoundingRect(block).height()
            block_number += 1
