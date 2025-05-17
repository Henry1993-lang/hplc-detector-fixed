
import sys
import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (QTextEdit,
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QFileDialog, QLabel, QComboBox, QMessageBox
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.signal import find_peaks, peak_widths
import matplotlib.pyplot as plt

class HPLCAnalyzer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HPLC Peak Analyzer (PyQt6)")
        self.setGeometry(200, 200, 1000, 600)

        self.layout = QVBoxLayout()

        self.label = QLabel("Select Radioisotope:")
        self.combo = QComboBox()
        self.combo.addItems(["18F", "11C"])

        self.load_button = QPushButton("Select CSV File")
        self.load_button.clicked.connect(self.load_csv)

        self.canvas = FigureCanvas(Figure(figsize=(10, 6)))
        self.ax = self.canvas.figure.add_subplot(111)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.combo)
        self.layout.addWidget(self.load_button)
        self.layout.addWidget(self.canvas)

        self.summary_box = QTextEdit()
        self.summary_box.setReadOnly(True)
        self.layout.addWidget(self.summary_box)
        self.setLayout(self.layout)

    def load_csv(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV files (*.csv)")
        if not file_name:
            return

        isotope = self.combo.currentText()
        half_life = {"18F": 110 * 60, "11C": 20.33 * 60}
        decay_constant = np.log(2) / half_life[isotope]

        try:
            df = pd.read_csv(file_name, encoding="shift-jis")
            df["日時"] = pd.to_datetime(df["日時"].str.replace(";", ":"), format="%Y/%m/%d %H:%M:%S")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read CSV: {e}")
            return

        ri6_col = next((col for col in df.columns if "RI6" in col), None)
        if not ri6_col:
            QMessageBox.warning(self, "Warning", "No 'RI6' column found in CSV.")
            return

        self.ax.clear()

        peaks, _ = find_peaks(df[ri6_col], height=20, distance=10, prominence=5, width=5)
        results_half = peak_widths(df[ri6_col], peaks, rel_height=0.88)

        self.ax.plot(df["日時"], df[ri6_col], label=ri6_col)
        ri5_col = next((col for col in df.columns if "RI5" in col), None)
        uv_col = next((col for col in df.columns if "UV" in col), None)
        if ri5_col:
            self.ax.plot(df["日時"], df[ri5_col], label=ri5_col)
        if uv_col:
            self.ax.plot(df["日時"], df[uv_col], label=uv_col)
    
        self.ax.plot(df["日時"].iloc[peaks], df[ri6_col].iloc[peaks], "x", label="Peaks", color="red")

        all_corrected_areas = []
        for i, peak in enumerate(peaks):
            left = int(results_half[2][i])
            right = int(results_half[3][i])
            self.ax.fill_between(df["日時"].iloc[left:right], df[ri6_col].iloc[left:right], alpha=0.3)
            x = (df["日時"].iloc[left:right] - df["日時"].iloc[left]).dt.total_seconds().values
            y = df[ri6_col].iloc[left:right].values
            elapsed_time = x[-1] if len(x) > 0 else 0
            corrected_y = y * np.exp(decay_constant * (x - elapsed_time))
            area = np.trapz(corrected_y, x)
            all_corrected_areas.append(area)
            self.ax.text(df["日時"].iloc[peak], float(df[ri6_col].iloc[peak]) + 0.05 * max(df[ri6_col]), f"{i+1}")

        total = sum(all_corrected_areas)
        summary = [f"Peak {i+1} Area: {area:.1f} ({(area/total*100):.1f}%)" for i, area in enumerate(all_corrected_areas)]
        self.ax.set_title("HPLC Peak Detection")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Signal Intensity")
        self.ax.legend()
        self.ax.grid(True)
        self.canvas.draw()

        self.summary_box.setText("\n".join(summary))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HPLCAnalyzer()
    window.show()
    sys.exit(app.exec())
