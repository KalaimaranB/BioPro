from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtWidgets import QLayout, QSizePolicy


class FlowLayout(QLayout):
    """A layout that arranges widgets left-to-right, wrapping to the next line when needed."""

    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def doLayout(self, rect, testOnly):
        y = rect.y()
        lineHeight = 0
        spacing = self.spacing()

        lines = []
        current_line = []
        current_width = 0

        # Group items into lines
        for item in self.itemList:
            wid = item.widget()
            spaceX = spacing
            if spaceX == -1 and wid is not None:
                spaceX = wid.style().layoutSpacing(
                    QSizePolicy.ControlType.PushButton,
                    QSizePolicy.ControlType.PushButton,
                    Qt.Orientation.Horizontal,
                )

            item_w = item.sizeHint().width()

            if current_line and (current_width + spaceX + item_w) > rect.width():
                lines.append((current_line, current_width))
                current_line = [(item, spaceX)]
                current_width = item_w
            else:
                current_line.append((item, spaceX))
                current_width += (spaceX if len(current_line) > 1 else 0) + item_w

        if current_line:
            lines.append((current_line, current_width))

        # Calculate uniform stretch based on the most populated line
        global_stretch = 0
        if lines:
            max_items = max(len(line) for line, _ in lines)
            for line_items, line_width in lines:
                if len(line_items) == max_items:
                    extra_space = max(0, rect.width() - line_width)
                    expandable_items = [
                        i
                        for i, _ in line_items
                        if i.expandingDirections() & Qt.Orientation.Horizontal
                    ]
                    global_stretch = extra_space / len(expandable_items) if expandable_items else 0
                    break

        # Layout each line with stretching
        for line_items, _line_width in lines:
            lineHeight = 0

            expandable_items = [
                i for i, _ in line_items if i.expandingDirections() & Qt.Orientation.Horizontal
            ]

            line_x = rect.x()

            # First pass: determine heights
            for item, _spaceX in line_items:
                item_w = item.sizeHint().width()
                if item in expandable_items:
                    item_w += global_stretch

                item_h = item.sizeHint().height()
                if item.hasHeightForWidth():
                    item_h = max(item_h, item.heightForWidth(int(item_w)))

                lineHeight = max(lineHeight, item_h)

            # Second pass: set geometry
            for i, (item, spaceX) in enumerate(line_items):
                if i > 0:
                    line_x += spaceX

                item_w = item.sizeHint().width()
                if item in expandable_items:
                    item_w += global_stretch

                item_h = item.sizeHint().height()
                if item.hasHeightForWidth():
                    item_h = max(item_h, item.heightForWidth(int(item_w)))

                if not testOnly:
                    item.setGeometry(QRect(int(line_x), int(y), int(item_w), int(item_h)))

                line_x += item_w

            y += lineHeight + spacing

        return y - rect.y() - spacing if lines else 0
