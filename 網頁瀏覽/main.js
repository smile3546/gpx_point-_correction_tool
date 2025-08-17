document.addEventListener('DOMContentLoaded', () => {
    console.log('路線切分瀏覽工具載入完成');

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
        version: '',
        routeName: '',
        partNumber: '',
        geojsonData: null,
        txtData: null
    };

    // DOM 元素
    const versionSelector = document.getElementById('route-version');
    const nameSelector = document.getElementById('route-name');
    const partSelector = document.getElementById('route-part');
    const segmentDetails = document.getElementById('segment-details');

    // 初始化事件監聽器
    initializeEventListeners();

    function initializeEventListeners() {
        // 版本選擇器變更
        versionSelector.addEventListener('change', async (e) => {
            const selectedVersion = e.target.value;
            console.log('選擇版本:', selectedVersion);

            if (selectedVersion) {
                currentData.version = selectedVersion;
                await loadRouteNames(selectedVersion);
                nameSelector.disabled = false;
                resetPartSelector();
                clearDisplay();
            } else {
                resetSelectors();
                clearDisplay();
            }
        });

        // 路線名稱選擇器變更
        nameSelector.addEventListener('change', async (e) => {
            const selectedName = e.target.value;
            console.log('選擇路線:', selectedName);

            if (selectedName) {
                currentData.routeName = selectedName;
                await loadPartNumbers(currentData.version, selectedName);
                partSelector.disabled = false;
                clearDisplay();
            } else {
                resetPartSelector();
                clearDisplay();
            }
        });

        // 段落選擇器變更
        partSelector.addEventListener('change', async (e) => {
            const selectedPart = e.target.value;
            console.log('選擇段落:', selectedPart);

            if (selectedPart) {
                currentData.partNumber = selectedPart;
                await loadSegmentData();
            } else {
                clearDisplay();
            }
        });
    }

    // 載入路線名稱列表
    async function loadRouteNames(version) {
        console.log(`載入版本 ${version} 的路線名稱...`);
        nameSelector.innerHTML = '<option value="">載入中...</option>';

        try {
            // 動態掃描可能的路線名稱（從實際資料夾結構推測）
            const possibleRoutes = [
                'mt_beidawu', 'mt_baiguda', '北大武山', '白姑大山',
                'chiyou_pintian', 'tao', 'tao_kalaye', 'tao_waterfall',
                'a_test', 'b_test'
            ];
            const availableRoutes = [];

            for (const routeName of possibleRoutes) {
                const isAvailable = await checkRouteExists(version, routeName);
                if (isAvailable) {
                    availableRoutes.push(routeName);
                    console.log(`發現路線: ${routeName}`);
                }
            }

            // 更新選擇器
            nameSelector.innerHTML = '<option value="">請選擇路線...</option>';
            availableRoutes.forEach(routeName => {
                const option = document.createElement('option');
                option.value = routeName;
                option.textContent = routeName;
                nameSelector.appendChild(option);
            });

            if (availableRoutes.length === 0) {
                nameSelector.innerHTML = '<option value="">未找到可用路線</option>';
                console.warn(`版本 ${version} 中沒有找到可用路線`);
            }

        } catch (error) {
            console.error('載入路線名稱失敗:', error);
            nameSelector.innerHTML = '<option value="">載入失敗</option>';
        }
    }

    // 檢查路線是否存在
    async function checkRouteExists(version, routeName) {
        try {
            const encodedRouteName = encodeURIComponent(routeName);
            const testPath = `/路線切分/${version}/geojson/${encodedRouteName}/${encodedRouteName}_切分好的_${version}_part1.geojson`;

            const response = await fetch(testPath, { method: 'HEAD' });
            return response.ok;
        } catch (error) {
            console.log(`路線 ${routeName} 檢查失敗:`, error);
            return false;
        }
    }

    // 載入段落編號列表
    async function loadPartNumbers(version, routeName) {
        console.log(`載入路線 ${routeName} 的段落編號...`);
        partSelector.innerHTML = '<option value="">載入中...</option>';

        try {
            const availableParts = [];
            const encodedRouteName = encodeURIComponent(routeName);

            // 從 part1 開始逐一檢查
            for (let i = 1; i <= 10; i++) { // 假設最多10個段落
                const partName = `part${i}`;
                const testPath = `/路線切分/${version}/geojson/${encodedRouteName}/${encodedRouteName}_切分好的_${version}_${partName}.geojson`;

                try {
                    const response = await fetch(testPath, { method: 'HEAD' });
                    if (response.ok) {
                        availableParts.push(partName);
                        console.log(`發現段落: ${partName}`);
                    } else {
                        break; // 假設段落是連續的，找不到就停止
                    }
                } catch (error) {
                    break;
                }
            }

            // 更新選擇器
            partSelector.innerHTML = '<option value="">請選擇段落...</option>';
            availableParts.forEach(partName => {
                const option = document.createElement('option');
                option.value = partName;
                option.textContent = partName.replace('part', 'Part ');
                partSelector.appendChild(option);
            });

            if (availableParts.length === 0) {
                partSelector.innerHTML = '<option value="">未找到段落</option>';
                console.warn(`路線 ${routeName} 沒有找到任何段落`);
            }

        } catch (error) {
            console.error('載入段落編號失敗:', error);
            partSelector.innerHTML = '<option value="">載入失敗</option>';
        }
    }

    // 載入段落資料
    async function loadSegmentData() {
        const { version, routeName, partNumber } = currentData;
        console.log(`載入段落資料: ${version}/${routeName}/${partNumber}`);

        try {
            showLoading();

            const encodedRouteName = encodeURIComponent(routeName);
            const geojsonPath = `/路線切分/${version}/geojson/${encodedRouteName}/${encodedRouteName}_切分好的_${version}_${partNumber}.geojson`;
            const txtPath = `/路線切分/${version}/txt/${encodedRouteName}/${encodedRouteName}_切分好的_${version}_${partNumber}_points.txt`;

            // 並行載入 GeoJSON 和 TXT 資料
            const [geojsonResponse, txtResponse] = await Promise.all([
                fetch(geojsonPath),
                fetch(txtPath)
            ]);

            if (!geojsonResponse.ok) {
                throw new Error(`無法載入 GeoJSON: ${geojsonResponse.status}`);
            }

            const rawGeojsonText = await geojsonResponse.text();
            // 修正 JSON 中的 NaN 值
            const cleanedGeojsonText = rawGeojsonText.replace(/"name":\s*NaN/g, '"name": null');
            currentData.geojsonData = JSON.parse(cleanedGeojsonText);

            if (txtResponse.ok) {
                currentData.txtData = await txtResponse.text();
            } else {
                console.warn('TXT 檔案載入失敗，僅顯示 GeoJSON 資料');
                currentData.txtData = null;
            }

            // 渲染資料
            renderMapData();
            renderSegmentInfo();
            renderDataTable();

            hideLoading();

        } catch (error) {
            console.error('載入段落資料失敗:', error);
            showError(`載入失敗: ${error.message}`);
        }
    }

    // 渲染地圖資料
    function renderMapData() {
        // 清空現有圖層
        routeLayer.clearLayers();
        pointsLayer.clearLayers();

        if (!currentData.geojsonData) return;

        console.log('渲染地圖資料...');

        const { geojsonData } = currentData;
        let bounds = null;

        // 渲染 GeoJSON 資料
        geojsonData.features.forEach(feature => {
            if (feature.geometry.type === 'LineString') {
                // 路線
                const line = L.geoJSON(feature, {
                    style: {
                        color: '#007bff',
                        weight: 4,
                        opacity: 0.8
                    }
                });
                routeLayer.addLayer(line);

                if (!bounds) {
                    bounds = line.getBounds();
                } else {
                    bounds.extend(line.getBounds());
                }
            } else if (feature.geometry.type === 'Point') {
                // 點位
                const coords = feature.geometry.coordinates;
                const latlng = L.latLng(coords[1], coords[0]);

                // 根據點位類型設定顏色
                let color = '#6c757d';
                if (feature.properties.type === 'comm') {
                    color = '#dc3545'; // 紅色：通訊點
                } else if (feature.properties.type === 'gpx') {
                    color = '#28a745'; // 綠色：GPX 點
                }

                const marker = L.circleMarker(latlng, {
                    radius: 6,
                    fillColor: color,
                    color: '#fff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                });

                // 設定 popup
                let popupContent = `<strong>順序:</strong> ${feature.properties.order}<br>`;
                if (feature.properties.name && feature.properties.name !== 'NaN') {
                    popupContent += `<strong>名稱:</strong> ${feature.properties.name}<br>`;
                }
                popupContent += `<strong>類型:</strong> ${feature.properties.type}<br>`;
                if (feature.properties.elevation) {
                    popupContent += `<strong>海拔:</strong> ${feature.properties.elevation}m<br>`;
                }
                if (feature.properties.time) {
                    const time = new Date(feature.properties.time).toLocaleString();
                    popupContent += `<strong>時間:</strong> ${time}`;
                }

                marker.bindPopup(popupContent);
                pointsLayer.addLayer(marker);

                if (!bounds) {
                    bounds = L.latLngBounds([latlng]);
                } else {
                    bounds.extend(latlng);
                }
            }
        });

        // 調整地圖視野
        if (bounds) {
            map.fitBounds(bounds, { padding: [20, 20] });
        }
    }

    // 渲染段落資訊
    function renderSegmentInfo() {
        if (!currentData.geojsonData) return;

        const { geojsonData, version, routeName, partNumber } = currentData;

        // 統計資訊
        const lineFeatures = geojsonData.features.filter(f => f.geometry.type === 'LineString');
        const pointFeatures = geojsonData.features.filter(f => f.geometry.type === 'Point');
        const commPoints = pointFeatures.filter(f => f.properties.type === 'comm');
        const gpxPoints = pointFeatures.filter(f => f.properties.type === 'gpx');

        // 從第一個 LineString 的 properties 獲取詳細資訊
        const routeInfo = lineFeatures.length > 0 ? lineFeatures[0].properties : {};

        const infoHTML = `
            <div class="stat-item">
                <span class="stat-label">路線版本:</span>
                <span class="stat-value">${version.replace('route_', 'Route ').toUpperCase()}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">路線名稱:</span>
                <span class="stat-value">${routeName}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">段落編號:</span>
                <span class="stat-value">${partNumber.replace('part', 'Part ')}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">起始點:</span>
                <span class="stat-value">${routeInfo.start_point || 'N/A'}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">結束點:</span>
                <span class="stat-value">${routeInfo.end_point || 'N/A'}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">總點位數:</span>
                <span class="stat-value">${pointFeatures.length}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">通訊點:</span>
                <span class="stat-value">${commPoints.length}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">GPX 點:</span>
                <span class="stat-value">${gpxPoints.length}</span>
            </div>
        `;

        segmentDetails.innerHTML = infoHTML;
    }

    // 渲染資料表格
    function renderDataTable() {
        if (dataTable) {
            dataTable.destroy();
        }

        if (!currentData.geojsonData) return;

        const pointFeatures = currentData.geojsonData.features.filter(f => f.geometry.type === 'Point');

        const tableData = pointFeatures.map(feature => {
            const coords = feature.geometry.coordinates;
            const props = feature.properties;

            // 處理時間格式
            let timeDisplay = 'N/A';
            if (props.time) {
                try {
                    timeDisplay = new Date(props.time).toLocaleString();
                } catch (e) {
                    timeDisplay = props.time;
                }
            }

            return [
                props.order || 'N/A',
                coords[1].toFixed(6), // 緯度
                coords[0].toFixed(6), // 經度
                props.elevation || 'N/A',
                props.type || 'N/A',
                (props.name && props.name !== 'NaN') ? props.name : 'N/A',
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
            if (rowIndex >= 0 && rowIndex < pointFeatures.length) {
                const feature = pointFeatures[rowIndex];
                const coords = feature.geometry.coordinates;
                const latlng = L.latLng(coords[1], coords[0]);

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

    // 重置選擇器
    function resetSelectors() {
        nameSelector.innerHTML = '<option value="">請先選擇版本...</option>';
        nameSelector.disabled = true;
        resetPartSelector();
    }

    function resetPartSelector() {
        partSelector.innerHTML = '<option value="">請先選擇路線...</option>';
        partSelector.disabled = true;
    }

    // 清空顯示
    function clearDisplay() {
        routeLayer.clearLayers();
        pointsLayer.clearLayers();
        segmentDetails.innerHTML = '<p>請選擇要檢視的路線段落</p>';

        if (dataTable) {
            dataTable.clear().draw();
        }

        currentData.geojsonData = null;
        currentData.txtData = null;
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

    console.log('路線切分瀏覽工具初始化完成');
});
