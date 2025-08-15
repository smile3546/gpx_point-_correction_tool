#!/usr/bin/env python3
"""
路線更新 API 服務器
提供 RESTful API 來儲存編輯後的檔案
"""

import json
import os
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)  # 允許跨域請求

# 設定工作目錄
WORK_DIR = Path("../data_work")

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康檢查端點"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'work_dir': str(WORK_DIR.absolute())
    })

@app.route('/api/save-edited-files', methods=['POST'])
def save_edited_files():
    """儲存編輯後的檔案到指定資料夾"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': '沒有接收到資料'})
        
        route_type = data.get('route_type')
        route_name = data.get('route_name')
        txt_content = data.get('txt_content')
        geojson_content = data.get('geojson_content')
        
        if not all([route_type, route_name, txt_content, geojson_content]):
            return jsonify({'success': False, 'error': '缺少必要參數'})
        
        # 建立目標資料夾
        base_dir = Path(WORK_DIR).parent
        txt_dir = base_dir / "修改後的檔案" / "txt"
        geojson_dir = base_dir / "修改後的檔案" / "geojson"
        
        print(f"目標資料夾：{txt_dir}")
        print(f"目標資料夾：{geojson_dir}")
        
        txt_dir.mkdir(parents=True, exist_ok=True)
        geojson_dir.mkdir(parents=True, exist_ok=True)
        
        # 儲存 TXT 檔案
        txt_filename = f"{route_name}_route_{route_type}_edited.txt"
        txt_path = txt_dir / txt_filename
        print(f"儲存 TXT 檔案：{txt_path}")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(txt_content)
        
        # 儲存 GeoJSON 檔案
        geojson_filename = f"{route_name}_route_{route_type}_edited.geojson"
        geojson_path = geojson_dir / geojson_filename
        print(f"儲存 GeoJSON 檔案：{geojson_path}")
        with open(geojson_path, 'w', encoding='utf-8') as f:
            f.write(geojson_content)
        
        return jsonify({
            'success': True, 
            'message': f'檔案已儲存：{txt_filename}, {geojson_filename}',
            'txt_path': str(txt_path),
            'geojson_path': str(geojson_path)
        })
        
    except Exception as e:
        print(f"儲存編輯檔案時發生錯誤: {e}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("🚀 啟動檔案儲存 API 服務器...")
    print(f"工作目錄: {WORK_DIR.absolute()}")
    print("API 端點:")
    print("  - POST /api/save-edited-files - 儲存編輯後的檔案")
    print("  - GET  /api/health           - 健康檢查")
    print("\n按 Ctrl+C 停止服務器")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
