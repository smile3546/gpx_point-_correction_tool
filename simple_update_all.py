#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd

# 讀取資料
print("讀取檔案...")
poi_df = pd.read_csv("FINAL_POI.csv", encoding="utf-8-sig")
feature_df = pd.read_csv("feature_report.csv", encoding="utf-8-sig")

print(f"POI資料: {len(poi_df)} 筆")
print(f"Feature資料: {len(feature_df)} 筆")

# 建立路線POI映射
route_poi_map = {}
for _, row in poi_df.iterrows():
    en_trail_name = row["en_trail_name"]
    if pd.isna(en_trail_name):
        continue

    if en_trail_name not in route_poi_map:
        route_poi_map[en_trail_name] = {"trail_id": row["trail_id"], "pois": []}

    route_poi_map[en_trail_name]["pois"].append(
        {"order": row["poi_order"], "poi_id": row["poi_id"]}
    )

# 排序POI
for route_name in route_poi_map:
    route_poi_map[route_name]["pois"].sort(key=lambda x: x["order"])

print(f"建立了 {len(route_poi_map)} 個路線的映射")

# 添加新欄位
feature_df["trail_id"] = None
feature_df["poi_previous_id"] = None
feature_df["poi_current_id"] = None

# 更新每筆記錄
updated_count = 0
for index, row in feature_df.iterrows():
    route_folder = row["route_folder"]
    part_number = int(row["part_number"])

    if route_folder in route_poi_map:
        route_info = route_poi_map[route_folder]
        pois = route_info["pois"]

        # 檢查part_number是否在有效範圍內
        if 1 <= part_number <= len(pois) - 1:
            # part_number對應POI序列中的索引
            prev_poi = pois[part_number - 1]["poi_id"]
            curr_poi = pois[part_number]["poi_id"]

            feature_df.loc[index, "trail_id"] = route_info["trail_id"]
            feature_df.loc[index, "poi_previous_id"] = prev_poi
            feature_df.loc[index, "poi_current_id"] = curr_poi
            updated_count += 1

print(f"更新了 {updated_count} 筆記錄")

# 重新排列欄位
cols = [
    "route_folder",
    "part_number",
    "filename",
    "trail_id",
    "poi_previous_id",
    "poi_current_id",
] + [
    col
    for col in feature_df.columns
    if col
    not in [
        "route_folder",
        "part_number",
        "filename",
        "trail_id",
        "poi_previous_id",
        "poi_current_id",
    ]
]
feature_df = feature_df[cols]

# 儲存
output_file = "feature_report_final.csv"
feature_df.to_csv(output_file, index=False, encoding="utf-8-sig")
print(f"結果已儲存至 {output_file}")

# 顯示每個路線的統計
print("\n各路線更新統計:")
updated_routes = feature_df[feature_df["trail_id"].notna()]
for route in updated_routes["route_folder"].unique():
    route_data = updated_routes[updated_routes["route_folder"] == route]
    trail_id = int(route_data["trail_id"].iloc[0])
    count = len(route_data)
    print(f"{route}: {count} 筆 (trail_id={trail_id})")
