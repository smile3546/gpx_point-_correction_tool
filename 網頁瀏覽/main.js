document.addEventListener('DOMContentLoaded', () => {
    console.log('GPX 檔案瀏覽工具載入完成');

    // 初始化地圖
    const map = L.map('map').setView([23.5, 121], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // 地圖圖層
    let routeLayer = L.featureGroup().addTo(map);
    let pointsLayer = L.layerGroup().addTo(map);

    // 資料表格
    let dataTable = null;

    // 當前選中的資料
    let currentData = {
        fileName: '',
        gpxData: null,
        parsedData: null
    };

    // GPX 解析功能
    function parseGPX(gpxText) {
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(gpxText, 'text/xml');
        
        const tracks = [];
        const waypoints = [];
        
        // 解析軌跡點 (trkpt)
        const trkElements = xmlDoc.getElementsByTagName('trk');
        for (let i = 0; i < trkElements.length; i++) {
            const trksegs = trkElements[i].getElementsByTagName('trkseg');
            for (let j = 0; j < trksegs.length; j++) {
                const trkpts = trksegs[j].getElementsByTagName('trkpt');
                const trackPoints = [];
                
                for (let k = 0; k < trkpts.length; k++) {
                    const trkpt = trkpts[k];
                    const lat = parseFloat(trkpt.getAttribute('lat'));
                    const lon = parseFloat(trkpt.getAttribute('lon'));
                    
                    const elevation = trkpt.getElementsByTagName('ele')[0]?.textContent;
                    const time = trkpt.getElementsByTagName('time')[0]?.textContent;
                    const name = trkpt.getElementsByTagName('name')[0]?.textContent;
                    
                    trackPoints.push({
                        lat: lat,
                        lon: lon,
                        elevation: elevation ? parseFloat(elevation) : null,
                        time: time,
                        name: name,
                        order: k + 1
                    });
                }
                
                if (trackPoints.length > 0) {
                    tracks.push(trackPoints);
                }
            }
        }
        
        // 解析航點 (wpt)
        const wptElements = xmlDoc.getElementsByTagName('wpt');
        for (let i = 0; i < wptElements.length; i++) {
            const wpt = wptElements[i];
            const lat = parseFloat(wpt.getAttribute('lat'));
            const lon = parseFloat(wpt.getAttribute('lon'));
            
            const elevation = wpt.getElementsByTagName('ele')[0]?.textContent;
            const name = wpt.getElementsByTagName('name')[0]?.textContent;
            const desc = wpt.getElementsByTagName('desc')[0]?.textContent;
            
            waypoints.push({
                lat: lat,
                lon: lon,
                elevation: elevation ? parseFloat(elevation) : null,
                name: name,
                description: desc,
                type: 'waypoint'
            });
        }
        
        return { tracks, waypoints };
    }

    // DOM 元素
    const nameSelector = document.getElementById('route-name');
    const segmentDetails = document.getElementById('segment-details');

    // 可用的 GPX 檔案列表
    let availableFiles = [];

    // 初始化事件監聽器
    initializeEventListeners();
    loadAvailableGPXFiles();

    function initializeEventListeners() {
        // GPX 檔案選擇器變更
        nameSelector.addEventListener('change', async (e) => {
            const selectedFile = e.target.value;
            console.log('選擇 GPX 檔案:', selectedFile);

            if (selectedFile) {
                currentData.fileName = selectedFile;
                await loadGPXData(selectedFile);
            } else {
                clearDisplay();
            }
        });
    }

    // 載入可用的 GPX 檔案列表
    async function loadAvailableGPXFiles() {
        console.log('掃描可用的 GPX 檔案...');
        nameSelector.innerHTML = '<option value="">掃描中...</option>';

        try {
            // 直接掃描修改好的gpx資料夾中的檔案
            const possibleFiles = [
                'hehuan_north_route_a.gpx',
                'hehuan_north_west_route_a.gpx', 
                'hehuan_north_west.gpx',
                'hehuan_north.gpx',
                'mt_baiguda_route_a.gpx',
                'mt_baiguda.gpx',
                'mt_beidawu_route_a.gpx',
                'mt_beidawu.gpx',
                'mt_jade_front_route_a.gpx',
                'mt_jade_front.gpx',
                'mt_jade_main_route_a.gpx',
                'mt_jade_main.gpx',
                'mt_jade_west_route_a.gpx',
                'mt_jade_west_route_b.gpx'
            ];

            const availableGPXFiles = [];
            for (const fileName of possibleFiles) {
                const fullPath = `../修改好的gpx/${fileName}`;
                const isAvailable = await checkGPXFileExists(fullPath);
                if (isAvailable) {
                    availableGPXFiles.push({
                        name: fileName,
                        full_path: fullPath,
                        directory: ''
                    });
                }
            }

            availableFiles = availableGPXFiles;
            
            // 更新選擇器
            nameSelector.innerHTML = '<option value="">請選擇 GPX 檔案...</option>';
            availableGPXFiles.forEach(fileInfo => {
                const option = document.createElement('option');
                option.value = fileInfo.full_path;
                option.textContent = fileInfo.name.replace('.gpx', '');
                nameSelector.appendChild(option);
            });

            if (availableGPXFiles.length === 0) {
                nameSelector.innerHTML = '<option value="">未找到 GPX 檔案</option>';
                console.warn('沒有找到可用的 GPX 檔案');
            } else {
                console.log(`成功載入 ${availableGPXFiles.length} 個 GPX 檔案`);
            }

        } catch (error) {
            console.error('載入 GPX 檔案列表失敗:', error);
            nameSelector.innerHTML = '<option value="">載入失敗</option>';
        }
    }

    // 檢查 GPX 檔案是否存在
    async function checkGPXFileExists(filePath) {
        try {
            const response = await fetch(filePath, { method: 'HEAD' });
            return response.ok;
        } catch (error) {
            console.log(`GPX 檔案 ${filePath} 檢查失敗:`, error);
            return false;
        }
    }

    // 載入 GPX 資料
    async function loadGPXData(filePath) {
        console.log(`載入 GPX 檔案: ${filePath}`);

        try {
            showLoading();

            const response = await fetch(filePath);

            if (!response.ok) {
                throw new Error(`無法載入 GPX 檔案: ${response.status}`);
            }

            const gpxText = await response.text();
            currentData.gpxData = gpxText;
            currentData.parsedData = parseGPX(gpxText);

            console.log('GPX 解析結果:', currentData.parsedData);

            // 渲染資料
            renderMapData();
            renderGPXInfo();
            renderDataTable();

            hideLoading();

        } catch (error) {
            console.error('載入 GPX 檔案失敗:', error);
            showError(`載入失敗: ${error.message}`);
        }
    }

    // 渲染地圖資料
    function renderMapData() {
        // 清空現有圖層
        routeLayer.clearLayers();
        pointsLayer.clearLayers();

        if (!currentData.parsedData) return;

        console.log('渲染地圖資料...');

        const { tracks, waypoints } = currentData.parsedData;
        let bounds = null;

        // 渲染軌跡
        tracks.forEach((track, trackIndex) => {
            if (track.length > 1) {
                // 創建軌跡線
                const latlngs = track.map(point => [point.lat, point.lon]);
                const polyline = L.polyline(latlngs, {
                    color: '#007bff',
                    weight: 4,
                    opacity: 0.8
                });
                routeLayer.addLayer(polyline);

                if (!bounds) {
                    bounds = polyline.getBounds();
                } else {
                    bounds.extend(polyline.getBounds());
                }
            }

            // 渲染軌跡點
            track.forEach((point, pointIndex) => {
                const latlng = L.latLng(point.lat, point.lon);

                const marker = L.circleMarker(latlng, {
                    radius: 4,
                    fillColor: '#28a745', // 綠色：軌跡點
                    color: '#fff',
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.7
                });

                // 設定 popup
                let popupContent = `<strong>軌跡點:</strong> ${point.order}<br>`;
                if (point.name) {
                    popupContent += `<strong>名稱:</strong> ${point.name}<br>`;
                }
                if (point.elevation) {
                    popupContent += `<strong>海拔:</strong> ${point.elevation.toFixed(1)}m<br>`;
                }
                if (point.time) {
                    const time = new Date(point.time).toLocaleString();
                    popupContent += `<strong>時間:</strong> ${time}`;
                }

                marker.bindPopup(popupContent);
                pointsLayer.addLayer(marker);

                if (!bounds) {
                    bounds = L.latLngBounds([latlng]);
                } else {
                    bounds.extend(latlng);
                }
            });
        });

        // 渲染航點
        waypoints.forEach((waypoint, index) => {
            const latlng = L.latLng(waypoint.lat, waypoint.lon);

            const marker = L.circleMarker(latlng, {
                radius: 8,
                fillColor: '#dc3545', // 紅色：航點
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8
            });

            // 設定 popup
            let popupContent = `<strong>航點:</strong> ${index + 1}<br>`;
            if (waypoint.name) {
                popupContent += `<strong>名稱:</strong> ${waypoint.name}<br>`;
            }
            if (waypoint.description) {
                popupContent += `<strong>描述:</strong> ${waypoint.description}<br>`;
            }
            if (waypoint.elevation) {
                popupContent += `<strong>海拔:</strong> ${waypoint.elevation.toFixed(1)}m`;
            }

            marker.bindPopup(popupContent);
            pointsLayer.addLayer(marker);

            if (!bounds) {
                bounds = L.latLngBounds([latlng]);
            } else {
                bounds.extend(latlng);
            }
        });

        // 調整地圖視野
        if (bounds) {
            map.fitBounds(bounds, { padding: [20, 20] });
        }
    }

    // 渲染 GPX 資訊
    function renderGPXInfo() {
        if (!currentData.parsedData) return;

        const { tracks, waypoints } = currentData.parsedData;
        const { fileName } = currentData;

        // 統計資訊
        let totalTrackPoints = 0;
        tracks.forEach(track => totalTrackPoints += track.length);

        // 計算海拔範圍
        let minElevation = null;
        let maxElevation = null;
        tracks.forEach(track => {
            track.forEach(point => {
                if (point.elevation) {
                    if (minElevation === null || point.elevation < minElevation) {
                        minElevation = point.elevation;
                    }
                    if (maxElevation === null || point.elevation > maxElevation) {
                        maxElevation = point.elevation;
                    }
                }
            });
        });

        const infoHTML = `
            <div class="stat-item">
                <span class="stat-label">檔案名稱:</span>
                <span class="stat-value">${fileName}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">軌跡數量:</span>
                <span class="stat-value">${tracks.length}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">軌跡點數:</span>
                <span class="stat-value">${totalTrackPoints}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">航點數量:</span>
                <span class="stat-value">${waypoints.length}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">海拔範圍:</span>
                <span class="stat-value">${minElevation !== null && maxElevation !== null ? 
                    `${minElevation.toFixed(0)}m - ${maxElevation.toFixed(0)}m` : 'N/A'}</span>
            </div>
        `;

        segmentDetails.innerHTML = infoHTML;
    }

    // 渲染資料表格
    function renderDataTable() {
        if (dataTable) {
            dataTable.destroy();
        }

        if (!currentData.parsedData) return;

        const { tracks, waypoints } = currentData.parsedData;
        const allPoints = [];

        // 收集所有軌跡點
        tracks.forEach((track, trackIndex) => {
            track.forEach(point => {
                allPoints.push({
                    ...point,
                    type: 'track',
                    trackIndex: trackIndex
                });
            });
        });

        // 收集所有航點
        waypoints.forEach((waypoint, waypointIndex) => {
            allPoints.push({
                ...waypoint,
                type: 'waypoint',
                order: waypointIndex + 1
            });
        });

        const tableData = allPoints.map(point => {
            // 處理時間格式
            let timeDisplay = 'N/A';
            if (point.time) {
                try {
                    timeDisplay = new Date(point.time).toLocaleString();
                } catch (e) {
                    timeDisplay = point.time;
                }
            }

            return [
                point.order || 'N/A',
                point.lat.toFixed(6), // 緯度
                point.lon.toFixed(6), // 經度
                point.elevation ? point.elevation.toFixed(1) : 'N/A',
                point.type === 'track' ? '軌跡點' : '航點',
                point.name || 'N/A',
                timeDisplay
            ];
        });

        dataTable = $('#point-table').DataTable({
            data: tableData,
            columns: [
                { title: "順序", width: "80px" },
                { title: "緯度" },
                { title: "經度" },
                { title: "海拔（約）" },
                { title: "類型", width: "80px" },
                { title: "名稱" },
                { title: "時間" }
            ],
            order: [[0, 'asc']], // 按順序排列
            paging: false,
            searching: false,
            info: false,
            scrollY: '300px',
            scrollCollapse: true,
            language: {
                emptyTable: "沒有資料可顯示"
            }
        });

        // 表格行點擊事件
        $('#point-table tbody').on('click', 'tr', function () {
            const rowIndex = dataTable.row(this).index();
            if (rowIndex >= 0 && rowIndex < allPoints.length) {
                const point = allPoints[rowIndex];
                const latlng = L.latLng(point.lat, point.lon);

                map.flyTo(latlng, 16);

                // 找到對應的 marker 並開啟 popup
                pointsLayer.eachLayer(layer => {
                    if (layer.getLatLng().equals(latlng)) {
                        layer.openPopup();
                    }
                });
            }
        });
    }

    // 清空顯示
    function clearDisplay() {
        routeLayer.clearLayers();
        pointsLayer.clearLayers();
        segmentDetails.innerHTML = '<p>請選擇要檢視的 GPX 檔案</p>';

        if (dataTable) {
            dataTable.clear().draw();
        }

        currentData.fileName = '';
        currentData.gpxData = null;
        currentData.parsedData = null;
    }

    // 顯示載入狀態
    function showLoading() {
        segmentDetails.innerHTML = '<div class="loading">載入中...</div>';
    }

    // 隱藏載入狀態
    function hideLoading() {
        // 由 renderSegmentInfo 接管
    }

    // 顯示錯誤
    function showError(message) {
        segmentDetails.innerHTML = `<div class="error">${message}</div>`;
    }

    console.log('GPX 檔案瀏覽工具初始化完成');
});
