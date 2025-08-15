點位調整工具

這是一個用於處理登山路線GPX軌跡和通訊點的工具，可以將路線分割並整合通訊點資料。

功能特色

前端網頁界面
- 互動式地圖顯示路線和點位
- 支援路線A和路線B切換顯示
- 可新增編輯和刪除點位
- 點位表格檢視和排序
- 下載修改後的檔案

後端處理工具
- GPX軌跡檔案解析和處理
- 通訊點資料整合
- 自動時間和高度插值
- 路線分割功能
- GeoJSON和TXT格式匯出

檔案結構

data_raw
- gpx資料夾存放原始GPX軌跡檔案
- txt資料夾存放通訊點資料檔案

data_work
- route_a資料夾存放處理後的路線A資料
- route_b資料夾存放處理後的路線B資料

frontend
- index.html網頁主檔案
- main.js前端邏輯
- style.css樣式設定

scripts
- pt_process.py主要處理程式
- utils.py工具函數
- update_route_api.py路線更新API

使用方式

1. 將GPX軌跡檔案放入data_raw/gpx資料夾
2. 將對應的通訊點TXT檔案放入data_raw/txt資料夾
3. 執行pt_process.py進行資料處理
4. 開啟frontend/index.html使用網頁界面

支援的檔案格式

GPX檔案
- 包含軌跡點時間和座標資訊
- 支援多軌跡和多段落

TXT檔案
- 制表符分隔的通訊點資料
- 包含緯度經度海拔和名稱資訊

輸出格式

GeoJSON
- 標準地理資料格式
- 包含路線幾何和點位屬性

TXT
- 制表符分隔的點位清單
- 包含順序座標高度類型名稱等資訊

技術規格

程式語言Python和JavaScript
地圖庫Leaflet
資料處理GeoPandas和Pandas
座標系統WGS84經緯度
檔案編碼UTF-8

注意事項

確保GPX和TXT檔案名稱對應
通訊點資料格式需符合規範
處理大型軌跡檔案時可能需要較長時間
建議在處理前備份原始資料
