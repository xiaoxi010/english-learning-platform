(function () {
    var page = document.getElementById('jilinDataPage');
    if (!page) return;

    var searchUrl = page.getAttribute('data-search-url');
    var schoolsUrl = page.getAttribute('data-schools-url');
    var filtersUrl = page.getAttribute('data-filters-url');
    var enabled = page.getAttribute('data-enabled') === '1';
    var DRAFT_KEY = 'gaokao_apply_system_draft';
    var PROFILE_KEY = 'gaokao_apply_profile';
    var PREFER_STORE_KEY = 'gaokao_apply_prefer_store';
    var planUrl = page.getAttribute('data-plan-url') || '';
    var gaokaoProvince = page.getAttribute('data-gaokao-province') || '吉林';
    var defaultBatch = page.getAttribute('data-default-batch') || 'undergraduate';
    var provinceBatches = [];
    var batchLabels = {};

    try {
        provinceBatches = JSON.parse(page.getAttribute('data-province-batches') || '[]');
    } catch (e) {
        provinceBatches = [];
    }
    try {
        batchLabels = JSON.parse(page.getAttribute('data-batch-labels') || '{}');
    } catch (e2) {
        batchLabels = {};
    }

    function availableBatchIds() {
        if (provinceBatches.length) {
            return provinceBatches.map(function (tab) { return tab.id; });
        }
        return ['strong', 'early', 'undergraduate', 'junior'];
    }

    function normalizeActiveBatch(batchId) {
        var ids = availableBatchIds();
        if (batchId && ids.indexOf(batchId) >= 0) return batchId;
        if (ids.indexOf(defaultBatch) >= 0) return defaultBatch;
        return ids[0] || 'undergraduate';
    }

    function batchDisplayLabel(batchId) {
        if (batchLabels && batchLabels[batchId]) return batchLabels[batchId];
        for (var i = 0; i < provinceBatches.length; i++) {
            if (provinceBatches[i].id === batchId) return provinceBatches[i].label;
        }
        var fallback = {
            strong: '强基计划',
            early: '提前批',
            undergraduate: '本科批',
            junior: '专科批'
        };
        return fallback[batchId] || batchId;
    }

    function getCurrentTab() {
        for (var i = 0; i < provinceBatches.length; i++) {
            if (provinceBatches[i].id === currentTabId) return provinceBatches[i];
        }
        return null;
    }

    function apiDatasetParam() {
        var tab = getCurrentTab();
        return (tab && tab.bucket) ? tab.bucket : currentTabId;
    }

    function apiBatchParam() {
        var tab = getCurrentTab();
        return (tab && tab.batch) ? tab.batch : '';
    }

    function datasetQueryParams() {
        var q = 'dataset=' + encodeURIComponent(apiDatasetParam());
        var batch = apiBatchParam();
        if (batch) q += '&batch=' + encodeURIComponent(batch);
        return q;
    }

    function syncStrongPageClass() {
        page.classList.toggle('gk-data-page--strong', isStrongDataset());
    }

    function withProvinceParam(params) {
        var code = gaokaoProvince || '吉林';
        return params + '&province=' + encodeURIComponent(code);
    }

    function urlWithProvince(baseUrl) {
        if (!baseUrl) return '';
        var sep = baseUrl.indexOf('?') >= 0 ? '&' : '?';
        return baseUrl + sep + 'province=' + encodeURIComponent(gaokaoProvince || '吉林');
    }

    var strongColumns = [];
    try {
        strongColumns = JSON.parse(page.getAttribute('data-strong-columns') || '[]');
    } catch (e) {
        strongColumns = [];
    }

    var EXPERT_COLUMNS = [
        { key: 'probability', label: '概率' },
        { key: 'school_name', label: '大学' },
        { key: 'major_name', label: '专业' },
        { key: 'duration', label: '学制' },
        { key: 'tuition', label: '学费' },
        { key: 'plan_count', label: '专业招收人数' },
        { key: 'school_type', label: '类型' },
        { key: 'score_chart', label: '过去3年分数' },
        { key: 'rank_chart', label: '过去3年专业位次' }
    ];

    var currentTabId = normalizeActiveBatch(page.getAttribute('data-dataset') || defaultBatch);
    page.setAttribute('data-dataset', currentTabId);
    syncStrongPageClass();
    var rankInp = document.getElementById('jilinRankInput');
    var scoreInp = document.getElementById('jilinScoreInput');
    var floatUpInp = document.getElementById('jilinFloatUpInput');
    var floatDownInp = document.getElementById('jilinFloatDownInput');
    var catSel = document.getElementById('jilinCategorySelect');
    var typeSel = document.getElementById('jilinTypeSelect');
    var tbody = document.getElementById('jilinDataTbody');
    var thead = document.getElementById('jilinDataThead');
    var strongWrap = document.getElementById('jilinStrongWrap');
    var schoolListWrap = document.getElementById('jilinSchoolListWrap');
    var schoolList = document.getElementById('jilinSchoolList');
    var meta = document.getElementById('jilinDataMeta');
    var drawerTabs = document.getElementById('jilinDrawerTabs');
    var applyDrawer = document.getElementById('jilinApplyDrawer');
    var applyDrawerBackdrop = document.getElementById('jilinApplyDrawerBackdrop');
    var applyDrawerClose = document.getElementById('jilinApplyDrawerClose');
    var applyOptionsBtn = document.getElementById('jilinApplyOptionsBtn');
    var drawerSchoolInp = document.getElementById('jilinDrawerSchoolInput');
    var drawerSearchBtn = document.getElementById('jilinDrawerSearchBtn');
    var drawerSearchTbody = document.getElementById('jilinDrawerSearchTbody');
    var drawerAddedTbody = document.getElementById('jilinDrawerAddedTbody');
    var saveDraftBtn = document.getElementById('jilinSaveDraftBtn');
    var generatePlanBtn = document.getElementById('jilinGeneratePlanBtn');
    var clearPreferBtn = document.getElementById('jilinClearPreferBtn');
    var debounce = null;
    var filtersLoaded = false;
    var profileProvinces = [];
    var profileMajorCategories = [];
    var profileMajorGroups = [];
    var addedSchools = [];
    var addedSchoolMeta = {};
    var drawerSearchResults = [];
    var searchSeq = 0;

    if (!enabled) {
        if (rankInp) rankInp.disabled = true;
        if (scoreInp) scoreInp.disabled = true;
        if (floatUpInp) floatUpInp.disabled = true;
        if (floatDownInp) floatDownInp.disabled = true;
        return;
    }

    function currentColumns() {
        return isStrongDataset() ? strongColumns : EXPERT_COLUMNS;
    }

    function colCount() {
        return currentColumns().length || 1;
    }

    function fmtCell(val) {
        return val == null || val === '' ? '—' : String(val);
    }

    function probClass(p) {
        if (p == null) return '';
        if (p >= 0.7) return 'gk-prob gk-prob--high';
        if (p >= 0.4) return 'gk-prob gk-prob--mid';
        return 'gk-prob gk-prob--low';
    }

    function formatProb(p) {
        if (p == null) return '—';
        return Math.round(p * 100) + '%';
    }

    function rebuildHeader() {
        if (!thead) return;
        var cols = currentColumns();
        var tr = document.createElement('tr');
        cols.forEach(function (col) {
            var th = document.createElement('th');
            th.textContent = col.label;
            if (col.key === 'score_chart' || col.key === 'rank_chart') {
                th.className = 'gk-data-th-chart';
            }
            tr.appendChild(th);
        });
        thead.innerHTML = '';
        thead.appendChild(tr);
    }

    function isExpertDataset() {
        var tab = getCurrentTab();
        if (tab) return tab.mode === 'expert';
        return currentTabId === 'early'
            || currentTabId === 'undergraduate'
            || currentTabId === 'junior';
    }

    function isStrongDataset() {
        var tab = getCurrentTab();
        if (tab) return tab.mode === 'strong';
        return currentTabId === 'strong';
    }

    function usesSchoolCardView() {
        return isExpertDataset() || isStrongDataset();
    }

    function toggleFilters() {
        /* 科类/类型由上一页与隐藏 select 维护，顶栏不再展示 */
    }

    function tabIsActive(btn) {
        var tabId = btn.getAttribute('data-tab-id') || btn.getAttribute('data-dataset') || '';
        return tabId === currentTabId;
    }

    function toggleResultView() {
        var cards = usesSchoolCardView();
        if (strongWrap) strongWrap.hidden = cards;
        if (schoolListWrap) schoolListWrap.hidden = !cards;
    }

    function renderSchoolEmpty(msg) {
        if (!schoolList) return;
        schoolList.innerHTML = '';
        var div = document.createElement('div');
        div.className = 'gk-school-empty';
        div.textContent = msg;
        schoolList.appendChild(div);
    }

    function renderEmpty(msg) {
        if (usesSchoolCardView()) {
            renderSchoolEmpty(msg);
            return;
        }
        if (!tbody) return;
        tbody.innerHTML = '';
        var tr = document.createElement('tr');
        tr.className = 'gk-data-empty';
        var td = document.createElement('td');
        td.colSpan = colCount();
        td.textContent = msg;
        tr.appendChild(td);
        tbody.appendChild(tr);
    }

    function getRankFloatSettings() {
        var up = floatUpInp ? parseInt(floatUpInp.value, 10) : 0;
        var down = floatDownInp ? parseInt(floatDownInp.value, 10) : 0;
        if (isNaN(up) || up < 0) up = 0;
        if (isNaN(down) || down < 0) down = 0;
        return { up: up, down: down };
    }

    function loadSystemDraft() {
        addedSchools = [];
        addedSchoolMeta = {};
        try {
            var raw = localStorage.getItem(DRAFT_KEY);
            if (!raw) return;
            var draft = JSON.parse(raw);
            addedSchools = (draft.added_schools || []).filter(Boolean);
            addedSchoolMeta = draft.added_school_meta || {};
        } catch (e) { /* ignore */ }
    }

    function saveSystemDraft(showTip) {
        localStorage.setItem(DRAFT_KEY, JSON.stringify({
            added_schools: addedSchools,
            added_school_meta: addedSchoolMeta,
            dataset: currentTabId
        }));
        if (showTip) alert('草稿已保存');
    }

    function persistProfileMetrics() {
        try {
            var raw = localStorage.getItem(PROFILE_KEY);
            var data = raw ? JSON.parse(raw) : {};
            if (scoreInp && scoreInp.value.trim()) {
                data.score_total_0 = scoreInp.value.trim();
                data.score = scoreInp.value.trim();
            }
            if (rankInp && rankInp.value.trim()) {
                data.score_rank_0 = rankInp.value.trim();
                data.province_rank = rankInp.value.trim();
            }
            var floats = getRankFloatSettings();
            data.rank_float_up = String(floats.up);
            data.rank_float_down = String(floats.down);
            localStorage.setItem(PROFILE_KEY, JSON.stringify(data));
        } catch (e) { /* ignore */ }
    }

    function schoolInSelectedRegion(meta) {
        if (!meta) return false;
        if (meta.in_selected_region === true) return true;
        var prov = meta.province || '';
        if (!prov || !profileProvinces.length) return false;
        return profileProvinces.some(function (p) {
            return String(p).replace(/(维吾尔自治区|回族自治区|壮族自治区|自治区|省|市)/g, '') === prov
                || String(p).indexOf(prov) >= 0
                || prov.indexOf(String(p).replace(/(维吾尔自治区|回族自治区|壮族自治区|自治区|省|市)/g, '')) >= 0;
        });
    }

    function isSchoolAdded(name) {
        return addedSchools.indexOf(name) >= 0;
    }

    function addSchoolToPool(meta) {
        var name = meta && meta.school_name;
        if (!name || isSchoolAdded(name)) return;
        addedSchools.push(name);
        addedSchoolMeta[name] = {
            school_name: name,
            province: meta.province || '',
            school_code: meta.school_code || '',
            in_selected_region: !!meta.in_selected_region
        };
        saveSystemDraft(false);
        renderDrawerAddedTable();
        runSearch();
    }

    function removeSchoolFromPool(name) {
        addedSchools = addedSchools.filter(function (n) { return n !== name; });
        delete addedSchoolMeta[name];
        saveSystemDraft(false);
        renderDrawerAddedTable();
        renderDrawerSearchTable();
        runSearch();
    }

    function attachLongPressDelete(btn, onDelete) {
        var PRESS_MS = 1000;
        var pressTimer = null;
        var longPressHandled = false;
        var progressBar = btn.querySelector('.gk-drawer-btn-cancel-progress');
        var label = btn.querySelector('.gk-drawer-btn-label');

        function stopProgress() {
            btn.classList.remove('gk-drawer-btn--cancel-hold');
            if (!progressBar) return;
            progressBar.style.transition = 'none';
            progressBar.style.width = '0%';
        }

        function startProgress() {
            stopProgress();
            btn.classList.add('gk-drawer-btn--cancel-hold');
            requestAnimationFrame(function () {
                progressBar.style.transition = 'width ' + PRESS_MS + 'ms linear';
                progressBar.style.width = '100%';
            });
        }

        function clearPress() {
            if (pressTimer) {
                clearTimeout(pressTimer);
                pressTimer = null;
            }
            stopProgress();
        }

        btn.addEventListener('mousedown', function (e) {
            if (e.button !== 0) return;
            longPressHandled = false;
            clearPress();
            startProgress();
            pressTimer = setTimeout(function () {
                longPressHandled = true;
                stopProgress();
                onDelete();
            }, PRESS_MS);
        });
        btn.addEventListener('mouseup', function (e) {
            if (e.button !== 0) return;
            clearPress();
            if (longPressHandled) return;
        });
        btn.addEventListener('mouseleave', clearPress);
        btn.addEventListener('touchstart', function () {
            longPressHandled = false;
            clearPress();
            startProgress();
            pressTimer = setTimeout(function () {
                longPressHandled = true;
                stopProgress();
                onDelete();
            }, PRESS_MS);
        }, { passive: true });
        btn.addEventListener('touchend', clearPress);
        btn.addEventListener('touchcancel', clearPress);
        btn.addEventListener('contextmenu', function (e) { e.preventDefault(); });
    }

    function buildDrawerRegionCell(meta) {
        var td = document.createElement('td');
        td.className = 'gk-drawer-action-col';
        if (schoolInSelectedRegion(meta)) {
            var tag = document.createElement('span');
            tag.className = 'gk-drawer-btn gk-drawer-btn--static';
            tag.textContent = '已选';
            td.appendChild(tag);
            return td;
        }
        if (isSchoolAdded(meta.school_name)) {
            var delBtn = document.createElement('button');
            delBtn.type = 'button';
            delBtn.className = 'gk-drawer-btn gk-drawer-btn--delete';
            var prog = document.createElement('span');
            prog.className = 'gk-drawer-btn-cancel-progress';
            prog.setAttribute('aria-hidden', 'true');
            var lbl = document.createElement('span');
            lbl.className = 'gk-drawer-btn-label';
            lbl.textContent = '删除大学';
            delBtn.appendChild(prog);
            delBtn.appendChild(lbl);
            attachLongPressDelete(delBtn, function () {
                removeSchoolFromPool(meta.school_name);
            });
            td.appendChild(delBtn);
        } else {
            var addBtn = document.createElement('button');
            addBtn.type = 'button';
            addBtn.className = 'gk-drawer-btn';
            addBtn.textContent = '添加学校';
            addBtn.addEventListener('click', function () {
                addSchoolToPool(meta);
                renderDrawerSearchTable();
            });
            td.appendChild(addBtn);
        }
        return td;
    }

    function buildDrawerJumpCell(meta, autoAdd) {
        var td = document.createElement('td');
        td.className = 'gk-drawer-action-col';
        var jumpBtn = document.createElement('button');
        jumpBtn.type = 'button';
        jumpBtn.className = 'gk-drawer-btn gk-drawer-btn--jump';
        jumpBtn.textContent = '跳转';
        jumpBtn.addEventListener('click', function () {
            if (autoAdd && !isSchoolAdded(meta.school_name) && !schoolInSelectedRegion(meta)) {
                addSchoolToPool(meta);
                renderDrawerSearchTable();
            }
            jumpToSchoolCard(meta.school_name);
        });
        td.appendChild(jumpBtn);
        return td;
    }

    function buildDrawerRow(meta, autoAddOnJump) {
        var tr = document.createElement('tr');
        var nameTd = document.createElement('td');
        nameTd.textContent = meta.school_name || '—';
        var provTd = document.createElement('td');
        provTd.textContent = meta.province || '—';
        var regionTd = document.createElement('td');
        var regionTag = document.createElement('span');
        regionTag.className = 'gk-drawer-region-tag' + (schoolInSelectedRegion(meta) ? ' gk-drawer-region-tag--selected' : '');
        regionTag.textContent = schoolInSelectedRegion(meta) ? '已选地域' : '地域外';
        regionTd.appendChild(regionTag);
        tr.appendChild(nameTd);
        tr.appendChild(provTd);
        tr.appendChild(regionTd);
        tr.appendChild(buildDrawerRegionCell(meta));
        tr.appendChild(buildDrawerJumpCell(meta, autoAddOnJump));
        return tr;
    }

    function renderDrawerSearchTable() {
        if (!drawerSearchTbody) return;
        drawerSearchTbody.innerHTML = '';
        if (!drawerSearchResults.length) {
            var empty = document.createElement('tr');
            empty.className = 'gk-drawer-empty';
            var td = document.createElement('td');
            td.colSpan = 5;
            td.textContent = '输入院校名称后点击搜索';
            empty.appendChild(td);
            drawerSearchTbody.appendChild(empty);
            return;
        }
        drawerSearchResults.forEach(function (meta) {
            drawerSearchTbody.appendChild(buildDrawerRow(meta, true));
        });
    }

    function renderDrawerAddedTable() {
        if (!drawerAddedTbody) return;
        drawerAddedTbody.innerHTML = '';
        if (!addedSchools.length) {
            var empty = document.createElement('tr');
            empty.className = 'gk-drawer-empty';
            var td = document.createElement('td');
            td.colSpan = 5;
            td.textContent = '暂无手动添加的院校';
            empty.appendChild(td);
            drawerAddedTbody.appendChild(empty);
            return;
        }
        addedSchools.forEach(function (name) {
            var meta = addedSchoolMeta[name] || { school_name: name, province: '', in_selected_region: false };
            meta.school_name = name;
            drawerAddedTbody.appendChild(buildDrawerRow(meta, false));
        });
    }

    function runDrawerSchoolSearch() {
        if (!schoolsUrl || !drawerSearchTbody) return;
        var q = drawerSchoolInp ? drawerSchoolInp.value.trim() : '';
        if (!q) {
            drawerSearchResults = [];
            renderDrawerSearchTable();
            return;
        }
        var params = 'limit=80&' + datasetQueryParams()
            + '&q=' + encodeURIComponent(q);
        if (profileProvinces.length && !isStrongDataset()) {
            params += '&provinces=' + encodeURIComponent(profileProvinces.join(','));
        }
        drawerSearchTbody.innerHTML = '';
        var loading = document.createElement('tr');
        loading.className = 'gk-drawer-empty';
        var td = document.createElement('td');
        td.colSpan = 5;
        td.textContent = '搜索中…';
        loading.appendChild(td);
        drawerSearchTbody.appendChild(loading);
        fetch(schoolsUrl + '?' + withProvinceParam(params))
            .then(function (r) { return r.json(); })
            .then(function (data) {
                drawerSearchResults = (data && data.ok && data.schools) ? data.schools : [];
                renderDrawerSearchTable();
            })
            .catch(function () {
                drawerSearchResults = [];
                renderDrawerSearchTable();
            });
    }

    function jumpToSchoolCard(schoolName) {
        if (!schoolName || !schoolList) return;
        closeApplyDrawer();
        var card = null;
        schoolList.querySelectorAll('.gk-school-card').forEach(function (el) {
            if (!card && el.getAttribute('data-school-name') === schoolName) {
                card = el;
            }
        });
        if (!card) {
            alert('当前列表中未找到该院校，请确认已添加或符合筛选条件');
            return;
        }
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        card.classList.add('gk-school-card--jump-highlight');
        setTimeout(function () {
            card.classList.remove('gk-school-card--jump-highlight');
        }, 1800);
    }

    function syncDrawerTabState() {
        if (!drawerTabs) return;
        drawerTabs.querySelectorAll('.gk-data-tab').forEach(function (btn) {
            btn.classList.toggle('gk-data-tab--on', tabIsActive(btn));
        });
    }

    function openApplyDrawer() {
        if (!applyDrawer) return;
        applyDrawer.hidden = false;
        document.body.classList.add('gk-drawer-open');
        syncDrawerTabState();
        renderDrawerAddedTable();
    }

    function closeApplyDrawer() {
        if (!applyDrawer) return;
        applyDrawer.hidden = true;
        document.body.classList.remove('gk-drawer-open');
    }

    function rankBandLegendHtml() {
        return (
            '<span class="gk-chart-key gk-chart-key--max">最高</span>' +
            '<span class="gk-chart-key gk-chart-key--min">最低</span>' +
            '<span class="gk-chart-key gk-chart-key--float">考生位次</span>'
        );
    }

    function buildRankBandChart(chartData, floatUp, floatDown) {
        var series = (chartData && chartData.series) || [];
        var userRank = chartData ? chartData.current : null;
        floatUp = floatUp || 0;
        floatDown = floatDown || 0;
        var W = 380;
        var H = 108;
        var padL = 38;
        var padR = 44;
        var padT = 14;
        var padB = 26;
        var innerW = W - padL - padR;
        var innerH = H - padT - padB;

        var candidateUpper = userRank != null ? Math.max(1, userRank - floatUp) : null;
        var candidateLower = userRank != null ? userRank + floatDown : null;

        var values = [];
        series.forEach(function (pt) {
            if (pt.min != null) values.push(pt.min);
            if (pt.max != null) values.push(pt.max);
        });
        if (candidateUpper != null) values.push(candidateUpper);
        if (candidateLower != null) values.push(candidateLower);
        if (userRank != null) values.push(userRank);

        if (!values.length) {
            var empty = document.createElement('div');
            empty.className = 'gk-mini-chart gk-mini-chart--empty';
            empty.textContent = '暂无数据';
            return empty;
        }

        var vMin = Math.min.apply(null, values);
        var vMax = Math.max.apply(null, values);
        if (vMin === vMax) {
            vMin -= 50;
            vMax += 50;
        }
        var padVal = (vMax - vMin) * 0.12;
        vMin -= padVal;
        vMax += padVal;

        function xAt(i) {
            if (series.length <= 1) return padL + innerW / 2;
            return padL + (innerW * i) / (series.length - 1);
        }

        function yAt(v) {
            if (v == null) return null;
            var t = (v - vMin) / (vMax - vMin);
            t = 1 - t;
            return padT + innerH * (1 - t);
        }

        function rankHighVal(pt) {
            return pt.min;
        }

        function rankLowVal(pt) {
            return pt.max;
        }

        function linePoints(getVal) {
            var pts = [];
            series.forEach(function (pt, i) {
                var v = getVal(pt);
                if (v == null) return;
                pts.push({ x: xAt(i), y: yAt(v), hasData: pt.has_data, idx: i });
            });
            return pts;
        }

        var lowPts = linePoints(rankLowVal);
        var svgNS = 'http://www.w3.org/2000/svg';
        var svg = document.createElementNS(svgNS, 'svg');
        svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
        svg.setAttribute('class', 'gk-mini-chart gk-mini-chart--rank-band');
        svg.setAttribute('role', 'img');

        function drawCandidateBand(upperVal, lowerVal) {
            if (upperVal == null || lowerVal == null) return;
            var yTop = yAt(upperVal);
            var yBottom = yAt(lowerVal);
            if (yTop == null || yBottom == null) return;
            var rect = document.createElementNS(svgNS, 'rect');
            rect.setAttribute('x', padL);
            rect.setAttribute('y', Math.min(yTop, yBottom));
            rect.setAttribute('width', innerW);
            rect.setAttribute('height', Math.abs(yBottom - yTop));
            rect.setAttribute('class', 'gk-chart-fill gk-chart-fill--float');
            svg.appendChild(rect);
        }

        function drawHorizontalLine(val, cls) {
            if (val == null) return;
            var y = yAt(val);
            if (y == null) return;
            var line = document.createElementNS(svgNS, 'line');
            line.setAttribute('x1', padL);
            line.setAttribute('x2', padL + innerW);
            line.setAttribute('y1', y);
            line.setAttribute('y2', y);
            line.setAttribute('class', 'gk-chart-line ' + cls);
            svg.appendChild(line);
        }

        function drawCurve(pts, lineCls, dotCls) {
            if (pts.length < 1) return;
            var poly = document.createElementNS(svgNS, 'polyline');
            poly.setAttribute('points', pts.map(function (p) { return p.x + ',' + p.y; }).join(' '));
            poly.setAttribute('class', lineCls);
            poly.setAttribute('fill', 'none');
            svg.appendChild(poly);
            pts.forEach(function (p) {
                var dot = document.createElementNS(svgNS, 'circle');
                dot.setAttribute('cx', p.x);
                dot.setAttribute('cy', p.y);
                dot.setAttribute('r', '3.2');
                dot.setAttribute('class', 'gk-chart-dot ' + dotCls + (p.hasData ? '' : ' gk-chart-dot--off'));
                svg.appendChild(dot);
            });
        }

        function drawHighRankLine() {
            var idx24 = -1;
            var idx25 = -1;
            series.forEach(function (pt, i) {
                if (pt.year === 24) idx24 = i;
                if (pt.year === 25) idx25 = i;
            });
            if (idx24 < 0 || idx25 < 0) return;
            var high25 = rankHighVal(series[idx25]);
            if (high25 == null) return;
            var y = yAt(high25);
            if (y == null) return;
            var x24 = xAt(idx24);
            var x25 = xAt(idx25);
            var line = document.createElementNS(svgNS, 'line');
            line.setAttribute('x1', x24);
            line.setAttribute('x2', x25);
            line.setAttribute('y1', y);
            line.setAttribute('y2', y);
            line.setAttribute('class', 'gk-chart-line gk-chart-line--max');
            svg.appendChild(line);
            var dot = document.createElementNS(svgNS, 'circle');
            dot.setAttribute('cx', x25);
            dot.setAttribute('cy', y);
            dot.setAttribute('r', '3.2');
            dot.setAttribute('class', 'gk-chart-dot gk-chart-dot--max');
            svg.appendChild(dot);
        }

        drawCandidateBand(candidateUpper, candidateLower);
        drawCurve(lowPts, 'gk-chart-line gk-chart-line--min', 'gk-chart-dot--min');
        drawHighRankLine();
        drawHorizontalLine(candidateUpper, 'gk-chart-line gk-chart-line--float-up');
        drawHorizontalLine(candidateLower, 'gk-chart-line gk-chart-line--float-down');
        drawHorizontalLine(userRank, 'gk-chart-line gk-chart-line--user-rank');

        function drawSideLabel(text, side, yVal, cls) {
            if (yVal == null) return;
            var y = yAt(yVal);
            if (y == null) return;
            var tx = document.createElementNS(svgNS, 'text');
            tx.setAttribute('y', y);
            tx.setAttribute('dominant-baseline', 'middle');
            tx.setAttribute('class', 'gk-chart-side-label ' + (cls || ''));
            if (side === 'left') {
                tx.setAttribute('x', 4);
                tx.setAttribute('text-anchor', 'start');
            } else {
                tx.setAttribute('x', W - 4);
                tx.setAttribute('text-anchor', 'end');
            }
            tx.textContent = text;
            svg.appendChild(tx);
        }

        if (userRank != null) {
            drawSideLabel(String(userRank), 'left', userRank, 'gk-chart-side-label--current');
        }
        var pt25 = null;
        series.forEach(function (pt) {
            if (pt.year === 25) pt25 = pt;
        });
        if (pt25) {
            var low25 = rankLowVal(pt25);
            if (low25 != null) {
                drawSideLabel(String(low25), 'right', low25, 'gk-chart-side-label--low25');
            }
        }

        function fmtRankVal(v) {
            return v == null ? '—' : String(v);
        }

        function fmtYearRankInfoTitle(year) {
            if (year == null || year === '') return '—年位次信息';
            return String(year) + '年位次信息';
        }

        function fmtRankDiff(fromVal, current) {
            if (fromVal == null || current == null) return null;
            return fromVal - current;
        }

        function fmtRankDiffHtml(fromVal, current) {
            var diff = fmtRankDiff(fromVal, current);
            if (diff == null) return '—';
            var cls = 'gk-chart-diff--zero';
            if (diff > 0) cls = 'gk-chart-diff--pos';
            else if (diff < 0) cls = 'gk-chart-diff--neg';
            return '<span class="gk-chart-diff ' + cls + '">' + diff + '</span>';
        }

        function yearMaxRank(pt) {
            return rankHighVal(pt);
        }

        function yearMinRank(pt) {
            return rankLowVal(pt);
        }

        series.forEach(function (pt, i) {
            var hit = document.createElementNS(svgNS, 'g');
            hit.setAttribute('class', 'gk-chart-year-hit');
            var zone = document.createElementNS(svgNS, 'rect');
            var cx = xAt(i);
            zone.setAttribute('x', cx - 22);
            zone.setAttribute('y', padT);
            zone.setAttribute('width', 44);
            zone.setAttribute('height', H - padT);
            zone.setAttribute('fill', 'transparent');
            hit.appendChild(zone);

            var tx = document.createElementNS(svgNS, 'text');
            tx.setAttribute('x', cx);
            tx.setAttribute('y', H - 6);
            tx.setAttribute('text-anchor', 'middle');
            tx.setAttribute('class', 'gk-chart-year' + (pt.has_data ? '' : ' gk-chart-year--dim'));
            tx.textContent = String(pt.year);
            hit.appendChild(tx);
            svg.appendChild(hit);
        });

        var tooltip = document.createElement('div');
        tooltip.className = 'gk-chart-year-tooltip';
        tooltip.hidden = true;
        var wrap = document.createElement('div');
        wrap.className = 'gk-chart-cell gk-chart-cell--rank-band';
        wrap.appendChild(svg);
        wrap.appendChild(tooltip);

        wrap.querySelectorAll('.gk-chart-year-hit').forEach(function (hitEl, i) {
            hitEl.addEventListener('mouseenter', function () {
                var pt = series[i];
                if (!pt) return;
                var maxV = yearMaxRank(pt);
                var minV = yearMinRank(pt);
                tooltip.innerHTML =
                    '<div class="gk-chart-year-tooltip-title">' + fmtYearRankInfoTitle(pt.year) + '</div>' +
                    '最高位次：' + fmtRankVal(maxV) + '；相差：' + fmtRankDiffHtml(maxV, userRank) + '<br>' +
                    '最低位次：' + fmtRankVal(minV) + '；相差：' + fmtRankDiffHtml(minV, userRank) + '<br>' +
                    '目前位次：' + fmtRankVal(userRank);
                var hitRect = hitEl.getBoundingClientRect();
                var wrapRect = wrap.getBoundingClientRect();
                var side = pt.year === 25 ? 'right' : 'left';
                tooltip.classList.remove('gk-chart-year-tooltip--left', 'gk-chart-year-tooltip--right');
                tooltip.classList.add('gk-chart-year-tooltip--' + side);
                var anchorX = side === 'right'
                    ? (hitRect.right - wrapRect.left)
                    : (hitRect.left - wrapRect.left);
                tooltip.style.left = anchorX + 'px';
                tooltip.style.top = (hitRect.top - wrapRect.top + hitRect.height / 2) + 'px';
                tooltip.hidden = false;
            });
            hitEl.addEventListener('mouseleave', function () {
                tooltip.hidden = true;
            });
        });

        return wrap;
    }

    function buildTrendChart(kind, chartData) {
        var series = (chartData && chartData.series) || [];
        var currentVal = chartData ? chartData.current : null;
        var W = 240;
        var H = 108;
        var padL = 10;
        var padR = 10;
        var padT = 14;
        var padB = 26;
        var innerW = W - padL - padR;
        var innerH = H - padT - padB;
        var invert = kind === 'rank';

        var values = [];
        series.forEach(function (pt) {
            if (pt.min != null) values.push(pt.min);
            if (pt.max != null) values.push(pt.max);
        });
        if (currentVal != null) values.push(currentVal);

        if (!values.length) {
            var empty = document.createElement('div');
            empty.className = 'gk-mini-chart gk-mini-chart--empty';
            empty.textContent = '暂无数据';
            return empty;
        }

        var vMin = Math.min.apply(null, values);
        var vMax = Math.max.apply(null, values);
        if (vMin === vMax) {
            vMin -= kind === 'rank' ? 50 : 5;
            vMax += kind === 'rank' ? 50 : 5;
        }
        var padVal = (vMax - vMin) * 0.12;
        vMin -= padVal;
        vMax += padVal;

        function xAt(i) {
            return padL + (innerW * i) / (series.length - 1);
        }

        function yAt(v) {
            if (v == null) return null;
            var t = (v - vMin) / (vMax - vMin);
            if (invert) t = 1 - t;
            return padT + innerH * (1 - t);
        }

        function linePoints(key) {
            var pts = [];
            series.forEach(function (pt, i) {
                var v = pt[key];
                if (v == null) return;
                pts.push({ x: xAt(i), y: yAt(v), hasData: pt.has_data });
            });
            return pts;
        }

        var minPts = linePoints('min');
        var maxPts = linePoints('max');
        var svgNS = 'http://www.w3.org/2000/svg';
        var svg = document.createElementNS(svgNS, 'svg');
        svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
        svg.setAttribute('class', 'gk-mini-chart');
        svg.setAttribute('role', 'img');

        function addPath(d, cls) {
            if (!d) return;
            var path = document.createElementNS(svgNS, 'path');
            path.setAttribute('d', d);
            path.setAttribute('class', cls);
            svg.appendChild(path);
        }

        function bandPath(maxLine, minLine) {
            if (!maxLine.length || !minLine.length) return '';
            var d = 'M' + maxLine[0].x + ',' + maxLine[0].y + ' ';
            maxLine.forEach(function (p) { d += 'L' + p.x + ',' + p.y + ' '; });
            for (var i = minLine.length - 1; i >= 0; i--) {
                d += 'L' + minLine[i].x + ',' + minLine[i].y + ' ';
            }
            d += 'Z';
            return d;
        }

        addPath(bandPath(maxPts, minPts), 'gk-chart-fill gk-chart-fill--band');

        function currentZoneClass(pt) {
            if (currentVal == null || !pt) return 'gk-chart-line--current-mid';
            var minV = pt.min;
            var maxV = pt.max;
            if (kind === 'score') {
                if (maxV != null && currentVal > maxV) return 'gk-chart-line--current-high';
                if (minV != null && currentVal < minV) return 'gk-chart-line--current-low';
                return 'gk-chart-line--current-mid';
            }
            if (minV != null && currentVal < minV) return 'gk-chart-line--current-high';
            if (maxV != null && currentVal > maxV) return 'gk-chart-line--current-low';
            return 'gk-chart-line--current-mid';
        }

        function segmentZoneClass(i) {
            var pt = series[i];
            var pt2 = series[i + 1] || pt;
            var ref = {
                min: pt.min != null ? pt.min : pt2.min,
                max: pt.max != null ? pt.max : pt2.max
            };
            return currentZoneClass(ref);
        }

        function drawLine(pts, lineCls, dotCls) {
            if (pts.length < 1) return;
            var poly = document.createElementNS(svgNS, 'polyline');
            poly.setAttribute('points', pts.map(function (p) { return p.x + ',' + p.y; }).join(' '));
            poly.setAttribute('class', lineCls);
            poly.setAttribute('fill', 'none');
            svg.appendChild(poly);
            pts.forEach(function (p) {
                var dot = document.createElementNS(svgNS, 'circle');
                dot.setAttribute('cx', p.x);
                dot.setAttribute('cy', p.y);
                dot.setAttribute('r', '3.2');
                dot.setAttribute('class', 'gk-chart-dot ' + dotCls + (p.hasData ? '' : ' gk-chart-dot--off'));
                svg.appendChild(dot);
            });
        }

        drawLine(minPts, 'gk-chart-line gk-chart-line--min', 'gk-chart-dot--min');
        drawLine(maxPts, 'gk-chart-line gk-chart-line--max', 'gk-chart-dot--max');

        if (currentVal != null) {
            var y = yAt(currentVal);
            for (var si = 0; si < series.length - 1; si++) {
                var seg = document.createElementNS(svgNS, 'line');
                seg.setAttribute('x1', xAt(si));
                seg.setAttribute('x2', xAt(si + 1));
                seg.setAttribute('y1', y);
                seg.setAttribute('y2', y);
                seg.setAttribute('class', 'gk-chart-line ' + segmentZoneClass(si));
                svg.appendChild(seg);
            }
        }

        series.forEach(function (pt, i) {
            var tx = document.createElementNS(svgNS, 'text');
            tx.setAttribute('x', xAt(i));
            tx.setAttribute('y', H - 6);
            tx.setAttribute('text-anchor', 'middle');
            tx.setAttribute('class', 'gk-chart-year' + (pt.has_data ? '' : ' gk-chart-year--dim'));
            tx.textContent = String(pt.year);
            svg.appendChild(tx);
        });

        var legend = document.createElement('div');
        legend.className = 'gk-chart-legend';
        legend.innerHTML =
            '<span class="gk-chart-key gk-chart-key--min">最低</span>' +
            '<span class="gk-chart-key gk-chart-key--max">最高</span>' +
            '<span class="gk-chart-key gk-chart-key--current">目前</span>';
        var wrap = document.createElement('div');
        wrap.className = 'gk-chart-cell';
        wrap.appendChild(svg);
        wrap.appendChild(legend);
        return wrap;
    }

    function renderExpertRow(rec) {
        var tr = document.createElement('tr');

        function addText(cls, text) {
            var td = document.createElement('td');
            if (cls) td.className = cls;
            td.textContent = text;
            tr.appendChild(td);
        }

        var tdProb = document.createElement('td');
        var probSpan = document.createElement('span');
        probSpan.className = probClass(rec.probability);
        probSpan.textContent = formatProb(rec.probability);
        tdProb.appendChild(probSpan);
        tr.appendChild(tdProb);

        addText('gk-data-td-school', fmtCell(rec.school_name));
        addText('gk-data-td-major', fmtCell(rec.major_name));
        addText('gk-data-td-num', fmtCell(rec.duration));
        addText('gk-data-td-num', fmtCell(rec.tuition));
        addText('gk-data-td-num', fmtCell(rec.plan_count));
        addText('gk-data-td-type', fmtCell(rec.school_type));

        var tdScore = document.createElement('td');
        tdScore.className = 'gk-data-td-chart';
        tdScore.appendChild(buildTrendChart('score', rec.score_chart));
        tr.appendChild(tdScore);

        var tdRank = document.createElement('td');
        tdRank.className = 'gk-data-td-chart';
        tdRank.appendChild(buildTrendChart('rank', rec.rank_chart));
        tr.appendChild(tdRank);

        return tr;
    }

    function renderStrongRow(rec) {
        var tr = document.createElement('tr');
        strongColumns.forEach(function (col) {
            var td = document.createElement('td');
            var val = rec[col.key];
            if (col.key === 'school_name') td.className = 'gk-data-td-school';
            if (col.key === 'major_name') td.className = 'gk-data-td-major';
            if (col.key === 'qualify_score' || col.key === 'admit_score') td.className = 'gk-data-td-num';
            td.textContent = val == null || val === '' ? '—' : String(val);
            tr.appendChild(td);
        });
        return tr;
    }

    function strongStatusClass(tierClass) {
        if (tierClass === 'safe') return 'gk-strong-status gk-strong-status--safe';
        if (tierClass === 'steady') return 'gk-strong-status gk-strong-status--steady';
        if (tierClass === 'reach') return 'gk-strong-status gk-strong-status--reach';
        return 'gk-strong-status gk-strong-status--none';
    }

    function getStrongCardMajors(card) {
        if (!isStrongCard(card) || !Array.isArray(card.majors)) return [];
        return card.majors;
    }

    function renderStrongDetailPanel(panel, card) {
        panel.innerHTML = '';
        panel.hidden = false;
        panel.dataset.mode = 'strong';

        var head = document.createElement('div');
        head.className = 'gk-group-detail-head';
        var title = document.createElement('div');
        title.className = 'gk-group-detail-title';
        title.textContent = (card.school_name || '院校') + ' · 强基专业';
        var headActions = document.createElement('div');
        headActions.className = 'gk-group-detail-head-actions';
        var closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'gk-group-detail-close';
        closeBtn.textContent = '收起';
        headActions.appendChild(closeBtn);
        head.appendChild(title);
        head.appendChild(headActions);
        panel.appendChild(head);

        var tableHost = document.createElement('div');
        tableHost.className = 'gk-apply-table-host';
        var majors = getStrongCardMajors(card);
        if (!majors.length) {
            var empty = document.createElement('div');
            empty.className = 'gk-school-majors-empty';
            empty.textContent = '暂无强基专业明细，请刷新页面后重试';
            tableHost.appendChild(empty);
            panel.appendChild(tableHost);
            closeBtn.addEventListener('click', function () {
                closeDetailPanel(panel.closest('.gk-school-card'));
            });
            return;
        }

        var tableWrap = document.createElement('div');
        tableWrap.className = 'gk-group-detail-table-wrap';
        var table = document.createElement('table');
        table.className = 'gk-group-detail-table gk-strong-detail-table';
        var thead = document.createElement('thead');
        var hr = document.createElement('tr');
        ['专业名称', '入围分', '录取分', '对比', '操作'].forEach(function (label) {
            var th = document.createElement('th');
            th.textContent = label;
            hr.appendChild(th);
        });
        thead.appendChild(hr);
        table.appendChild(thead);

        var article = panel.closest('.gk-school-card');
        var tbody = document.createElement('tbody');
        majors.forEach(function (m) {
            var tier = m.score_status_class || 'none';
            var tr = document.createElement('tr');
            tr.setAttribute('data-prefer-key', strongPreferKey(m));
            tr.setAttribute('data-tier-class', tier);
            tr.setAttribute('data-qualify-score', m.qualify_score != null ? String(m.qualify_score) : '');
            tr.setAttribute('data-admit-score', m.admit_score != null ? String(m.admit_score) : '');
            tr.setAttribute('data-score-status', m.score_status_label || '');
            tr.appendChild(detailCell(m.major_name, 'gk-strong-col-major'));
            tr.appendChild(detailCell(m.qualify_score, 'gk-data-td-num'));
            tr.appendChild(detailCell(m.admit_score, 'gk-data-td-num'));
            var statusTd = document.createElement('td');
            if (m.score_status_label) {
                var badge = document.createElement('span');
                badge.className = strongStatusClass(m.score_status_class);
                badge.textContent = m.score_status_label;
                if (m.score_diff != null) {
                    badge.title = '与参考分相差 ' + m.score_diff + ' 分';
                }
                statusTd.appendChild(badge);
            } else {
                statusTd.textContent = '—';
            }
            tr.appendChild(statusTd);
            tr.appendChild(detailActionCell());
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        tableWrap.appendChild(table);
        tableHost.appendChild(tableWrap);
        panel.appendChild(tableHost);

        requestAnimationFrame(function () {
            restorePreferRows(article);
        });

        closeBtn.addEventListener('click', function () {
            closeDetailPanel(panel.closest('.gk-school-card'));
        });
    }

    function openStrongPanel(article, card, applyBtn) {
        var panel = article.querySelector('.gk-group-detail-panel');
        if (!panel) return;
        card = card || article._gkCardData;
        if (!isStrongCard(card)) return;
        closeDetailPanel(article);
        if (applyBtn) syncApplyBtnState(applyBtn, true);
        article._gkCardData = card;
        renderStrongDetailPanel(panel, card);
        syncPreferGroupPanel(article);
    }

    function renderStrongSchoolCards(records) {
        if (!schoolList) return;
        schoolList.innerHTML = '';
        records = (records || []).filter(isStrongCard);
        if (!records.length) {
            renderSchoolEmpty('暂无强基计划院校数据');
            return;
        }
        records.forEach(function (card) {
            var article = document.createElement('article');
            article.className = 'gk-school-card gk-school-card--strong';
            article.setAttribute('data-school-name', card.school_name || '');
            article.setAttribute('data-school-code', card.school_code || '');
            article._gkCardData = card;

            var row = document.createElement('div');
            row.className = 'gk-school-card-row';

            var applyBtn = document.createElement('button');
            applyBtn.type = 'button';
            applyBtn.className = 'gk-school-apply-btn';
            syncApplyBtnState(applyBtn, false);
            applyBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                toggleApplyPanel(article, card, applyBtn);
            });

            var probBox = document.createElement('div');
            probBox.className = tierClassName(card.tier_class);
            var probPct = document.createElement('div');
            probPct.className = 'gk-school-tier-pct';
            var strongMajors = getStrongCardMajors(card);
            if (card.tier_class && card.tier_class !== 'none') {
                probPct.textContent = card.tier_label || '—';
            } else {
                probPct.textContent = strongMajors.length ? String(strongMajors.length) : '—';
            }
            var probLabel = document.createElement('div');
            probLabel.className = 'gk-school-tier-label';
            probLabel.textContent = card.tier_class && card.tier_class !== 'none'
                ? '对比'
                : '专业';
            probBox.appendChild(probPct);
            probBox.appendChild(probLabel);

            var main = document.createElement('div');
            main.className = 'gk-school-main';
            var mainHead = document.createElement('div');
            mainHead.className = 'gk-school-main-head';
            var title = document.createElement('h3');
            title.className = 'gk-school-name';
            title.textContent = card.school_name || '';
            mainHead.appendChild(title);
            mainHead.appendChild(applyBtn);
            var loc = document.createElement('div');
            loc.className = 'gk-school-loc';
            loc.textContent = card.location_line || '';
            var tags = document.createElement('div');
            tags.className = 'gk-school-tags';
            (card.tags || []).forEach(function (tag) {
                var span = document.createElement('span');
                span.className = 'gk-school-tag';
                span.textContent = tag;
                tags.appendChild(span);
            });
            var stats = document.createElement('div');
            stats.className = 'gk-school-stats';
            var statsParts = [
                '<span>强基专业 ' + (strongMajors.length || '—') + ' 个</span>'
            ];
            if (card.qualify_range) {
                statsParts.push('<span>入围参考 ' + card.qualify_range + '</span>');
            }
            stats.innerHTML = statsParts.join('');
            main.appendChild(mainHead);
            main.appendChild(loc);
            main.appendChild(tags);
            main.appendChild(stats);
            main.addEventListener('click', function (e) {
                if (e.target.closest('.gk-school-apply-btn')) return;
                toggleApplyPanel(article, card, applyBtn);
            });

            row.appendChild(probBox);
            row.appendChild(main);

            var preferPanel = document.createElement('div');
            preferPanel.className = 'gk-school-prefer-panel';
            preferPanel.hidden = true;
            preferPanel.addEventListener('click', function (e) {
                e.stopPropagation();
            });
            var preferList = document.createElement('div');
            preferList.className = 'gk-prefer-group-list';
            preferPanel.appendChild(preferList);
            row.appendChild(preferPanel);

            article.appendChild(row);

            var detailPanel = document.createElement('div');
            detailPanel.className = 'gk-group-detail-panel';
            detailPanel.hidden = true;
            article.appendChild(detailPanel);

            schoolList.appendChild(article);
            syncPreferGroupPanel(article);
            syncSchoolCardPreferGradient(article);
        });
    }

    function renderRows(records) {
        if (isExpertDataset()) {
            renderSchoolCards(records);
            return;
        }
        if (isStrongDataset()) {
            renderStrongSchoolCards(records);
            return;
        }
        if (!tbody) return;
        tbody.innerHTML = '';
        if (!records || !records.length) {
            renderEmpty('未找到匹配记录');
            return;
        }
        records.forEach(function (rec) {
            tbody.appendChild(renderStrongRow(rec));
        });
    }

    function tierClassName(tierClass) {
        if (tierClass === 'safe') return 'gk-school-tier gk-school-tier--safe';
        if (tierClass === 'steady') return 'gk-school-tier gk-school-tier--steady';
        if (tierClass === 'reach') return 'gk-school-tier gk-school-tier--reach';
        return 'gk-school-tier gk-school-tier--none';
    }

    function probTierFromValue(p) {
        if (p == null) return { label: '', class: 'none' };
        if (p >= 0.8) return { label: '保', class: 'safe' };
        if (p >= 0.5) return { label: '稳', class: 'steady' };
        return { label: '冲', class: 'reach' };
    }

    function majorProbClass(tierClass) {
        if (tierClass === 'safe') return 'gk-school-major-prob gk-school-major-prob--safe';
        if (tierClass === 'steady') return 'gk-school-major-prob gk-school-major-prob--steady';
        if (tierClass === 'reach') return 'gk-school-major-prob gk-school-major-prob--reach';
        return 'gk-school-major-prob gk-school-major-prob--none';
    }

    function groupBtnClass(tierClass) {
        return 'gk-major-group-btn gk-major-group-btn--' + (tierClass || 'none');
    }

    function detailRankChartCell(detail) {
        var floats = getRankFloatSettings();
        var chartData = detail.rank_chart || { series: [], current: null };
        if (rankInp && rankInp.value.trim()) {
            var rankVal = parseInt(rankInp.value.trim(), 10);
            if (!isNaN(rankVal)) {
                chartData = {
                    series: chartData.series || [],
                    current: rankVal
                };
            }
        }
        var td = document.createElement('td');
        td.className = 'gk-group-detail-chart gk-group-detail-chart--rank';
        td.appendChild(buildRankBandChart(chartData, floats.up, floats.down));
        return td;
    }

    function detailCell(text, className) {
        var val = text == null || text === '' ? '—' : String(text);
        var td = document.createElement('td');
        if (className) td.className = className;
        td.textContent = val;
        return td;
    }

    function detailProbCell(planCount, probability, tier) {
        var td = document.createElement('td');
        td.className = 'gk-group-detail-col-prob';
        var stack = document.createElement('div');
        stack.className = 'gk-prob-stack';
        var planBox = document.createElement('div');
        planBox.className = 'gk-prob-stack-plan';
        var pcRaw = planCount == null || planCount === '' ? '' : String(planCount).replace(/人$/, '').trim();
        planBox.textContent = pcRaw ? (pcRaw + '人') : '-人';
        var probBox = document.createElement('div');
        probBox.className = 'gk-prob-stack-pct gk-prob-stack-pct--' + (tier || 'none');
        probBox.textContent = probability == null ? '—' : (Math.round(probability * 100) + '%');
        stack.appendChild(planBox);
        stack.appendChild(probBox);
        td.appendChild(stack);
        return td;
    }

    var PREFER_ROW_CLASSES = [
        'gk-group-detail-row--prefer-safe',
        'gk-group-detail-row--prefer-steady',
        'gk-group-detail-row--prefer-reach',
        'gk-group-detail-row--prefer-none'
    ];

    var PREFER_TIER_END = {
        safe: '#ecfdf5',
        steady: '#fefce8',
        reach: '#fff1f2',
        none: '#f8fafc'
    };

    function parsePreferKey(key) {
        if (!key) return { groupCode: '', majorCode: '', majorName: '', majorNote: '' };
        if (key.indexOf('强基||') === 0) {
            var rest = key.slice(4);
            var sp = rest.split('||');
            if (sp.length <= 1) {
                return { groupCode: '强基', majorCode: '', majorName: sp[0] || '', majorNote: '' };
            }
            return {
                groupCode: '强基',
                majorCode: sp[0] || '',
                majorName: sp[1] || '',
                majorNote: sp.slice(2).join('||')
            };
        }
        var parts = key.split('||');
        if (parts.length <= 2) {
            return { groupCode: parts[0] || '', majorCode: '', majorName: parts[1] || '', majorNote: '' };
        }
        return {
            groupCode: parts[0] || '',
            majorCode: parts[1] || '',
            majorName: parts[2] || '',
            majorNote: parts.slice(3).join('||')
        };
    }

    function preferRowKey(groupCode, majorName, majorCode, majorNote) {
        var note = majorNote != null ? String(majorNote) : '';
        return [
            groupCode || '',
            majorCode || '',
            majorName || '',
            note
        ].join('||');
    }

    function strongPreferKey(majorOrName) {
        if (majorOrName && typeof majorOrName === 'object') {
            return preferRowKey(
                '强基',
                majorOrName.major_name || '',
                majorOrName.major_code || '',
                majorOrName.major_note
            );
        }
        return preferRowKey('强基', majorOrName || '', '', '');
    }

    function majorNameFromPreferKey(key) {
        return parsePreferKey(key).majorName;
    }

    function isStrongCard(card) {
        return !!(card && card.card_type === 'strong_base');
    }

    function groupCodeFromPreferKey(key) {
        return parsePreferKey(key).groupCode;
    }

    function circledNumber(n) {
        n = parseInt(n, 10);
        if (!n || n < 1) return '';
        if (n <= 20) return String.fromCharCode(0x2460 + n - 1);
        return '(' + n + ')';
    }

    function groupHasProfileMatch(card, groupCode) {
        if (!card || !groupCode) return false;
        return (card.major_groups || []).some(function (g) {
            return (g.group_code || '') === groupCode;
        });
    }

    function countPrefersInGroup(article, groupCode) {
        var store = getPreferStore(article);
        if (!store || !groupCode) return 0;
        var count = 0;
        Object.keys(store).forEach(function (key) {
            if (store[key] && store[key].selected && groupCodeFromPreferKey(key) === groupCode) {
                count += 1;
            }
        });
        return count;
    }

    function getPreferItemsSummary(article) {
        var store = getPreferStore(article);
        if (!store) return [];
        var card = article && article._gkCardData;
        if (isStrongCard(card)) {
            var items = [];
            Object.keys(store).forEach(function (key) {
                if (!store[key] || !store[key].selected) return;
                var name = majorNameFromPreferKey(key);
                if (!name) return;
                items.push({
                    group_code: name,
                    label: name,
                    count: 1,
                    tier_class: store[key].tierClass || 'none'
                });
            });
            return items.sort(function (a, b) {
                return String(a.label).localeCompare(String(b.label));
            });
        }
        return getPreferGroupsSummary(article).map(function (item) {
            item.label = item.group_code;
            return item;
        });
    }

    function tierClassForPreferItem(card, item) {
        if (isStrongCard(card)) {
            var majors = card.majors || [];
            for (var i = 0; i < majors.length; i++) {
                if ((majors[i].major_name || '') === (item.group_code || '')) {
                    return majors[i].score_status_class || item.tier_class || 'none';
                }
            }
        }
        return groupTierFromCard(card, item.group_code);
    }

    function groupTierFromCard(card, groupCode) {
        if (!card || !groupCode) return 'none';
        var groups = getCardMajorGroupList(card);
        for (var i = 0; i < groups.length; i++) {
            if ((groups[i].group_code || '') === groupCode) {
                return groups[i].tier_class || 'none';
            }
        }
        return 'none';
    }

    function getPreferGroupsSummary(article) {
        var store = getPreferStore(article);
        if (!store) return [];
        var map = {};
        Object.keys(store).forEach(function (key) {
            if (!store[key] || !store[key].selected) return;
            var gc = groupCodeFromPreferKey(key);
            if (!gc || gc === '强基') return;
            if (!map[gc]) map[gc] = { group_code: gc, count: 0 };
            map[gc].count += 1;
        });
        return Object.keys(map).map(function (k) { return map[k]; }).sort(function (a, b) {
            return String(a.group_code).localeCompare(String(b.group_code));
        });
    }

    function updatePreferGroupCardButton(btn, groupCode, count, tierClass, article, label) {
        btn.type = 'button';
        btn.className = groupBtnClass(tierClass) + ' gk-major-group-btn--has-prefer gk-prefer-group-btn';
        btn.setAttribute('data-group-code', groupCode || '');
        btn.textContent = '';
        var inner = document.createElement('span');
        inner.className = 'gk-major-group-btn-inner';
        var codeEl = document.createElement('span');
        codeEl.className = 'gk-major-group-btn-code';
        codeEl.textContent = label || groupCode || '—';
        codeEl.title = label || groupCode || '';
        inner.appendChild(codeEl);
        if (count > 0) {
            var sufEl = document.createElement('span');
            sufEl.className = 'gk-major-group-btn-suffix';
            sufEl.textContent = circledNumber(count);
            inner.appendChild(sufEl);
        }
        btn.appendChild(inner);
        var panel = article && article.querySelector('.gk-group-detail-panel');
        var card = article && article._gkCardData;
        var active = false;
        if (panel && !panel.hidden && card) {
            if (isStrongCard(card) && panel.dataset.mode === 'strong') {
                active = true;
            } else if (panel.dataset.mode === 'apply' && (panel.dataset.activeGroup || '') === (groupCode || '')) {
                active = true;
            }
        }
        btn.classList.toggle('gk-major-group-btn--active', active);
    }

    function syncPreferGroupPanel(article) {
        if (!article) return;
        var panel = article.querySelector('.gk-school-prefer-panel');
        var list = article.querySelector('.gk-prefer-group-list');
        if (!panel || !list) return;
        var card = article._gkCardData;
        var summaries = getPreferItemsSummary(article);
        list.innerHTML = '';
        if (!summaries.length) {
            panel.hidden = true;
            return;
        }
        panel.hidden = false;
        summaries.forEach(function (item) {
            var btn = document.createElement('button');
            var tierClass = tierClassForPreferItem(card, item);
            updatePreferGroupCardButton(btn, item.group_code, item.count, tierClass, article, item.label);
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                if (!card) return;
                var applyBtn = article.querySelector('.gk-school-apply-btn');
                if (isStrongCard(card)) {
                    openStrongPanel(article, card, applyBtn);
                } else {
                    openApplyPanel(article, card, item.group_code || '');
                }
            });
            list.appendChild(btn);
        });
    }

    function buildGroupTabSuffix(groupCode, article) {
        var suffix = '';
        var card = article && article._gkCardData;
        if (groupHasProfileMatch(card, groupCode)) {
            suffix += '含';
        }
        var preferCount = countPrefersInGroup(article, groupCode);
        if (preferCount > 0) {
            suffix += circledNumber(preferCount);
        }
        return suffix;
    }

    function updateGroupTabButton(btn, groupCode, article) {
        if (!btn) return;
        var code = groupCode || '—';
        var suffix = buildGroupTabSuffix(groupCode, article);
        btn.textContent = '';
        var inner = document.createElement('span');
        inner.className = 'gk-major-group-btn-inner';
        var codeEl = document.createElement('span');
        codeEl.className = 'gk-major-group-btn-code';
        codeEl.textContent = code;
        inner.appendChild(codeEl);
        if (suffix) {
            var sufEl = document.createElement('span');
            sufEl.className = 'gk-major-group-btn-suffix';
            sufEl.textContent = suffix;
            inner.appendChild(sufEl);
        }
        btn.appendChild(inner);
        btn.classList.toggle('gk-major-group-btn--has-prefer', countPrefersInGroup(article, groupCode) > 0);
    }

    function syncGroupTabLabels(article) {
        if (!article) return;
        article.querySelectorAll('.gk-apply-group-tabs .gk-major-group-btn').forEach(function (btn) {
            var code = btn.getAttribute('data-group-code') || '';
            updateGroupTabButton(btn, code, article);
        });
    }

    var preferStoreBySchool = {};

    function loadPreferStoreFromStorage() {
        try {
            var raw = localStorage.getItem(PREFER_STORE_KEY);
            if (!raw) return;
            var parsed = JSON.parse(raw);
            if (parsed && typeof parsed === 'object') {
                preferStoreBySchool = parsed;
            }
        } catch (e) { /* ignore */ }
        Object.keys(preferStoreBySchool).forEach(function (key) {
            if (key.indexOf('expert:') !== 0) return;
            var migrated = 'undergraduate' + key.slice(6);
            if (!preferStoreBySchool[migrated]) {
                preferStoreBySchool[migrated] = preferStoreBySchool[key];
            }
            delete preferStoreBySchool[key];
        });
        Object.keys(preferStoreBySchool).forEach(function (key) {
            if (key.indexOf('::') >= 0) return;
            var idx = key.indexOf(':');
            if (idx <= 0) return;
            var migrated = key.slice(0, idx) + '::' + key.slice(idx + 1);
            if (!preferStoreBySchool[migrated]) {
                preferStoreBySchool[migrated] = preferStoreBySchool[key];
            }
            delete preferStoreBySchool[key];
        });
    }

    function persistPreferStore() {
        try {
            localStorage.setItem(PREFER_STORE_KEY, JSON.stringify(preferStoreBySchool));
        } catch (e) { /* ignore */ }
    }

    function preferStoreKey(article) {
        if (!article) return '';
        var name = article.getAttribute('data-school-name') || '';
        if (!name) return '';
        return currentTabId + '::' + name;
    }

    function getPreferStore(article) {
        if (!article) return null;
        if (!article._preferStore) {
            var key = preferStoreKey(article);
            article._preferStore = (key && preferStoreBySchool[key]) ? preferStoreBySchool[key] : {};
            if (key) preferStoreBySchool[key] = article._preferStore;
        }
        return article._preferStore;
    }

    function capturePreferSnapshot(tr, article, meta) {
        var schoolName = article.getAttribute('data-school-name') || '';
        var groupCode = groupCodeFromPreferKey(meta.key);
        var majorName = majorNameFromPreferKey(meta.key);
        var card = article._gkCardData;
        var snap = {
            selected: true,
            tierClass: meta.tierClass,
            probability: meta.probability,
            schoolName: schoolName,
            school_code: (card && card.school_code) || article.getAttribute('data-school-code') || '',
            groupCode: groupCode,
            majorName: majorName,
            dataset: currentTabId,
            batch: apiBatchParam(),
            bucket: apiDatasetParam(),
            preferKey: meta.key
        };
        if (tr) {
            snap.major_code = tr.getAttribute('data-major-code') || '';
            snap.groupCode = tr.getAttribute('data-group-code') || groupCode;
            snap.duration = tr.getAttribute('data-duration') || '';
            snap.tuition = tr.getAttribute('data-tuition') || '';
            snap.major_note = tr.getAttribute('data-major-note') || '';
            if (!snap.major_note) {
                var noteEl = tr.querySelector('.gk-group-detail-note-text');
                var noteText = noteEl ? String(noteEl.textContent || '').trim() : '';
                snap.major_note = noteText === '—' ? '' : noteText;
            }
            snap.rank_2025 = tr.getAttribute('data-rank-2025') || '';
            snap.rank_max_2025 = tr.getAttribute('data-rank-max-2025') || '';
            if (tr.getAttribute('data-qualify-score')) {
                snap.qualify_score = tr.getAttribute('data-qualify-score');
            }
            if (tr.getAttribute('data-admit-score')) {
                snap.admit_score = tr.getAttribute('data-admit-score');
            }
            if (tr.getAttribute('data-score-status')) {
                snap.score_status_label = tr.getAttribute('data-score-status');
            }
        }
        return snap;
    }

    function countAllPrefers() {
        var total = 0;
        Object.keys(preferStoreBySchool).forEach(function (schoolKey) {
            var store = preferStoreBySchool[schoolKey];
            if (!store) return;
            Object.keys(store).forEach(function (preferKey) {
                if (store[preferKey] && store[preferKey].selected) total += 1;
            });
        });
        return total;
    }

    function clearAllPrefers() {
        preferStoreBySchool = {};
        document.querySelectorAll('.gk-school-card').forEach(function (article) {
            article._preferStore = {};
            article.querySelectorAll('.gk-prefer-btn').forEach(function (btn) {
                if (btn.classList.contains('gk-prefer-btn--on')) {
                    setPreferSelected(btn, false, true);
                }
            });
            syncSchoolCardPreferGradient(article);
            syncGroupTabLabels(article);
            syncPreferGroupPanel(article);
        });
        persistPreferStore();
    }

    function attachClearPreferButton(btn) {
        var PRESS_MS = 3000;
        var pressTimer = null;
        var longPressHandled = false;
        var progressBar = btn.querySelector('.gk-system-clear-btn-progress');

        function stopProgress() {
            btn.classList.remove('gk-system-clear-btn--hold');
            if (!progressBar) return;
            progressBar.style.transition = 'none';
            progressBar.style.width = '0%';
        }

        function startProgress() {
            stopProgress();
            btn.classList.add('gk-system-clear-btn--hold');
            requestAnimationFrame(function () {
                if (!progressBar) return;
                progressBar.style.transition = 'width ' + PRESS_MS + 'ms linear';
                progressBar.style.width = '100%';
            });
        }

        function clearPress() {
            if (pressTimer) {
                clearTimeout(pressTimer);
                pressTimer = null;
            }
            stopProgress();
        }

        function onPressStart(e) {
            if (e.type === 'mousedown' && e.button !== 0) return;
            longPressHandled = false;
            clearPress();
            startProgress();
            pressTimer = setTimeout(function () {
                longPressHandled = true;
                stopProgress();
                if (!countAllPrefers()) return;
                clearAllPrefers();
            }, PRESS_MS);
        }

        function onPressEnd(e) {
            if (e.type === 'mouseup' && e.button !== 0) return;
            if (pressTimer) {
                clearTimeout(pressTimer);
                pressTimer = null;
            }
            stopProgress();
        }

        btn.addEventListener('mousedown', onPressStart);
        btn.addEventListener('mouseup', onPressEnd);
        btn.addEventListener('mouseleave', clearPress);
        btn.addEventListener('touchstart', onPressStart, { passive: true });
        btn.addEventListener('touchend', onPressEnd);
        btn.addEventListener('touchcancel', clearPress);
        btn.addEventListener('contextmenu', function (e) {
            e.preventDefault();
        });
        btn.addEventListener('click', function (e) {
            e.preventDefault();
        });
    }

    function readPreferRowMeta(tr) {
        if (!tr) return { key: '', tierClass: 'none', probability: null };
        var probRaw = tr.getAttribute('data-probability');
        var prob = probRaw === '' || probRaw == null ? null : parseFloat(probRaw);
        if (isNaN(prob)) prob = null;
        return {
            key: tr.getAttribute('data-prefer-key') || '',
            tierClass: tr.getAttribute('data-tier-class') || 'none',
            probability: prob
        };
    }

    function syncSchoolCardPreferGradient(article) {
        if (!article) return;
        var store = getPreferStore(article);
        var entries = [];
        if (store) {
            Object.keys(store).forEach(function (key) {
                if (store[key] && store[key].selected) entries.push(store[key]);
            });
        }
        if (!entries.length) {
            article.classList.remove('gk-school-card--prefer');
            article.style.removeProperty('--prefer-end');
            return;
        }
        var best = entries[0];
        entries.forEach(function (entry) {
            if (entry.probability != null && (best.probability == null || entry.probability > best.probability)) {
                best = entry;
            }
        });
        var endColor = PREFER_TIER_END[best.tierClass] || PREFER_TIER_END.none;
        article.classList.add('gk-school-card--prefer');
        article.style.setProperty('--prefer-end', endColor);
    }

    function restorePreferRows(article) {
        var store = getPreferStore(article);
        if (!article || !store) return;
        article.querySelectorAll('.gk-prefer-btn').forEach(function (btn) {
            var tr = btn.closest('tr');
            if (!tr) return;
            var key = tr.getAttribute('data-prefer-key');
            if (key && store[key] && store[key].selected) {
                setPreferSelected(btn, true, true);
            }
        });
    }

    function setPreferSelected(btn, selected, skipStore) {
        var tr = btn.closest('tr');
        var tierClass = (tr && tr.getAttribute('data-tier-class')) || 'none';
        btn.classList.toggle('gk-prefer-btn--on', !!selected);
        btn.setAttribute('aria-pressed', selected ? 'true' : 'false');
        if (!tr) return;
        PREFER_ROW_CLASSES.forEach(function (cls) {
            tr.classList.remove(cls);
        });
        if (selected) {
            tr.classList.add('gk-group-detail-row--prefer-' + (tierClass || 'none'));
        }
        if (skipStore) return;
        var article = btn.closest('.gk-school-card');
        if (!article) return;
        var meta = readPreferRowMeta(tr);
        if (!meta.key) return;
        var store = getPreferStore(article);
        if (selected) {
            store[meta.key] = capturePreferSnapshot(tr, article, meta);
        } else {
            delete store[meta.key];
        }
        persistPreferStore();
        syncSchoolCardPreferGradient(article);
        syncGroupTabLabels(article);
        syncPreferGroupPanel(article);
    }

    function attachPreferButton(btn) {
        var PRESS_MS = 200;
        var pressTimer = null;
        var longPressHandled = false;
        var progressBar = btn.querySelector('.gk-prefer-btn-cancel-progress');

        function stopCancelProgress() {
            btn.classList.remove('gk-prefer-btn--cancel-hold');
            if (!progressBar) return;
            progressBar.style.transition = 'none';
            progressBar.style.width = '0%';
        }

        function startCancelProgress() {
            if (!btn.classList.contains('gk-prefer-btn--on') || !progressBar) return;
            stopCancelProgress();
            btn.classList.add('gk-prefer-btn--cancel-hold');
            requestAnimationFrame(function () {
                progressBar.style.transition = 'width ' + PRESS_MS + 'ms linear';
                progressBar.style.width = '100%';
            });
        }

        function clearPress() {
            if (pressTimer) {
                clearTimeout(pressTimer);
                pressTimer = null;
            }
            stopCancelProgress();
        }

        function onPressStart(e) {
            if (e.type === 'mousedown' && e.button !== 0) return;
            longPressHandled = false;
            clearPress();
            if (btn.classList.contains('gk-prefer-btn--on')) {
                startCancelProgress();
            }
            pressTimer = setTimeout(function () {
                longPressHandled = true;
                stopCancelProgress();
                if (btn.classList.contains('gk-prefer-btn--on')) {
                    setPreferSelected(btn, false);
                }
            }, PRESS_MS);
        }

        function onPressEnd(e) {
            if (e.type === 'mouseup' && e.button !== 0) return;
            if (pressTimer) {
                clearTimeout(pressTimer);
                pressTimer = null;
            }
            stopCancelProgress();
            if (longPressHandled) return;
            if (!btn.classList.contains('gk-prefer-btn--on')) {
                setPreferSelected(btn, true);
            }
        }

        btn.addEventListener('mousedown', onPressStart);
        btn.addEventListener('mouseup', onPressEnd);
        btn.addEventListener('mouseleave', clearPress);
        btn.addEventListener('touchstart', onPressStart, { passive: true });
        btn.addEventListener('touchend', onPressEnd);
        btn.addEventListener('touchcancel', clearPress);
        btn.addEventListener('contextmenu', function (e) {
            e.preventDefault();
        });
    }

    function detailActionCell() {
        var td = document.createElement('td');
        td.className = 'gk-group-detail-action';
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'gk-prefer-btn';
        btn.setAttribute('aria-pressed', 'false');
        var label = document.createElement('span');
        label.className = 'gk-prefer-btn-label';
        label.textContent = '优选';
        var progress = document.createElement('span');
        progress.className = 'gk-prefer-btn-cancel-progress';
        progress.setAttribute('aria-hidden', 'true');
        btn.appendChild(progress);
        btn.appendChild(label);
        attachPreferButton(btn);
        td.appendChild(btn);
        return td;
    }

    function resetNoteClamp(tr) {
        var noteTd = tr.querySelector('.gk-group-detail-note');
        var inner = noteTd && noteTd.querySelector('.gk-group-detail-note-text');
        if (!noteTd || !inner) return;
        noteTd.style.maxHeight = '';
        inner.style.display = '';
        inner.style.width = '';
        inner.style.webkitLineClamp = '';
        inner.style.webkitBoxOrient = '';
        inner.style.maxHeight = '';
        inner.style.overflow = '';
        inner.style.textOverflow = '';
    }

    function clampDetailNoteRow(tr) {
        if (!tr || tr.classList.contains('gk-group-detail-row--note-expanded')) return;
        var noteTd = tr.querySelector('.gk-group-detail-note');
        var inner = noteTd && noteTd.querySelector('.gk-group-detail-note-text');
        if (!noteTd || !inner || inner.textContent === '—') return;

        resetNoteClamp(tr);

        inner.style.display = '-webkit-box';
        inner.style.webkitBoxOrient = 'vertical';
        inner.style.webkitLineClamp = '1';
        inner.style.overflow = 'hidden';

        var rowTarget = 0;
        tr.querySelectorAll('td:not(.gk-group-detail-note)').forEach(function (td) {
            rowTarget = Math.max(rowTarget, td.offsetHeight);
        });
        if (rowTarget < 1) rowTarget = 40;

        var cs = window.getComputedStyle(noteTd);
        var padY = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
        var padX = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
        var lineHeight = parseFloat(window.getComputedStyle(inner).lineHeight) || 18;
        var contentH = Math.max(lineHeight, rowTarget - padY);

        inner.style.display = 'block';
        inner.style.webkitLineClamp = 'unset';
        inner.style.webkitBoxOrient = '';
        inner.style.maxHeight = 'none';
        inner.style.width = Math.max(0, noteTd.clientWidth - padX) + 'px';
        var fullHeight = inner.scrollHeight;
        inner.style.width = '';

        if (fullHeight <= contentH + 1) {
            inner.style.overflow = 'visible';
            return;
        }

        var lines = Math.max(1, Math.floor((contentH + 0.01) / lineHeight));
        inner.style.display = '-webkit-box';
        inner.style.webkitBoxOrient = 'vertical';
        inner.style.overflow = 'hidden';
        inner.style.textOverflow = 'ellipsis';
        inner.style.webkitLineClamp = String(lines);
        inner.style.maxHeight = contentH + 'px';
        noteTd.style.maxHeight = rowTarget + 'px';
    }

    function clampDetailNoteRows(root) {
        var tables = [];
        if (root && root.classList && root.classList.contains('gk-group-detail-table')) {
            tables = [root];
        } else if (root && root.querySelectorAll) {
            tables = Array.prototype.slice.call(root.querySelectorAll('.gk-group-detail-table'));
        } else {
            tables = Array.prototype.slice.call(document.querySelectorAll('.gk-group-detail-table'));
        }
        tables.forEach(function (table) {
            table.querySelectorAll('tbody tr').forEach(clampDetailNoteRow);
        });
    }

    function detailNoteCell(text) {
        var val = text == null || text === '' ? '—' : String(text);
        var td = document.createElement('td');
        td.className = 'gk-group-detail-note';
        var inner = document.createElement('span');
        inner.className = 'gk-group-detail-note-text';
        inner.textContent = val;
        td.appendChild(inner);
        if (val !== '—') {
            td.title = '点击展开/收起备注';
            td.addEventListener('click', function (e) {
                e.stopPropagation();
                var tr = td.closest('tr');
                if (!tr) return;
                var tbody = tr.parentElement;
                var willExpand = !tr.classList.contains('gk-group-detail-row--note-expanded');
                if (tbody) {
                    tbody.querySelectorAll('.gk-group-detail-row--note-expanded').forEach(function (row) {
                        row.classList.remove('gk-group-detail-row--note-expanded');
                        resetNoteClamp(row);
                    });
                }
                if (willExpand) {
                    tr.classList.add('gk-group-detail-row--note-expanded');
                    resetNoteClamp(tr);
                }
                if (tbody) {
                    requestAnimationFrame(function () {
                        clampDetailNoteRows(tbody.closest('.gk-group-detail-table'));
                    });
                }
            });
        }
        return td;
    }

    function syncApplyBtnState(btn, expanded) {
        if (!btn) return;
        btn.classList.toggle('gk-school-apply-btn--active', !!expanded);
        btn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        btn.textContent = expanded ? '收起' : '展开';
    }

    function closeDetailPanel(article) {
        var panel = article.querySelector('.gk-group-detail-panel');
        if (!panel) return;
        panel.hidden = true;
        panel.innerHTML = '';
        delete panel.dataset.mode;
        delete panel.dataset.activeGroup;
        article.querySelectorAll('.gk-major-group-btn--active').forEach(function (btn) {
            btn.classList.remove('gk-major-group-btn--active');
            btn.setAttribute('aria-expanded', 'false');
        });
        article.querySelectorAll('.gk-school-apply-btn').forEach(function (btn) {
            syncApplyBtnState(btn, false);
        });
        syncPreferGroupPanel(article);
    }

    function appendGroupDetailTable(container, group, displayMode, showTuition) {
        displayMode = displayMode || 'chart';
        showTuition = !!showTuition;
        var useChart = displayMode !== 'numbers';
        var tableWrap = document.createElement('div');
        tableWrap.className = 'gk-group-detail-table-wrap';
        var table = document.createElement('table');
        table.className = 'gk-group-detail-table';
        if (showTuition) {
            table.classList.add('gk-group-detail-table--show-tuition');
        }
        var thead = document.createElement('thead');
        var hr = document.createElement('tr');
        var headerLabels = [
            { label: '概率', colClass: 'gk-group-detail-col-prob' },
            { label: '专业名称' },
            { label: '学制' },
            { label: '学费', colClass: 'gk-group-detail-col-tuition' },
            { label: '选科要求' }
        ];
        if (useChart) {
            headerLabels.push({ label: '25最低分', colClass: 'gk-group-detail-col-score25' });
            headerLabels.push({ label: '25最高分', colClass: 'gk-group-detail-col-score25' });
            headerLabels.push({ label: '过去3年位次', chart: true });
        } else {
            headerLabels.push({ label: '25最低分' });
            headerLabels.push({ label: '25最高分' });
            headerLabels.push({ label: '25位次' });
            headerLabels.push({ label: '24最低分' });
            headerLabels.push({ label: '24位次' });
            headerLabels.push({ label: '23最低分' });
            headerLabels.push({ label: '23位次' });
        }
        headerLabels.push({ label: '备注' });
        headerLabels.push({ label: '操作' });
        headerLabels.forEach(function (item) {
            var th = document.createElement('th');
            if (item.chart) {
                th.className = 'gk-group-detail-th-chart';
                var head = document.createElement('div');
                head.className = 'gk-group-detail-chart-head';
                var title = document.createElement('div');
                title.className = 'gk-group-detail-chart-title';
                title.textContent = item.label;
                var legend = document.createElement('div');
                legend.className = 'gk-chart-legend gk-chart-legend--rank-band';
                legend.innerHTML = rankBandLegendHtml();
                head.appendChild(title);
                head.appendChild(legend);
                th.appendChild(head);
            } else {
                th.textContent = item.label;
                if (item.colClass) {
                    th.className = item.colClass;
                }
            }
            hr.appendChild(th);
        });
        thead.appendChild(hr);
        table.appendChild(thead);

        var tbody = document.createElement('tbody');
        (group.all_majors || group.majors || []).forEach(function (m) {
            var d = m.detail || m;
            var tier = m.tier_class || probTierFromValue(m.probability).class;
            var tr = document.createElement('tr');
            tr.setAttribute('data-tier-class', tier);
            tr.setAttribute('data-prefer-key', preferRowKey(
                group.group_code,
                d.major_name || m.major_name,
                d.major_code || m.major_code,
                d.major_note != null ? d.major_note : (m.major_note != null ? m.major_note : '')
            ));
            tr.setAttribute('data-probability', m.probability != null ? String(m.probability) : '');
            tr.setAttribute('data-group-code', group.group_code || '');
            tr.setAttribute('data-major-code', d.major_code || m.major_code || '');
            tr.setAttribute('data-duration', d.duration != null ? String(d.duration) : '');
            tr.setAttribute('data-tuition', d.tuition != null ? String(d.tuition) : '');
            tr.setAttribute('data-major-note', d.major_note != null ? String(d.major_note) : '');
            tr.setAttribute('data-rank-2025', d.rank_2025 != null ? String(d.rank_2025) : '');
            tr.setAttribute('data-rank-max-2025', d.rank_max_2025 != null ? String(d.rank_max_2025) : '');
            tr.appendChild(detailProbCell(d.plan_count || m.plan_count, m.probability, tier));
            tr.appendChild(detailCell(d.major_name || m.major_name));
            tr.appendChild(detailCell(d.duration));
            tr.appendChild(detailCell(d.tuition, 'gk-group-detail-col-tuition'));
            tr.appendChild(detailCell(d.subject_requirement));
            if (useChart) {
                tr.appendChild(detailCell(d.score_2025, 'gk-group-detail-col-score25'));
                tr.appendChild(detailCell(d.score_max_2025, 'gk-group-detail-col-score25'));
                tr.appendChild(detailRankChartCell(d));
            } else {
                tr.appendChild(detailCell(d.score_2025));
                tr.appendChild(detailCell(d.score_max_2025));
                tr.appendChild(detailCell(d.rank_2025));
                tr.appendChild(detailCell(d.score_2024));
                tr.appendChild(detailCell(d.rank_2024));
                tr.appendChild(detailCell(d.score_2023));
                tr.appendChild(detailCell(d.rank_2023));
            }
            tr.appendChild(detailNoteCell(d.major_note));
            tr.appendChild(detailActionCell());
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        tableWrap.appendChild(table);
        container.appendChild(tableWrap);
        var article = articleFromPanel(container.closest('.gk-group-detail-panel'));
        requestAnimationFrame(function () {
            clampDetailNoteRows(table);
            restorePreferRows(article);
        });
    }

    function getCardMajorGroups(card) {
        if (!card) return [];
        if (card.all_major_groups && card.all_major_groups.length) {
            return card.all_major_groups;
        }
        return card.major_groups || [];
    }

    function getCardMajorGroupList(card) {
        var groups = getCardMajorGroups(card);
        if (groups.length) return groups;
        if (card && (card.majors || []).length) {
            return [{
                group_code: '—',
                tier_class: 'none',
                tier_label: '',
                majors: card.majors,
                all_majors: card.majors
            }];
        }
        return [];
    }

    function findApplyGroupIndex(allGroups, groupCode) {
        if (!groupCode) return 0;
        for (var i = 0; i < allGroups.length; i++) {
            if ((allGroups[i].group_code || '') === groupCode) return i;
        }
        return 0;
    }

    function articleFromPanel(panel) {
        return panel.closest('.gk-school-card');
    }

    function renderApplyPanel(panel, allGroups, schoolName, initialGroupCode) {
        panel.innerHTML = '';
        panel.hidden = false;
        panel.dataset.mode = 'apply';
        panel.dataset.scoreDisplay = 'chart';
        if (panel.dataset.showTuition == null) panel.dataset.showTuition = '0';

        var article = articleFromPanel(panel);
        var head = document.createElement('div');
        head.className = 'gk-group-detail-head';
        var title = document.createElement('div');
        title.className = 'gk-group-detail-title';
        title.textContent = (schoolName || '院校') + ' · 专业组填报';
        var headActions = document.createElement('div');
        headActions.className = 'gk-group-detail-head-actions';
        var tuitionToggleBtn = document.createElement('button');
        tuitionToggleBtn.type = 'button';
        tuitionToggleBtn.className = 'gk-group-detail-tuition-toggle';
        tuitionToggleBtn.textContent = '显示学费';
        var displayToggleBtn = document.createElement('button');
        displayToggleBtn.type = 'button';
        displayToggleBtn.className = 'gk-group-detail-display-toggle';
        var closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'gk-group-detail-close';
        closeBtn.textContent = '收起';
        headActions.appendChild(tuitionToggleBtn);
        headActions.appendChild(displayToggleBtn);
        headActions.appendChild(closeBtn);
        head.appendChild(title);
        head.appendChild(headActions);
        panel.appendChild(head);

        function syncDisplayToggleLabel() {
            var mode = panel.dataset.scoreDisplay || 'chart';
            displayToggleBtn.textContent = mode === 'chart' ? '显示数字' : '显示折线图';
        }
        syncDisplayToggleLabel();

        function syncTuitionToggleBtn() {
            var on = panel.dataset.showTuition === '1';
            tuitionToggleBtn.classList.toggle('gk-group-detail-tuition-toggle--on', on);
            tuitionToggleBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
        }
        syncTuitionToggleBtn();

        var tabsWrap = document.createElement('div');
        tabsWrap.className = 'gk-apply-group-tabs';
        var tableHost = document.createElement('div');
        tableHost.className = 'gk-apply-table-host';

        function renderActiveGroupTable() {
            if (!allGroups.length) return;
            var idx = findApplyGroupIndex(allGroups, panel.dataset.activeGroup || '');
            var group = allGroups[idx];
            if (!group) return;
            tableHost.innerHTML = '';
            try {
                appendGroupDetailTable(
                    tableHost,
                    group,
                    panel.dataset.scoreDisplay || 'chart',
                    panel.dataset.showTuition === '1'
                );
            } catch (err) {
                console.error('gk appendGroupDetailTable failed', err);
                var errBox = document.createElement('div');
                errBox.className = 'gk-school-majors-empty';
                errBox.textContent = '表格加载失败，请刷新后重试';
                tableHost.appendChild(errBox);
            }
        }

        tuitionToggleBtn.addEventListener('click', function () {
            panel.dataset.showTuition = panel.dataset.showTuition === '1' ? '0' : '1';
            syncTuitionToggleBtn();
            renderActiveGroupTable();
        });

        displayToggleBtn.addEventListener('click', function () {
            var mode = panel.dataset.scoreDisplay || 'chart';
            panel.dataset.scoreDisplay = mode === 'chart' ? 'numbers' : 'chart';
            syncDisplayToggleLabel();
            renderActiveGroupTable();
        });

        if (!allGroups.length) {
            panel.dataset.activeGroup = '';
            var empty = document.createElement('div');
            empty.className = 'gk-school-majors-empty';
            empty.textContent = '暂无专业组';
            tableHost.appendChild(empty);
        } else {
            var tabBtns = [];
            var initialIdx = findApplyGroupIndex(allGroups, initialGroupCode);
            allGroups.forEach(function (group, idx) {
                var tabBtn = document.createElement('button');
                tabBtn.type = 'button';
                tabBtn.className = groupBtnClass(group.tier_class);
                tabBtn.setAttribute('data-group-code', group.group_code || '');
                updateGroupTabButton(tabBtn, group.group_code || '', article);
                tabBtn.addEventListener('click', function () {
                    tabBtns.forEach(function (b) { b.classList.remove('gk-major-group-btn--active'); });
                    tabBtn.classList.add('gk-major-group-btn--active');
                    panel.dataset.activeGroup = group.group_code || '';
                    renderActiveGroupTable();
                    syncPreferGroupPanel(article);
                });
                tabBtns.push(tabBtn);
                tabsWrap.appendChild(tabBtn);
            });
            tabBtns[initialIdx].classList.add('gk-major-group-btn--active');
            panel.dataset.activeGroup = allGroups[initialIdx].group_code || '';
        }

        panel.appendChild(tabsWrap);
        panel.appendChild(tableHost);

        if (allGroups.length) {
            renderActiveGroupTable();
        }
        syncPreferGroupPanel(article);

        closeBtn.addEventListener('click', function () {
            closeDetailPanel(article);
        });
    }

    function openApplyPanel(article, card, initialGroupCode) {
        var panel = article.querySelector('.gk-group-detail-panel');
        var applyBtn = article.querySelector('.gk-school-apply-btn');
        if (!panel || !card) return;

        closeDetailPanel(article);
        if (applyBtn) {
            syncApplyBtnState(applyBtn, true);
        }
        article._gkCardData = card;
        var allGroups = getCardMajorGroupList(card);
        renderApplyPanel(panel, allGroups, card.school_name || '', initialGroupCode || '');
    }

    function toggleApplyPanel(article, card, applyBtn) {
        var panel = article.querySelector('.gk-group-detail-panel');
        if (!panel) return;
        card = card || article._gkCardData;
        if (!card) return;
        var isStrong = isStrongCard(card);
        var mode = isStrong ? 'strong' : 'apply';
        var isOpen = !panel.hidden && panel.dataset.mode === mode;

        if (isOpen) {
            closeDetailPanel(article);
            return;
        }

        if (isStrong) {
            openStrongPanel(article, card, applyBtn);
            return;
        }

        openApplyPanel(article, card, '');
    }

    function renderSchoolCards(records) {
        if (!schoolList) return;
        schoolList.innerHTML = '';
        if (!records || !records.length) {
            renderSchoolEmpty('未找到匹配院校');
            return;
        }
        records.forEach(function (card) {
            var article = document.createElement('article');
            article.className = 'gk-school-card';
            article.setAttribute('data-school-name', card.school_name || '');
            article.setAttribute('data-school-code', card.school_code || '');
            article._gkCardData = card;

            var row = document.createElement('div');
            row.className = 'gk-school-card-row';

            var applyBtn = document.createElement('button');
            applyBtn.type = 'button';
            applyBtn.className = 'gk-school-apply-btn';
            syncApplyBtnState(applyBtn, false);
            applyBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                toggleApplyPanel(article, card, applyBtn);
            });

            var probBox = document.createElement('div');
            probBox.className = tierClassName(card.tier_class);
            var probPct = document.createElement('div');
            probPct.className = 'gk-school-tier-pct';
            probPct.textContent = card.probability == null ? '—' : (Math.round(card.probability * 100) + '%');
            var probLabel = document.createElement('div');
            probLabel.className = 'gk-school-tier-label';
            probLabel.textContent = card.tier_label || '';
            probBox.appendChild(probPct);
            probBox.appendChild(probLabel);

            var main = document.createElement('div');
            main.className = 'gk-school-main';
            var mainHead = document.createElement('div');
            mainHead.className = 'gk-school-main-head';
            var title = document.createElement('h3');
            title.className = 'gk-school-name';
            title.textContent = card.school_name || '';
            mainHead.appendChild(title);
            mainHead.appendChild(applyBtn);
            var loc = document.createElement('div');
            loc.className = 'gk-school-loc';
            loc.textContent = card.location_line || '';
            var tags = document.createElement('div');
            tags.className = 'gk-school-tags';
            (card.tags || []).forEach(function (tag) {
                var span = document.createElement('span');
                span.className = 'gk-school-tag';
                span.textContent = tag;
                tags.appendChild(span);
            });
            var stats = document.createElement('div');
            stats.className = 'gk-school-stats';
            stats.innerHTML =
                '<span>院校代码 ' + (card.school_code || '—') + '</span>' +
                '<span>25年计划 ' + (card.plan_count || '—') + '人</span>' +
                '<span>25年' + (card.category_label || '物理') + '最低分 ' + (card.min_score != null ? card.min_score : '—') + '</span>' +
                '<span>最低位次 ' + (card.min_rank != null ? card.min_rank : '—') + '</span>';
            main.appendChild(mainHead);
            main.appendChild(loc);
            main.appendChild(tags);
            main.appendChild(stats);
            main.addEventListener('click', function (e) {
                if (e.target.closest('.gk-school-apply-btn')) return;
                toggleApplyPanel(article, card, applyBtn);
            });

            row.appendChild(probBox);
            row.appendChild(main);

            var preferPanel = document.createElement('div');
            preferPanel.className = 'gk-school-prefer-panel';
            preferPanel.hidden = true;
            preferPanel.addEventListener('click', function (e) {
                e.stopPropagation();
            });
            var preferList = document.createElement('div');
            preferList.className = 'gk-prefer-group-list';
            preferPanel.appendChild(preferList);
            row.appendChild(preferPanel);

            article.appendChild(row);

            var detailPanel = document.createElement('div');
            detailPanel.className = 'gk-group-detail-panel';
            detailPanel.hidden = true;
            article.appendChild(detailPanel);

            schoolList.appendChild(article);
            syncPreferGroupPanel(article);
            syncSchoolCardPreferGradient(article);
        });
    }

    function hasProfileFilters() {
        return profileProvinces.length > 0 || profileMajorCategories.length > 0 || profileMajorGroups.length > 0;
    }

    function hasSearchCriteria() {
        var cat = catSel ? catSel.value : '';
        var typeVal = typeSel ? typeSel.value : '';
        return !!(cat || typeVal || hasProfileFilters() || addedSchools.length || isExpertDataset() || isStrongDataset());
    }

    function profileFilterSummary() {
        var parts = [];
        if (profileProvinces.length) {
            parts.push(profileProvinces.length + ' 个地区');
        }
        var majorCount = profileMajorCategories.length || profileMajorGroups.length;
        if (majorCount) {
            parts.push(majorCount + ' 个专业类');
        }
        return parts.length ? ('已按上一页选择筛选：' + parts.join('、')) : '';
    }

    function runSearch() {
        var cat = catSel ? catSel.value : '';
        var typeVal = typeSel ? typeSel.value : '';
        if (!hasSearchCriteria()) {
            if (meta) {
                meta.textContent = isStrongDataset()
                    ? '强基计划展示全部院校，填写高考分数可对比入围参考线。'
                    : '填写分数与位次后可显示录取概率与位次折线图。';
            }
            renderEmpty(isStrongDataset()
                ? '切换到强基计划标签即可查看全部院校'
                : '请先在上一页选择院校地域与目标专业');
            return;
        }
        if (meta) meta.textContent = '查询中…';
        var params = 'limit=500&' + datasetQueryParams();
        if (isStrongDataset()) {
            if (scoreInp && scoreInp.value.trim()) {
                params += '&user_score=' + encodeURIComponent(scoreInp.value.trim());
            }
            params += '&view=school';
        } else if (isExpertDataset()) {
            if (cat) params += '&category=' + encodeURIComponent(cat);
            if (typeVal) params += '&type=' + encodeURIComponent(typeVal);
            if (profileProvinces.length) {
                params += '&provinces=' + encodeURIComponent(profileProvinces.join(','));
            }
            if (profileMajorCategories.length) {
                params += '&major_categories=' + encodeURIComponent(profileMajorCategories.join(','));
            }
            if (profileMajorGroups.length) {
                params += '&major_groups=' + encodeURIComponent(profileMajorGroups.join(','));
            }
            if (addedSchools.length) {
                params += '&extra_schools=' + encodeURIComponent(addedSchools.join(','));
            }
            if (hasProfileFilters() || addedSchools.length) {
                params += '&sort_by_score=1';
            }
            if (rankInp && rankInp.value.trim()) {
                params += '&user_rank=' + encodeURIComponent(rankInp.value.trim());
            }
            if (scoreInp && scoreInp.value.trim()) {
                params += '&user_score=' + encodeURIComponent(scoreInp.value.trim());
            }
            params += '&view=school';
        }
        var reqSeq = ++searchSeq;
        var reqTabId = currentTabId;
        fetch(searchUrl + '?' + withProvinceParam(params))
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (reqSeq !== searchSeq || reqTabId !== currentTabId) return;
                if (!data || !data.ok) {
                    if (meta) meta.textContent = '';
                    renderEmpty((data && data.message) || '查询失败');
                    return;
                }
                var summary = profileFilterSummary();
                var countText;
                if (isStrongDataset()) {
                    countText = data.total > data.records.length
                        ? ('共 ' + data.total + ' 所院校，显示前 ' + data.records.length + ' 所')
                        : ('共 ' + data.total + ' 所院校');
                } else {
                    countText = data.total > data.records.length
                        ? ('找到 ' + data.total + ' 所院校，显示前 ' + data.records.length + ' 所（按分数从高到低）')
                        : ('找到 ' + data.total + ' 所院校（按分数从高到低）');
                }
                if (meta) {
                    meta.textContent = summary ? (summary + ' · ' + countText) : countText;
                }
                renderRows(data.records);
            })
            .catch(function () {
                if (reqSeq !== searchSeq || reqTabId !== currentTabId) return;
                if (meta) meta.textContent = '';
                renderEmpty('查询失败，请稍后重试');
            });
    }

    function scheduleSearch() {
        clearTimeout(debounce);
        debounce = setTimeout(runSearch, 300);
    }

    function fillFilterSelect(sel, values) {
        if (!sel) return;
        var keep = sel.value;
        while (sel.options.length > 1) {
            sel.remove(1);
        }
        (values || []).forEach(function (val) {
            var opt = document.createElement('option');
            opt.value = val;
            opt.textContent = val;
            sel.appendChild(opt);
        });
        if (keep && sel.querySelector('option[value="' + keep + '"]')) {
            sel.value = keep;
        } else {
            sel.value = '';
        }
    }

    function loadFilters() {
        if (!filtersUrl || isStrongDataset()) return;
        fetch(filtersUrl + '?' + withProvinceParam(datasetQueryParams()))
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data || !data.ok) return;
                filtersLoaded = true;
                fillFilterSelect(catSel, data.category || []);
                fillFilterSelect(typeSel, data.type || []);
                applySavedProfile();
                if (hasSearchCriteria()) {
                    runSearch();
                }
            })
            .catch(function () {});
    }

    function switchTab(btn) {
        currentTabId = normalizeActiveBatch(
            btn.getAttribute('data-tab-id') || btn.getAttribute('data-dataset') || defaultBatch
        );
        page.setAttribute('data-dataset', currentTabId);
        syncStrongPageClass();
        syncDrawerTabState();
        rebuildHeader();
        toggleFilters();
        toggleResultView();
        if (catSel) catSel.value = '';
        if (typeSel) typeSel.value = '';
        filtersLoaded = false;
        if (meta) {
            meta.textContent = isStrongDataset()
                ? '强基计划展示全部院校，填写高考分数可对比入围参考线。'
                : '填写分数与位次后可显示录取概率与位次折线图。';
        }
        if (isExpertDataset()) {
            loadFilters();
        } else {
            scheduleSearch();
        }
    }

    if (drawerTabs) {
        drawerTabs.querySelectorAll('.gk-data-tab').forEach(function (btn) {
            btn.addEventListener('click', function () {
                if (tabIsActive(btn)) return;
                switchTab(btn);
            });
        });
    }

    [rankInp, scoreInp, floatUpInp, floatDownInp].forEach(function (el) {
        if (!el) return;
        el.addEventListener('input', function () {
            persistProfileMetrics();
            scheduleSearch();
        });
        el.addEventListener('change', function () {
            persistProfileMetrics();
            runSearch();
        });
    });
    if (catSel) catSel.addEventListener('change', runSearch);
    if (typeSel) typeSel.addEventListener('change', runSearch);

    if (applyOptionsBtn) {
        applyOptionsBtn.addEventListener('click', openApplyDrawer);
    }
    if (applyDrawerClose) applyDrawerClose.addEventListener('click', closeApplyDrawer);
    if (applyDrawerBackdrop) applyDrawerBackdrop.addEventListener('click', closeApplyDrawer);
    if (drawerSearchBtn) drawerSearchBtn.addEventListener('click', runDrawerSchoolSearch);
    if (drawerSchoolInp) {
        drawerSchoolInp.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') runDrawerSchoolSearch();
        });
    }
    if (saveDraftBtn) {
        saveDraftBtn.addEventListener('click', function () {
            persistProfileMetrics();
            saveSystemDraft(true);
        });
    }
    if (generatePlanBtn) {
        generatePlanBtn.addEventListener('click', function () {
            persistProfileMetrics();
            saveSystemDraft(false);
            persistPreferStore();
            if (!countAllPrefers()) {
                alert('请先在各批次中为意向院校/专业点击「优选」，再生成志愿表。');
                return;
            }
            if (planUrl) {
                window.location.href = urlWithProvince(planUrl);
            } else {
                alert('志愿表页面未配置，请联系管理员。');
            }
        });
    }
    if (clearPreferBtn) {
        attachClearPreferButton(clearPreferBtn);
    }

    function applySavedProfile() {
        profileProvinces = [];
        profileMajorCategories = [];
        profileMajorGroups = [];
        try {
            var raw = localStorage.getItem(PROFILE_KEY);
            if (!raw) return;
            var p = JSON.parse(raw);
            profileProvinces = (p.target_provinces || []).filter(Boolean);
            profileMajorCategories = (p.target_majors || []).filter(Boolean);
            profileMajorGroups = (p.target_major_groups || []).filter(Boolean);
            var rank = p.score_rank_0 || p.province_rank;
            var score = p.score_total_0 || p.score;
            var floatUp = parseInt(p.rank_float_up, 10);
            var floatDown = parseInt(p.rank_float_down, 10);
            if (rankInp && rank) rankInp.value = String(rank).trim();
            if (scoreInp && score) scoreInp.value = String(score).trim();
            if (floatUpInp) floatUpInp.value = isNaN(floatUp) || floatUp < 0 ? '0' : String(floatUp);
            if (floatDownInp) floatDownInp.value = isNaN(floatDown) || floatDown < 0 ? '0' : String(floatDown);
            if (catSel) {
                var subj = p.score_subjects_0 || p.subject_combo || '';
                var s = String(subj);
                var cat = s.indexOf('历') >= 0 || s === '历史' ? '历史' : '物理';
                if (catSel.querySelector('option[value="' + cat + '"]')) catSel.value = cat;
            }
        } catch (e) { /* ignore */ }
    }

    loadPreferStoreFromStorage();
    loadSystemDraft();
    rebuildHeader();
    loadFilters();
    toggleFilters();
    toggleResultView();
    applySavedProfile();
    renderDrawerAddedTable();
    if (!hasProfileFilters() && !addedSchools.length && !isStrongDataset()) {
        renderEmpty('请先在上一页选择院校地域与目标专业');
    } else if (isStrongDataset()) {
        scheduleSearch();
    }
})();
