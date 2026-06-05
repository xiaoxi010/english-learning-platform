(function () {
    var page = document.getElementById('gkPlanPage');
    if (!page) return;

    var PROFILE_KEY = 'gaokao_apply_profile';
    var PREFER_STORE_KEY = 'gaokao_apply_prefer_store';
    var PLAN_ORDER_KEY = 'gaokao_apply_plan_order';

    var systemUrl = page.getAttribute('data-system-url') || '';
    var planLookupUrl = page.getAttribute('data-plan-lookup-url') || '';
    var gaokaoProvince = page.getAttribute('data-gaokao-province') || '吉林';
    var basicSection = document.getElementById('gkPlanBasicSection');
    var basicGrid = document.getElementById('gkPlanBasicGrid');
    var batchHost = document.getElementById('gkPlanBatchSections');
    var planBody = document.getElementById('gkPlanBody');
    var planEmpty = document.getElementById('gkPlanEmpty');
    var printBtn = document.getElementById('gkPlanPrintBtn');
    var printTitleEl = document.getElementById('gkPlanPrintTitle');

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

    var FALLBACK_BATCHES = [
        { id: 'strong', label: '强基计划', mode: 'strong' },
        { id: 'early', label: '提前批', mode: 'expert' },
        { id: 'undergraduate', label: '本科批', mode: 'expert' },
        { id: 'junior', label: '专科批', mode: 'expert' }
    ];

    function buildBatchesConfig() {
        if (provinceBatches.length) {
            return provinceBatches.map(function (tab) {
                return {
                    id: tab.id,
                    label: tab.label,
                    mode: tab.mode || (tab.id === 'strong' ? 'strong' : 'expert'),
                    bucket: tab.bucket || tab.id,
                    batch: tab.batch || ''
                };
            });
        }
        return FALLBACK_BATCHES.slice();
    }

    var BATCHES = buildBatchesConfig();

    var BASIC_FIELDS = [
        { key: 'name', label: '姓名' },
        { key: 'gender', label: '性别' },
        { key: 'region', label: '地域' },
        { key: 'gaokao_province', label: '高考省份' },
        { key: 'ethnicity', label: '民族' },
        { key: 'phone', label: '手机号' },
        { key: 'high_school', label: '高中' },
        { key: 'birthday', label: '出生日期' },
        { key: 'score_subjects_0', label: '选科', alt: 'subject_combo' },
        { key: 'score_total_0', label: '高考分数', alt: 'score' },
        { key: 'score_rank_0', label: '省内位次', alt: 'province_rank' },
        { key: 'rank_float_up', label: '位次上浮' },
        { key: 'rank_float_down', label: '位次下浮' }
    ];

    var preferStore = {};
    var planOrder = {};
    var profile = {};
    var slideSortState = null;
    var pendingSlideSort = null;
    var SLIDE_SORT_DRAG_THRESHOLD = 8;
    var codeLookupCache = {};
    var preferStoreDirty = false;

    function loadProfile() {
        try {
            var raw = localStorage.getItem(PROFILE_KEY);
            profile = raw ? JSON.parse(raw) : {};
        } catch (e) {
            profile = {};
        }
    }

    function loadPreferStore() {
        try {
            var raw = localStorage.getItem(PREFER_STORE_KEY);
            preferStore = raw ? JSON.parse(raw) : {};
        } catch (e) {
            preferStore = {};
        }
        if (!preferStore || typeof preferStore !== 'object') preferStore = {};
    }

    function loadOrder() {
        try {
            var raw = localStorage.getItem(PLAN_ORDER_KEY);
            planOrder = raw ? JSON.parse(raw) : {};
        } catch (e) {
            planOrder = {};
        }
        if (!planOrder || typeof planOrder !== 'object') planOrder = {};
    }

    function saveOrder() {
        localStorage.setItem(PLAN_ORDER_KEY, JSON.stringify(planOrder));
    }

    function ensurePlanUi() {
        if (!planOrder.__ui || typeof planOrder.__ui !== 'object') {
            planOrder.__ui = { allExpanded: false };
        }
        if (planOrder.__ui.allExpanded == null) {
            planOrder.__ui.allExpanded = false;
        }
    }

    function ensureBatchUi(batchId) {
        if (!planOrder[batchId]) return;
        if (planOrder[batchId].allExpanded == null) {
            ensurePlanUi();
            planOrder[batchId].allExpanded = !!planOrder.__ui.allExpanded;
        }
    }

    function isBatchAllExpanded(batchId) {
        ensureBatchUi(batchId);
        return !!(planOrder[batchId] && planOrder[batchId].allExpanded);
    }

    function setBatchSchoolsExpanded(batchId, expanded) {
        if (!planOrder[batchId]) return;
        ensureBatchUi(batchId);
        planOrder[batchId].allExpanded = !!expanded;
        planOrder[batchId].collapsed = {};
        saveOrder();
        renderPlan();
    }

    function syncBatchToggleBtn(btn, batchId) {
        if (!btn) return;
        btn.textContent = isBatchAllExpanded(batchId) ? '全部收起' : '全部展开';
    }

    function parseStoreKey(storeKey) {
        if (!storeKey) return null;
        if (storeKey.indexOf('::') >= 0) {
            var parts = storeKey.split('::');
            return {
                dataset: parts[0],
                schoolName: parts.slice(1).join('::')
            };
        }
        var idx = storeKey.indexOf(':');
        if (idx <= 0) return null;
        return {
            dataset: storeKey.slice(0, idx),
            schoolName: storeKey.slice(idx + 1)
        };
    }

    function batchConfig(batchId) {
        for (var i = 0; i < BATCHES.length; i++) {
            if (BATCHES[i].id === batchId) return BATCHES[i];
        }
        return null;
    }

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

    function groupCodeFromPreferKey(key) {
        return parsePreferKey(key).groupCode;
    }

    function majorNameFromPreferKey(key) {
        return parsePreferKey(key).majorName;
    }

    function profileValue(field) {
        if (!field) return '';
        var val = profile[field.key];
        if ((val == null || val === '') && field.alt) val = profile[field.alt];
        return val == null || val === '' ? '—' : String(val);
    }

    function planPrintTitleText() {
        var name = profileValue({ key: 'name' });
        if (name === '—') name = '';
        return (name || '—') + '位 志愿表';
    }

    function syncPrintHead() {
        var titleText = planPrintTitleText();
        if (printTitleEl) printTitleEl.textContent = titleText;
    }

    function tierLabel(tier) {
        if (tier === 'safe') return '保';
        if (tier === 'steady') return '稳';
        if (tier === 'reach') return '冲';
        return '—';
    }

    function probTierFromValue(p) {
        if (p == null || p === '') return { label: '—', class: 'none' };
        var n = parseFloat(p);
        if (isNaN(n)) return { label: '—', class: 'none' };
        if (n >= 0.8) return { label: '保', class: 'safe' };
        if (n >= 0.5) return { label: '稳', class: 'steady' };
        return { label: '冲', class: 'reach' };
    }

    function resolveMajorTier(major) {
        if (major.tierClass && major.tierClass !== 'none') {
            return { tierClass: major.tierClass, label: tierLabel(major.tierClass) };
        }
        if (major.probability != null && major.probability !== '') {
            var t = probTierFromValue(major.probability);
            return { tierClass: t.class, label: t.label };
        }
        return { tierClass: 'none', label: '—' };
    }

    function schoolTierFromSchool(school, mode) {
        var best = null;
        var bestProb = null;
        school.groups.forEach(function (g) {
            g.majors.forEach(function (m) {
                var p = m.probability != null && m.probability !== '' ? parseFloat(m.probability) : null;
                if (!best) {
                    best = m;
                    bestProb = p;
                    return;
                }
                if (p != null && !isNaN(p) && (bestProb == null || isNaN(bestProb) || p > bestProb)) {
                    best = m;
                    bestProb = p;
                }
            });
        });
        if (!best) return { tierClass: 'none', pct: '—', label: '—' };
        var tier = resolveMajorTier(best);
        var pct = '—';
        if (mode === 'expert' && best.probability != null && best.probability !== '') {
            pct = formatProb(best.probability);
        } else if (mode === 'strong' && tier.tierClass !== 'none') {
            pct = best.score_status_label || tier.label;
        } else if (best.probability != null && best.probability !== '') {
            pct = formatProb(best.probability);
        }
        return { tierClass: tier.tierClass, pct: pct, label: tier.label };
    }

    function planTierClassName(tierClass) {
        return 'gk-school-tier gk-plan-school-tier gk-school-tier--' + (tierClass || 'none');
    }

    function createSchoolTierBox(school, mode) {
        var info = schoolTierFromSchool(school, mode);
        var box = document.createElement('div');
        box.className = planTierClassName(info.tierClass);
        var pctEl = document.createElement('div');
        pctEl.className = 'gk-school-tier-pct';
        pctEl.textContent = info.pct;
        var labelEl = document.createElement('div');
        labelEl.className = 'gk-school-tier-label';
        labelEl.textContent = info.label;
        box.appendChild(pctEl);
        box.appendChild(labelEl);
        return box;
    }

    function formatProb(p) {
        if (p == null || p === '') return '—';
        var n = parseFloat(p);
        if (isNaN(n)) return '—';
        return Math.round(n * 100) + '%';
    }

    function fmtCode(code) {
        if (code == null || code === '') return '—';
        return String(code);
    }

    function fmtNote(text) {
        if (text == null || text === '') return '—';
        return String(text);
    }

    function lookupCacheKey(batchId, schoolName, groupCode, majorName) {
        return [batchId, schoolName || '', groupCode || '', majorName || ''].join('\u0001');
    }

    function applyMetaToItem(item, meta) {
        if (!meta) return item;
        if (meta.school_code && !item.school_code) item.school_code = meta.school_code;
        if (meta.major_code && !item.major_code) item.major_code = meta.major_code;
        if (meta.group_code && (!item.groupCode || item.groupCode === '—')) {
            item.groupCode = meta.group_code;
        }
        if (meta.duration && !item.duration) item.duration = meta.duration;
        if (meta.tuition && !item.tuition) item.tuition = meta.tuition;
        if (meta.major_note && !item.major_note) item.major_note = meta.major_note;
        if (meta.rank_2025 && !item.rank_2025) item.rank_2025 = meta.rank_2025;
        if (meta.rank_max_2025 && !item.rank_max_2025) item.rank_max_2025 = meta.rank_max_2025;
        return item;
    }

    function enrichItemFromLookup(batchId, item) {
        var key = lookupCacheKey(batchId, item.schoolName, item.groupCode, item.majorName);
        return applyMetaToItem(item, codeLookupCache[key]);
    }

    function collectBatchPreferItems(batchId) {
        var list = [];
        Object.keys(preferStore).forEach(function (storeKey) {
            var parsed = parseStoreKey(storeKey);
            if (!parsed || parsed.dataset !== batchId) return;
            var schoolStore = preferStore[storeKey];
            if (!schoolStore) return;
            Object.keys(schoolStore).forEach(function (preferKey) {
                var item = schoolStore[preferKey];
                if (!item || !item.selected) return;
                list.push({
                    storeKey: storeKey,
                    preferKey: preferKey,
                    school_name: item.schoolName || parsed.schoolName,
                    group_code: item.groupCode || groupCodeFromPreferKey(preferKey),
                    major_name: item.majorName || majorNameFromPreferKey(preferKey)
                });
            });
        });
        return list;
    }

    function fetchBatchLookups(batchId, items, done) {
        if (!planLookupUrl || !items.length) {
            done();
            return;
        }
        var batchCfg = batchConfig(batchId) || {};
        fetch(planLookupUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                dataset: batchCfg.bucket || batchId,
                batch: batchCfg.batch || '',
                province: gaokaoProvince,
                items: items.map(function (it) {
                    return {
                        school_name: it.school_name,
                        group_code: it.group_code,
                        major_name: it.major_name,
                        batch: batchCfg.batch || ''
                    };
                })
            })
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data || !data.ok || !data.results) {
                    done();
                    return;
                }
                data.results.forEach(function (meta, idx) {
                    var ref = items[idx];
                    if (!ref) return;
                    var cacheKey = lookupCacheKey(
                        batchId,
                        ref.school_name,
                        ref.group_code,
                        ref.major_name
                    );
                    codeLookupCache[cacheKey] = meta || {};
                    var store = preferStore[ref.storeKey];
                    if (!store || !store[ref.preferKey]) return;
                    var before = JSON.stringify(store[ref.preferKey]);
                    applyMetaToItem(store[ref.preferKey], meta);
                    if (JSON.stringify(store[ref.preferKey]) !== before) {
                        preferStoreDirty = true;
                    }
                });
                done();
            })
            .catch(function () { done(); });
    }

    function loadAllLookups(done) {
        var jobs = [];
        BATCHES.forEach(function (batch) {
            var items = collectBatchPreferItems(batch.id);
            if (items.length) jobs.push({ batchId: batch.id, items: items });
        });
        if (!jobs.length) {
            done();
            return;
        }
        var left = jobs.length;
        jobs.forEach(function (job) {
            fetchBatchLookups(job.batchId, job.items, function () {
                left -= 1;
                if (left <= 0) {
                    if (preferStoreDirty) {
                        localStorage.setItem(PREFER_STORE_KEY, JSON.stringify(preferStore));
                        preferStoreDirty = false;
                    }
                    done();
                }
            });
        });
    }

    function normalizePreferItem(item, preferKey, parsed, batchId) {
        var base = {
            preferKey: item.preferKey || preferKey,
            schoolName: item.schoolName || parsed.schoolName || '',
            school_code: item.school_code || '',
            groupCode: item.groupCode || groupCodeFromPreferKey(preferKey),
            majorName: item.majorName || majorNameFromPreferKey(preferKey),
            major_code: item.major_code || '',
            duration: item.duration || '',
            tuition: item.tuition || '',
            major_note: item.major_note || '',
            rank_2025: item.rank_2025 || '',
            rank_max_2025: item.rank_max_2025 || '',
            tierClass: item.tierClass || 'none',
            probability: item.probability,
            qualify_score: item.qualify_score || '',
            admit_score: item.admit_score || '',
            score_status_label: item.score_status_label || ''
        };
        return enrichItemFromLookup(batchId, base);
    }

    function buildBatchData(batchId) {
        var schoolsMap = {};
        Object.keys(preferStore).forEach(function (storeKey) {
            var parsed = parseStoreKey(storeKey);
            if (!parsed || parsed.dataset !== batchId) return;
            var schoolStore = preferStore[storeKey];
            if (!schoolStore) return;
            Object.keys(schoolStore).forEach(function (preferKey) {
                var item = schoolStore[preferKey];
                if (!item || !item.selected) return;
                var normalized = normalizePreferItem(item, preferKey, parsed, batchId);
                var schoolName = normalized.schoolName;
                var groupCode = normalized.groupCode || '—';
                if (!schoolsMap[schoolName]) {
                    schoolsMap[schoolName] = {
                        school_name: schoolName,
                        school_code: normalized.school_code || '',
                        groupsMap: {}
                    };
                }
                if (!schoolsMap[schoolName].school_code && normalized.school_code) {
                    schoolsMap[schoolName].school_code = normalized.school_code;
                }
                if (!schoolsMap[schoolName].groupsMap[groupCode]) {
                    schoolsMap[schoolName].groupsMap[groupCode] = {
                        group_code: groupCode,
                        majors: []
                    };
                }
                schoolsMap[schoolName].groupsMap[groupCode].majors.push(normalized);
            });
        });
        return {
            schools: Object.keys(schoolsMap).sort(function (a, b) {
                return a.localeCompare(b, 'zh-CN');
            }).map(function (name) {
                var entry = schoolsMap[name];
                return {
                    school_name: name,
                    school_code: entry.school_code || '',
                    groups: Object.keys(entry.groupsMap).sort(function (a, b) {
                        return a.localeCompare(b, 'zh-CN');
                    }).map(function (gc) {
                        return entry.groupsMap[gc];
                    })
                };
            })
        };
    }

    function ensureBatchOrder(batchId, batchData) {
        if (!planOrder[batchId]) {
            planOrder[batchId] = { schoolOrder: [], groups: {}, collapsed: {}, allExpanded: false };
        }
        var bo = planOrder[batchId];
        if (!bo.collapsed) bo.collapsed = {};
        ensureBatchUi(batchId);
        batchData.schools.forEach(function (school) {
            if (bo.schoolOrder.indexOf(school.school_name) < 0) {
                bo.schoolOrder.push(school.school_name);
            }
            if (!bo.groups[school.school_name]) {
                bo.groups[school.school_name] = { groupOrder: [], majors: {} };
            }
            var go = bo.groups[school.school_name];
            school.groups.forEach(function (group) {
                if (go.groupOrder.indexOf(group.group_code) < 0) {
                    go.groupOrder.push(group.group_code);
                }
                var majorKeys = group.majors.map(function (m) { return m.preferKey; });
                if (!go.majors[group.group_code]) {
                    go.majors[group.group_code] = majorKeys.slice();
                } else {
                    majorKeys.forEach(function (pk) {
                        if (go.majors[group.group_code].indexOf(pk) < 0) {
                            go.majors[group.group_code].push(pk);
                        }
                    });
                    go.majors[group.group_code] = go.majors[group.group_code].filter(function (pk) {
                        return majorKeys.indexOf(pk) >= 0;
                    });
                }
            });
            go.groupOrder = go.groupOrder.filter(function (gc) {
                return school.groups.some(function (g) { return g.group_code === gc; });
            });
        });
        bo.schoolOrder = bo.schoolOrder.filter(function (name) {
            return batchData.schools.some(function (s) { return s.school_name === name; });
        });
    }

    function isSchoolCollapsed(batchId, schoolName) {
        var bo = planOrder[batchId];
        if (bo && bo.collapsed && Object.prototype.hasOwnProperty.call(bo.collapsed, schoolName)) {
            return !!bo.collapsed[schoolName];
        }
        return !isBatchAllExpanded(batchId);
    }

    function toggleSchoolCollapse(batchId, schoolName) {
        if (!planOrder[batchId]) return;
        if (!planOrder[batchId].collapsed) planOrder[batchId].collapsed = {};
        var nowCollapsed = isSchoolCollapsed(batchId, schoolName);
        planOrder[batchId].collapsed[schoolName] = !nowCollapsed;
        saveOrder();
        renderPlan();
    }

    function applyMajorOrder(group, go) {
        var majorMap = {};
        group.majors.forEach(function (m) { majorMap[m.preferKey] = m; });
        var orderList = (go && go.majors && go.majors[group.group_code]) || [];
        var ordered = [];
        orderList.forEach(function (pk) {
            if (majorMap[pk]) ordered.push(majorMap[pk]);
        });
        group.majors.forEach(function (m) {
            if (orderList.indexOf(m.preferKey) < 0) ordered.push(m);
        });
        return { group_code: group.group_code, majors: ordered };
    }

    function applyBatchOrder(batchId, batchData) {
        var bo = planOrder[batchId];
        var schoolMap = {};
        batchData.schools.forEach(function (s) { schoolMap[s.school_name] = s; });
        var orderedSchools = [];
        bo.schoolOrder.forEach(function (name) {
            var school = schoolMap[name];
            if (!school) return;
            var go = bo.groups[name] || { groupOrder: [], majors: {} };
            var groupMap = {};
            school.groups.forEach(function (g) { groupMap[g.group_code] = g; });
            var orderedGroups = [];
            go.groupOrder.forEach(function (gc) {
                if (groupMap[gc]) orderedGroups.push(applyMajorOrder(groupMap[gc], go));
            });
            school.groups.forEach(function (g) {
                if (go.groupOrder.indexOf(g.group_code) < 0) {
                    orderedGroups.push(applyMajorOrder(g, go));
                }
            });
            orderedSchools.push({
                school_name: name,
                school_code: school.school_code || '',
                groups: orderedGroups
            });
        });
        batchData.schools.forEach(function (school) {
            if (bo.schoolOrder.indexOf(school.school_name) < 0) {
                var go = bo.groups[school.school_name] || { groupOrder: [], majors: {} };
                orderedSchools.push({
                    school_name: school.school_name,
                    school_code: school.school_code || '',
                    groups: school.groups.map(function (g) { return applyMajorOrder(g, go); })
                });
            }
        });
        return orderedSchools;
    }

    function hasAnyPrefers() {
        var found = false;
        Object.keys(preferStore).some(function (key) {
            var store = preferStore[key];
            if (!store) return false;
            return Object.keys(store).some(function (pk) {
                if (store[pk] && store[pk].selected) {
                    found = true;
                    return true;
                }
                return false;
            });
        });
        return found;
    }

    function slideSortFlowChildren(listEl, dragEl) {
        return Array.from(listEl.children).filter(function (c) {
            return c !== dragEl;
        });
    }

    function slideSortComputeIndex(listEl, dragEl, clientY) {
        var nodes = slideSortFlowChildren(listEl, dragEl);
        for (var i = 0; i < nodes.length; i++) {
            var rect = nodes[i].getBoundingClientRect();
            if (clientY < rect.top + rect.height / 2) return i;
        }
        return nodes.length;
    }

    function slideSortFlip(listEl, dragEl, mutate) {
        var items = slideSortFlowChildren(listEl, dragEl).filter(function (n) {
            return !n.classList.contains('gk-plan-sort-placeholder');
        });
        var tops = new Map();
        items.forEach(function (el) {
            tops.set(el, el.getBoundingClientRect().top);
        });
        mutate();
        items.forEach(function (el) {
            if (!el.isConnected || !tops.has(el)) return;
            var delta = tops.get(el) - el.getBoundingClientRect().top;
            if (Math.abs(delta) < 0.5) return;
            el.style.transition = 'none';
            el.style.transform = 'translateY(' + delta + 'px)';
            el.offsetHeight;
            el.classList.add('gk-plan-sort-sliding');
            el.style.transition = '';
            requestAnimationFrame(function () {
                el.style.transform = '';
            });
            el.addEventListener('transitionend', function onSlideEnd(ev) {
                if (ev.propertyName !== 'transform') return;
                el.removeEventListener('transitionend', onSlideEnd);
                el.classList.remove('gk-plan-sort-sliding');
                el.style.transition = '';
                el.style.transform = '';
            });
        });
    }

    function slideSortMovePlaceholder(state, insertIndex) {
        if (state.insertIndex === insertIndex) return;
        state.insertIndex = insertIndex;
        slideSortFlip(state.listEl, state.dragEl, function () {
            var nodes = slideSortFlowChildren(state.listEl, state.dragEl);
            if (insertIndex >= nodes.length) {
                state.listEl.appendChild(state.placeholder);
            } else {
                var ref = nodes[insertIndex];
                if (ref !== state.placeholder) {
                    state.listEl.insertBefore(state.placeholder, ref);
                }
            }
        });
    }

    function slideSortOnMove(e) {
        if (!slideSortState) return;
        var s = slideSortState;
        s.ghost.style.left = (e.clientX - s.offsetX) + 'px';
        s.ghost.style.top = (e.clientY - s.offsetY) + 'px';
        slideSortMovePlaceholder(s, slideSortComputeIndex(s.listEl, s.dragEl, e.clientY));
    }

    function slideSortCleanup(state, commit) {
        document.removeEventListener('pointermove', slideSortOnMove);
        document.removeEventListener('pointerup', slideSortOnEnd);
        document.removeEventListener('pointercancel', slideSortOnEnd);
        document.body.classList.remove('gk-plan-sort-active');
        if (state.ghost && state.ghost.parentNode) state.ghost.parentNode.removeChild(state.ghost);
        if (state.placeholder && state.placeholder.parentNode) {
            if (commit) state.listEl.insertBefore(state.dragEl, state.placeholder);
            state.placeholder.parentNode.removeChild(state.placeholder);
        }
        state.dragEl.style.display = '';
        state.dragEl.classList.remove('gk-plan-drag-source');
        state.listEl.querySelectorAll('.gk-plan-sort-sliding').forEach(function (el) {
            el.classList.remove('gk-plan-sort-sliding');
            el.style.transform = '';
        });
        if (commit && state.onCommit) state.onCommit(state);
        else if (!commit) renderPlan();
        slideSortState = null;
    }

    function slideSortOnEnd() {
        if (!slideSortState) return;
        slideSortCleanup(slideSortState, true);
    }

    function beginSlideSort(e, dragEl, config) {
        if (slideSortState) return;
        if (e.button !== 0) return;
        var listEl = config.getListEl ? config.getListEl(dragEl) : null;
        if (!listEl) return;

        var rect = dragEl.getBoundingClientRect();
        var placeholder = config.createPlaceholder
            ? config.createPlaceholder(dragEl, rect)
            : (function () {
                var ph = document.createElement('div');
                ph.className = 'gk-plan-sort-placeholder';
                ph.style.height = rect.height + 'px';
                return ph;
            })();

        var ghost = config.createGhost
            ? config.createGhost(dragEl, rect)
            : (function () {
                var g = dragEl.cloneNode(true);
                g.className = 'gk-plan-sort-ghost';
                g.style.width = rect.width + 'px';
                return g;
            })();
        ghost.style.left = rect.left + 'px';
        ghost.style.top = rect.top + 'px';
        document.body.appendChild(ghost);

        var dragIndex = Array.from(listEl.children).indexOf(dragEl);
        listEl.insertBefore(placeholder, dragEl);
        dragEl.classList.add('gk-plan-drag-source');
        dragEl.style.display = 'none';

        slideSortState = {
            dragEl: dragEl,
            listEl: listEl,
            placeholder: placeholder,
            ghost: ghost,
            offsetX: e.clientX - rect.left,
            offsetY: e.clientY - rect.top,
            insertIndex: dragIndex,
            dragIndex: dragIndex,
            onCommit: config.onCommit
        };

        document.body.classList.add('gk-plan-sort-active');
        document.addEventListener('pointermove', slideSortOnMove);
        document.addEventListener('pointerup', slideSortOnEnd);
        document.addEventListener('pointercancel', slideSortOnEnd);
        e.preventDefault();
    }

    function clearPendingSlideSort() {
        document.removeEventListener('pointermove', onPendingSlideSortMove);
        document.removeEventListener('pointerup', onPendingSlideSortEnd);
        document.removeEventListener('pointercancel', onPendingSlideSortEnd);
        pendingSlideSort = null;
    }

    function onPendingSlideSortMove(e) {
        if (!pendingSlideSort || pendingSlideSort.started) return;
        var dx = e.clientX - pendingSlideSort.startX;
        var dy = e.clientY - pendingSlideSort.startY;
        if (Math.sqrt(dx * dx + dy * dy) < SLIDE_SORT_DRAG_THRESHOLD) return;
        pendingSlideSort.started = true;
        var cfg = pendingSlideSort.config;
        var dragEl = pendingSlideSort.dragEl;
        clearPendingSlideSort();
        beginSlideSort(e, dragEl, cfg);
        slideSortOnMove(e);
    }

    function onPendingSlideSortEnd(e) {
        if (!pendingSlideSort) return;
        var cfg = pendingSlideSort.config;
        var started = pendingSlideSort.started;
        clearPendingSlideSort();
        if (!started && cfg.onTap) cfg.onTap(e);
    }

    function startPendingSlideSort(e, dragEl, config) {
        if (slideSortState || pendingSlideSort) return;
        pendingSlideSort = {
            dragEl: dragEl,
            config: config,
            startX: e.clientX,
            startY: e.clientY,
            started: false
        };
        document.addEventListener('pointermove', onPendingSlideSortMove);
        document.addEventListener('pointerup', onPendingSlideSortEnd);
        document.addEventListener('pointercancel', onPendingSlideSortEnd);
    }

    function attachSlideSortPointer(triggerEl, dragEl, config) {
        triggerEl.addEventListener('pointerdown', function (e) {
            if (config.canStart && !config.canStart(e)) return;
            if (e.button !== 0) return;
            if (config.onTap) {
                startPendingSlideSort(e, dragEl, config);
                return;
            }
            beginSlideSort(e, dragEl, config);
        });
    }

    function slideSortPlaceholderRow(dragEl, rect) {
        var tr = document.createElement('tr');
        tr.className = 'gk-plan-sort-placeholder gk-plan-sort-placeholder--row';
        var td = document.createElement('td');
        td.colSpan = 20;
        td.style.height = Math.max(rect.height, 36) + 'px';
        tr.appendChild(td);
        return tr;
    }

    function slideSortGhostRow(dragEl, rect) {
        var wrap = document.createElement('div');
        wrap.className = 'gk-plan-sort-ghost gk-plan-sort-ghost--row';
        wrap.style.width = rect.width + 'px';
        var table = document.createElement('table');
        table.className = 'gk-plan-table';
        table.appendChild(dragEl.cloneNode(true));
        wrap.appendChild(table);
        return wrap;
    }

    function syncSchoolOrderFromDom(batchId, listEl) {
        var bo = planOrder[batchId];
        if (!bo || !listEl) return;
        var order = [];
        listEl.querySelectorAll(':scope > .gk-plan-school').forEach(function (el, index) {
            order.push(el.getAttribute('data-school'));
            el.setAttribute('data-school-index', String(index));
            var idxEl = el.querySelector('.gk-plan-school-index');
            if (idxEl) idxEl.textContent = String(index + 1);
        });
        bo.schoolOrder = order.filter(function (name) { return !!name; });
        saveOrder();
    }

    function syncGroupOrderFromDom(batchId, schoolName, listEl) {
        var go = planOrder[batchId] && planOrder[batchId].groups[schoolName];
        if (!go || !listEl) return;
        var order = [];
        listEl.querySelectorAll(':scope > .gk-plan-group').forEach(function (el, index) {
            order.push(el.getAttribute('data-group-code'));
            el.setAttribute('data-group-index', String(index));
        });
        go.groupOrder = order.filter(function (code) { return code != null; });
        saveOrder();
    }

    function syncMajorOrderFromDom(batchId, schoolName, groupCode, tbody) {
        var go = planOrder[batchId] && planOrder[batchId].groups[schoolName];
        if (!go || !tbody) return;
        var order = [];
        tbody.querySelectorAll(':scope > .gk-plan-major-row').forEach(function (tr, index) {
            var pk = tr.getAttribute('data-prefer-key');
            if (pk) order.push(pk);
            tr.setAttribute('data-major-index', String(index));
            var idxTd = tr.querySelector('.gk-plan-td-index');
            if (idxTd) idxTd.textContent = String(index + 1);
        });
        go.majors[groupCode] = order;
        saveOrder();
    }

    function createDragHandle(label) {
        var handle = document.createElement('span');
        handle.className = 'gk-plan-drag-handle no-print';
        handle.classList.add('gk-plan-drag-handle--static');
        handle.setAttribute('aria-label', label || '拖动排序');
        handle.title = label || '拖动排序';
        handle.textContent = '⠿';
        return handle;
    }

    function createCodeBadge(code, title) {
        var span = document.createElement('span');
        span.className = 'gk-plan-code';
        if (title) span.title = title;
        span.textContent = fmtCode(code);
        return span;
    }

    function schoolDragBlockedTarget(target) {
        return !!(target && target.closest &&
            target.closest('button, a, input, textarea, select, .gk-plan-table, .gk-plan-major-row'));
    }

    function renderBasicInfo() {
        if (!basicGrid) return;
        basicGrid.innerHTML = '';
        BASIC_FIELDS.forEach(function (field) {
            var item = document.createElement('div');
            item.className = 'gk-plan-basic-item';
            var label = document.createElement('span');
            label.className = 'gk-plan-basic-label';
            label.textContent = field.label;
            var value = document.createElement('span');
            value.className = 'gk-plan-basic-value';
            value.textContent = profileValue(field);
            item.appendChild(label);
            item.appendChild(value);
            basicGrid.appendChild(item);
        });
        var stamp = document.createElement('div');
        stamp.className = 'gk-plan-basic-item gk-plan-basic-item--stamp';
        stamp.innerHTML = '<span class="gk-plan-basic-label">生成时间</span><span class="gk-plan-basic-value">' +
            new Date().toLocaleString('zh-CN', { hour12: false }) + '</span>';
        basicGrid.appendChild(stamp);
    }

    function renderMajorRows(group, batchId, schoolName, mode) {
        var tbody = document.createElement('tbody');
        group.majors.forEach(function (major, majorIndex) {
            var tr = document.createElement('tr');
            tr.className = 'gk-plan-major-row';
            tr.setAttribute('data-prefer-key', major.preferKey || '');
            tr.setAttribute('data-major-index', String(majorIndex));

            var dragTd = document.createElement('td');
            dragTd.className = 'gk-plan-td-drag no-print';
            var majorHandle = createDragHandle('拖动专业排序');
            majorHandle.setAttribute('data-drag-level', 'major');
            majorHandle.setAttribute('data-batch', batchId);
            majorHandle.setAttribute('data-school', schoolName);
            majorHandle.setAttribute('data-group', group.group_code || '');
            majorHandle.setAttribute('data-prefer-key', major.preferKey || '');
            dragTd.appendChild(majorHandle);
            tr.appendChild(dragTd);

            var idxTd = document.createElement('td');
            idxTd.className = 'gk-plan-td-index';
            idxTd.textContent = String(majorIndex + 1);
            tr.appendChild(idxTd);

            if (mode === 'expert') {
                var codeTd = document.createElement('td');
                codeTd.className = 'gk-plan-td-code';
                codeTd.textContent = fmtCode(major.major_code);
                tr.appendChild(codeTd);
            }

            var majorTd = document.createElement('td');
            majorTd.className = 'gk-plan-td-major';
            majorTd.textContent = major.majorName || '—';
            tr.appendChild(majorTd);

            var durTd = document.createElement('td');
            durTd.className = 'gk-plan-td-num';
            durTd.textContent = fmtCode(major.duration);
            tr.appendChild(durTd);

            var tuitionTd = document.createElement('td');
            tuitionTd.className = 'gk-plan-td-num';
            tuitionTd.textContent = fmtCode(major.tuition);
            tr.appendChild(tuitionTd);

            var noteTd = document.createElement('td');
            noteTd.className = 'gk-plan-td-note';
            noteTd.textContent = fmtNote(major.major_note);
            if (major.major_note) noteTd.title = String(major.major_note);
            tr.appendChild(noteTd);

            var rankMinTd = document.createElement('td');
            rankMinTd.className = 'gk-plan-td-num';
            rankMinTd.textContent = fmtCode(major.rank_2025);
            tr.appendChild(rankMinTd);

            var rankMaxTd = document.createElement('td');
            rankMaxTd.className = 'gk-plan-td-num';
            rankMaxTd.textContent = fmtCode(major.rank_max_2025);
            tr.appendChild(rankMaxTd);

            if (mode === 'expert') {
                var probTd = document.createElement('td');
                probTd.className = 'gk-plan-td-num';
                probTd.textContent = formatProb(major.probability);
                tr.appendChild(probTd);

                var tierTd = document.createElement('td');
                var badge = document.createElement('span');
                badge.className = 'gk-plan-tier gk-plan-tier--' + (major.tierClass || 'none');
                badge.textContent = tierLabel(major.tierClass);
                tierTd.appendChild(badge);
                tr.appendChild(tierTd);
            } else {
                var qTd = document.createElement('td');
                qTd.className = 'gk-plan-td-num';
                qTd.textContent = major.qualify_score || '—';
                tr.appendChild(qTd);

                var aTd = document.createElement('td');
                aTd.className = 'gk-plan-td-num';
                aTd.textContent = major.admit_score || '—';
                tr.appendChild(aTd);

                var stTd = document.createElement('td');
                if (major.score_status_label) {
                    var stBadge = document.createElement('span');
                    stBadge.className = 'gk-plan-tier gk-plan-tier--' + (major.tierClass || 'none');
                    stBadge.textContent = major.score_status_label;
                    stTd.appendChild(stBadge);
                } else {
                    stTd.textContent = '—';
                }
                tr.appendChild(stTd);
            }

            attachSlideSortPointer(majorHandle, tr, {
                getListEl: function () { return tbody; },
                createPlaceholder: slideSortPlaceholderRow,
                createGhost: slideSortGhostRow,
                onCommit: function () {
                    syncMajorOrderFromDom(batchId, schoolName, group.group_code, tbody);
                }
            });

            tbody.appendChild(tr);
        });
        return tbody;
    }

    function renderGroupBlock(group, batchId, schoolName, groupIndex, mode) {
        var block = document.createElement('div');
        block.className = 'gk-plan-group';
        block.setAttribute('data-group-code', group.group_code || '');
        block.setAttribute('data-group-index', String(groupIndex));

        var head = document.createElement('div');
        head.className = 'gk-plan-group-head';

        var groupHandle = createDragHandle('拖动专业组排序');
        groupHandle.setAttribute('data-drag-level', 'group');
        head.appendChild(groupHandle);

        var title = document.createElement('div');
        title.className = 'gk-plan-group-title';
        if (mode === 'strong' && group.group_code === '强基') {
            title.appendChild(document.createTextNode('强基专业 '));
            title.appendChild(createCodeBadge(group.group_code, '专业组代码'));
        } else {
            title.appendChild(document.createTextNode('专业组 '));
            title.appendChild(createCodeBadge(group.group_code, '专业组代码'));
        }
        head.appendChild(title);
        block.appendChild(head);

        attachSlideSortPointer(head, block, {
            getListEl: function () { return block.parentElement; },
            canStart: function (e) {
                return !e.target.closest('.gk-plan-table, .gk-plan-major-row, button, a, input, textarea, select');
            },
            onCommit: function (state) {
                syncGroupOrderFromDom(batchId, schoolName, state.listEl);
            }
        });

        var tableWrap = document.createElement('div');
        tableWrap.className = 'gk-plan-table-wrap';
        var table = document.createElement('table');
        table.className = 'gk-plan-table gk-plan-table--' + (mode === 'strong' ? 'strong' : 'expert');
        var thead = document.createElement('thead');
        var hr = document.createElement('tr');
        var headers = mode === 'strong'
            ? ['', '序号', '专业名称', '学制', '学费', '专业备注', '25最低位次', '25最高位次', '入围分', '录取分', '对比']
            : ['', '序号', '专业代码', '专业名称', '学制', '学费', '专业备注', '25最低位次', '25最高位次', '概率', '档位'];
        headers.forEach(function (label, i) {
            var th = document.createElement('th');
            th.textContent = label;
            if (i === 0) th.className = 'gk-plan-th-drag no-print';
            if (i === 1) th.className = 'gk-plan-th-index';
            if (label === '专业名称') th.className = 'gk-plan-th-major';
            if (label === '专业备注') th.className = 'gk-plan-th-note';
            thead.appendChild(th);
        });
        table.appendChild(thead);
        table.appendChild(renderMajorRows(group, batchId, schoolName, mode));
        tableWrap.appendChild(table);
        block.appendChild(tableWrap);
        return block;
    }

    function renderSchoolBlock(school, batchId, schoolIndex, mode) {
        var block = document.createElement('article');
        block.className = 'gk-plan-school';
        block.setAttribute('data-school', school.school_name || '');
        block.setAttribute('data-school-index', String(schoolIndex));

        var collapsed = isSchoolCollapsed(batchId, school.school_name);

        var head = document.createElement('div');
        head.className = 'gk-plan-school-head';
        head.setAttribute('role', 'button');
        head.setAttribute('tabindex', '0');
        head.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        head.title = collapsed ? '单击展开，拖动排序' : '单击收起，拖动排序';

        head.appendChild(createSchoolTierBox(school, mode));

        var indexEl = document.createElement('span');
        indexEl.className = 'gk-plan-school-index';
        indexEl.textContent = String(schoolIndex + 1);
        head.appendChild(indexEl);

        var titleWrap = document.createElement('div');
        titleWrap.className = 'gk-plan-school-title-wrap';
        var title = document.createElement('h3');
        title.className = 'gk-plan-school-name';
        title.textContent = school.school_name || '—';
        titleWrap.appendChild(title);
        var codeBadge = createCodeBadge(school.school_code, '院校代码');
        codeBadge.classList.add('gk-plan-code--school');
        titleWrap.appendChild(codeBadge);
        head.appendChild(titleWrap);

        var expandHint = document.createElement('span');
        expandHint.className = 'gk-plan-expand-hint no-print';
        expandHint.textContent = collapsed ? '▸' : '▾';
        expandHint.setAttribute('aria-hidden', 'true');
        head.appendChild(expandHint);
        block.appendChild(head);

        function toggleSchoolExpand() {
            toggleSchoolCollapse(batchId, school.school_name);
        }

        head.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggleSchoolExpand();
            }
        });

        attachSlideSortPointer(head, block, {
            getListEl: function () { return block.closest('.gk-plan-school-list'); },
            canStart: function (e) {
                if (schoolDragBlockedTarget(e.target)) return false;
                if (e.target.closest('.gk-plan-school-body')) return false;
                return true;
            },
            onTap: function () {
                toggleSchoolExpand();
            },
            onCommit: function (state) {
                syncSchoolOrderFromDom(batchId, state.listEl);
            }
        });

        var body = document.createElement('div');
        body.className = 'gk-plan-school-body';
        if (collapsed) body.hidden = true;

        school.groups.forEach(function (group, groupIndex) {
            body.appendChild(renderGroupBlock(
                group,
                batchId,
                school.school_name,
                groupIndex,
                mode
            ));
        });
        block.appendChild(body);
        return block;
    }

    function renderBatchSection(batch, schools) {
        if (!schools.length) return null;
        var section = document.createElement('section');
        section.className = 'gk-plan-section gk-plan-section--batch';
        section.setAttribute('data-batch', batch.id);

        var headRow = document.createElement('div');
        headRow.className = 'gk-plan-section-head';

        var title = document.createElement('h2');
        title.className = 'gk-plan-section-title';
        title.textContent = batch.label;

        var toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.className = 'gk-plan-batch-toggle-btn no-print';
        toggleBtn.setAttribute('data-batch', batch.id);
        syncBatchToggleBtn(toggleBtn, batch.id);
        toggleBtn.addEventListener('click', function () {
            setBatchSchoolsExpanded(batch.id, !isBatchAllExpanded(batch.id));
        });

        headRow.appendChild(title);
        headRow.appendChild(toggleBtn);
        section.appendChild(headRow);

        var list = document.createElement('div');
        list.className = 'gk-plan-school-list';
        schools.forEach(function (school, schoolIndex) {
            list.appendChild(renderSchoolBlock(
                school,
                batch.id,
                schoolIndex,
                batch.mode
            ));
        });
        section.appendChild(list);
        return section;
    }

    function renderPlan() {
        if (!batchHost) return;
        batchHost.innerHTML = '';
        var hasBatch = false;

        BATCHES.forEach(function (batch) {
            var batchData = buildBatchData(batch.id);
            if (!batchData.schools.length) return;
            ensureBatchOrder(batch.id, batchData);
            var orderedSchools = applyBatchOrder(batch.id, batchData);
            var section = renderBatchSection(batch, orderedSchools);
            if (section) {
                batchHost.appendChild(section);
                hasBatch = true;
            }
        });

        saveOrder();

        if (!hasBatch) {
            if (planBody) planBody.hidden = true;
            if (planEmpty) planEmpty.hidden = false;
            if (basicSection) basicSection.hidden = true;
            return;
        }

        if (planBody) planBody.hidden = false;
        if (planEmpty) planEmpty.hidden = true;
        if (basicSection) basicSection.hidden = false;
        renderBasicInfo();
        syncPrintHead();
    }

    var savedDocumentTitle = '';

    if (printBtn) {
        printBtn.addEventListener('click', function () {
            expandAllForPrint();
            requestAnimationFrame(function () {
                requestAnimationFrame(function () {
                    window.print();
                });
            });
        });
    }

    var printSnapshot = null;
    var printPrepActive = false;

    function expandAllForPrint() {
        if (printPrepActive) return;
        printPrepActive = true;
        printSnapshot = JSON.parse(JSON.stringify(planOrder));
        BATCHES.forEach(function (b) {
            if (!planOrder[b.id]) return;
            planOrder[b.id].allExpanded = true;
            planOrder[b.id].collapsed = {};
        });
        document.body.classList.add('gk-plan-print-prep');
        renderPlan();
        savedDocumentTitle = document.title;
        document.title = planPrintTitleText();
    }

    function restoreAfterPrint() {
        if (!printPrepActive) return;
        printPrepActive = false;
        document.body.classList.remove('gk-plan-print-prep');
        if (savedDocumentTitle) {
            document.title = savedDocumentTitle;
            savedDocumentTitle = '';
        }
        if (printSnapshot) {
            planOrder = printSnapshot;
            printSnapshot = null;
            saveOrder();
        }
        renderPlan();
    }

    window.addEventListener('beforeprint', expandAllForPrint);
    window.addEventListener('afterprint', restoreAfterPrint);

    loadProfile();
    loadPreferStore();
    loadOrder();
    ensurePlanUi();
    syncPrintHead();

    if (!hasAnyPrefers()) {
        if (planBody) planBody.hidden = true;
        if (planEmpty) planEmpty.hidden = false;
        if (basicSection) basicSection.hidden = true;
    } else {
        loadAllLookups(function () {
            renderPlan();
        });
    }
})();
