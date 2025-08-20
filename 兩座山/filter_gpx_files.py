#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GPX 檔案過濾器
根據 CSV 檔案中的 new_filename 欄位，只保留有對應記錄的 GPX 檔案
"""

import os
import pandas as pd
from pathlib import Path


def read_csv_and_get_filenames(csv_file_path):
    """讀取 CSV 檔案並提取 new_filename 欄位"""
    try:
        df = pd.read_csv(csv_file_path)
        if "new_filename" not in df.columns:
            raise ValueError(f"CSV 檔案 {csv_file_path} 中沒有 'new_filename' 欄位")

        # 提取所有 new_filename，移除空值
        filenames = df["new_filename"].dropna().tolist()
        print(f"從 {csv_file_path} 讀取到 {len(filenames)} 個檔案名稱")
        return set(filenames)  # 使用 set 提高查找效率

    except Exception as e:
        print(f"讀取 CSV 檔案時發生錯誤: {e}")
        return set()


def filter_gpx_directory(gpx_dir_path, keep_filenames, dry_run=True):
    """過濾 GPX 目錄，只保留指定的檔案"""
    gpx_dir = Path(gpx_dir_path)

    if not gpx_dir.exists():
        print(f"目錄不存在: {gpx_dir_path}")
        return

    # 獲取目錄中所有 GPX 檔案
    gpx_files = list(gpx_dir.glob("*.gpx"))
    print(f"\n在 {gpx_dir_path} 中找到 {len(gpx_files)} 個 GPX 檔案")

    # 統計資訊
    keep_count = 0
    delete_count = 0
    delete_files = []

    for gpx_file in gpx_files:
        filename = gpx_file.name

        if filename in keep_filenames:
            keep_count += 1
            print(f"  保留: {filename}")
        else:
            delete_count += 1
            delete_files.append(gpx_file)
            if dry_run:
                print(f"  [預刪除]: {filename}")
            else:
                print(f"  刪除: {filename}")

    print(f"\n統計結果:")
    print(f"  保留檔案: {keep_count} 個")
    print(f"  刪除檔案: {delete_count} 個")

    # 執行刪除操作
    if not dry_run and delete_files:
        for file_to_delete in delete_files:
            try:
                file_to_delete.unlink()
                print(f"已刪除: {file_to_delete.name}")
            except Exception as e:
                print(f"刪除失敗 {file_to_delete.name}: {e}")


def main():
    """主函數"""
    print("GPX 檔案過濾器")
    print("=" * 50)

    # 定義檔案路徑
    script_dir = Path(__file__).parent
    base_dir = script_dir

    # 關山嶺山配置
    guanshanling_csv = base_dir / "#7Guanshanling_Mountain_clustering_dbscan.csv"
    guanshanling_gpx_dir = base_dir / "Guanshanling_processed_gpx"

    # 塔關山配置
    taguan_csv = base_dir / "#9Tagua _clustering_dbscan.csv"
    taguan_gpx_dir = base_dir / "Taguan_processed_gpx"

    # 檢查檔案是否存在
    missing_files = []
    for file_path in [guanshanling_csv, taguan_csv]:
        if not file_path.exists():
            missing_files.append(str(file_path))

    for dir_path in [guanshanling_gpx_dir, taguan_gpx_dir]:
        if not dir_path.exists():
            missing_files.append(str(dir_path))

    if missing_files:
        print("錯誤: 以下檔案或目錄不存在:")
        for missing in missing_files:
            print(f"  - {missing}")
        return

    # 直接執行刪除模式
    dry_run = False
    print("\n執行模式: 實際刪除檔案")

    # 處理關山嶺山
    print("\n" + "=" * 50)
    print("處理關山嶺山 GPX 檔案")
    print("=" * 50)

    guanshanling_filenames = read_csv_and_get_filenames(guanshanling_csv)
    if guanshanling_filenames:
        filter_gpx_directory(guanshanling_gpx_dir, guanshanling_filenames, dry_run)

    # 處理塔關山
    print("\n" + "=" * 50)
    print("處理塔關山 GPX 檔案")
    print("=" * 50)

    taguan_filenames = read_csv_and_get_filenames(taguan_csv)
    if taguan_filenames:
        filter_gpx_directory(taguan_gpx_dir, taguan_filenames, dry_run)

    print("\n" + "=" * 50)
    print("處理完成!")


if __name__ == "__main__":
    # 檢查必要的依賴
    try:
        import pandas as pd
    except ImportError:
        print("錯誤: 需要安裝 pandas 套件")
        print("請執行: pip install pandas")
        exit(1)

    main()
