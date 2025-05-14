import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog, Toplevel, Text, Scrollbar, RIGHT, Y, BOTH
from scipy.signal import find_peaks, peak_widths
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# 日本語フォントの設定
plt.rcParams['font.family'] = 'IPAexGothic'

def select_file():
    """ファイルダイアログを表示してCSVファイルを選択"""
    root = Tk()
    root.withdraw()  # メインウィンドウを非表示
    file_path = filedialog.askopenfilename(
        filetypes=[("CSV files", "*.csv")], 
        title="Select a CSV file"
    )
    root.destroy()
    return file_path

def plot_graph_and_display_data():
    # 減衰定数の設定 (18Fの半減期から計算)
    decay_constant = np.log(2) / (110 * 60)  # 単位: 秒

    # CSVファイルの読み込み（ファイルダイアログから選択）
    file_path = select_file()

    # ファイルが選択された場合にのみ処理を行う
    if file_path:
        try:
            # CSVファイルを適切なエンコードで読み込み
            data = pd.read_csv(file_path, encoding='shift-jis')  # もしくは 'ISO-8859-1', 'utf-8'
        except UnicodeDecodeError:
            print("エンコーディングの問題が発生しました。異なるエンコーディングで再試行してください。")
            return

        # '日時'カラムの時間部分のセパレータを置換してから日付時刻型に変換
        data['日時'] = pd.to_datetime(data['日時'].str.replace(';', ':'), format='%Y/%m/%d %H:%M:%S')

        # Seabornのテーマ設定
        sns.set_theme()

        # RI6C4のデータからピークを検出
        peaks, _ = find_peaks(data['RI6'], height=20, distance=10, prominence=5, width=5)
        
        # ピークの幅を取得（widths 関数でピークの左端と右端を取得）
        results_half = peak_widths(data['RI6'], peaks, rel_height=0.88)

        # 補正前と補正後の面積を格納するリスト
        original_peak_areas = []
        corrected_peak_areas = []

        # Tkinterウィンドウ内でグラフを表示
        root = Tk()
        root.title("グラフとデータ表示")

        fig, ax = plt.subplots(figsize=(10, 6))

        # 折れ線グラフの作成
        sns.lineplot(data=data, x='日時', y='UV_DATA', label='UV_DATAC4', color='black', ax=ax)
        sns.lineplot(data=data, x='日時', y='RI6', label='RI6', color='red', ax=ax)
        sns.lineplot(data=data, x='日時', y='RI5', label='RI5', color='navy', ax=ax)

        # 検出されたピークを赤色でプロット
        ax.plot(data['日時'][peaks], data['RI6'][peaks], "ro", label='Peaks')

        # ピーク範囲の表示と塗りつぶし
        for i, peak in enumerate(peaks):
            left_ip = int(results_half[2][i])  # ピークの左端のインデックス
            right_ip = int(results_half[3][i])  # ピークの右端のインデックス

            # 左端と右端に縦線を追加
            ax.axvline(x=data['日時'][left_ip], color='green', linestyle='--', label='Peak Start' if i == 0 else "")
            ax.axvline(x=data['日時'][right_ip], color='orange', linestyle='--', label='Peak End' if i == 0 else "")

            # ピーク面積の計算
            x = (data['日時'][left_ip:right_ip] - data['日時'][left_ip]).dt.total_seconds().values
            y = data['RI6'][left_ip:right_ip].values

            # 補正前の面積
            original_area = np.trapz(y, x)
            original_peak_areas.append(original_area)

            # 減衰補正
            elapsed_time = (data['日時'][peak] - data['日時'].iloc[0]).total_seconds()
            decay_correction = np.exp(decay_constant * elapsed_time)
            corrected_area = original_area * decay_correction
            corrected_peak_areas.append(corrected_area)

            # 塗りつぶし
            ax.fill_between(data['日時'][left_ip:right_ip], 0, data['RI6'][left_ip:right_ip], color='red', alpha=0.5)

            # ピークの中心付近にテキストを表示、位置を調整
            peak_center = data['日時'][left_ip:right_ip].iloc[len(data['日時'][left_ip:right_ip]) // 2]
            offset = (i % 2) * 0.7 + 0.8  # 偶数と奇数でオフセットを調整
            ax.text(peak_center, max(y) * (0.5+ offset), f"Area {i+1}", ha='center', va='center', fontsize=10, color='black')

        # x軸とy軸のラベルを非表示
        ax.set_xlabel('')
        ax.set_ylabel('')

        # Tkinterウィンドウ内にグラフを埋め込む
        canvas = FigureCanvasTkAgg(fig, master=root)
        canvas.draw()
        canvas.get_tk_widget().pack()

        # 面積とパーセンテージの表示
        results_window = Toplevel(root)
        results_window.title("ピーク面積と放射化学純度")

        # テキストウィジェットを使って結果を表示
        text_widget = Text(results_window, height=15, width=50)
        text_widget.pack(side="left", fill=BOTH, expand=True)

        scrollbar = Scrollbar(results_window)
        scrollbar.pack(side=RIGHT, fill=Y)
        text_widget.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=text_widget.yview)

        # ピークごとの面積とパーセンテージを表示
        text_widget.insert('end', "Percentage of each peak relative to total corrected area:\n")
        total_corrected_area = sum(corrected_peak_areas)
        for i, (original_area, corrected_area) in enumerate(zip(original_peak_areas, corrected_peak_areas)):
            percentage = (corrected_area / total_corrected_area) * 100
            text_widget.insert('end', f"Peak {i+1}: {percentage:.2f}% (Original Area: {original_area:.2f}, Corrected Area: {corrected_area:.2f})\n")

        root.mainloop()

    else:
        print("No file was selected.")

# ファイルを選択し、グラフとデータを表示
plot_graph_and_display_data()

if __name__ == "__main__":
    plot_graph_and_display_data()

