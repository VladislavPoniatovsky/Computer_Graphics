import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def pad_image(img_arr, pad_size):
    return np.pad(img_arr, ((pad_size, pad_size), (pad_size, pad_size)), mode='reflect')


def box_filter(img_arr, kernel_size=3):
    pad = kernel_size // 2
    padded = pad_image(img_arr, pad)
    h, w = img_arr.shape
    output = np.zeros((h, w), dtype=np.float32)

    for i in range(h):
        for j in range(w):
            region = padded[i:i + kernel_size, j:j + kernel_size]
            output[i, j] = np.mean(region)

    return np.clip(output, 0, 255).astype(np.uint8)


def gaussian_filter(img_arr, kernel_size=3, sigma=1.5):
    pad = kernel_size // 2
    ax = np.linspace(-(kernel_size // 2), kernel_size // 2, kernel_size)
    gauss = np.exp(-0.5 * np.square(ax / sigma))
    kernel = np.outer(gauss, gauss)
    kernel = kernel / np.sum(kernel)

    padded = pad_image(img_arr, pad)
    h, w = img_arr.shape
    output = np.zeros((h, w), dtype=np.float32)

    for i in range(h):
        for j in range(w):
            region = padded[i:i + kernel_size, j:j + kernel_size]
            output[i, j] = np.sum(region * kernel)

    return np.clip(output, 0, 255).astype(np.uint8)


def threshold_manual(img_arr, T):
    binary = np.zeros_like(img_arr, dtype=np.uint8)
    binary[img_arr >= T] = 255
    return binary


def otsu_threshold(img_arr):
    hist, _ = np.histogram(img_arr.ravel(), bins=256, range=(0, 256))
    total_pixels = img_arr.size

    current_max = 0
    best_thresh = 0
    sum_all = np.dot(np.arange(256), hist)
    sum_b = 0
    w_b = 0

    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total_pixels - w_b
        if w_f == 0:
            break

        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_all - sum_b) / w_f

        var_between = w_b * w_f * ((m_b - m_f) ** 2)

        if var_between > current_max:
            current_max = var_between
            best_thresh = t

    return threshold_manual(img_arr, best_thresh), best_thresh


def histogram_threshold(img_arr, delta_t=0.5):
    T = np.mean(img_arr)

    while True:
        g1 = img_arr[img_arr >= T]
        g2 = img_arr[img_arr < T]

        m1 = np.mean(g1) if len(g1) > 0 else 0
        m2 = np.mean(g2) if len(g2) > 0 else 0

        T_next = 0.5 * (m1 + m2)
        if abs(T - T_next) < delta_t:
            break
        T = T_next

    final_thresh = int(np.round(T))
    return threshold_manual(img_arr, final_thresh), final_thresh


class ImageProcessingApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1050x650")

        self.current_img = None
        self.processed_img = None

        self._setup_ui()

    def _setup_ui(self):
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(control_frame, text="1. Загрузка изображения", font=('Helvetica', 11, 'bold')).pack(anchor=tk.W,
                                                                                                      pady=(0, 5))

        btn_load = ttk.Button(control_frame, text="Выбрать файл...", command=self.load_image)
        btn_load.pack(fill=tk.X, pady=2)

        ttk.Separator(control_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        ttk.Label(control_frame, text="2. Низкочастотные фильтры", font=('Helvetica', 11, 'bold')).pack(anchor=tk.W,
                                                                                                        pady=(0, 5))

        ttk.Label(control_frame, text="Размер ядра:").pack(anchor=tk.W)
        self.kernel_spinner = ttk.Spinbox(control_frame, from_=3, to=15, increment=2)
        self.kernel_spinner.set(3)
        self.kernel_spinner.pack(fill=tk.X, pady=2)

        btn_box = ttk.Button(control_frame, text="Усредняющий (Box) фильтр", command=self.apply_box)
        btn_box.pack(fill=tk.X, pady=2)

        btn_gauss = ttk.Button(control_frame, text="Фильтр Гаусса (σ=1.5)", command=self.apply_gauss)
        btn_gauss.pack(fill=tk.X, pady=2)

        ttk.Separator(control_frame, orient='horizontal').pack(fill=tk.X, pady=10)


        ttk.Label(control_frame, text="3. Глобальная пороговая обработка", font=('Helvetica', 11, 'bold')).pack(
            anchor=tk.W, pady=(0, 5))

        btn_otsu = ttk.Button(control_frame, text="Метод Оцу", command=self.apply_otsu)
        btn_otsu.pack(fill=tk.X, pady=2)

        btn_hist_thresh = ttk.Button(control_frame, text="Метод на основе гистограммы",
                                     command=self.apply_histogram_method)
        btn_hist_thresh.pack(fill=tk.X, pady=2)

        ttk.Separator(control_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        self.lbl_info = ttk.Label(control_frame, text="Порог: —", font=('Helvetica', 10, 'italic'))
        self.lbl_info.pack(anchor=tk.W, pady=5)

        self.fig, (self.ax_orig, self.ax_proc) = plt.subplots(1, 2, figsize=(7, 4.5))
        self.fig.tight_layout(pad=3.0)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._reset_plots()

    def _reset_plots(self):
        self.ax_orig.clear()
        self.ax_proc.clear()
        self.ax_orig.set_title("Исходное изображение")
        self.ax_proc.set_title("Результат обработки")
        self.ax_orig.axis('off')
        self.ax_proc.axis('off')
        self.canvas.draw()

    def update_plots(self, title_proc="Результат"):
        self.ax_orig.clear()
        self.ax_proc.clear()

        self.ax_orig.imshow(self.current_img, cmap='gray', vmin=0, vmax=255)
        self.ax_orig.set_title("Исходное изображение")
        self.ax_orig.axis('off')

        self.ax_proc.imshow(self.processed_img, cmap='gray', vmin=0, vmax=255)
        self.ax_proc.set_title(title_proc)
        self.ax_proc.axis('off')

        self.canvas.draw()

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff")])
        if path:
            img = Image.open(path).convert('L')
            self.current_img = np.array(img)
            self.processed_img = self.current_img.copy()
            self.lbl_info.config(text="Порог: —")
            self.update_plots("Результат обработки")

    def apply_box(self):
        if self.current_img is None:
            messagebox.showwarning("Ошибка", "Сначала загрузите изображение!")
            return
        k_size = int(self.kernel_spinner.get())
        if k_size % 2 == 0:
            k_size += 1
        self.processed_img = box_filter(self.current_img, kernel_size=k_size)
        self.update_plots(f"Box Filter ({k_size}x{k_size})")

    def apply_gauss(self):
        if self.current_img is None:
            messagebox.showwarning("Ошибка", "Сначала загрузите изображение!")
            return
        k_size = int(self.kernel_spinner.get())
        if k_size % 2 == 0:
            k_size += 1
        self.processed_img = gaussian_filter(self.current_img, kernel_size=k_size, sigma=1.5)
        self.update_plots(f"Gaussian Filter ({k_size}x{k_size})")

    def apply_otsu(self):
        if self.current_img is None:
            messagebox.showwarning("Ошибка", "Сначала загрузите изображение!")
            return
        binary, t = otsu_threshold(self.current_img)
        self.processed_img = binary
        self.lbl_info.config(text=f"Порог Отсу T = {t}")
        self.update_plots(f"Метод Отсу (T={t})")

    def apply_histogram_method(self):
        if self.current_img is None:
            messagebox.showwarning("Ошибка", "Сначала загрузите изображение!")
            return
        binary, t = histogram_threshold(self.current_img)
        self.processed_img = binary
        self.lbl_info.config(text=f"Порог по гистограмме T = {t}")
        self.update_plots(f"Метод гистограммы (T={t})")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessingApp(root)
    root.mainloop()