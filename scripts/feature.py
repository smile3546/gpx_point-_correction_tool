import os
import json
import pandas as pd
import numpy as np
import re
from math import radians, sin, cos, sqrt, atan2, degrees, atan


def haversine(lat1, lon1, lat2, lon2):
    """
    計算兩個GPS座標點之間的直線距離（公尺）。
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    r_earth = 6371000  # 地球半徑（公尺）
    return c * r_earth


def calculate_features(filepath):
    """
    對單一GeoJSON檔案計算所有指定的特徵。
    優化計算方式以提升精確度和效率。
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])

    # 1. 讀取路線與點的資料
    try:
        # 優先使用 LineString 作為距離計算基準
        line_string = None
        for f in features:
            if f["geometry"]["type"] == "LineString":
                line_string = f["geometry"]["coordinates"]
                break

        # 收集有效的點位資料
        points = []
        for f in features:
            if (
                f["geometry"]["type"] == "Point"
                and f["properties"].get("elevation") is not None
                and f["properties"].get("order") is not None
            ):
                points.append(f)

        # 按 order 排序
        points.sort(key=lambda p: int(p["properties"]["order"]))

    except (KeyError, TypeError, ValueError) as e:
        return {"錯誤": f"檔案格式不符或缺少必要資料: {str(e)}"}

    if len(points) < 2:
        return {"錯誤": "有效的資料點少於2個，無法計算坡度等資訊"}

    # 2. 計算路線基本屬性 - 水平總長度
    total_distance = 0
    if line_string and len(line_string) > 1:
        # 使用 LineString 計算更精確的總距離
        for i in range(len(line_string) - 1):
            lon1, lat1 = line_string[i]
            lon2, lat2 = line_string[i + 1]
            total_distance += haversine(lat1, lon1, lat2, lon2)
    else:
        # 備用方案：使用點位計算距離
        coords = [p["geometry"]["coordinates"] for p in points]
        for i in range(len(coords) - 1):
            lon1, lat1 = coords[i]
            lon2, lat2 = coords[i + 1]
            total_distance += haversine(lat1, lon1, lat2, lon2)

    # 3. 海拔相關特徵計算
    elevations = [float(p["properties"]["elevation"]) for p in points]
    coords = [p["geometry"]["coordinates"] for p in points]

    min_elevation = min(elevations)
    max_elevation = max(elevations)
    elevation_range = max_elevation - min_elevation
    high_elevation = max_elevation > 2438  # 高山症風險評估指標

    # 4. 海拔變化與坡度計算優化
    segment_distances = []
    elevation_changes = []
    slopes_percent = []
    slopes_degrees = []

    cumulative_up = 0  # 累積上升
    cumulative_down = 0  # 累積下降
    max_slope_info = {
        "slope_percent": 0,
        "slope_degrees": 0,
        "point": None,
        "segment_idx": 0,
    }

    for i in range(len(points) - 1):
        # 計算段落距離
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        segment_dist = haversine(lat1, lon1, lat2, lon2)
        segment_distances.append(segment_dist)

        # 計算海拔變化
        ele_change = elevations[i + 1] - elevations[i]
        elevation_changes.append(ele_change)

        # 累積上升/下降
        if ele_change > 0:
            cumulative_up += ele_change
        else:
            cumulative_down += abs(ele_change)

        # 計算坡度（避免除零錯誤）
        if segment_dist > 1:  # 至少1公尺才計算坡度
            slope_percent = (ele_change / segment_dist) * 100
            slope_degrees = degrees(atan(slope_percent / 100))

            slopes_percent.append(slope_percent)
            slopes_degrees.append(slope_degrees)

            # 記錄最大坡度
            if abs(slope_percent) > abs(max_slope_info["slope_percent"]):
                max_slope_info.update(
                    {
                        "slope_percent": slope_percent,
                        "slope_degrees": slope_degrees,
                        "point": (lat2, lon2),
                        "segment_idx": i,
                    }
                )

    # 5. 計算整體海拔變化率
    if total_distance > 0:
        elevation_change = (
            (cumulative_up - cumulative_down) / total_distance * 1000
        )  # 每公里變化
    else:
        elevation_change = 0

    # 6. 坡度統計分析
    if slopes_degrees:
        slope_std_dev = np.std(slopes_degrees)
        slope_variance = np.var(slopes_degrees)
        max_slope_degrees = max_slope_info["slope_degrees"]
        max_slope_percent = max_slope_info["slope_percent"]
    else:
        slope_std_dev = 0
        slope_variance = 0
        max_slope_degrees = 0
        max_slope_percent = 0

    # 7. 坡度頻率分布（使用角度）
    if slopes_degrees:
        bins = [-np.inf, -15, -10, -5, -1, 1, 5, 10, 15, np.inf]
        labels = [
            "<-15°",
            "-15°~-10°",
            "-10°~-5°",
            "-5°~-1°",
            "-1°~1°",
            "1°~5°",
            "5°~10°",
            "10°~15°",
            ">15°",
        ]

        freq_dist = pd.cut(
            slopes_degrees, bins=bins, labels=labels, right=False
        ).value_counts()
        freq_dist_percent = (freq_dist / len(slopes_degrees) * 100).round(2)
        freq_dist_dict = freq_dist_percent.to_dict()
    else:
        freq_dist_dict = {}

    # 8. 格式化最大坡度點位資訊
    max_slope_point = (
        f"({max_slope_info['point'][0]:.6f}, {max_slope_info['point'][1]:.6f})"
        if max_slope_info["point"]
        else "N/A"
    )

    return {
        "distance": round(total_distance, 2),
        "elevation_range": round(elevation_range, 1),
        "elevation_change": round(elevation_change, 2),
        "elevation_gain": round(cumulative_up, 1),
        "elevation_loss": round(cumulative_down, 1),
        "high_elevation": high_elevation,
        "max_slope_percent": round(max_slope_percent, 2),
        "max_slope_degrees": round(max_slope_degrees, 2),
        "max_slope_point": max_slope_point,
        "slope_std_dev": round(slope_std_dev, 2),
        "slope_variance": round(slope_variance, 2),
        "slope_freq_dist": freq_dist_dict,
    }


def main():
    """
    主程式：尋找、處理所有GeoJSON檔案並產生報告。
    """
    # 設定目標路徑
    target_path = os.path.join("..", "最終json_txt", "1.切分過的路線")

    # 檢查路徑是否存在，如果不存在則嘗試其他可能的路徑
    if not os.path.exists(target_path):
        # 嘗試從當前目錄開始
        alt_path = os.path.join("最終json_txt", "1.切分過的路線")
        if os.path.exists(alt_path):
            target_path = alt_path
        else:
            # 嘗試絕對路徑方式
            current_dir = os.getcwd()
            parent_dir = os.path.dirname(current_dir)
            abs_path = os.path.join(parent_dir, "最終json_txt", "1.切分過的路線")
            if os.path.exists(abs_path):
                target_path = abs_path

    print(f"使用路徑: {os.path.abspath(target_path)}")

    try:
        # 收集所有子資料夾中的 geojson 檔案
        all_files = []
        for route_folder in os.listdir(target_path):
            route_folder_path = os.path.join(target_path, route_folder)
            if os.path.isdir(route_folder_path):
                for file in os.listdir(route_folder_path):
                    if file.endswith(".geojson"):
                        file_info = {
                            "filename": file,
                            "filepath": os.path.join(route_folder_path, file),
                            "route_folder": route_folder,
                        }
                        all_files.append(file_info)

        if not all_files:
            raise FileNotFoundError
    except FileNotFoundError:
        print(f"錯誤：在路徑 '{target_path}' 下找不到任何 '.geojson' 檔案。")
        return
    except Exception as e:
        print(f"讀取檔案時發生錯誤：{str(e)}")
        return

    def extract_sort_key(file_info):
        """提取排序鍵值：先按路線資料夾，再按part編號"""
        route_folder = file_info["route_folder"]
        filename = file_info["filename"]

        # 提取 part 編號
        part_match = re.search(r"part(\d+)", filename)
        part_number = int(part_match.group(1)) if part_match else 0

        return (route_folder, part_number)

    sorted_files = sorted(all_files, key=extract_sort_key)

    print(f"找到並依序處理以下檔案: {[f['filename'] for f in sorted_files]}")

    results = []
    for file_info in sorted_files:
        features = calculate_features(file_info["filepath"])
        features["filename"] = file_info["filename"]
        features["route_folder"] = file_info["route_folder"]

        # 提取 part 編號
        part_match = re.search(r"part(\d+)", file_info["filename"])
        features["part_number"] = int(part_match.group(1)) if part_match else 0

        results.append(features)

    # 建立並美化 DataFrame 報告
    df = pd.DataFrame(results)

    # 重新排列欄位順序
    if "錯誤" not in df.columns:
        df = df[
            [
                "route_folder",
                "part_number",
                "filename",
                "distance",
                "elevation_range",
                "elevation_change",
                "elevation_gain",
                "elevation_loss",
                "high_elevation",
                "max_slope_percent",
                "max_slope_degrees",
                "max_slope_point",
                "slope_std_dev",
                "slope_variance",
                "slope_freq_dist",
            ]
        ]

        # 格式化浮點數顯示
        pd.options.display.float_format = "{:.2f}".format
        df["max_slope_point"] = df["max_slope_point"].astype(str)
        df["slope_freq_dist"] = df["slope_freq_dist"].astype(str)

    print("\n--- 路線特徵報告 ---")
    print(df.to_string())

    # 儲存報告至CSV檔案
    csv_filename = "feature_report.csv"
    df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
    print(f"\n報告已成功儲存至 {csv_filename}")


if __name__ == "__main__":
    main()
