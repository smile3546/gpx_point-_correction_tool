document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM 載入完成，開始初始化...');

    // 初始化地圖
    const map = L.map('map').setView([23.5, 121], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    let routeLine = L.featureGroup().addTo(map);
    let markers = L.layerGroup().addTo(map);
    let backgroundRouteLayer = null; // 新增：背景路線層

    let currentRoutePath = 'route_a';
    let currentRouteName = '';
    let geojsonData = null;
    let backgroundGeojsonData = null; // 新增：背景路線資料
    let dataTable = null;
    let pointMarkers = []; // 存放所有點位 Marker 的陣列
    let pointFeatures = []; // 存放所有點位特徵的陣列
    let selectedPoints = new Set(); // 存放選中的點位 ID
    let modifications = { added: [], deleted: [], modified: [] }; // 修改追蹤
    let isAddingPoint = false; // 是否正在新增點位模式

    // 動態路線名稱列表 - 將從資料夾結構讀取
    let routeNames = [];

    // 全域變數：當前路線資料
    let currentRouteData = {
        routeA: { points: [], metadata: {} },
        routeB: { points: [], metadata: {} }
    };

    // 動態掃描 data_work 資料夾中的路線
    async function initializeRouteNames() {
        console.log('開始動態掃描 data_work 資料夾...');

        try {
            // 掃描可能的路線名稱
            const possibleRoutes = [
                'mt_beidawu', 'mt_baiguda', '北大武山', '白姑大山',
                'chiyou_pintian', 'tao', 'tao_kalaye', 'tao_waterfall',
                'a_test', 'b_test'
            ];
            
            const availableRoutes = [];
            
            for (const routeName of possibleRoutes) {
                const isAvailable = await checkRouteExists(routeName);
                if (isAvailable) {
                    availableRoutes.push(routeName);
                    console.log(`發現可用路線: ${routeName}`);
                }
            }
            
            routeNames = availableRoutes;
            console.log('動態掃描完成，可用路線:', routeNames);

            // 載入路線選擇器
            loadRouteNames();
            
        } catch (error) {
            console.error('動態掃描失敗，使用預設路線列表:', error);
            // 回退到預設列表
            routeNames = ['mt_beidawu', 'mt_baiguda'];
            loadRouteNames();
        }
    }

    // 檢查路線是否在 data_work 中存在
    async function checkRouteExists(routeName) {
        try {
            const encodedRouteName = encodeURIComponent(routeName);
            // 檢查 route_a 中的 route.geojson 是否存在
            const testPath = `/data_work/route_a/${encodedRouteName}/route.geojson`;
            
            const response = await fetch(testPath, { method: 'HEAD' });
            return response.ok;
        } catch (error) {
            console.log(`路線 ${routeName} 檢查失敗:`, error);
            return false;
        }
    }

    // 初始化路線列表
    initializeRouteNames().catch(error => {
        console.error('初始化路線列表失敗:', error);
    });

    function loadRouteNames() {
        const routeSelector = document.getElementById('route-selector');
        routeSelector.innerHTML = '';

        console.log('正在載入路線選擇器，路線數量:', routeNames.length);

        if (routeNames.length > 0) {
            routeNames.forEach(name => {
                const option = document.createElement('option');
                option.value = name;
                option.textContent = name; // 直接使用原始名稱，不進行編碼
                routeSelector.appendChild(option);
                console.log('新增路線選項:', name);
            });
            currentRouteName = routeNames[0];
            console.log('設定預設路線:', currentRouteName);

            // 檢查預設路線的檔案是否存在
            checkRouteFileExists(currentRouteName).then(async exists => {
                if (exists) {
                    await loadRouteData();
                } else {
                    console.warn('預設路線檔案不存在，嘗試下一個路線');
                    tryNextRoute();
                }
            });
        } else {
            console.error('沒有找到任何路線資料');
            alert('未發現任何路線資料。請檢查 data_work 資料夾結構。');
        }
    }

    // 新增：檢查路線檔案是否存在
    async function checkRouteFileExists(routeName) {
        // 使用 encodeURIComponent 確保中文路徑正確編碼
        const encodedRouteName = encodeURIComponent(routeName);
        // 使用絕對路徑，從伺服器根目錄開始
        const geojsonPath = `/data_work/${currentRoutePath}/${encodedRouteName}/route.geojson`;

        console.log(`檢查檔案存在性: ${routeName} -> ${geojsonPath}`);

        try {
            const response = await fetch(geojsonPath, { method: 'HEAD' });
            console.log(`檔案檢查結果: ${routeName}, 狀態: ${response.status}, 路徑: ${geojsonPath}`);
            return response.ok;
        } catch (error) {
            console.error(`檔案檢查失敗: ${routeName}, 錯誤:`, error);
            return false;
        }
    }

    // 新增：嘗試下一個可用的路線
    function tryNextRoute() {
        const currentIndex = routeNames.indexOf(currentRouteName);
        const nextIndex = (currentIndex + 1) % routeNames.length;

        console.log(`嘗試下一個路線: 當前索引 ${currentIndex}, 下一個索引 ${nextIndex}`);

        if (nextIndex !== currentIndex) {
            currentRouteName = routeNames[nextIndex];
            console.log('嘗試下一個路線:', currentRouteName);

            checkRouteFileExists(currentRouteName).then(async exists => {
                if (exists) {
                    console.log('找到可用路線:', currentRouteName);
                    await loadRouteData();
                } else {
                    console.warn('路線檔案不存在:', currentRouteName);
                    if (nextIndex < routeNames.length - 1) {
                        tryNextRoute();
                    } else {
                        console.error('已嘗試所有路線，都沒有找到可用檔案');
                        alert('沒有找到任何可用的路線檔案。請檢查 data_work 資料夾。');
                    }
                }
            });
        } else {
            console.error('沒有找到任何可用的路線檔案');
            alert('沒有找到任何可用的路線檔案。請檢查 data_work 資料夾。');
        }
    }

    const routeSelector = document.getElementById('route-selector');
    routeSelector.addEventListener('change', (e) => {
        const selectedRoute = e.target.value;
        console.log('選擇路線:', selectedRoute);

        // 檢查選擇的路線檔案是否存在
        checkRouteFileExists(selectedRoute).then(async exists => {
            if (exists) {
                currentRouteName = selectedRoute;
                await loadRouteData();
            } else {
                console.warn('選擇的路線檔案不存在:', selectedRoute);
                alert(`路線 "${selectedRoute}" 的檔案不存在，請選擇其他路線。`);
                // 恢復到之前的路線
                routeSelector.value = currentRouteName;
            }
        });
    });

    document.getElementById('show-route-a').addEventListener('click', async () => {
        currentRoutePath = 'route_a';
        document.getElementById('show-route-a').classList.add('active');
        document.getElementById('show-route-b').classList.remove('active');
        await loadRouteData();
    });

    document.getElementById('show-route-b').addEventListener('click', async () => {
        currentRoutePath = 'route_b';
        document.getElementById('show-route-a').classList.remove('active');
        document.getElementById('show-route-b').classList.add('active');
        await loadRouteData();
    });

    async function loadRouteData() {
        if (!currentRouteName) return;

        markers.clearLayers();
        routeLine.clearLayers();
        pointMarkers = [];
        pointFeatures = [];
        selectedPoints.clear();

        // 使用 encodeURIComponent 確保中文路徑正確編碼
        const encodedRouteName = encodeURIComponent(currentRouteName);
        // 使用絕對路徑，從伺服器根目錄開始
        const geojsonPath = `/data_work/${currentRoutePath}/${encodedRouteName}/route.geojson`;

        fetch(geojsonPath)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`找不到路線檔案: ${geojsonPath}`);
                }
                return response.json();
            })
            .then(async data => {
                geojsonData = data;

                // 從 GeoJSON 中提取點位特徵
                if (data.features) {
                    data.features.forEach(feature => {
                        if (feature.geometry.type === 'Point') {
                            // 清理點位特徵的屬性，確保沒有 NaN 值
                            if (feature.properties) {
                                Object.keys(feature.properties).forEach(key => {
                                    const value = feature.properties[key];
                                    if (typeof value === 'number' && isNaN(value)) {
                                        feature.properties[key] = null;
                                    }
                                });
                            }
                            pointFeatures.push(feature);
                        }
                    });
                }

                // 載入背景路線，確保在渲染前完成
                await loadBackgroundRoute();
                renderMapAndTable();
                updateButtonStates();

                console.log('載入路線資料成功:', currentRouteName, '點位數量:', pointFeatures.length);
            })
            .catch(error => {
                console.error("載入 GeoJSON 檔案失敗:", error);
                alert(error.message);
            });
    }

    // 新增：載入背景路線
    async function loadBackgroundRoute() {
        if (!currentRouteName) {
            console.log('沒有當前路線名稱，跳過背景路線載入');
            return;
        }

        // 清除現有的背景路線層
        if (backgroundRouteLayer) {
            map.removeLayer(backgroundRouteLayer);
            backgroundRouteLayer = null;
        }

        // 確定背景路線路徑
        const backgroundRoutePath = currentRoutePath === 'route_a' ? 'route_b' : 'route_a';
        const encodedRouteName = encodeURIComponent(currentRouteName);
        // 使用絕對路徑，從伺服器根目錄開始
        const backgroundGeojsonPath = `/data_work/${backgroundRoutePath}/${encodedRouteName}/route.geojson`;

        console.log(`嘗試載入背景路線: ${currentRouteName} -> ${backgroundRoutePath}`);
        console.log(`背景路線完整路徑: ${backgroundGeojsonPath}`);

        try {
            const response = await fetch(backgroundGeojsonPath);
            console.log(`背景路線 HTTP 回應: ${response.status} ${response.statusText}`);

            if (response.ok) {
                backgroundGeojsonData = await response.json();
                console.log('背景路線載入成功:', backgroundRoutePath, currentRouteName);
                console.log('背景路線特徵數量:', backgroundGeojsonData.features ? backgroundGeojsonData.features.length : 0);

                // 檢查背景路線的結構
                if (backgroundGeojsonData.features) {
                    const lineStrings = backgroundGeojsonData.features.filter(f => f.geometry.type === 'LineString');
                    const points = backgroundGeojsonData.features.filter(f => f.geometry.type === 'Point');
                    console.log('背景路線結構 - LineString:', lineStrings.length, 'Point:', points.length);

                    if (lineStrings.length === 0) {
                        console.warn('背景路線沒有 LineString 特徵，無法顯示灰色線條');
                    }

                    if (points.length === 0) {
                        console.warn('背景路線沒有 Point 特徵，無法顯示灰色點位');
                    } else {
                        console.log('背景路線包含點位，準備渲染:', points.length, '個點位');
                        // 顯示前幾個點位的詳細資訊
                        points.slice(0, 3).forEach((point, index) => {
                            console.log(`背景點位 ${index}:`, point.geometry.coordinates, point.properties);
                        });
                    }
                }
            } else {
                console.log(`背景路線檔案不存在 (${response.status}): ${backgroundGeojsonPath}`);

                // 嘗試載入其他可用的背景路線
                await tryLoadAlternativeBackgroundRoute(backgroundRoutePath);
            }
        } catch (error) {
            console.error('載入背景路線失敗:', error);

            // 嘗試載入其他可用的背景路線
            await tryLoadAlternativeBackgroundRoute(backgroundRoutePath);
        }
    }

    // 新增：嘗試載入替代背景路線
    async function tryLoadAlternativeBackgroundRoute(backgroundRoutePath) {
        console.log('嘗試載入替代背景路線...');

        // 已知在兩個資料夾中都存在的路線
        const availableRoutes = ['tao_waterfall', '北大武山', '白姑大山'];

        for (const routeName of availableRoutes) {
            if (routeName === currentRouteName) continue; // 跳過當前路線

            const encodedRouteName = encodeURIComponent(routeName);
            const alternativePath = `/data_work/${backgroundRoutePath}/${encodedRouteName}/route.geojson`;

            console.log(`嘗試替代路線: ${routeName} -> ${alternativePath}`);

            try {
                const response = await fetch(alternativePath);
                if (response.ok) {
                    backgroundGeojsonData = await response.json();
                    console.log(`成功載入替代背景路線: ${routeName}`);

                    // 檢查是否有 LineString
                    if (backgroundGeojsonData.features) {
                        const lineStrings = backgroundGeojsonData.features.filter(f => f.geometry.type === 'LineString');
                        if (lineStrings.length > 0) {
                            console.log(`替代背景路線包含 ${lineStrings.length} 個 LineString`);
                            return; // 成功載入，退出
                        }
                    }
                }
            } catch (error) {
                console.log(`替代路線 ${routeName} 載入失敗:`, error);
            }
        }

        console.log('沒有找到可用的背景路線');
        backgroundGeojsonData = null;
    }

    function renderMapAndTable() {
        // 清空現有的地圖層
        markers.clearLayers();
        routeLine.clearLayers();
        pointMarkers = [];

        // 清除背景路線層
        if (backgroundRouteLayer) {
            map.removeLayer(backgroundRouteLayer);
            backgroundRouteLayer = null;
        }

        if (!geojsonData && pointFeatures.length === 0) {
            console.error("沒有資料可以渲染。");
            return;
        }

        let routeColor = (currentRoutePath === 'route_a') ? '#dc3545' : '#007bff';

        // 渲染背景路線（灰色）
        console.log('背景路線渲染檢查:');
        console.log('- backgroundGeojsonData 存在:', !!backgroundGeojsonData);
        console.log('- currentRoutePath:', currentRoutePath);
        console.log('- currentRouteName:', currentRouteName);

        if (backgroundGeojsonData) {
            console.log('開始渲染背景路線...');
            console.log('背景路線資料結構:', backgroundGeojsonData);

            // 先渲染線條
            const backgroundLineLayer = L.geoJSON(backgroundGeojsonData, {
                style: (feature) => {
                    if (feature.geometry.type === 'LineString') {
                        console.log('渲染背景路線線條');
                        return {
                            color: '#888888',
                            weight: 3,
                            opacity: 0.7
                        };
                    }
                    return null;
                },
                filter: (feature) => {
                    return feature.geometry.type === 'LineString';
                },
                onEachFeature: (feature, layer) => {
                    layer.interactive = false;
                    if (layer.setZIndexOffset) {
                        layer.setZIndexOffset(-1000);
                    }
                }
            });

            // 然後手動渲染點位
            const backgroundPointsGroup = L.layerGroup();
            let pointCount = 0;

            if (backgroundGeojsonData.features) {
                backgroundGeojsonData.features.forEach(feature => {
                    if (feature.geometry.type === 'Point') {
                        const coords = feature.geometry.coordinates;
                        const latlng = L.latLng(coords[1], coords[0]);

                        console.log(`手動渲染背景點位 ${pointCount}:`, latlng);

                        const marker = L.circleMarker(latlng, {
                            color: '#666666',
                            fillColor: '#999999',
                            weight: 1,
                            opacity: 0.8,
                            fillOpacity: 0.6,
                            radius: 3
                        });

                        marker.interactive = false;
                        backgroundPointsGroup.addLayer(marker);
                        pointCount++;
                    }
                });
            }

            console.log(`手動渲染了 ${pointCount} 個背景點位`);

            // 將兩個圖層組合
            backgroundRouteLayer = L.layerGroup([backgroundLineLayer, backgroundPointsGroup]);
            backgroundRouteLayer.addTo(map);

            console.log('背景路線層已添加到地圖，樣式：灰色實線，包含灰色小圓點');
        } else {
            console.log('沒有背景路線資料');
        }

        // 如果有 GeoJSON 資料，渲染主要路線（在背景路線之上）
        if (geojsonData) {
            const mainRouteLayer = L.geoJSON(geojsonData, {
                style: (feature) => {
                    if (feature.geometry.type === 'LineString') {
                        console.log('渲染主要路線，顏色:', routeColor);
                        return {
                            color: routeColor,
                            weight: 5,
                            opacity: 1.0
                        };
                    }
                },
                onEachFeature: (feature, layer) => {
                    if (feature.geometry.type === 'LineString') {
                        // 設定較高的 z-index，確保在前景
                        if (layer.setZIndexOffset) {
                            layer.setZIndexOffset(1000);
                        }
                        routeLine.addLayer(layer);
                        console.log('主要路線線條設定為前景，Z-index: 1000');
                    }
                }
            });
        }

        // 渲染所有點位（包括原有的和新增的）
        pointFeatures.forEach((feature, index) => {
            if (feature.geometry.type === 'Point') {
                const latlng = L.latLng(feature.geometry.coordinates[1], feature.geometry.coordinates[0]);

                // 根據點位類型設定不同顏色
                let fillColor = '#808080';
                if (feature.properties && feature.properties.type === 'comm') {
                    fillColor = '#ff6b6b';
                } else if (feature.properties && feature.properties.type === 'gpx') {
                    fillColor = '#4ecdc4';
                }

                let marker = L.circleMarker(latlng, {
                    radius: 6,
                    fillColor: fillColor,
                    color: '#000',
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.8
                });

                // 設定 popup 內容
                let popupContent = '';
                if (feature.properties && feature.properties.order) {
                    popupContent += `順序: ${feature.properties.order}<br>`;
                }
                if (feature.properties && feature.properties.name) {
                    popupContent += `名稱: ${feature.properties.name}<br>`;
                }
                if (feature.properties && feature.properties.type) {
                    popupContent += `類型: ${feature.properties.type}<br>`;
                }
                if (feature.properties && feature.properties.elevation) {
                    popupContent += `海拔: ${feature.properties.elevation}m`;
                }
                marker.bindPopup(popupContent);

                // 添加點擊事件
                marker.on('click', () => {
                    togglePointSelection(index);
                });

                markers.addLayer(marker);
                pointMarkers.push(marker);
            }
        });

        // 調整地圖視圖
        if (routeLine.getLayers().length > 0) {
            map.fitBounds(routeLine.getBounds());
        } else if (markers.getLayers().length > 0) {
            map.fitBounds(markers.getBounds());
        } else {
            map.setView([23.5, 121], 10);
        }

        renderTable();
    }

    function renderTable() {
        if (dataTable) {
            dataTable.destroy();
        }

        // 準備表格資料
        let tableData = pointFeatures.map((feature, index) => {
            // 安全處理海拔值
            let elevationDisplay = 'N/A';
            if (feature.properties.elevation !== null && feature.properties.elevation !== undefined) {
                const elevation = parseFloat(feature.properties.elevation);
                if (!isNaN(elevation)) {
                    elevationDisplay = elevation.toString();
                }
            }

            return [
                `<input type="checkbox" class="point-checkbox" data-index="${index}" ${selectedPoints.has(index) ? 'checked' : ''}>`,
                feature.properties.order || 'N/A',
                feature.geometry.coordinates[1].toFixed(6),
                feature.geometry.coordinates[0].toFixed(6),
                elevationDisplay,
                feature.properties.type || 'N/A',
                feature.properties.name || 'N/A'
            ];
        });

        dataTable = $('#point-table').DataTable({
            data: tableData,
            columns: [
                { title: "選擇", orderable: false, width: "50px" },
                { title: "順序" },
                { title: "緯度" },
                { title: "經度" },
                { title: "海拔（約）" },
                { title: "類型" },
                { title: "名稱" }
            ],
            ordering: false,
            paging: false,
            searching: false,
            info: false,
            scrollY: '300px',
            scrollCollapse: true,
            destroy: true
        });

        // 監聽表格選擇框變化
        $('#point-table tbody').off('change', '.point-checkbox').on('change', '.point-checkbox', function () {
            const index = parseInt($(this).data('index'));
            if (this.checked) {
                selectedPoints.add(index);
            } else {
                selectedPoints.delete(index);
            }
            updateButtonStates();
        });

        // 監聽表格行點擊
        $('#point-table tbody').off('click', 'tr').on('click', 'tr', function (e) {
            if (e.target.type !== 'checkbox') {
                const index = dataTable.row(this).index();
                if (index >= 0 && index < pointFeatures.length) {
                    const point = pointFeatures[index];
                    const latlng = L.latLng(point.geometry.coordinates[1], point.geometry.coordinates[0]);
                    map.flyTo(latlng, 16);
                    if (pointMarkers[index]) {
                        pointMarkers[index].openPopup();
                    }
                }
            }
        });
    }

    function togglePointSelection(index) {
        if (selectedPoints.has(index)) {
            selectedPoints.delete(index);
        } else {
            selectedPoints.add(index);
        }
        updateButtonStates();
        renderTable(); // 重新渲染表格以更新選擇狀態

        console.log('切換點位選擇:', index, '選中點位數量:', selectedPoints.size);
    }

    function updateButtonStates() {
        const deleteBtn = document.getElementById('delete-point');
        const statusDiv = document.getElementById('modification-status');

        // 更新刪除按鈕狀態
        deleteBtn.disabled = selectedPoints.size === 0;

        // 更新修改狀態顯示
        const hasChanges = modifications.added.length > 0 ||
            modifications.deleted.length > 0 ||
            modifications.modified.length > 0;

        if (hasChanges) {
            statusDiv.textContent = `有 ${modifications.added.length} 個新增、${modifications.deleted.length} 個刪除、${modifications.modified.length} 個修改`;
            statusDiv.classList.add('has-changes');
        } else {
            statusDiv.textContent = '';
            statusDiv.classList.remove('has-changes');
        }
    }

    // 新增點位功能
    document.getElementById('add-point').addEventListener('click', () => {
        showAddPointModal();
    });

    function showAddPointModal() {
        const modal = document.getElementById('add-point-modal');
        modal.style.display = 'block';

        // 清空表單
        document.getElementById('add-point-form').reset();

        // 設定預設座標（地圖中心）
        const center = map.getCenter();
        document.getElementById('point-lat').value = center.lat.toFixed(6);
        document.getElementById('point-lng').value = center.lng.toFixed(6);
    }

    function showAddPointModalAtLocation(lat, lng) {
        const modal = document.getElementById('add-point-modal');
        modal.style.display = 'block';

        // 清空表單
        document.getElementById('add-point-form').reset();

        // 設定點擊位置的座標
        document.getElementById('point-lat').value = lat.toFixed(6);
        document.getElementById('point-lng').value = lng.toFixed(6);

        // 自動計算插入位置和順序
        const insertInfo = calculateInsertPosition(lat, lng);
        document.getElementById('point-order').value = insertInfo.position;
    }

    function closeModal() {
        document.getElementById('add-point-modal').style.display = 'none';
    }

    function closeDeleteModal() {
        document.getElementById('delete-confirm-modal').style.display = 'none';
    }

    // 地圖點擊新增點位
    map.on('click', function (e) {
        // 檢查是否在新增點位模式
        const modal = document.getElementById('add-point-modal');
        if (modal.style.display === 'block') {
            document.getElementById('point-lat').value = e.latlng.lat.toFixed(6);
            document.getElementById('point-lng').value = e.latlng.lng.toFixed(6);
        } else {
            // 如果不在新增模式，點擊地圖直接新增點位
            showAddPointModalAtLocation(e.latlng.lat, e.latlng.lng);
        }
    });

    // 新增點位表單提交
    document.getElementById('add-point-form').addEventListener('submit', function (e) {
        e.preventDefault();

        // 驗證輸入值
        const lat = parseFloat(document.getElementById('point-lat').value);
        const lng = parseFloat(document.getElementById('point-lng').value);
        const elevationInput = document.getElementById('point-elevation').value;
        const elevation = elevationInput ? parseFloat(elevationInput) : null;

        // 檢查數值是否有效
        if (isNaN(lat) || isNaN(lng)) {
            alert('請輸入有效的緯度和經度數值');
            return;
        }

        if (elevation !== null && isNaN(elevation)) {
            alert('請輸入有效的海拔數值');
            return;
        }

        const formData = {
            type: document.getElementById('point-type').value,
            name: document.getElementById('point-name').value,
            latitude: lat,
            longitude: lng,
            elevation: elevation,
            order: document.getElementById('point-order').value
        };

        addPoint(formData);
        closeModal();
    });

    function addPoint(pointData) {
        // 生成新的點位 ID
        const newPointId = `new_${Date.now()}`;

        // 建立新的點位特徵
        const newFeature = {
            type: 'Feature',
            geometry: {
                type: 'Point',
                coordinates: [pointData.longitude, pointData.latitude]
            },
            properties: {
                order: generateNewOrder(pointData.order),
                type: pointData.type,
                name: pointData.name || '',
                elevation: pointData.elevation || null,
                id: newPointId
            }
        };

        // 根據插入位置決定插入索引
        let insertIndex = 0;
        if (pointData.order === 'end') {
            insertIndex = pointFeatures.length;
        } else if (pointData.order === 'custom') {
            // 使用計算出的插入位置
            const insertInfo = calculateInsertPosition(pointData.latitude, pointData.longitude);
            insertIndex = insertInfo.insertIndex;
        }

        // 插入新點位
        pointFeatures.splice(insertIndex, 0, newFeature);

        // 重新計算順序編號
        recalculateOrder();

        // 記錄修改
        modifications.added.push({
            pointId: newPointId,
            data: pointData,
            timestamp: new Date()
        });

        // 重新渲染地圖和表格
        renderMapAndTable();
        updateButtonStates();

        console.log('新增點位成功:', newFeature);
        console.log('當前點位數量:', pointFeatures.length);
    }

    function generateNewOrder(position) {
        if (position === 'start') {
            return '1';
        } else if (position === 'end') {
            return (pointFeatures.length + 1).toString();
        } else {
            return Math.floor(pointFeatures.length / 2 + 1).toString();
        }
    }

    function recalculateOrder() {
        pointFeatures.forEach((feature, index) => {
            feature.properties.order = (index + 1).toString();
        });

        console.log('重新計算順序完成，點位數量:', pointFeatures.length);
    }

    function calculateInsertPosition(lat, lng) {
        if (pointFeatures.length === 0) {
            return { position: 'start', insertIndex: 0 };
        }

        const newPoint = L.latLng(lat, lng);
        let closestDistance = Infinity;
        let closestIndex = -1;

        // 找到最近的點位
        for (let i = 0; i < pointFeatures.length; i++) {
            const feature = pointFeatures[i];
            const pointLatLng = L.latLng(feature.geometry.coordinates[1], feature.geometry.coordinates[0]);
            const distance = newPoint.distanceTo(pointLatLng);

            if (distance < closestDistance) {
                closestDistance = distance;
                closestIndex = i;
            }
        }

        // 決定插入位置
        if (closestIndex === 0) {
            return { position: 'start', insertIndex: 0 };
        } else if (closestIndex === pointFeatures.length - 1) {
            return { position: 'end', insertIndex: pointFeatures.length };
        } else {
            // 在兩個點之間插入，新點位會變成 closestIndex + 1
            return { position: 'custom', insertIndex: closestIndex + 1 };
        }
    }



    // 刪除點位功能
    document.getElementById('delete-point').addEventListener('click', () => {
        if (selectedPoints.size === 0) return;

        showDeleteConfirmModal();
    });

    function showDeleteConfirmModal() {
        const modal = document.getElementById('delete-confirm-modal');
        const pointsList = document.getElementById('delete-points-list');

        pointsList.innerHTML = '';
        selectedPoints.forEach(index => {
            const point = pointFeatures[index];
            const div = document.createElement('div');
            div.textContent = `順序 ${point.properties.order}: ${point.properties.name || '無名稱'}`;
            pointsList.appendChild(div);
        });

        modal.style.display = 'block';
    }

    document.getElementById('confirm-delete').addEventListener('click', () => {
        deleteSelectedPoints();
        closeDeleteModal();
    });

    function deleteSelectedPoints() {
        const pointsToDelete = Array.from(selectedPoints).sort((a, b) => b - a); // 從大到小排序

        console.log('準備刪除點位:', pointsToDelete);

        pointsToDelete.forEach(index => {
            const point = pointFeatures[index];

            // 記錄刪除的點位
            modifications.deleted.push({
                pointId: point.properties.id || `point_${index}`,
                data: point,
                timestamp: new Date()
            });

            // 從陣列中移除
            pointFeatures.splice(index, 1);
        });

        // 重新計算順序編號
        recalculateOrder();

        // 清空選擇
        selectedPoints.clear();

        // 重新渲染
        renderMapAndTable();
        updateButtonStates();

        console.log('刪除完成，剩餘點位數量:', pointFeatures.length);
    }



    // 修改後的儲存功能 - 使用瀏覽器下載
    document.getElementById('save-txt').addEventListener('click', () => {
        // 1. 生成 TXT 內容
        let txtContent = "順序\t緯度\t經度\t海拔（約）\t類型\t名稱\n";

        pointFeatures.forEach(feature => {
            // 安全處理海拔值
            let elevationDisplay = 'N/A';
            if (feature.properties.elevation !== null && feature.properties.elevation !== undefined) {
                const elevation = parseFloat(feature.properties.elevation);
                if (!isNaN(elevation)) {
                    elevationDisplay = elevation.toString();
                }
            }

            let row = `${feature.properties.order}\t${feature.geometry.coordinates[1].toFixed(6)}\t${feature.geometry.coordinates[0].toFixed(6)}\t${elevationDisplay}\t${feature.properties.type || 'N/A'}\t${feature.properties.name || 'N/A'}`;
            txtContent += row + "\n";
        });

        // 2. 生成 GeoJSON 內容
        const geojsonContent = generateGeoJSON();

        // 3. 下載 TXT 檔案 - 確保中文檔案名稱正確處理
        const txtFilename = `${currentRouteName}_route_${currentRoutePath === 'route_a' ? 'a' : 'b'}_edited.txt`;
        downloadFile(txtContent, txtFilename, 'text/plain;charset=utf-8');

        // 4. 下載 GeoJSON 檔案 - 確保中文檔案名稱正確處理
        const geojsonFilename = `${currentRouteName}_route_${currentRoutePath === 'route_a' ? 'a' : 'b'}_edited.geojson`;
        downloadFile(JSON.stringify(geojsonContent, null, 2), geojsonFilename, 'application/json;charset=utf-8');

        alert("已將編輯後的點位儲存為 TXT 和 GeoJSON 檔案，請檢查您的下載資料夾！");
    });

    function downloadFile(content, filename, contentType) {
        const blob = new Blob([content], { type: contentType });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        // 確保中文檔案名稱正確處理
        link.download = filename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
    }



    function generateGeoJSON() {
        const geojson = {
            type: "FeatureCollection",
            features: []
        };

        // 線段 Feature
        if (pointFeatures.length > 1) {
            const coords = pointFeatures.map(feature => [
                feature.geometry.coordinates[0],
                feature.geometry.coordinates[1]
            ]);

            geojson.features.push({
                type: "Feature",
                geometry: {
                    type: "LineString",
                    coordinates: coords
                },
                properties: {
                    name: `${currentRouteName}_${currentRoutePath}`,
                    route_type: "main_route",
                    total_points: pointFeatures.length,
                    comm_points: pointFeatures.filter(f => f.properties.type === 'comm').length,
                    gpx_points: pointFeatures.filter(f => f.properties.type === 'gpx').length
                }
            });
        }

        // 點位 Features
        pointFeatures.forEach(feature => {
            // 清理屬性，確保沒有 NaN 或無效值
            const cleanProperties = {};
            if (feature.properties) {
                Object.keys(feature.properties).forEach(key => {
                    const value = feature.properties[key];
                    // 過濾掉 NaN 值，保留 null 和其他有效值
                    if (value !== undefined && !(typeof value === 'number' && isNaN(value))) {
                        cleanProperties[key] = value;
                    }
                });
            }

            geojson.features.push({
                type: "Feature",
                geometry: feature.geometry,
                properties: cleanProperties
            });
        });

        return geojson;
    }

    // 全域函式供 HTML 調用
    window.closeModal = closeModal;
    window.closeDeleteModal = closeDeleteModal;
});