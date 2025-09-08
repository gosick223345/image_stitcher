# image_stitcher

拖曳圖片即可上下/左右拼接，支援 **等比例對齊、最大/最小基準、間距、背景色、即時預覽（可隱藏/顯示）、單次/直接輸出、自動 reset** 的 Python GUI（Tkinter + Pillow）。

## 功能
<img width="1099" height="673" alt="image" src="https://github.com/user-attachments/assets/c547ccb2-0bbf-4ea3-8c10-d18095e50995" />
- 拖曳多張圖片或整個資料夾
- 上下/左右拼接與等比例對齊（直向=同寬、橫向=同高；可選取最大或最小邊作為基準）
- 設定間距與背景色
- **即時預覽面板**（可縮放、可捲動；可一鍵隱藏/顯示）
- 輸出模式
  - 單次輸出：跳存檔視窗
  - 直接輸出：選資料夾與副檔名，檔名自動 `1,2,3…` 遞增（可顯示成功訊息、不跳視窗）
- **自動 reset**：輸出成功後清空清單並把編號重置為 1

## 安裝
```bash
pip install -r requirements.txt
# Linux 如需 Tkinter：
# Ubuntu/Debian: sudo apt-get install python3-tk
```

## 使用
```bash
python image_stitcher.py
```

## 授權
MIT
