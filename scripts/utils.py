import pandas as pd
from pathlib import Path
from typing import List, Tuple

def load_txt_points(txt_file: Path) -> pd.DataFrame:
    """從 TXT 檔案讀取資料，並確保欄位名稱正確。"""
    if not txt_file.exists():
        print(f"檔案不存在: {txt_file}")
        return pd.DataFrame()
    try:
        # 假設 TXT 檔案包含 'latitude', 'longitude', 'elevation' 欄位
        df = pd.read_csv(txt_file)
        if not all(col in df.columns for col in ['latitude', 'longitude', 'elevation']):
            raise ValueError("TXT 檔案欄位不正確，應包含 'latitude', 'longitude', 'elevation'。")
        return df
    except Exception as e:
        print(f"讀取 TXT 檔案 {txt_file} 時發生錯誤: {e}")
        return pd.DataFrame()

def load_communication_points(txt_file: Path) -> List[Tuple[str, float, float, float]]:
    """從原始 TXT 檔案讀取通訊點資料。"""
    if not txt_file.exists():
        return []
    try:
        df = pd.read_csv(txt_file, sep="\t")
        points = []
        for _, row in df.iterrows():
            lat = float(str(row["緯度"]).replace("°", "").strip())
            lon = float(str(row["經度"]).replace("°", "").strip())
            ele = float(str(row["海拔（約）"]).replace("m", "").strip())
            label = f"{row['步道名稱']} {row['路標指示']}"
            points.append((label, lat, lon, ele))
        return points
    except Exception as e:
        print(f"讀取通訊點時發生錯誤，請檢查 TXT 檔案格式: {e}")
        return []