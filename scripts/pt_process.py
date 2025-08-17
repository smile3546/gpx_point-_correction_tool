import gpxpy
import pandas as pd
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point, LineString
from haversine import haversine, Unit
import json
from typing import Tuple, List
from datetime import datetime, timedelta


# 1. GPX → GeoDataFrame (保留時間)
def load_gpx_to_gdf(gpx_path: Path) -> gpd.GeoDataFrame:
    """從 GPX 檔案載入軌跡點，並保留時間資訊"""
    with open(gpx_path, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)
    rows = []
    for track in gpx.tracks:
        for seg in track.segments:
            for idx, pt in enumerate(seg.points):
                rows.append(
                    {
                        "latitude": pt.latitude,
                        "longitude": pt.longitude,
                        "elevation": pt.elevation,
                        "time": pt.time,  # <<< 關鍵改動：保留時間
                        "geometry": Point(pt.longitude, pt.latitude),
                        "point_type": "gpx",  # 標記點位來源
                        "name": None,  # 通訊點名稱欄位
                    }
                )
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    return gdf.sort_values("time").reset_index(drop=True)


# 1. TXT → GeoDataFrame（通訊點） - 修正以處理實際格式
def load_txt_to_gdf(txt_path: Path) -> gpd.GeoDataFrame:
    """從 TXT 檔案載入通訊點"""
    df = pd.read_csv(txt_path, sep="\t", encoding="utf-8")

    # 處理緯度欄位
    df["緯度"] = pd.to_numeric(
        df["緯度"].astype(str).str.replace("°", ""), errors="coerce"
    )

    # 處理經度欄位
    df["經度"] = pd.to_numeric(
        df["經度"].astype(str).str.replace("°", ""), errors="coerce"
    )

    # 處理海拔欄位
    df["海拔（約）"] = pd.to_numeric(
        df["海拔（約）"].astype(str).str.replace("m", ""), errors="coerce"
    )

    # 使用路標指示作為點位名稱，如果沒有則使用步道名稱
    df["點位名稱"] = df["路標指示"].fillna(df["步道名稱"])

    # 建立 GeoDataFrame
    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df["經度"], df["緯度"]), crs="EPSG:4326"
    )

    return gdf


# 2. (新) 依最後通訊點分割原始 GPX 路線
def split_route_by_last_comm(
    route_gdf: gpd.GeoDataFrame, last_comm_geom: Point
) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    根據最後通訊點分割原始 GPX 路線成路線 A 和路線 B。
    路線 A：起點到最後通訊點最近的 GPX 點
    路線 B：最後通訊點最近的 GPX 點到終點
    """
    # 找到距離最後通訊點最近的 GPX 軌跡點
    distances = route_gdf.geometry.distance(last_comm_geom)
    closest_idx = distances.idxmin()

    # 路線 A：從起點到最近點（包含）
    route_a = route_gdf.iloc[: closest_idx + 1].copy().reset_index(drop=True)

    # 路線 B：從最近點（包含）到終點
    route_b = route_gdf.iloc[closest_idx:].copy().reset_index(drop=True)

    return route_a, route_b


# 3. (改進) 將所有通訊點插入路線並進行時間和高度插值
def insert_comm_points_with_interpolation(
    route_gdf: gpd.GeoDataFrame, comm_gdf: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    將所有通訊點插入到路線中，並為通訊點計算插值時間和高度。
    """
    all_points = route_gdf.to_dict("records")

    # 如果路線只有一個點，無法插入通訊點
    if len(route_gdf) < 2:
        print("警告：路線少於2個點，無法插入通訊點")
        return route_gdf

    # 為每個通訊點找到最適合的插入位置
    for _, comm_point in comm_gdf.iterrows():
        comm_geom = comm_point.geometry

        # 找到距離通訊點最近的 GPX 點
        distances = route_gdf.geometry.distance(comm_geom)
        closest_idx = distances.idxmin()

        # 獲取最近點及其前後點的時間和高度資訊
        closest_point = route_gdf.iloc[closest_idx]
        time1 = closest_point.time
        elevation1 = closest_point.elevation

        # 計算插值時間和高度
        interpolated_time = None
        interpolated_elevation = None

        # 如果有前一個點，計算與前一個點的插值
        if closest_idx > 0:
            prev_point = route_gdf.iloc[closest_idx - 1]
            time0 = prev_point.time
            elevation0 = prev_point.elevation

            # 計算通訊點在兩點之間的相對位置
            total_distance = prev_point.geometry.distance(closest_point.geometry)
            if total_distance > 0:
                distance_to_prev = prev_point.geometry.distance(comm_geom)
                ratio = min(1.0, max(0.0, distance_to_prev / total_distance))

                # 時間插值
                if pd.notna(time0) and pd.notna(time1):
                    time_diff = time1 - time0
                    interpolated_time = time0 + time_diff * ratio

                # 高度插值
                if pd.notna(elevation0) and pd.notna(elevation1):
                    elevation_diff = elevation1 - elevation0
                    interpolated_elevation = elevation0 + elevation_diff * ratio

        # 如果有後一個點，計算與後一個點的插值
        if closest_idx < len(route_gdf) - 1:
            next_point = route_gdf.iloc[closest_idx + 1]
            time2 = next_point.time
            elevation2 = next_point.elevation

            # 計算通訊點在兩點之間的相對位置
            total_distance = closest_point.geometry.distance(next_point.geometry)
            if total_distance > 0:
                distance_to_closest = closest_point.geometry.distance(comm_geom)
                ratio = min(1.0, max(0.0, distance_to_closest / total_distance))

                # 時間插值（如果還沒有計算）
                if interpolated_time is None and pd.notna(time1) and pd.notna(time2):
                    time_diff = time2 - time1
                    interpolated_time = time1 + time_diff * ratio

                # 高度插值（如果還沒有計算）
                if (
                    interpolated_elevation is None
                    and pd.notna(elevation1)
                    and pd.notna(elevation2)
                ):
                    elevation_diff = elevation2 - elevation1
                    interpolated_elevation = elevation1 + elevation_diff * ratio

        # 如果通訊點本身有高度，優先使用
        if pd.notna(comm_point.get("海拔（約）")):
            interpolated_elevation = comm_point.get("海拔（約）")

        # 如果還是沒有高度，使用最近點的高度
        if interpolated_elevation is None and pd.notna(elevation1):
            interpolated_elevation = elevation1

        # 建立通訊點資料
        new_point = {
            "latitude": comm_point.geometry.y,
            "longitude": comm_point.geometry.x,
            "elevation": interpolated_elevation,
            "time": interpolated_time,
            "geometry": comm_point.geometry,
            "point_type": "comm",
            "name": comm_point.get("點位名稱") or "通訊點",
            "insert_index": closest_idx + 0.5,  # 用於無時間時的排序
        }

        all_points.append(new_point)

    # 建立合併的 GeoDataFrame
    merged_gdf = gpd.GeoDataFrame(all_points, crs=route_gdf.crs)

    return merged_gdf


# 4. (改進) 對合併路線進行最終時間排序
def final_time_sort(merged_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    對包含 GPX 軌跡點和通訊點的合併路線進行最終時間排序。
    優先使用時間排序，如果沒有時間則使用插入索引。
    """
    # 複製資料以避免修改原始資料
    sorted_gdf = merged_gdf.copy()

    # 檢查是否有時間資訊
    has_time = not sorted_gdf["time"].isna().all()

    if has_time:
        # 有時間資訊，優先使用時間排序
        print("    -> 使用時間排序")

        # 為沒有時間的點設定一個較晚的時間
        max_time = sorted_gdf["time"].max()
        if pd.notna(max_time):
            # 為沒有時間的點設定比最大時間晚1小時的時間
            sorted_gdf["sort_time"] = sorted_gdf["time"].fillna(
                max_time + pd.Timedelta(hours=1)
            )
        else:
            # 如果所有時間都是 NaN，使用插入索引
            sorted_gdf["sort_time"] = sorted_gdf["insert_index"].fillna(
                sorted_gdf.index
            )

        # 按時間排序
        sorted_gdf = sorted_gdf.sort_values(by="sort_time").reset_index(drop=True)
        sorted_gdf = sorted_gdf.drop(columns=["sort_time"], errors="ignore")

    else:
        # 沒有時間資訊，使用插入索引排序
        print("    -> 使用插入索引排序")

        # 為 GPX 點設定插入索引為其原始索引
        sorted_gdf["sort_index"] = sorted_gdf.index.where(
            sorted_gdf["insert_index"].isna(), sorted_gdf["insert_index"]
        )

        # 按插入索引排序
        sorted_gdf = sorted_gdf.sort_values(by="sort_index").reset_index(drop=True)
        sorted_gdf = sorted_gdf.drop(columns=["sort_index"], errors="ignore")

    # 清理輔助欄位
    sorted_gdf = sorted_gdf.drop(columns=["insert_index"], errors="ignore")

    return sorted_gdf


# 5. 匯出 TXT + GeoJSON (改進版)
def export_gdf_to_txt_geojson(
    gdf: gpd.GeoDataFrame, output_path: Path, route_name: str
):
    """將處理好的路線資料匯出成 TXT 和 GeoJSON"""
    output_path.mkdir(parents=True, exist_ok=True)

    export_df = gdf.copy()

    # 產生順序欄位
    export_df["順序"] = range(1, len(export_df) + 1)

    # 為通訊點加上特殊標記
    comm_points = export_df[export_df["point_type"] == "comm"]
    for idx in comm_points.index:
        name = export_df.loc[idx, "name"] or "通訊點"
        export_df.loc[idx, "順序"] = f"{export_df.loc[idx, '順序']}({name})"

    # 匯出 TXT 檔案 - 改進格式
    txt_data = []
    for idx, row in export_df.iterrows():
        txt_row = {
            "順序": export_df.loc[idx, "順序"],
            "緯度": f"{row['latitude']:.6f}",
            "經度": f"{row['longitude']:.6f}",
            "海拔（約）": (
                f"{row['elevation']:.1f}" if pd.notna(row["elevation"]) else "N/A"
            ),
            "類型": row["point_type"],
            "名稱": row.get("name", "") or "",
        }

        # 如果有時間資訊，加入時間
        if pd.notna(row.get("time")):
            if hasattr(row["time"], "isoformat"):
                txt_row["時間"] = row["time"].isoformat()
            else:
                txt_row["時間"] = str(row["time"])

        txt_data.append(txt_row)

    # 轉換為 DataFrame 並匯出
    txt_df = pd.DataFrame(txt_data)
    txt_df.to_csv(
        output_path / "points.txt", sep="\t", index=False, encoding="utf-8-sig"
    )

    # 建立 GeoJSON
    geojson = {"type": "FeatureCollection", "features": []}

    # 線段 Feature - 包含所有點（按順序排列）
    if len(gdf) > 1:
        coords = [(row.longitude, row.latitude) for _, row in gdf.iterrows()]
        geojson["features"].append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {
                    "name": f"{route_name}",
                    "route_type": "main_route",
                    "total_points": len(gdf),
                    "comm_points": len(gdf[gdf["point_type"] == "comm"]),
                    "gpx_points": len(gdf[gdf["point_type"] == "gpx"]),
                },
            }
        )

    # 點位 Features - 包含所有點位
    for idx, row in gdf.iterrows():
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row.longitude, row.latitude],
            },
            "properties": {
                "order": export_df.loc[idx, "順序"],
                "type": row.point_type,
                "name": row.get("name", ""),
                "elevation": row.get("elevation"),
            },
        }

        # 如果有時間資訊，加入時間
        if pd.notna(row.get("time")):
            if hasattr(row["time"], "isoformat"):
                feature["properties"]["time"] = row["time"].isoformat()
            else:
                feature["properties"]["time"] = str(row["time"])

        geojson["features"].append(feature)

    # 寫入 GeoJSON 檔案
    with open(output_path / "route.geojson", "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(
        f"  -> 匯出完成：{len(gdf)} 個點位 (GPX: {len(gdf[gdf['point_type'] == 'gpx'])}, 通訊點: {len(gdf[gdf['point_type'] == 'comm'])})"
    )


# 6. 主流程 (完全重構)
if __name__ == "__main__":
    raw_gpx_folder = Path("./data_raw/gpx")
    raw_txt_folder = Path("./data_raw/txt")
    work_folder = Path("./data_work")

    # 建立輸出資料夾
    work_folder.mkdir(parents=True, exist_ok=True)

    print("開始處理 GPX 路線與通訊點...")

    for gpx_file in raw_gpx_folder.glob("*.gpx"):
        base = gpx_file.stem
        txt_file = raw_txt_folder / f"{base}.txt"

        if not txt_file.exists():
            print(f"缺少對應的 TXT 檔案: {txt_file.name}")
            continue

        print(f"\n處理中: {gpx_file.name}")

        try:
            # 1. 讀取資料 (保留 time 欄位)
            print("  -> 讀取 GPX 軌跡...")
            route_gdf = load_gpx_to_gdf(gpx_file)

            print("  -> 讀取通訊點...")
            comm_gdf = load_txt_to_gdf(txt_file)

            if route_gdf.empty:
                print(f"GPX 檔案為空: {gpx_file.name}")
                continue

            if comm_gdf.empty:
                print(f"通訊點檔案為空: {txt_file.name}")
                continue

            print(f"  -> GPX 軌跡點: {len(route_gdf)}, 通訊點: {len(comm_gdf)}")

            # 2. 根據最後通訊點分割原始路線
            print("  -> 依最後通訊點分割路線...")
            last_comm_geom = comm_gdf.geometry.iloc[-1]
            route_a_base, route_b_base = split_route_by_last_comm(
                route_gdf, last_comm_geom
            )

            print(f"     路線 A: {len(route_a_base)} 個點")
            print(f"     路線 B: {len(route_b_base)} 個點")

            # 3. 分別為路線 A 和 B 插入所有通訊點
            print("  -> 為路線 A 插入通訊點並進行時間插值...")
            route_a_with_comm = insert_comm_points_with_interpolation(
                route_a_base, comm_gdf
            )

            print("  -> 為路線 B 插入通訊點並進行時間插值...")
            route_b_with_comm = insert_comm_points_with_interpolation(
                route_b_base, comm_gdf
            )

            # 4. 對兩條路線進行最終時間排序
            print("  -> 進行最終時間排序...")
            final_route_a = final_time_sort(route_a_with_comm)
            final_route_b = final_time_sort(route_b_with_comm)

            # 5. 匯出結果
            if not final_route_a.empty:
                print("  -> 匯出路線 A...")
                export_gdf_to_txt_geojson(
                    final_route_a, work_folder / "route_a" / base, f"{base}_路線A"
                )

            if not final_route_b.empty:
                print("  -> 匯出路線 B...")
                export_gdf_to_txt_geojson(
                    final_route_b, work_folder / "route_b" / base, f"{base}_路線B"
                )

        except Exception as e:
            print(f"處理 {gpx_file.name} 時發生錯誤: {str(e)}")
            continue

    print("\n所有路線處理完成！")
    print(f"結果已匯出至: {work_folder.absolute()}")
