import sys
import colorsys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit,
    QSlider, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QColor, QPainter, QLinearGradient


class ColorPickerCanvas(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.setStyleSheet("border: 2px solid #555; border-radius: 10px; background-color: white;")
        self.selected_pos = QPoint(100, 100)
        self.on_color_picked = None

    def paintEvent(self, event):
        painter = QPainter(self)
        width = self.width()
        height = self.height()

        step = 2
        for x in range(0, width, step):
            hue = x / width
            grad = QLinearGradient(0, 0, 0, height)
            grad.setColorAt(0.0, QColor.fromHsvF(0, 0, 1.0))
            grad.setColorAt(0.5, QColor.fromHsvF(hue, 1.0, 1.0))
            grad.setColorAt(1.0, QColor.fromHsvF(0, 0, 0.0))

            painter.setPen(Qt.NoPen)
            painter.setBrush(grad)
            painter.drawRect(x, 0, step, height)

        painter.setPen(Qt.white)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(self.selected_pos.x() - 5, self.selected_pos.y() - 5, 10, 10)
        painter.setPen(Qt.black)
        painter.drawEllipse(self.selected_pos.x() - 6, self.selected_pos.y() - 6, 12, 12)

    def mousePressEvent(self, event):
        self.pick_color(event.pos())

    def mouseMoveEvent(self, event):
        self.pick_color(event.pos())

    def pick_color(self, pos):
        x = max(0, min(pos.x(), self.width() - 1))
        y = max(0, min(pos.y(), self.height() - 1))
        self.selected_pos = QPoint(x, y)
        self.update()

        hue = x / self.width()
        y_ratio = y / self.height()

        if y_ratio <= 0.5:
            sat = y_ratio * 2
            val = 1.0
            rgb = QColor.fromHsvF(hue, sat, val)
        else:
            sat = 1.0
            val = 1.0 - (y_ratio - 0.5) * 2
            rgb = QColor.fromHsvF(hue, sat, max(0.0, val))

        if self.on_color_picked:
            self.on_color_picked([rgb.red(), rgb.green(), rgb.blue()])

    def update_marker_from_rgb(self, r, g, b):
        color = QColor(r, g, b)
        h, s, v, _ = color.getHsv()
        if h < 0: h = 0
        x = int((h / 360.0) * self.width())

        if v == 255:
            y = int((1.0 - (s / 255.0)) * 0.5 * self.height())
        else:
            y = int(0.5 * self.height() + (1.0 - (v / 255.0)) * 0.5 * self.height())

        self.selected_pos = QPoint(max(0, min(x, self.width())), max(0, min(y, self.height())))
        self.update()


class ColorConverterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Цветовые модели: CMYK, RGB, HLS")
        self.setFixedSize(680, 560)

        self.current_rgb = [255, 128, 0]
        self.updating = False

        self.init_ui()
        self.update_all_from_rgb()

    def init_ui(self):
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)

        left_layout = QVBoxLayout()
        self.inputs = {}
        self.sliders = {}

        models_config = {
            "RGB": [("R", 0, 255), ("G", 0, 255), ("B", 0, 255)],
            "CMYK": [("C", 0, 100), ("M", 0, 100), ("Y", 0, 100), ("K", 0, 100)],
            "HLS": [("H", 0, 360), ("L", 0, 100), ("S", 0, 100)]
        }

        grid = QGridLayout()
        row = 0

        for model_name, params in models_config.items():
            title_label = QLabel(f"<b>Модель {model_name}</b>")
            grid.addWidget(title_label, row, 0, 1, 3)
            row += 1

            self.inputs[model_name] = {}
            self.sliders[model_name] = {}

            for p_name, p_min, p_max in params:
                lbl = QLabel(f"{p_name}:")

                txt_input = QLineEdit()
                txt_input.setFixedWidth(60)
                txt_input.textEdited.connect(lambda text, m=model_name, p=p_name: self.on_text_changed(m, p, text))

                slider = QSlider(Qt.Horizontal)
                slider.setRange(p_min, p_max)
                slider.valueChanged.connect(lambda val, m=model_name, p=p_name: self.on_slider_changed(m, p, val))

                grid.addWidget(lbl, row, 0)
                grid.addWidget(slider, row, 1)
                grid.addWidget(txt_input, row, 2)

                self.inputs[model_name][p_name] = txt_input
                self.sliders[model_name][p_name] = slider
                row += 1

        left_layout.addLayout(grid)
        main_layout.addLayout(left_layout)

        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignCenter)

        palette_title = QLabel("<b>Палитра цветов</b>")
        palette_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(palette_title)

        self.color_palette = ColorPickerCanvas()
        self.color_palette.on_color_picked = self.on_palette_picked
        right_layout.addWidget(self.color_palette)

        right_layout.addSpacing(10)

        self.color_preview = QFrame()
        self.color_preview.setFixedSize(200, 50)
        self.color_preview.setStyleSheet(
            "background-color: rgb(255, 128, 0); border: 2px solid #555; border-radius: 8px;")
        right_layout.addWidget(self.color_preview)

        hex_layout = QHBoxLayout()
        hex_label = QLabel("HEX:")
        self.hex_input = QLineEdit()
        self.hex_input.setText("#FF8000")
        self.hex_input.setFixedWidth(100)
        self.hex_input.textEdited.connect(self.on_hex_edited)
        hex_layout.addWidget(hex_label)
        hex_layout.addWidget(self.hex_input)
        hex_layout.setAlignment(Qt.AlignCenter)
        right_layout.addLayout(hex_layout)

        main_layout.addLayout(right_layout)
        self.setCentralWidget(central_widget)

    def rgb_to_cmyk(self, r, g, b):
        r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
        k = 1.0 - max(r_norm, g_norm, b_norm)
        if k >= 1.0:
            return 0, 0, 0, 100
        c = (1.0 - r_norm - k) / (1.0 - k)
        m = (1.0 - g_norm - k) / (1.0 - k)
        y = (1.0 - b_norm - k) / (1.0 - k)
        return round(c * 100), round(m * 100), round(y * 100), round(k * 100)

    def cmyk_to_rgb(self, c, m, y, k):
        c_n, m_n, y_n, k_n = c / 100.0, m / 100.0, y / 100.0, k / 100.0
        r = 255 * (1.0 - c_n) * (1.0 - k_n)
        g = 255 * (1.0 - m_n) * (1.0 - k_n)
        b = 255 * (1.0 - y_n) * (1.0 - k_n)
        return max(0, min(255, round(r))), max(0, min(255, round(g))), max(0, min(255, round(b)))

    def rgb_to_hls(self, r, g, b):
        r_n, g_n, b_n = r / 255.0, g / 255.0, b / 255.0
        h, l, s = colorsys.rgb_to_hls(r_n, g_n, b_n)
        return round(h * 360), round(l * 100), round(s * 100)

    def hls_to_rgb(self, h, l, s):
        h_n, l_n, s_n = h / 360.0, l / 100.0, s / 100.0
        r_n, g_n, b_n = colorsys.hls_to_rgb(h_n, l_n, s_n)
        return max(0, min(255, round(r_n * 255))), max(0, min(255, round(g_n * 255))), max(0,
                                                                                           min(255, round(b_n * 255)))

    def update_all_from_rgb(self):
        if self.updating:
            return
        self.updating = True

        r, g, b = self.current_rgb
        c, m, y, k = self.rgb_to_cmyk(r, g, b)
        h, l, s = self.rgb_to_hls(r, g, b)

        values = {
            "RGB": {"R": r, "G": g, "B": b},
            "CMYK": {"C": c, "M": m, "Y": y, "K": k},
            "HLS": {"H": h, "L": l, "S": s}
        }

        for model_name, params in values.items():
            for p_name, val in params.items():
                slider = self.sliders[model_name][p_name]
                slider.blockSignals(True)
                slider.setValue(val)
                slider.blockSignals(False)

                txt_input = self.inputs[model_name][p_name]
                if not txt_input.hasFocus():
                    txt_input.blockSignals(True)
                    txt_input.setText(str(val))
                    txt_input.blockSignals(False)

        hex_val = f"#{r:02X}{g:02X}{b:02X}"
        self.color_preview.setStyleSheet(f"background-color: {hex_val}; border: 2px solid #555; border-radius: 8px;")

        if not self.hex_input.hasFocus():
            self.hex_input.blockSignals(True)
            self.hex_input.setText(hex_val)
            self.hex_input.blockSignals(False)

        self.color_palette.update_marker_from_rgb(r, g, b)

        self.updating = False

    def on_slider_changed(self, model_name, param_name, value):
        if self.updating:
            return

        txt_input = self.inputs[model_name][param_name]
        if not txt_input.hasFocus():
            txt_input.blockSignals(True)
            txt_input.setText(str(value))
            txt_input.blockSignals(False)

        try:
            if model_name == "RGB":
                r = self.sliders["RGB"]["R"].value()
                g = self.sliders["RGB"]["G"].value()
                b = self.sliders["RGB"]["B"].value()
                self.current_rgb = [r, g, b]
            elif model_name == "CMYK":
                c = self.sliders["CMYK"]["C"].value()
                m = self.sliders["CMYK"]["M"].value()
                y = self.sliders["CMYK"]["Y"].value()
                k = self.sliders["CMYK"]["K"].value()
                self.current_rgb = list(self.cmyk_to_rgb(c, m, y, k))
            elif model_name == "HLS":
                h = self.sliders["HLS"]["H"].value()
                l = self.sliders["HLS"]["L"].value()
                s = self.sliders["HLS"]["S"].value()
                self.current_rgb = list(self.hls_to_rgb(h, l, s))

            self.update_all_from_rgb()
        except ValueError:
            pass

    def on_text_changed(self, model_name, param_name, text):
        if self.updating or not text:
            return
        try:
            val = int(text)
            max_val = 360 if (model_name == "HLS" and param_name == "H") else (255 if model_name == "RGB" else 100)
            if 0 <= val <= max_val:
                slider = self.sliders[model_name][param_name]
                slider.blockSignals(True)
                slider.setValue(val)
                slider.blockSignals(False)
                self.on_slider_changed(model_name, param_name, val)
        except ValueError:
            pass

    def on_hex_edited(self, text):
        if self.updating:
            return
        
        if text.startswith("#") and len(text) == 7:
            try:
                color = QColor(text)
                if color.isValid():
                    self.current_rgb = [color.red(), color.green(), color.blue()]
                    self.update_all_from_rgb()
            except ValueError:
                pass

    def on_palette_picked(self, rgb):
        if self.updating:
            return
        self.current_rgb = rgb
        self.update_all_from_rgb()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ColorConverterApp()
    window.show()
    sys.exit(app.exec_())