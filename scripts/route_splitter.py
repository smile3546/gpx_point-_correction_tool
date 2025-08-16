import pandas as pd
import json
import os
from pathlib import Path
from typing import List, Dict, Tuple, Any


def read_points_file(points_path: Path) -> pd.DataFrame:
    """
    讀取 points.txt 檔案
    
    Args:
        points_path: points.txt 檔案路徑
        
    Returns:
        包含所有點位資料的 DataFrame
    """
    try:
        df = pd.read_csv(points_path, sep='\t', encoding='utf-8-sig')
        return df
    except Exception as e:
        print(f"❌ 讀取 {points_path} 失敗: {e}")
        return pd.DataFrame()


def read_geojson_file(geojson_path: Path) -> Dict[str, Any]:
    """
    讀取 route.geojson 檔案
    
    Args:
        geojson_path: route.geojson 檔案路徑
        
    Returns:
        GeoJSON 字典資料
    """
    try:
        with open(geojson_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 讀取 {geojson_path} 失敗: {e}")
        return {}


def read_original_comm_points(route_name: str) -> List[Dict[str, Any]]:
    """
    讀取原始通訊點資料
    
    Args:
        route_name: 路線名稱
        
    Returns:
        原始通訊點列表
    """
    raw_txt_path = Path(f"./data_raw/txt/{route_name}.txt")
    
    if not raw_txt_path.exists():
        print(f"  ❌ 找不到原始通訊點檔案: {raw_txt_path}")
        return []
    
    try:
        df = pd.read_csv(raw_txt_path, sep='\t', encoding='utf-8-sig')
        comm_points = []
        
        for idx, row in df.iterrows():
            comm_points.append({
                'name': row.get('路標指示', ''),
                'lat': float(row.get('緯度', 0)),
                'lon': float(row.get('經度', 0)),
                'elevation': row.get('海拔（約）', None)
            })
        
        print(f"  -> 讀取到 {len(comm_points)} 個原始通訊點: {[pt['name'] for pt in comm_points]}")
        return comm_points
        
    except Exception as e:
        print(f"  ❌ 讀取原始通訊點失敗: {e}")
        return []


def find_comm_points_in_route(df: pd.DataFrame, original_comm_points: List[Dict[str, Any]]) -> List[Tuple[int, str, str]]:
    """
    在處理後的路線中找出通訊點位置
    
    Args:
        df: 點位資料 DataFrame
        original_comm_points: 原始通訊點列表
        
    Returns:
        [(行號, 通訊點名稱, 順序), ...] 的列表，按順序排列
    """
    comm_points = []
    
    # 為每個原始通訊點找到在路線中的對應位置
    for original_pt in original_comm_points:
        target_lat = original_pt['lat']
        target_lon = original_pt['lon']
        target_name = original_pt['name']
        
        # 在 DataFrame 中尋找最接近的點
        min_distance = float('inf')
        best_match_idx = None
        best_match_order = None
        
        for idx, row in df.iterrows():
            row_lat = float(row.get('緯度', 0))
            row_lon = float(row.get('經度', 0))
            
            # 計算距離（簡單的歐幾里得距離）
            distance = ((row_lat - target_lat) ** 2 + (row_lon - target_lon) ** 2) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                best_match_idx = idx
                best_match_order = str(row.get('順序', ''))
        
        if best_match_idx is not None:
            comm_points.append((best_match_idx, target_name, best_match_order))
            print(f"    找到通訊點 '{target_name}' 在索引 {best_match_idx} (順序: {best_match_order})")
    
    # 按照在路線中的順序排列
    comm_points.sort(key=lambda x: x[0])
    
    print(f"  -> 找到 {len(comm_points)} 個通訊點: {[f'{name}({order})' for _, name, order in comm_points]}")
    return comm_points


def split_route_by_comm_points(df: pd.DataFrame, comm_points: List[Tuple[int, str, str]]) -> List[Dict[str, Any]]:
    """
    根據通訊點切分路線
    
    Args:
        df: 點位資料 DataFrame
        comm_points: 通訊點列表 [(行號, 名稱, 順序), ...]
        
    Returns:
        路線段列表，每段包含起始點、結束點、資料等資訊
    """
    if len(comm_points) < 2:
        print(f"  ⚠️ 通訊點少於2個，無法切分")
        return []
    
    segments = []
    
    for i in range(len(comm_points) - 1):
        start_idx, start_name, start_order = comm_points[i]
        end_idx, end_name, end_order = comm_points[i + 1]
        
        # 切分資料：從起始通訊點到結束通訊點，包含兩點之間的所有點
        # start_idx 和 end_idx 已經是 DataFrame 的正確索引
        segment_data = df.iloc[start_idx:end_idx + 1].copy()
        
        segment_info = {
            'part_number': i + 1,
            'start_point': {
                'index': start_idx,
                'name': start_name,
                'order': start_order
            },
            'end_point': {
                'index': end_idx,
                'name': end_name,
                'order': end_order
            },
            'data': segment_data,
            'point_count': len(segment_data)
        }
        
        segments.append(segment_info)
        print(f"    Part {i+1}: {start_name} → {end_name} ({len(segment_data)} 個點) [索引: {start_idx}-{end_idx}]")
    
    return segments


def export_segment_txt(segment: Dict[str, Any], output_base: Path, route_name: str, route_type: str) -> None:
    """
    匯出路線段的 TXT 檔案
    
    Args:
        segment: 路線段資料
        output_base: 輸出基礎目錄
        route_name: 路線名稱
        route_type: 路線類型 (route_a 或 route_b)
    """
    part_num = segment['part_number']
    filename = f"{route_name}_切分好的_{route_type}_part{part_num}_points.txt"
    
    # 建立正確的目錄結構：route_a/txt/路線名稱/
    output_path = output_base / route_type / "txt" / route_name
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 重新編號順序
    data = segment['data'].copy()
    data['順序'] = range(1, len(data) + 1)
    
    # 保持通訊點的特殊標記
    for idx, row in data.iterrows():
        if row.get('類型') == 'comm':
            name = row.get('名稱', 'comm')
            data.loc[idx, '順序'] = f"{data.loc[idx, '順序']}({name})"
    
    # 匯出檔案
    file_path = output_path / filename
    data.to_csv(file_path, sep='\t', index=False, encoding='utf-8-sig')
    print(f"      ✓ 匯出 TXT: {route_type}/txt/{route_name}/{filename}")


def export_segment_geojson(segment: Dict[str, Any], original_geojson: Dict[str, Any], 
                          output_base: Path, route_name: str, route_type: str) -> None:
    """
    匯出路線段的 GeoJSON 檔案
    
    Args:
        segment: 路線段資料
        original_geojson: 原始 GeoJSON 資料
        output_base: 輸出基礎目錄
        route_name: 路線名稱
        route_type: 路線類型 (route_a 或 route_b)
    """
    part_num = segment['part_number']
    filename = f"{route_name}_切分好的_{route_type}_part{part_num}.geojson"
    
    # 建立正確的目錄結構：route_a/geojson/路線名稱/
    output_path = output_base / route_type / "geojson" / route_name
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 建立新的 GeoJSON
    new_geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    
    # 取得段落資料
    segment_data = segment['data']
    
    # 建立 LineString 特徵（路線）
    if len(segment_data) > 1:
        coords = []
        for _, row in segment_data.iterrows():
            coords.append([float(row['經度']), float(row['緯度'])])
        
        linestring_feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            },
            "properties": {
                "name": f"{route_name}_{route_type}_part{part_num}",
                "route_type": "segment",
                "part_number": part_num,
                "start_point": segment['start_point']['name'],
                "end_point": segment['end_point']['name'],
                "total_points": len(segment_data),
                "comm_points": len(segment_data[segment_data['類型'] == 'comm']),
                "gpx_points": len(segment_data[segment_data['類型'] == 'gpx'])
            }
        }
        new_geojson["features"].append(linestring_feature)
    
    # 建立點位特徵
    for idx, (_, row) in enumerate(segment_data.iterrows()):
        # 重新編號
        order = idx + 1
        if row.get('類型') == 'comm':
            name = row.get('名稱', 'comm')
            order_display = f"{order}({name})"
        else:
            order_display = order
        
        point_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row['經度']), float(row['緯度'])]
            },
            "properties": {
                "order": order_display,
                "type": row.get('類型', 'gpx'),
                "name": row.get('名稱', '') or None,
                "elevation": float(row['海拔（約）']) if pd.notna(row.get('海拔（約）')) else None
            }
        }
        
        # 添加時間資訊（如果有）
        if pd.notna(row.get('時間')):
            point_feature["properties"]["time"] = str(row['時間'])
        
        new_geojson["features"].append(point_feature)
    
    # 匯出檔案
    file_path = output_path / filename
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(new_geojson, f, ensure_ascii=False, indent=2)
    
    print(f"      ✓ 匯出 GeoJSON: {route_type}/geojson/{route_name}/{filename}")


def process_single_route(route_dir: Path, route_name: str, route_type: str, output_base: Path) -> None:
    """
    處理單一路線的切分
    
    Args:
        route_dir: 路線目錄（包含 points.txt 和 route.geojson）
        route_name: 路線名稱
        route_type: 路線類型 (route_a 或 route_b)
        output_base: 輸出基礎目錄
    """
    print(f"\n📍 處理 {route_name} - {route_type}")
    
    # 檔案路徑
    points_file = route_dir / "points.txt"
    geojson_file = route_dir / "route.geojson"
    
    # 檢查檔案是否存在
    if not points_file.exists():
        print(f"  ❌ 找不到 {points_file}")
        return
    if not geojson_file.exists():
        print(f"  ❌ 找不到 {geojson_file}")
        return
    
    # 讀取資料
    print(f"  -> 讀取資料...")
    df = read_points_file(points_file)
    geojson = read_geojson_file(geojson_file)
    
    if df.empty or not geojson:
        print(f"  ❌ 資料讀取失敗")
        return
    
    # 讀取原始通訊點資料
    print(f"  -> 讀取原始通訊點資料...")
    original_comm_points = read_original_comm_points(route_name)
    
    if not original_comm_points:
        print(f"  ❌ 無法讀取原始通訊點資料")
        return
    
    # 在處理後的路線中找出通訊點位置
    print(f"  -> 在路線中定位通訊點...")
    comm_points = find_comm_points_in_route(df, original_comm_points)
    
    if len(comm_points) < 2:
        print(f"  ⚠️ 通訊點不足，跳過切分")
        return
    
    # 切分路線
    print(f"  -> 切分路線...")
    segments = split_route_by_comm_points(df, comm_points)
    
    if not segments:
        print(f"  ❌ 路線切分失敗")
        return
    
    # 匯出每個段落
    print(f"  -> 匯出 {len(segments)} 個段落...")
    for segment in segments:
        export_segment_txt(segment, output_base, route_name, route_type)
        export_segment_geojson(segment, geojson, output_base, route_name, route_type)
    
    print(f"  ✅ {route_name} - {route_type} 處理完成")


def main():
    """主要執行函數"""
    print("🚀 開始路線切分處理...")
    
    # 設定路徑
    data_work_dir = Path("./data_work")
    output_base_dir = Path("./路線切分")
    
    # 檢查來源目錄
    if not data_work_dir.exists():
        print(f"❌ 找不到來源目錄: {data_work_dir}")
        return
    
    # 建立基礎輸出目錄結構
    output_base_dir.mkdir(exist_ok=True)
    
    # 建立 route_a 和 route_b 的基礎結構
    for route_type in ["route_a", "route_b"]:
        route_dir = output_base_dir / route_type
        route_dir.mkdir(exist_ok=True)
        (route_dir / "txt").mkdir(exist_ok=True)
        (route_dir / "geojson").mkdir(exist_ok=True)
    
    # 遍歷處理所有路線
    route_types = ["route_a", "route_b"]
    
    for route_type in route_types:
        route_type_dir = data_work_dir / route_type
        
        if not route_type_dir.exists():
            print(f"⚠️ 跳過不存在的目錄: {route_type_dir}")
            continue
        
        # 遍歷每個路線目錄
        for route_dir in route_type_dir.iterdir():
            if route_dir.is_dir():
                route_name = route_dir.name
                process_single_route(route_dir, route_name, route_type, output_base_dir)
    
    print(f"\n✅ 所有路線切分處理完成！")
    print(f"結果已匯出至: {output_base_dir.absolute()}")


if __name__ == "__main__":
    main()
