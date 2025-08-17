#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GeoJSON 轉 GPX 工具
將 data_work 資料夾中的 route.geojson 檔案轉換為 GPX 格式
"""

import json
import os
from pathlib import Path
from datetime import datetime


def scan_data_work():
    """掃描 data_work 資料夾，取得所有 route.geojson 檔案"""
    data_work_path = Path("data_work")
    print(f"  -> 掃描路徑: {data_work_path.absolute()}")
    geojson_files = []

    # 掃描 route_a 和 route_b
    for route_type in ["route_a", "route_b"]:
        route_path = data_work_path / route_type

        # 掃描每個路線資料夾
        for route_dir in route_path.iterdir():
            if route_dir.is_dir():
                geojson_file = route_dir / "route.geojson"
                if geojson_file.exists():
                    route_name = route_dir.name
                    geojson_files.append(
                        {
                            "file_path": geojson_file,
                            "route_name": route_name,
                            "route_type": route_type,
                            "output_name": f"{route_name}_{route_type}.gpx",
                        }
                    )

    return geojson_files


def geojson_to_gpx(geojson_data, output_filename):
    """將 GeoJSON 資料轉換為 GPX 格式"""

    # GPX 檔案開頭
    gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="GPX Route Converter" xmlns="http://www.topografix.com/GPX/1/1">
"""

    # 提取路線名稱（去掉 .gpx 副檔名）
    track_name = output_filename.replace(".gpx", "")

    # 收集所有點位（按順序）
    points = []
    waypoints = []

    for feature in geojson_data["features"]:
        if feature["geometry"]["type"] == "Point":
            coords = feature["geometry"]["coordinates"]
            props = feature["properties"]

            point_data = {
                "lon": coords[0],
                "lat": coords[1],
                "elevation": props.get("elevation"),
                "time": props.get("time"),
                "name": props.get("name"),
                "type": props.get("type"),
                "order": props.get("order", 0),
            }

            points.append(point_data)

            # 如果是通訊點，也加入航點
            if props.get("type") == "comm" or props.get("name"):
                waypoints.append(point_data)

    # 按順序排序點位（處理混合的字串和數字）
    def sort_key(point):
        order = point["order"]
        if isinstance(order, str):
            try:
                # 嘗試提取數字部分
                import re

                numbers = re.findall(r"\d+", str(order))
                return int(numbers[0]) if numbers else 0
            except:
                return 0
        return int(order) if order else 0

    points.sort(key=sort_key)

    # 生成航點 (waypoints)
    for wpt in waypoints:
        gpx_content += f'  <wpt lat="{wpt["lat"]}" lon="{wpt["lon"]}">\n'

        if wpt["elevation"]:
            gpx_content += f'    <ele>{wpt["elevation"]}</ele>\n'

        if wpt["time"]:
            # 轉換時間格式
            time_str = wpt["time"].replace("+00:00", "Z")
            gpx_content += f"    <time>{time_str}</time>\n"

        if wpt["name"]:
            gpx_content += f'    <name>{wpt["name"]}</name>\n'

        if wpt["type"]:
            gpx_content += f'    <type>{wpt["type"]}</type>\n'

        gpx_content += "  </wpt>\n"

    # 生成軌跡 (track)
    gpx_content += f"  <trk>\n"
    gpx_content += f"    <name>{track_name}</name>\n"
    gpx_content += f"    <trkseg>\n"

    for point in points:
        gpx_content += f'      <trkpt lat="{point["lat"]}" lon="{point["lon"]}">\n'

        if point["elevation"]:
            gpx_content += f'        <ele>{point["elevation"]}</ele>\n'

        if point["time"]:
            # 轉換時間格式
            time_str = point["time"].replace("+00:00", "Z")
            gpx_content += f"        <time>{time_str}</time>\n"

        gpx_content += "      </trkpt>\n"

    gpx_content += "    </trkseg>\n"
    gpx_content += "  </trk>\n"
    gpx_content += "</gpx>"

    return gpx_content


def main():
    """主要執行流程"""
    print("🚀 開始 GeoJSON 轉 GPX 處理...")

    # 建立輸出資料夾
    output_dir = Path("修改好的gpx")
    output_dir.mkdir(exist_ok=True)

    # 掃描所有 GeoJSON 檔案
    geojson_files = scan_data_work()
    print(f"  -> 找到 {len(geojson_files)} 個路線檔案")

    # 處理每個檔案
    for file_info in geojson_files:
        print(f"  -> 處理 {file_info['route_name']}_{file_info['route_type']}...")

        # 讀取 GeoJSON
        with open(file_info["file_path"], "r", encoding="utf-8") as f:
            geojson_data = json.load(f)

        # 轉換為 GPX
        gpx_content = geojson_to_gpx(geojson_data, file_info["output_name"])

        # 寫入 GPX 檔案
        output_path = output_dir / file_info["output_name"]
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(gpx_content)

        print(f"     ✓ 轉換完成：{output_path}")

    print("✅ 所有檔案轉換完成！")


if __name__ == "__main__":
    main()
