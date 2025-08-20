import pandas as pd
import json
import os
import math
from pathlib import Path
from typing import List, Dict, Tuple, Any


def calculate_distance(lat1, lon1, lat2, lon2):
    """計算兩點間的地理距離（公尺），使用 Haversine 公式"""
    # 轉換為弧度
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine 公式
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    # 地球半徑（公尺）
    earth_radius = 6371000
    return earth_radius * c


def interpolate_missing_data_df(df: pd.DataFrame) -> pd.DataFrame:
    """對 DataFrame 中缺少時間和高度的點位進行插值"""
    from datetime import datetime

    # 建立副本避免修改原始資料
    df_copy = df.copy()

    # 處理高度插值
    for i in range(len(df_copy)):
        if (
            pd.isna(df_copy.iloc[i].get("海拔（約）"))
            or str(df_copy.iloc[i].get("海拔（約）")).strip() == "N/A"
        ):
            # 找前一個有高度的點
            prev_idx = i - 1
            while prev_idx >= 0 and (
                pd.isna(df_copy.iloc[prev_idx].get("海拔（約）"))
                or str(df_copy.iloc[prev_idx].get("海拔（約）")).strip() == "N/A"
            ):
                prev_idx -= 1

            # 找後一個有高度的點
            next_idx = i + 1
            while next_idx < len(df_copy) and (
                pd.isna(df_copy.iloc[next_idx].get("海拔（約）"))
                or str(df_copy.iloc[next_idx].get("海拔（約）")).strip() == "N/A"
            ):
                next_idx += 1

            # 如果前後都有高度，進行插值
            if prev_idx >= 0 and next_idx < len(df_copy):
                prev_point = df_copy.iloc[prev_idx]
                next_point = df_copy.iloc[next_idx]

                # 計算累積距離
                total_distance = 0
                current_distance = 0

                for j in range(prev_idx, next_idx):
                    dist = calculate_distance(
                        float(df_copy.iloc[j]["緯度"]),
                        float(df_copy.iloc[j]["經度"]),
                        float(df_copy.iloc[j + 1]["緯度"]),
                        float(df_copy.iloc[j + 1]["經度"]),
                    )
                    total_distance += dist
                    if j < i:
                        current_distance += dist

                # 高度插值
                if total_distance > 0:
                    ratio = current_distance / total_distance
                    prev_ele = float(prev_point["海拔（約）"])
                    next_ele = float(next_point["海拔（約）"])
                    interpolated_ele = prev_ele + (next_ele - prev_ele) * ratio
                    df_copy.iloc[i, df_copy.columns.get_loc("海拔（約）")] = round(
                        interpolated_ele, 1
                    )

    # 處理時間插值（如果有時間欄位）
    if "時間" in df_copy.columns:
        for i in range(len(df_copy)):
            if pd.isna(df_copy.iloc[i].get("時間")) or str(
                df_copy.iloc[i].get("時間")
            ).strip() in ["", "N/A"]:
                # 找前一個有時間的點
                prev_idx = i - 1
                while prev_idx >= 0 and (
                    pd.isna(df_copy.iloc[prev_idx].get("時間"))
                    or str(df_copy.iloc[prev_idx].get("時間")).strip() in ["", "N/A"]
                ):
                    prev_idx -= 1

                # 找後一個有時間的點
                next_idx = i + 1
                while next_idx < len(df_copy) and (
                    pd.isna(df_copy.iloc[next_idx].get("時間"))
                    or str(df_copy.iloc[next_idx].get("時間")).strip() in ["", "N/A"]
                ):
                    next_idx += 1

                # 如果前後都有時間，進行插值
                if prev_idx >= 0 and next_idx < len(df_copy):
                    prev_point = df_copy.iloc[prev_idx]
                    next_point = df_copy.iloc[next_idx]

                    # 計算累積距離
                    total_distance = 0
                    current_distance = 0

                    for j in range(prev_idx, next_idx):
                        dist = calculate_distance(
                            float(df_copy.iloc[j]["緯度"]),
                            float(df_copy.iloc[j]["經度"]),
                            float(df_copy.iloc[j + 1]["緯度"]),
                            float(df_copy.iloc[j + 1]["經度"]),
                        )
                        total_distance += dist
                        if j < i:
                            current_distance += dist

                    # 時間插值
                    if total_distance > 0:
                        ratio = current_distance / total_distance
                        prev_time_str = str(prev_point["時間"])
                        next_time_str = str(next_point["時間"])

                        try:
                            prev_time = datetime.fromisoformat(
                                prev_time_str.replace("Z", "+00:00")
                            )
                            next_time = datetime.fromisoformat(
                                next_time_str.replace("Z", "+00:00")
                            )
                            time_diff = next_time - prev_time
                            interpolated_time = prev_time + time_diff * ratio
                            df_copy.iloc[
                                i, df_copy.columns.get_loc("時間")
                            ] = interpolated_time.isoformat().replace(
                                "+00:00", "+00:00"
                            )
                        except:
                            pass  # 如果時間格式有問題，跳過

    return df_copy


def read_points_file(points_path: Path) -> pd.DataFrame:
    """讀取 points.txt 檔案"""
    try:
        df = pd.read_csv(points_path, sep="\t", encoding="utf-8-sig")
        return df
    except Exception as e:
        print(f"讀取 {points_path} 失敗: {e}")
        return pd.DataFrame()


def read_geojson_file(geojson_path: Path) -> Dict[str, Any]:
    """讀取 route.geojson 檔案"""
    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"讀取 {geojson_path} 失敗: {e}")
        return {}


def read_original_comm_points(route_name: str) -> List[Dict[str, Any]]:
    """讀取原始通訊點資料"""
    raw_txt_path = Path(f"./data_raw/txt/{route_name}.txt")

    if not raw_txt_path.exists():
        print(f"  找不到原始通訊點檔案: {raw_txt_path}")
        return []

    try:
        df = pd.read_csv(raw_txt_path, sep="\t", encoding="utf-8-sig")
        comm_points = []

        for idx, row in df.iterrows():
            comm_points.append(
                {
                    "name": row.get("路標指示", ""),
                    "lat": float(row.get("緯度", 0)),
                    "lon": float(row.get("經度", 0)),
                    "elevation": row.get("海拔（約）", None),
                }
            )

        print(
            f"  -> 讀取到 {len(comm_points)} 個原始通訊點: {[pt['name'] for pt in comm_points]}"
        )
        return comm_points

    except Exception as e:
        print(f"  讀取原始通訊點失敗: {e}")
        return []


def find_comm_points_in_original_route(
    df: pd.DataFrame, original_comm_points: List[Dict[str, Any]]
) -> List[Tuple[int, str, str]]:
    """在原始路線中找出通訊點位置（用於確定來回路線的切分點）"""
    comm_points = []

    # 為每個原始通訊點找到在原始路線中的對應位置
    for original_pt in original_comm_points:
        target_lat = original_pt["lat"]
        target_lon = original_pt["lon"]
        target_name = original_pt["name"]

        # 在 DataFrame 中尋找最接近的點
        min_distance = float("inf")
        best_match_idx = None
        best_match_order = None

        for idx, row in df.iterrows():
            row_lat = float(row.get("緯度", 0))
            row_lon = float(row.get("經度", 0))

            # 計算距離（簡單的歐幾里得距離）
            distance = (
                (row_lat - target_lat) ** 2 + (row_lon - target_lon) ** 2
            ) ** 0.5

            if distance < min_distance:
                min_distance = distance
                best_match_idx = idx
                best_match_order = str(row.get("順序", ""))

        if best_match_idx is not None:
            comm_points.append((best_match_idx, target_name, best_match_order))
            print(
                f"    找到通訊點 '{target_name}' 在原始路線索引 {best_match_idx} (順序: {best_match_order})"
            )

    # 按照在路線中的順序排列
    comm_points.sort(key=lambda x: x[0])

    print(
        f"  -> 在原始路線找到 {len(comm_points)} 個通訊點: {[f'{name}({order})' for _, name, order in comm_points]}"
    )
    return comm_points


def calculate_roundtrip_segments(
    roundtrip_route: pd.DataFrame,
    original_comm_indices: List[int],
    original_comm_points: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """計算來回路線的切分段落"""
    if len(original_comm_indices) < 2:
        print("  通訊點少於2個，無法切分")
        return []

    segments = []
    total_points = len(roundtrip_route)
    original_length = (total_points + 1) // 2  # 原始路線長度（來回路線去掉重複點）

    # 計算來回路線中的對應索引
    # 原始路線索引 -> 來回路線中的去程和回程索引
    def get_roundtrip_indices(original_idx):
        forward_idx = original_idx  # 去程索引不變
        backward_idx = total_points - 1 - original_idx  # 回程索引：總長度-1-原始索引
        return forward_idx, backward_idx

    # 生成所有切分段
    part_num = 1

    # 去程段落
    for i in range(len(original_comm_indices) - 1):
        start_original_idx = original_comm_indices[i]
        end_original_idx = original_comm_indices[i + 1]

        start_roundtrip_idx = start_original_idx
        end_roundtrip_idx = end_original_idx

        segment_data = roundtrip_route.iloc[
            start_roundtrip_idx : end_roundtrip_idx + 1
        ].copy()

        segment_info = {
            "part_number": part_num,
            "direction": "forward",
            "start_point": {
                "index": start_roundtrip_idx,
                "name": original_comm_points[i]["name"],
                "original_index": start_original_idx,
            },
            "end_point": {
                "index": end_roundtrip_idx,
                "name": original_comm_points[i + 1]["name"],
                "original_index": end_original_idx,
            },
            "data": segment_data,
            "point_count": len(segment_data),
        }

        segments.append(segment_info)
        print(
            f"    去程 Part {part_num}: {original_comm_points[i]['name']} → {original_comm_points[i + 1]['name']} ({len(segment_data)} 個點) [索引: {start_roundtrip_idx}-{end_roundtrip_idx}]"
        )
        part_num += 1

    # 回程段落（順序相反）
    for i in range(len(original_comm_indices) - 1, 0, -1):
        start_original_idx = original_comm_indices[i]
        end_original_idx = original_comm_indices[i - 1]

        start_roundtrip_idx = total_points - 1 - start_original_idx
        end_roundtrip_idx = total_points - 1 - end_original_idx

        segment_data = roundtrip_route.iloc[
            start_roundtrip_idx : end_roundtrip_idx + 1
        ].copy()

        segment_info = {
            "part_number": part_num,
            "direction": "backward",
            "start_point": {
                "index": start_roundtrip_idx,
                "name": original_comm_points[i]["name"],
                "original_index": start_original_idx,
            },
            "end_point": {
                "index": end_roundtrip_idx,
                "name": original_comm_points[i - 1]["name"],
                "original_index": end_original_idx,
            },
            "data": segment_data,
            "point_count": len(segment_data),
        }

        segments.append(segment_info)
        print(
            f"    回程 Part {part_num}: {original_comm_points[i]['name']} → {original_comm_points[i - 1]['name']} ({len(segment_data)} 個點) [索引: {start_roundtrip_idx}-{end_roundtrip_idx}]"
        )
        part_num += 1

    return segments


def create_roundtrip_route(df: pd.DataFrame) -> pd.DataFrame:
    """建立往返路線：從最後一個點開始反向重複"""
    if len(df) <= 1:
        return df.copy()

    # 原始路線
    forward_route = df.copy()

    # 反向路線（去掉最後一個點避免重複，然後反向）
    reverse_route = df.iloc[:-1].copy()
    reverse_route = reverse_route.iloc[::-1].reset_index(drop=True)

    # 合併往返路線
    roundtrip_route = pd.concat([forward_route, reverse_route], ignore_index=True)

    # 重新編號順序
    roundtrip_route["順序"] = range(1, len(roundtrip_route) + 1)

    print(
        f"    建立往返路線：原路線 {len(forward_route)} 點 + 回程 {len(reverse_route)} 點 = 總計 {len(roundtrip_route)} 點"
    )

    return roundtrip_route


def create_roundtrip_comm_points(
    original_comm_points: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """建立往返通訊點：從最後一個通訊點開始反向重複"""
    if len(original_comm_points) <= 1:
        return original_comm_points.copy()

    # 原始通訊點
    forward_comm = original_comm_points.copy()

    # 反向通訊點（去掉最後一個避免重複，然後反向）
    reverse_comm = original_comm_points[:-1].copy()
    reverse_comm.reverse()

    # 合併往返通訊點
    roundtrip_comm = forward_comm + reverse_comm

    print(
        f"    建立往返通訊點：去程 {len(forward_comm)} 點 + 回程 {len(reverse_comm)} 點 = 總計 {len(roundtrip_comm)} 點"
    )

    return roundtrip_comm


def export_segment_geojson(
    segment: Dict[str, Any], output_path: Path, route_name: str, part_num: int
) -> None:
    """匯出路線段的 GeoJSON 檔案（來回路線的切分段）"""
    filename = f"{route_name}_part{part_num}.geojson"
    file_path = output_path / filename

    # 建立新的 GeoJSON
    new_geojson = {"type": "FeatureCollection", "features": []}

    # 取得段落資料
    segment_data = segment["data"]

    # 建立 LineString 特徵（路線）
    if len(segment_data) > 1:
        coords = []
        for _, row in segment_data.iterrows():
            coords.append([float(row["經度"]), float(row["緯度"])])

        linestring_feature = {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "name": f"{route_name}_part{part_num}",
                "route_type": "roundtrip_segment",
                "part_number": part_num,
                "start_point": segment["start_point"]["name"],
                "end_point": segment["end_point"]["name"],
                "total_points": len(segment_data),
            },
        }
        new_geojson["features"].append(linestring_feature)

    # 建立點位特徵
    for _, row in segment_data.iterrows():
        point_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["經度"]), float(row["緯度"])],
            },
            "properties": {
                "order": row["順序"],  # 使用來回路線的順序編號
                "type": row.get("類型", "gpx"),
                "name": row.get("名稱", "") if row.get("名稱") != "N/A" else None,
                "elevation": (
                    float(row["海拔（約）"])
                    if pd.notna(row.get("海拔（約）"))
                    and str(row.get("海拔（約）")).strip() != "N/A"
                    else None
                ),
            },
        }

        # 添加時間資訊（如果有）
        if (
            "時間" in row
            and pd.notna(row.get("時間"))
            and str(row.get("時間")).strip() not in ["", "N/A"]
        ):
            point_feature["properties"]["time"] = str(row["時間"])

        new_geojson["features"].append(point_feature)

    # 匯出檔案
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(new_geojson, f, ensure_ascii=False, indent=2)

    print(f"      匯出來回切分路線: {filename}")


def export_roundtrip_geojson(
    df: pd.DataFrame, output_path: Path, route_name: str
) -> None:
    """匯出往返路線的 GeoJSON 檔案"""
    filename = f"{route_name}_roundtrip.geojson"
    file_path = output_path / filename

    # 建立新的 GeoJSON
    new_geojson = {"type": "FeatureCollection", "features": []}

    # 建立 LineString 特徵（路線）
    if len(df) > 1:
        coords = []
        for _, row in df.iterrows():
            coords.append([float(row["經度"]), float(row["緯度"])])

        linestring_feature = {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "name": f"{route_name}_roundtrip",
                "route_type": "roundtrip",
                "total_points": len(df),
            },
        }
        new_geojson["features"].append(linestring_feature)

    # 建立點位特徵
    for _, row in df.iterrows():
        point_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["經度"]), float(row["緯度"])],
            },
            "properties": {
                "order": row["順序"],
                "type": row.get("類型", "gpx"),
                "name": row.get("名稱", "") if row.get("名稱") != "N/A" else None,
                "elevation": (
                    float(row["海拔（約）"])
                    if pd.notna(row.get("海拔（約）"))
                    and str(row.get("海拔（約）")).strip() != "N/A"
                    else None
                ),
            },
        }

        # 添加時間資訊（如果有）
        if (
            "時間" in row
            and pd.notna(row.get("時間"))
            and str(row.get("時間")).strip() not in ["", "N/A"]
        ):
            point_feature["properties"]["time"] = str(row["時間"])

        new_geojson["features"].append(point_feature)

    # 匯出檔案
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(new_geojson, f, ensure_ascii=False, indent=2)

    print(f"      匯出往返路線: {filename}")


def export_roundtrip_txt(
    comm_points: List[Dict[str, Any]], output_path: Path, route_name: str
) -> None:
    """匯出往返通訊點的 TXT 檔案"""
    filename = f"{route_name}_roundtrip.txt"
    file_path = output_path / filename

    # 建立 DataFrame
    data = []
    for i, pt in enumerate(comm_points, 1):
        data.append(
            {
                "順序": i,
                "步道名稱": route_name,
                "路標指示": pt["name"],
                "緯度": pt["lat"],
                "經度": pt["lon"],
                "海拔（約）": pt.get("elevation", ""),
            }
        )

    df = pd.DataFrame(data)

    # 匯出檔案
    df.to_csv(file_path, sep="\t", index=False, encoding="utf-8-sig")
    print(f"      匯出往返通訊點: {filename}")


def process_single_route(route_name: str, output_base: Path) -> None:
    """處理單一路線的完整流程"""
    print(f"\n處理 {route_name}")

    # 檔案路徑
    points_file = Path(f"./已改好的txt_geojson/{route_name}/points.txt")
    geojson_file = Path(f"./已改好的txt_geojson/{route_name}/route.geojson")

    # 檢查檔案是否存在
    if not points_file.exists():
        print(f"  找不到 {points_file}")
        return
    if not geojson_file.exists():
        print(f"  找不到 {geojson_file}")
        return

    # 讀取資料
    print(f"  -> 讀取資料...")
    df = read_points_file(points_file)
    geojson = read_geojson_file(geojson_file)

    if df.empty or not geojson:
        print(f"  資料讀取失敗")
        return

    # 進行插值處理
    print(f"  -> 進行高度和時間插值...")
    df = interpolate_missing_data_df(df)

    # 讀取原始通訊點資料
    print(f"  -> 讀取原始通訊點資料...")
    original_comm_points = read_original_comm_points(route_name)

    if not original_comm_points:
        print(f"  無法讀取原始通訊點資料")
        return

    # 建立輸出目錄
    cut_output_dir = output_base / "1.切分過的路線" / route_name
    roundtrip_geojson_dir = output_base / "2.往前重複的geojson" / route_name
    roundtrip_txt_dir = output_base / "3.往前重複的txt" / route_name

    cut_output_dir.mkdir(parents=True, exist_ok=True)
    roundtrip_geojson_dir.mkdir(parents=True, exist_ok=True)
    roundtrip_txt_dir.mkdir(parents=True, exist_ok=True)

    # *** 修正流程：先在原始路線找通訊點，再建立來回路線，最後按邏輯切分 ***

    # 1. 在原始路線中定位通訊點位置
    print(f"  -> 在原始路線中定位通訊點...")
    comm_points_in_original = find_comm_points_in_original_route(
        df, original_comm_points
    )

    # 2. 建立完整的來回路線
    print(f"  -> 建立來回路線...")
    roundtrip_route = create_roundtrip_route(df)

    if len(comm_points_in_original) >= 2:
        # 3. 提取通訊點索引和資料
        original_comm_indices = [idx for idx, _, _ in comm_points_in_original]

        # 4. 計算來回路線的切分段落
        print(f"  -> 計算來回路線切分段落...")
        roundtrip_segments = calculate_roundtrip_segments(
            roundtrip_route, original_comm_indices, original_comm_points
        )

        if roundtrip_segments:
            print(f"  -> 匯出 {len(roundtrip_segments)} 個來回切分段落...")
            for segment in roundtrip_segments:
                export_segment_geojson(
                    segment, cut_output_dir, route_name, segment["part_number"]
                )
    else:
        print(f"  原始路線中通訊點不足，跳過切分")

    # 4. 匯出完整往返路線 (GeoJSON)
    print(f"  -> 匯出完整往返路線...")
    export_roundtrip_geojson(roundtrip_route, roundtrip_geojson_dir, route_name)

    # 5. 往返通訊點 (TXT)
    print(f"  -> 建立往返通訊點...")
    roundtrip_comm = create_roundtrip_comm_points(original_comm_points)
    export_roundtrip_txt(roundtrip_comm, roundtrip_txt_dir, route_name)

    print(f"  {route_name} 處理完成")


def main():
    """主要執行函數"""
    print("開始路線處理...")

    # 設定路徑
    source_dir = Path("./已改好的txt_geojson")
    output_base_dir = Path("./最終json_txt")

    # 檢查來源目錄
    if not source_dir.exists():
        print(f"找不到來源目錄: {source_dir}")
        return

    # 建立基礎輸出目錄結構
    output_base_dir.mkdir(exist_ok=True)
    (output_base_dir / "1.切分過的路線").mkdir(exist_ok=True)
    (output_base_dir / "2.往前重複的geojson").mkdir(exist_ok=True)
    (output_base_dir / "3.往前重複的txt").mkdir(exist_ok=True)

    # 遍歷處理所有路線
    for route_dir in source_dir.iterdir():
        if route_dir.is_dir():
            route_name = route_dir.name
            process_single_route(route_name, output_base_dir)

    print(f"\n所有路線處理完成！")
    print(f"結果已匯出至: {output_base_dir.absolute()}")


if __name__ == "__main__":
    main()
