(function () {
    var form = document.getElementById('gaokaoCareerForm');
    if (!form) return;

    var user = form.getAttribute('data-user') || 'default';
    var storageKey = 'gaokao_career_draft_' + user;

    var flushSlotsToStore = null;

    function collect() {
        if (flushSlotsToStore) flushSlotsToStore();
        var data = {};
        form.querySelectorAll('[data-field]').forEach(function (el) {
            var key = el.getAttribute('data-field');
            if (!key) return;
            if (el.type === 'checkbox') {
                data[key] = el.checked;
            } else {
                data[key] = el.value;
            }
        });
        return data;
    }

    function apply(data) {
        if (!data) return;
        form.querySelectorAll('[data-field]').forEach(function (el) {
            var key = el.getAttribute('data-field');
            if (data[key] === undefined) return;
            if (el.type === 'checkbox') {
                el.checked = !!data[key];
            } else {
                el.value = data[key];
            }
        });
    }

    function save() {
        try {
            localStorage.setItem(storageKey, JSON.stringify(collect()));
            alert('草稿已保存到本浏览器（' + user + '）');
        } catch (e) {
            alert('保存失败：' + (e.message || e));
        }
    }

    var selectedMajorGroups = {};
    var selectedMajorItems = {};
    var majorGroupsHidden = document.getElementById('majorGroupsHidden');
    var majorItemsHidden = document.getElementById('majorItemsHidden');
    var majorSection = document.getElementById('gcMajorSection');

    var selectedEarlyGroups = {};
    var selectedEarlySchools = {};
    var earlyGroupsHidden = document.getElementById('earlyGroupsHidden');
    var earlySchoolsHidden = document.getElementById('earlySchoolsHidden');
    var earlySection = document.getElementById('gcEarlySection');

    function syncEarlySchoolsHidden() {
        if (!earlySchoolsHidden) return;
        earlySchoolsHidden.value = Object.keys(selectedEarlySchools).filter(function (id) {
            return selectedEarlySchools[id];
        }).join(',');
    }

    function syncEarlyGroupsHidden() {
        if (!earlyGroupsHidden) return;
        earlyGroupsHidden.value = Object.keys(selectedEarlyGroups).filter(function (id) {
            return selectedEarlyGroups[id];
        }).join(',');
    }

    function updateTimelineVisibility() {
        var timelineSection = document.getElementById('gcTimelineSection');
        if (!timelineSection) return;
        timelineSection.querySelectorAll('[data-timeline-for]').forEach(function (el) {
            if (timelineShowAll) {
                el.hidden = false;
                return;
            }
            var refs = (el.getAttribute('data-timeline-for') || '').split(',');
            var show = refs.some(function (id) {
                id = id.trim();
                return id && selectedEarlyGroups[id];
            });
            el.hidden = !show;
        });
    }

    var timelineShowAll = false;
    var timelineShowAllHidden = document.getElementById('timelineShowAllHidden');
    var btnTimelineShowAll = document.getElementById('btnTimelineShowAll');

    function setTimelineShowAll(on) {
        timelineShowAll = !!on;
        if (timelineShowAllHidden) {
            timelineShowAllHidden.value = timelineShowAll ? '1' : '0';
        }
        if (btnTimelineShowAll) {
            btnTimelineShowAll.setAttribute('aria-pressed', timelineShowAll ? 'true' : 'false');
        }
        updateTimelineVisibility();
    }

    function restoreTimelineShowAllFromDraft(data) {
        if (!data || data.timeline_show_all === undefined) {
            setTimelineShowAll(false);
            return;
        }
        var v = data.timeline_show_all;
        setTimelineShowAll(v === true || v === '1' || v === 1);
    }

    if (btnTimelineShowAll) {
        btnTimelineShowAll.addEventListener('click', function () {
            setTimelineShowAll(!timelineShowAll);
            try {
                localStorage.setItem(storageKey, JSON.stringify(collect()));
            } catch (e) { /* ignore */ }
        });
    }

    function updateEarlyPanels() {
        if (!earlySection) return;
        earlySection.querySelectorAll('[data-early-panel]').forEach(function (panel) {
            var id = panel.getAttribute('data-early-panel');
            panel.hidden = !selectedEarlyGroups[id];
        });
        earlySection.querySelectorAll('[data-early-group]').forEach(function (btn) {
            var id = btn.getAttribute('data-early-group');
            btn.classList.toggle('gc-major-btn--on', !!selectedEarlyGroups[id]);
        });
        earlySection.querySelectorAll('[data-early-school]').forEach(function (btn) {
            var id = btn.getAttribute('data-early-school');
            btn.classList.toggle('gc-major-btn--on', !!selectedEarlySchools[id]);
        });
        syncEarlyPrintTags();
        updateTimelineVisibility();
    }

    function restoreEarlyGroupsFromHidden() {
        selectedEarlyGroups = {};
        selectedEarlySchools = {};
        var raw = earlyGroupsHidden ? earlyGroupsHidden.value : '';
        if (raw) {
            raw.split(',').forEach(function (id) {
                id = id.trim();
                if (id) selectedEarlyGroups[id] = true;
            });
        }
        var rawSchools = earlySchoolsHidden ? earlySchoolsHidden.value : '';
        if (rawSchools) {
            rawSchools.split(',').forEach(function (id) {
                id = id.trim();
                if (id) selectedEarlySchools[id] = true;
            });
        }
        updateEarlyPanels();
    }

    function syncMajorItemsHidden() {
        if (!majorItemsHidden) return;
        majorItemsHidden.value = Object.keys(selectedMajorItems).filter(function (id) {
            return selectedMajorItems[id];
        }).join(',');
    }

    function syncMajorGroupsHidden() {
        if (!majorGroupsHidden) return;
        var ids = Object.keys(selectedMajorGroups).filter(function (id) {
            return selectedMajorGroups[id];
        });
        majorGroupsHidden.value = ids.join(',');
    }

    function updateMajorPanels() {
        form.querySelectorAll('[data-major-panel]').forEach(function (panel) {
            var id = panel.getAttribute('data-major-panel');
            panel.hidden = !selectedMajorGroups[id];
        });
        if (majorSection) {
            majorSection.querySelectorAll('[data-major-group]').forEach(function (btn) {
                var id = btn.getAttribute('data-major-group');
                btn.classList.toggle('gc-major-btn--on', !!selectedMajorGroups[id]);
            });
            majorSection.querySelectorAll('[data-major-item]').forEach(function (btn) {
                var id = btn.getAttribute('data-major-item');
                btn.classList.toggle('gc-major-btn--on', !!selectedMajorItems[id]);
            });
        }
        syncMajorPrintTags();
    }

    function restoreMajorGroupsFromHidden() {
        selectedMajorGroups = {};
        selectedMajorItems = {};
        var raw = majorGroupsHidden ? majorGroupsHidden.value : '';
        if (raw) {
            raw.split(',').forEach(function (id) {
                id = id.trim();
                if (id) selectedMajorGroups[id] = true;
            });
        }
        var rawItems = majorItemsHidden ? majorItemsHidden.value : '';
        if (rawItems) {
            rawItems.split(',').forEach(function (id) {
                id = id.trim();
                if (id) selectedMajorItems[id] = true;
            });
        }
        updateMajorPanels();
    }

    var LEGACY_CAT_ID = {
        '1': '01', '2': '02', '3': '03', '4': '04', '5': '05', '6': '06', '7': '07',
        '8': '09', '9': '10', '10': '12', '11': '13'
    };

    function migrateLegacyMajorDraft(data) {
        if (!data || !majorGroupsHidden) return;
        var raw = data.major_selected_groups ? String(data.major_selected_groups).trim() : '';
        if (!raw) return;
        var mapped = raw.split(',').map(function (id) {
            id = id.trim();
            if (!id || id === 'engineering') return '';
            if (/^cat_/.test(id)) return id;
            var m = /^cat_(\d+)$/.exec(id);
            if (m && LEGACY_CAT_ID[m[1]]) return 'cat_' + LEGACY_CAT_ID[m[1]];
            if (/^\d{2}$/.test(id)) return 'cat_' + id;
            if (/^eng_/.test(id)) return 'cat_' + id.replace(/^eng_/, '');
            return id;
        }).filter(Boolean);
        if (mapped.length) {
            majorGroupsHidden.value = mapped.join(',');
            data.major_selected_groups = majorGroupsHidden.value;
        }
    }

    function migrateLegacyEarlyDraft(data) {
        if (!data) return;
        if (data.early_selected_groups && String(data.early_selected_groups).trim()) return;
        var ids = [];
        Object.keys(data).forEach(function (key) {
            var m = /^early_(\d+)$/.exec(key);
            if (m && data[key] === true) ids.push('early_' + m[1]);
        });
        if (ids.length && earlyGroupsHidden) {
            earlyGroupsHidden.value = ids.join(',');
            data.early_selected_groups = earlyGroupsHidden.value;
        }
    }

    try {
        var raw = localStorage.getItem(storageKey);
        if (raw) {
            var draft = JSON.parse(raw);
            migrateLegacyMajorDraft(draft);
            migrateLegacyEarlyDraft(draft);
            apply(draft);
            restoreTimelineShowAllFromDraft(draft);
        } else {
            setTimelineShowAll(false);
        }
    } catch (e) {
        setTimelineShowAll(false);
    }
    restoreMajorGroupsFromHidden();
    restoreEarlyGroupsFromHidden();
    preparePrintTags(document.getElementById('earlyGroupBtns'), '.gc-major-btn[data-early-group]');
    syncEarlyPrintTags();
    prepareAllMajorCatPrintTags();
    syncMajorPrintTags();

    var btn = document.getElementById('gcSaveDraft');
    if (btn) btn.addEventListener('click', save);

    function initProvinceCombobox() {
        var wrap = document.getElementById('gaokaoProvinceCombo');
        if (!wrap) return;
        var input = wrap.querySelector('.gc-combobox-input');
        var listbox = document.getElementById('gaokaoProvinceListbox');
        var toggle = document.getElementById('gaokaoProvinceToggle');
        if (!input || !listbox) return;

        var options = Array.prototype.slice.call(listbox.querySelectorAll('li[role="option"]'));
        var activeIndex = -1;

        function openList() {
            listbox.hidden = false;
            input.setAttribute('aria-expanded', 'true');
            filterList(input.value.trim());
        }

        function closeList() {
            listbox.hidden = true;
            input.setAttribute('aria-expanded', 'false');
            activeIndex = -1;
            options.forEach(function (li) {
                li.classList.remove('gc-combobox-option--active');
            });
        }

        function filterList(q) {
            var lower = q.toLowerCase();
            var visible = 0;
            options.forEach(function (li) {
                var val = li.getAttribute('data-value') || '';
                var text = (li.textContent || '').trim();
                var match = !q
                    || text.indexOf(q) >= 0
                    || val.indexOf(q) >= 0
                    || text.toLowerCase().indexOf(lower) >= 0
                    || val.toLowerCase().indexOf(lower) >= 0;
                li.classList.toggle('gc-combobox-option--hidden', !match);
                if (match) visible += 1;
            });
            var empty = listbox.querySelector('.gc-combobox-option--empty');
            if (!empty) {
                empty = document.createElement('li');
                empty.className = 'gc-combobox-option--empty';
                empty.textContent = '无匹配省份';
                listbox.appendChild(empty);
            }
            empty.classList.toggle('gc-combobox-option--hidden', visible > 0);
        }

        function selectOption(li) {
            if (!li || li.classList.contains('gc-combobox-option--empty')) return;
            var val = li.getAttribute('data-value') || '';
            var label = (li.textContent || '').trim();
            input.value = label || val;
            closeList();
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }

        function highlightIndex(idx) {
            var visible = options.filter(function (li) {
                return !li.classList.contains('gc-combobox-option--hidden')
                    && !li.classList.contains('gc-combobox-option--empty');
            });
            options.forEach(function (li) {
                li.classList.remove('gc-combobox-option--active');
            });
            if (idx < 0 || idx >= visible.length) return;
            activeIndex = idx;
            visible[idx].classList.add('gc-combobox-option--active');
            visible[idx].scrollIntoView({ block: 'nearest' });
        }

        input.addEventListener('focus', openList);
        input.addEventListener('input', function () {
            openList();
            filterList(input.value.trim());
            highlightIndex(0);
        });
        input.addEventListener('keydown', function (e) {
            var visible = options.filter(function (li) {
                return !li.classList.contains('gc-combobox-option--hidden')
                    && !li.classList.contains('gc-combobox-option--empty');
            });
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (listbox.hidden) openList();
                highlightIndex(Math.min(activeIndex + 1, visible.length - 1));
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                highlightIndex(Math.max(activeIndex - 1, 0));
            } else if (e.key === 'Enter') {
                if (!listbox.hidden && activeIndex >= 0 && visible[activeIndex]) {
                    e.preventDefault();
                    selectOption(visible[activeIndex]);
                }
            } else if (e.key === 'Escape') {
                closeList();
            }
        });

        if (toggle) {
            toggle.addEventListener('click', function (e) {
                e.preventDefault();
                if (listbox.hidden) {
                    openList();
                    input.focus();
                } else {
                    closeList();
                }
            });
        }

        listbox.addEventListener('mousedown', function (e) {
            var li = e.target.closest('li[role="option"]');
            if (li) {
                e.preventDefault();
                selectOption(li);
            }
        });

        document.addEventListener('click', function (e) {
            if (!wrap.contains(e.target)) closeList();
        });
    }

    initProvinceCombobox();

    var provinceField = form.querySelector('[data-field="gaokao_province"]');
    if (provinceField) {
        var onProvinceChange = function () {
            updateJilinOnlySectionsVisibility();
        };
        provinceField.addEventListener('input', onProvinceChange);
        provinceField.addEventListener('change', onProvinceChange);
    }

    function eachProvinceOption(cb) {
        var listbox = document.getElementById('gaokaoProvinceListbox');
        if (!listbox) return;
        listbox.querySelectorAll('li[role="option"]').forEach(function (li) {
            if (li.classList.contains('gc-combobox-option--empty')) return;
            cb(li.getAttribute('data-value') || '', (li.textContent || '').trim(), li);
        });
    }

    function normalizeGaokaoProvince(raw) {
        raw = (raw || '').trim();
        if (!raw) return '';
        var found = '';
        eachProvinceOption(function (val, label) {
            if (!found && (raw === val || raw === label)) found = val;
        });
        if (found) return found;
        return raw
            .replace(/维吾尔自治区$/, '')
            .replace(/壮族自治区$/, '')
            .replace(/回族自治区$/, '')
            .replace(/自治区$/, '')
            .replace(/省$/, '')
            .replace(/市$/, '');
    }

    function isJilinGaokaoProvince() {
        var inp = form.querySelector('[data-field="gaokao_province"]');
        return normalizeGaokaoProvince(inp ? inp.value : '') === '吉林';
    }

    function updateJilinOnlySectionsVisibility() {
        var jilin = isJilinGaokaoProvince();
        var scoreRef = document.getElementById('gcScoreRefSection');
        var enrollPlan = document.getElementById('gcEnrollPlanSection');
        if (scoreRef) scoreRef.hidden = !jilin;
        if (enrollPlan) enrollPlan.hidden = !jilin;
        if (window._gcUpdateScoreRefProvincePlans) {
            window._gcUpdateScoreRefProvincePlans();
        }
    }

    function formatGaokaoProvinceDisplay(raw) {
        raw = (raw || '').trim();
        if (!raw) return '';
        var label = '';
        eachProvinceOption(function (val, lbl) {
            if (!label && (raw === val || raw === lbl)) label = lbl;
        });
        return label || raw;
    }

    (function formatSavedProvinceField() {
        var inp = form.querySelector('[data-field="gaokao_province"]');
        if (inp && inp.value.trim()) {
            inp.value = formatGaokaoProvinceDisplay(inp.value.trim());
        }
    })();

    var lookupUrl = form.getAttribute('data-score-lookup-url');
    var SCORE_ROW = 0;
    var MAX_ELECTIVE = 3;
    var ELEC_LABELS = { phy: '物', chem: '化', bio: '生', pol: '政', his: '历', geo: '地', tech: '技' };
    var ELEC_FULL = {
        phy: '物理', chem: '化学', bio: '生物', pol: '政治', his: '历史', geo: '地理', tech: '技术',
    };
    var ELEC_ORDER = ['phy', 'chem', 'bio', 'his', 'pol', 'geo', 'tech'];
    var selectedElec = {};
    var slotBindings = [null, null, null];
    var autoCalcOn = false;
    var autoCalcManualOff = false;
    var rankDebounce = null;

    var electiveBtns = document.getElementById('electiveBtns');
    var subjectsHidden = document.getElementById('scoreSubjectsHidden');
    var btnAutoCalc = document.getElementById('btnAutoCalc');
    var btnElecRating = document.getElementById('btnElecRating');
    var btnElecOptimal = document.getElementById('btnElecOptimal');
    var electiveRatingUrl = form.getAttribute('data-elective-rating-url') || '';

    function fieldEl(name) {
        return form.querySelector('[data-field="' + name + '"]');
    }

    function coreInputRow0(col) {
        return form.querySelector('[data-core-col="' + col + '"]');
    }

    function elecSlotInput(slot) {
        return form.querySelector('[data-elec-slot="' + slot + '"][data-score-row="0"]');
    }

    function elecTh(slot) {
        return form.querySelector('[data-elec-th="' + slot + '"]');
    }

    function storeField(key) {
        if (key === 'phy') return fieldEl('score_phy_0');
        if (key === 'his') return fieldEl('score_his_0');
        if (key === 'chem') return fieldEl('score_chem_0');
        if (key === 'bio') return fieldEl('score_bio_0');
        if (key === 'pol') return fieldEl('score_pol_0');
        if (key === 'geo') return fieldEl('score_geo_0');
        if (key === 'tech') return fieldEl('score_tech_0');
        return null;
    }

    function getSelectedList() {
        return ELEC_ORDER.filter(function (k) {
            return selectedElec[k];
        });
    }

    function parseScore(val) {
        if (val == null || String(val).trim() === '') return null;
        var n = parseFloat(String(val).replace(/[^\d.]/g, ''));
        return isNaN(n) ? null : n;
    }

    function syncSubjectsHidden() {
        if (!subjectsHidden) return;
        var s = '';
        ELEC_ORDER.forEach(function (k) {
            if (selectedElec[k]) s += ELEC_LABELS[k];
        });
        subjectsHidden.value = s;
    }

    flushSlotsToStore = function () {
        for (var s = 0; s < 3; s++) {
            var key = slotBindings[s];
            var slotInp = elecSlotInput(s);
            var store = key ? storeField(key) : null;
            if (store && slotInp && !slotInp.disabled) {
                store.value = slotInp.value;
            }
        }
    };

    function updateElectiveSlots() {
        var list = getSelectedList();
        flushSlotsToStore();

        for (var s = 0; s < 3; s++) {
            var th = elecTh(s);
            var inp = elecSlotInput(s);
            var key = list[s] || null;
            slotBindings[s] = key;

            if (th) {
                th.textContent = key ? ELEC_FULL[key] : '选考' + (s + 1);
            }
            if (!inp) continue;

            if (key) {
                var store = storeField(key);
                inp.disabled = false;
                inp.classList.remove('gc-score-cell--off');
                inp.value = store ? store.value : '';
                inp.setAttribute('data-elec-key', key);
            } else {
                inp.disabled = true;
                inp.classList.add('gc-score-cell--off');
                inp.value = '';
                inp.removeAttribute('data-elec-key');
            }
        }

        ELEC_ORDER.forEach(function (k) {
            if (selectedElec[k]) return;
            var st = storeField(k);
            if (st) st.value = '';
        });
    }

    function migrateHistoryScoreStore() {
        if (!selectedElec.his || selectedElec.phy) return;
        var hisStore = fieldEl('score_his_0');
        var phyStore = fieldEl('score_phy_0');
        if (hisStore && phyStore && !String(hisStore.value).trim() && String(phyStore.value).trim()) {
            hisStore.value = phyStore.value;
            phyStore.value = '';
        }
    }

    function restoreElectivesFromHidden() {
        var s = subjectsHidden ? subjectsHidden.value : '';
        selectedElec = {};
        if (s) {
            if (s.indexOf('物') >= 0) selectedElec.phy = true;
            if (s.indexOf('化') >= 0) selectedElec.chem = true;
            if (s.indexOf('生') >= 0) selectedElec.bio = true;
            if (s.indexOf('政') >= 0) selectedElec.pol = true;
            if (s.indexOf('历') >= 0 || s.indexOf('史') >= 0) selectedElec.his = true;
            if (s.indexOf('地') >= 0) selectedElec.geo = true;
            if (s.indexOf('技') >= 0) selectedElec.tech = true;
            if (electiveBtns) {
                electiveBtns.querySelectorAll('.gc-elec-btn').forEach(function (btn) {
                    var k = btn.getAttribute('data-elec');
                    btn.classList.toggle('gc-elec-btn--on', !!selectedElec[k]);
                });
            }
        }
        migrateHistoryScoreStore();
        updateElectiveSlots();
    }

    function countSelectedElec() {
        var n = 0;
        ELEC_ORDER.forEach(function (k) {
            if (selectedElec[k]) n += 1;
        });
        return n;
    }

    function inferSubject(province) {
        if (selectedElec.his) return 'history';
        if (selectedElec.phy) return 'physics';
        if (normalizeGaokaoProvince(province) === '上海') return 'physics';
        return 'physics';
    }

    function allSubjectsReady() {
        var cn = parseScore(coreInputRow0('cn') && coreInputRow0('cn').value);
        var math = parseScore(coreInputRow0('math') && coreInputRow0('math').value);
        var en = parseScore(coreInputRow0('en') && coreInputRow0('en').value);
        if (cn == null || math == null || en == null) return false;
        if (countSelectedElec() !== MAX_ELECTIVE) return false;
        flushSlotsToStore();
        for (var s = 0; s < 3; s++) {
            var inp = elecSlotInput(s);
            if (!inp || inp.disabled || parseScore(inp.value) == null) return false;
        }
        return true;
    }

    function sumSubjectScores() {
        flushSlotsToStore();
        var sum = 0;
        ['cn', 'math', 'en'].forEach(function (col) {
            var inp = coreInputRow0(col);
            var v = inp ? parseScore(inp.value) : null;
            if (v != null) sum += v;
        });
        for (var s = 0; s < 3; s++) {
            var inp = elecSlotInput(s);
            if (!inp || inp.disabled) continue;
            var v = parseScore(inp.value);
            if (v != null) sum += v;
        }
        return sum > 0 ? Math.round(sum * 10) / 10 : null;
    }

    function lookupLastYearRank(total, province, subject) {
        if (!lookupUrl || !province || total == null) return Promise.resolve(null);
        return fetch(lookupUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                province: province,
                subject: subject,
                score: Math.round(total),
            }),
        }).then(function (r) { return r.json(); }).catch(function () { return null; });
    }

    function applyRankResult(data) {
        var rankInp = fieldEl('score_rank_' + SCORE_ROW);
        var sameInp = fieldEl('score_same_' + SCORE_ROW);
        if (!data || !data.ok) {
            if (rankInp) rankInp.value = '';
            if (sameInp) sameInp.value = '';
            if (window._gcRefreshAllScorePlanTables) window._gcRefreshAllScorePlanTables();
            return;
        }
        if (rankInp) rankInp.value = data.rank != null ? String(data.rank) : '';
        if (sameInp) sameInp.value = data.same_score_count != null ? String(data.same_score_count) : '';
        if (window._gcRefreshAllScorePlanTables) window._gcRefreshAllScorePlanTables();
    }

    function setAutoCalcUi(on) {
        autoCalcOn = on;
        if (!btnAutoCalc) return;
        btnAutoCalc.classList.toggle('gc-auto-calc-btn--on', on);
        btnAutoCalc.setAttribute('aria-pressed', on ? 'true' : 'false');
        btnAutoCalc.textContent = on
            ? '自动计算：开'
            : (btnAutoCalc.getAttribute('data-default-label') || '自动计算');
    }

    function setElecActionButtonActive(btn, active, onClass) {
        if (!btn) return;
        btn.classList.toggle(onClass, !!active);
        if (active) {
            btn.setAttribute('data-shown', '1');
            btn.setAttribute('aria-pressed', 'true');
        } else {
            btn.textContent = btn.getAttribute('data-default-label') || '';
            btn.removeAttribute('data-shown');
            btn.setAttribute('aria-pressed', 'false');
        }
    }

    function resetElecActionButtons() {
        setElecActionButtonActive(btnElecRating, false, 'gc-elec-rating-btn--on');
        setElecActionButtonActive(btnElecOptimal, false, 'gc-elec-optimal-btn--on');
    }

    function applyElecRatingText(data) {
        return data && data.rating ? ('评级：' + data.rating) : '暂无数据';
    }

    function applyElecOptimalText(data) {
        if (!data) return '暂无数据';
        var combo = data.optimal_combo ? String(data.optimal_combo).trim() : '';
        var grade = data.optimal_grade ? String(data.optimal_grade).trim() : '';
        if (combo && grade) return combo + '：' + grade;
        if (combo) return combo;
        return '暂无数据';
    }

    function fetchElectiveRating() {
        var birthdayEl = fieldEl('birthday');
        var birthday = birthdayEl ? birthdayEl.value.trim() : '';
        var subjects = subjectsHidden ? subjectsHidden.value.trim() : '';
        if (!electiveRatingUrl) {
            return Promise.resolve({});
        }
        var url = electiveRatingUrl
            + '?birthday=' + encodeURIComponent(birthday)
            + '&subjects=' + encodeURIComponent(subjects);
        return fetch(url)
            .then(function (r) { return r.json(); })
            .catch(function () { return {}; });
    }

    var elecActionRefreshTimer = null;
    function refreshElecActionButtonsIfShown() {
        var ratingShown = btnElecRating && btnElecRating.getAttribute('data-shown') === '1';
        var optimalShown = btnElecOptimal && btnElecOptimal.getAttribute('data-shown') === '1';
        if (!ratingShown && !optimalShown) return;

        clearTimeout(elecActionRefreshTimer);
        elecActionRefreshTimer = setTimeout(function () {
            fetchElectiveRating().then(function (data) {
                if (ratingShown && btnElecRating) {
                    btnElecRating.textContent = applyElecRatingText(data);
                    btnElecRating.classList.add('gc-elec-rating-btn--on');
                }
                if (optimalShown && btnElecOptimal) {
                    btnElecOptimal.textContent = applyElecOptimalText(data);
                    btnElecOptimal.classList.add('gc-elec-optimal-btn--on');
                }
            });
        }, 300);
    }

    if (btnElecRating) {
        btnElecRating.addEventListener('click', function () {
            if (btnElecRating.getAttribute('data-shown') === '1') {
                setElecActionButtonActive(btnElecRating, false, 'gc-elec-rating-btn--on');
                return;
            }
            btnElecRating.disabled = true;
            fetchElectiveRating().then(function (data) {
                btnElecRating.textContent = applyElecRatingText(data);
                setElecActionButtonActive(btnElecRating, true, 'gc-elec-rating-btn--on');
            }).finally(function () {
                btnElecRating.disabled = false;
            });
        });
    }

    if (btnElecOptimal) {
        btnElecOptimal.addEventListener('click', function () {
            if (btnElecOptimal.getAttribute('data-shown') === '1') {
                setElecActionButtonActive(btnElecOptimal, false, 'gc-elec-optimal-btn--on');
                return;
            }
            btnElecOptimal.disabled = true;
            fetchElectiveRating().then(function (data) {
                btnElecOptimal.textContent = applyElecOptimalText(data);
                setElecActionButtonActive(btnElecOptimal, true, 'gc-elec-optimal-btn--on');
            }).finally(function () {
                btnElecOptimal.disabled = false;
            });
        });
    }

    var birthdayField = fieldEl('birthday');
    if (birthdayField) {
        birthdayField.addEventListener('input', refreshElecActionButtonsIfShown);
        birthdayField.addEventListener('change', refreshElecActionButtonsIfShown);
    }

    function maybeEnableAutoByProvince() {
        var provinceInp = fieldEl('gaokao_province');
        var p = provinceInp ? provinceInp.value.trim() : '';
        if (p && !autoCalcManualOff) setAutoCalcUi(true);
    }

    function recalcScores() {
        var totalInp = fieldEl('score_total_' + SCORE_ROW);
        var provinceInp = fieldEl('gaokao_province');
        if (!totalInp) return;

        var total = sumSubjectScores();
        totalInp.value = total != null ? String(total) : '';

        if (!allSubjectsReady()) {
            applyRankResult(null);
            return;
        }

        var province = normalizeGaokaoProvince(provinceInp ? provinceInp.value.trim() : '');
        if (!province) {
            applyRankResult(null);
            return;
        }

        var subject = inferSubject(province);
        clearTimeout(rankDebounce);
        rankDebounce = setTimeout(function () {
            lookupLastYearRank(total, province, subject).then(function (data) {
                applyRankResult(data);
                try {
                    localStorage.setItem(storageKey, JSON.stringify(collect()));
                } catch (e) { /* ignore */ }
            });
        }, 300);
    }

    function runCalcIfAuto() {
        if (autoCalcOn) recalcScores();
    }

    if (electiveBtns) {
        electiveBtns.addEventListener('click', function (e) {
            var btn = e.target.closest('.gc-elec-btn');
            if (!btn) return;
            var key = btn.getAttribute('data-elec');
            if (!key) return;

            if (selectedElec[key]) {
                selectedElec[key] = false;
                btn.classList.remove('gc-elec-btn--on');
            } else {
                if (countSelectedElec() >= MAX_ELECTIVE) return;
                selectedElec[key] = true;
                btn.classList.add('gc-elec-btn--on');
            }
            syncSubjectsHidden();
            updateElectiveSlots();
            refreshElecActionButtonsIfShown();
            runCalcIfAuto();
            if (window._gcRefreshAllScorePlanLookups) window._gcRefreshAllScorePlanLookups();
            try {
                localStorage.setItem(storageKey, JSON.stringify(collect()));
            } catch (err) { /* ignore */ }
        });
    }

    if (btnAutoCalc) {
        btnAutoCalc.addEventListener('click', function () {
            if (autoCalcOn) {
                setAutoCalcUi(false);
                autoCalcManualOff = true;
            } else {
                setAutoCalcUi(true);
                autoCalcManualOff = false;
                recalcScores();
            }
        });
    }

    function bindScoreInputs() {
        form.querySelectorAll('[data-core-col]').forEach(function (inp) {
            inp.addEventListener('input', function () {
                var v = inp.value.replace(/[^\d.]/g, '');
                if (inp.value !== v) inp.value = v;
                runCalcIfAuto();
            });
        });
        form.querySelectorAll('[data-elec-slot]').forEach(function (inp) {
            inp.addEventListener('input', function () {
                var v = inp.value.replace(/[^\d.]/g, '');
                if (inp.value !== v) inp.value = v;
                var key = inp.getAttribute('data-elec-key');
                var store = key ? storeField(key) : null;
                if (store) store.value = inp.value;
                runCalcIfAuto();
            });
        });
        var totalInp = fieldEl('score_total_' + SCORE_ROW);
        if (totalInp) {
            totalInp.addEventListener('input', runCalcIfAuto);
        }
    }

    bindScoreInputs();

    var provinceInp = fieldEl('gaokao_province');
    if (provinceInp) {
        provinceInp.addEventListener('change', function () {
            maybeEnableAutoByProvince();
            runCalcIfAuto();
        });
        provinceInp.addEventListener('input', function () {
            clearTimeout(rankDebounce);
            rankDebounce = setTimeout(function () {
                maybeEnableAutoByProvince();
                runCalcIfAuto();
            }, 400);
        });
    }

    restoreElectivesFromHidden();
    updateElectiveSlots();
    setAutoCalcUi(false);
    maybeEnableAutoByProvince();
    if (autoCalcOn) setTimeout(recalcScores, 150);

    function syncRegionNonCapitalButton(row) {
        if (!row) return;
        var btn = row.querySelector('.gc-region-noncapital-btn');
        var hidden = row.querySelector('.gc-region-noncapital-value');
        if (!btn || !hidden) return;
        var acceptLabel = btn.getAttribute('data-accept-label') || '可以接受非省会城市';
        var rejectLabel = btn.getAttribute('data-reject-label') || '不能接受非省会城市';
        if (hidden.value === 'reject') {
            btn.classList.remove('gc-region-noncapital-btn--accept');
            btn.classList.add('gc-region-noncapital-btn--reject');
            btn.textContent = rejectLabel;
            btn.setAttribute('aria-pressed', 'true');
        } else {
            hidden.value = 'accept';
            btn.classList.remove('gc-region-noncapital-btn--reject');
            btn.classList.add('gc-region-noncapital-btn--accept');
            btn.textContent = acceptLabel;
            btn.setAttribute('aria-pressed', 'false');
        }
    }

    function syncAllRegionNonCapitalButtons() {
        if (!regionSection) return;
        regionSection.querySelectorAll('.gc-region-row').forEach(syncRegionNonCapitalButton);
    }

    function resetRegionNonCapitalButton(row) {
        var hidden = row ? row.querySelector('.gc-region-noncapital-value') : null;
        if (hidden) hidden.value = 'accept';
        syncRegionNonCapitalButton(row);
    }

    function initRegionRowFooter() {
        form.querySelectorAll('.gc-region-noncapital-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var row = btn.closest('.gc-region-row');
                var hidden = row ? row.querySelector('.gc-region-noncapital-value') : null;
                if (!hidden) return;
                hidden.value = hidden.value === 'reject' ? 'accept' : 'reject';
                syncRegionNonCapitalButton(row);
                if (regionSection) refreshCollapseLocks(regionSection);
                persistDraftQuiet();
            });
        });

        form.querySelectorAll('.gc-region-favorite-cities').forEach(function (inp) {
            inp.addEventListener('click', function (e) {
                e.stopPropagation();
            });
            inp.addEventListener('input', function () {
                var row = inp.closest('.gc-region-row');
                if (!row) return;
                if (inp.value.trim()) {
                    if (regionCollapseMode === 'auto') {
                        applyAutoCollapseInSection(regionSection, row);
                    } else {
                        setCollapseOpen(row, true);
                    }
                }
                refreshCollapseLocks(regionSection);
            });
        });

        syncAllRegionNonCapitalButtons();
    }

    var collapsePrintState = [];
    var printHideState = [];
    var regionSection = document.getElementById('gcRegionSection');
    var regionCollapseMode = 'auto';
    var majorCollapseMode = 'auto';
    var btnRegionCollapseMode = document.getElementById('btnRegionCollapseMode');
    var btnMajorCollapseMode = document.getElementById('btnMajorCollapseMode');

    function isCollapseOpen(wrap) {
        var trigger = wrap && wrap.querySelector('.gc-collapse-trigger');
        return !!(trigger && trigger.getAttribute('aria-expanded') === 'true');
    }

    function setCollapseOpen(wrap, open) {
        if (!wrap) return;
        var body = wrap.querySelector('.gc-collapse-body');
        var trigger = wrap.querySelector('.gc-collapse-trigger');
        if (!body || !trigger) return;
        body.hidden = !open;
        trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    function regionRowHasSelection(row) {
        if (!row) return false;
        if (row.querySelector('input[type="checkbox"]:checked')) return true;
        var fav = row.querySelector('.gc-region-favorite-cities');
        if (fav && fav.value.trim()) return true;
        var hidden = row.querySelector('.gc-region-noncapital-value');
        return !!(hidden && hidden.value === 'reject');
    }

    function regionProvinceIsSelected(label) {
        if (!label) return false;
        var cb = label.querySelector('input[type="checkbox"]');
        return !!(cb && cb.checked);
    }

    function majorDisciplineHasSelectedCategory(block) {
        if (!block) return false;
        return Array.prototype.some.call(block.querySelectorAll('[data-major-group]'), function (btn) {
            var gid = btn.getAttribute('data-major-group');
            return gid && selectedMajorGroups[gid];
        });
    }

    function majorDisciplineHasSelection(block) {
        if (!block || !majorSection) return false;
        var catBtns = block.querySelectorAll('[data-major-group]');
        for (var i = 0; i < catBtns.length; i++) {
            var gid = catBtns[i].getAttribute('data-major-group');
            if (!gid) continue;
            if (selectedMajorGroups[gid]) return true;
            var panel = majorSection.querySelector('[data-major-panel="' + gid + '"]');
            if (!panel) continue;
            if (panel.querySelector('[data-major-item].gc-major-btn--on')) return true;
        }
        return false;
    }

    function regionRowSelectionCount(row) {
        if (!row) return 0;
        return row.querySelectorAll('input[type="checkbox"]:checked').length;
    }

    function majorDisciplineSelectionCount(block) {
        if (!block || !majorSection) return 0;
        var n = 0;
        block.querySelectorAll('[data-major-group]').forEach(function (btn) {
            var gid = btn.getAttribute('data-major-group');
            if (gid && selectedMajorGroups[gid]) n += 1;
        });
        return n;
    }

    function inputsHaveValue(inputs) {
        return Array.prototype.some.call(inputs || [], function (inp) {
            return inp.value.trim();
        });
    }

    function majorPanelHasReselectableContent(panel) {
        if (!panel) return false;
        if (panel.querySelector('[data-major-item].gc-major-btn--on')) return true;
        return inputsHaveValue(panel.querySelectorAll('input[data-field], textarea[data-field]'));
    }

    function earlySubsecHasSelection(subsec) {
        if (!subsec) return false;
        if (subsec.querySelector('[data-early-school].gc-major-btn--on')) return true;
        return inputsHaveValue(subsec.querySelectorAll('input[data-field], textarea[data-field]'));
    }

    function earlyPanelHasSelection(panel) {
        if (!panel) return false;
        if (panel.querySelector('[data-early-school].gc-major-btn--on')) return true;
        var subsecs = panel.querySelectorAll('.gc-early-subsec');
        if (subsecs.length) {
            return Array.prototype.some.call(subsecs, earlySubsecHasSelection);
        }
        return inputsHaveValue(panel.querySelectorAll('input[data-field], textarea[data-field]'));
    }

    function partClearTargetHasSelection(clearBtn) {
        if (!clearBtn) return false;
        var kind = clearBtn.getAttribute('data-clear-kind');
        if (kind === 'region-row') {
            return regionRowHasSelection(clearBtn.closest('.gc-region-row'));
        }
        if (kind === 'major-discipline') {
            return majorDisciplineHasSelection(clearBtn.closest('.gc-major-discipline'));
        }
        if (kind === 'major-panel') {
            return majorPanelHasReselectableContent(clearBtn.closest('.gc-major-panel'));
        }
        if (kind === 'early-panel') {
            return earlyPanelHasSelection(clearBtn.closest('[data-early-panel]'));
        }
        if (kind === 'early-subsec') {
            return earlySubsecHasSelection(clearBtn.closest('.gc-early-subsec'));
        }
        return false;
    }

    function refreshPartClearButtons(scope) {
        var root = scope || form;
        if (!root || !root.querySelectorAll) return;
        root.querySelectorAll('[data-clear-kind]').forEach(function (btn) {
            btn.hidden = !partClearTargetHasSelection(btn);
        });
    }

    function updateCollapseIndicator(wrap, count) {
        if (!wrap) return;
        var chevron = wrap.querySelector('.gc-collapse-chevron');
        var countEl = wrap.querySelector('.gc-collapse-count');
        if (!chevron || !countEl) return;
        var n = count || 0;
        if (n > 0) {
            chevron.hidden = true;
            countEl.hidden = false;
            countEl.textContent = String(n);
            countEl.setAttribute('aria-label', '已选' + n + '项');
        } else {
            chevron.hidden = false;
            countEl.hidden = true;
        }
    }

    function collapseHelpersForSection(sectionRoot) {
        if (sectionRoot && sectionRoot.id === 'gcRegionSection') {
            return {
                hasSelection: regionRowHasSelection,
                count: regionRowSelectionCount,
            };
        }
        return {
            hasSelection: majorDisciplineHasSelection,
            count: majorDisciplineSelectionCount,
        };
    }

    function refreshCollapseLocks(sectionRoot) {
        if (!sectionRoot) return;
        var helpers = collapseHelpersForSection(sectionRoot);
        sectionRoot.querySelectorAll('.gc-collapse').forEach(function (wrap) {
            var n = helpers.count(wrap);
            wrap.classList.toggle('gc-collapse--locked', n > 0);
            wrap.classList.toggle('gc-collapse--has-selection', helpers.hasSelection(wrap));
            updateCollapseIndicator(wrap, n);
        });
        refreshPartClearButtons(sectionRoot);
    }

    function applySectionCollapseMode(sectionRoot, mode) {
        if (!sectionRoot) return;
        var helpers = collapseHelpersForSection(sectionRoot);
        if (mode === 'all') {
            sectionRoot.querySelectorAll('.gc-collapse').forEach(function (wrap) {
                setCollapseOpen(wrap, true);
            });
        } else {
            sectionRoot.querySelectorAll('.gc-collapse').forEach(function (wrap) {
                if (helpers.hasSelection(wrap)) setCollapseOpen(wrap, true);
                else setCollapseOpen(wrap, false);
            });
        }
        refreshCollapseLocks(sectionRoot);
    }

    function applyAutoCollapseInSection(sectionRoot, activeWrap) {
        if (!sectionRoot || !activeWrap) return;
        var helpers = collapseHelpersForSection(sectionRoot);
        setCollapseOpen(activeWrap, true);
        sectionRoot.querySelectorAll('.gc-collapse').forEach(function (wrap) {
            if (wrap === activeWrap) return;
            if (helpers.hasSelection(wrap)) setCollapseOpen(wrap, true);
            else setCollapseOpen(wrap, false);
        });
        refreshCollapseLocks(sectionRoot);
    }

    function onCollapseTriggerClick(wrap) {
        if (!wrap) return;
        var sectionRoot = wrap.closest('#gcRegionSection, #gcMajorSection');
        var mode = sectionRoot && sectionRoot.id === 'gcRegionSection' ? regionCollapseMode : majorCollapseMode;
        var helpers = collapseHelpersForSection(sectionRoot);

        if (mode === 'all') {
            if (isCollapseOpen(wrap)) {
                if (helpers.hasSelection(wrap)) return;
                setCollapseOpen(wrap, false);
            } else {
                setCollapseOpen(wrap, true);
            }
            refreshCollapseLocks(sectionRoot);
            return;
        }

        if (isCollapseOpen(wrap)) {
            if (helpers.hasSelection(wrap)) return;
            setCollapseOpen(wrap, false);
            refreshCollapseLocks(sectionRoot);
            return;
        }

        applyAutoCollapseInSection(sectionRoot, wrap);
    }

    function setRegionCollapseMode(mode) {
        regionCollapseMode = mode === 'all' ? 'all' : 'auto';
        if (btnRegionCollapseMode) {
            var showAll = regionCollapseMode === 'all';
            btnRegionCollapseMode.setAttribute('aria-pressed', showAll ? 'true' : 'false');
            btnRegionCollapseMode.textContent = showAll ? '全部展示' : '自动折叠';
        }
        applySectionCollapseMode(regionSection, regionCollapseMode);
    }

    function setMajorCollapseMode(mode) {
        majorCollapseMode = mode === 'all' ? 'all' : 'auto';
        if (btnMajorCollapseMode) {
            var showAll = majorCollapseMode === 'all';
            btnMajorCollapseMode.setAttribute('aria-pressed', showAll ? 'true' : 'false');
            btnMajorCollapseMode.textContent = showAll ? '全部展示' : '自动折叠';
        }
        applySectionCollapseMode(majorSection, majorCollapseMode);
    }

    function initCollapsibles() {
        form.querySelectorAll('.gc-collapse-trigger').forEach(function (btn) {
            if (btn.dataset.collapseBound) return;
            btn.dataset.collapseBound = '1';
            btn.addEventListener('click', function () {
                onCollapseTriggerClick(btn.closest('.gc-collapse'));
            });
        });
    }

    function syncCollapseOpenFromContent() {
        if (regionSection) {
            regionSection.querySelectorAll('.gc-region-row.gc-collapse').forEach(function (row) {
                if (regionRowHasSelection(row)) setCollapseOpen(row, true);
            });
            refreshCollapseLocks(regionSection);
        }
        if (majorSection) {
            majorSection.querySelectorAll('.gc-major-discipline.gc-collapse').forEach(function (block) {
                if (majorDisciplineHasSelection(block)) setCollapseOpen(block, true);
            });
            refreshCollapseLocks(majorSection);
        }
    }

    function expandCollapsiblesForPrint() {
        collapsePrintState = [];
        form.querySelectorAll('.gc-collapse').forEach(function (wrap) {
            var body = wrap.querySelector('.gc-collapse-body');
            var trigger = wrap.querySelector('.gc-collapse-trigger');
            if (!body || !trigger) return;

            var sectionRoot = wrap.closest('#gcRegionSection, #gcMajorSection');
            var hasSel = false;
            if (wrap.classList.contains('gc-region-row')) {
                hasSel = regionRowHasSelection(wrap);
            } else if (wrap.classList.contains('gc-major-discipline')) {
                hasSel = majorDisciplineHasSelectedCategory(wrap);
            } else if (sectionRoot) {
                var helpers = collapseHelpersForSection(sectionRoot);
                hasSel = helpers ? helpers.hasSelection(wrap) : wrap.classList.contains('gc-collapse--has-selection');
            } else {
                hasSel = wrap.classList.contains('gc-collapse--has-selection');
            }

            if (!hasSel) {
                wrap.classList.add('gc-print-skip');
                collapsePrintState.push({ wrap: wrap, skipOnly: true });
                return;
            }

            collapsePrintState.push({
                wrap: wrap,
                body: body,
                trigger: trigger,
                wasHidden: body.hidden,
                skipOnly: false,
            });
            setCollapseOpen(wrap, true);
        });
    }

    function restoreCollapsiblesAfterPrint() {
        collapsePrintState.forEach(function (item) {
            if (item.skipOnly) {
                item.wrap.classList.remove('gc-print-skip');
                return;
            }
            item.body.hidden = item.wasHidden;
            item.trigger.setAttribute('aria-expanded', item.wasHidden ? 'false' : 'true');
        });
        collapsePrintState = [];
        syncCollapseOpenFromContent();
    }

    function markPrintVisibility() {
        printHideState.forEach(function (el) {
            el.classList.remove('gc-print-skip');
        });
        printHideState = [];

        if (regionSection) refreshCollapseLocks(regionSection);
        if (majorSection) refreshCollapseLocks(majorSection);

        var scoreRef = document.getElementById('gcScoreRefSection');
        if (scoreRef) {
            scoreRef.classList.add('gc-print-skip');
            printHideState.push(scoreRef);
        }
        var enrollPlan = document.getElementById('gcEnrollPlanSection');
        if (enrollPlan) {
            enrollPlan.classList.add('gc-print-skip');
            printHideState.push(enrollPlan);
        }

        if (regionSection) {
            regionSection.querySelectorAll('.gc-region-row').forEach(function (row) {
                if (!regionRowHasSelection(row)) {
                    row.classList.add('gc-print-skip');
                    printHideState.push(row);
                    return;
                }
                row.querySelectorAll('.gc-region-province').forEach(function (label) {
                    if (!regionProvinceIsSelected(label)) {
                        label.classList.add('gc-print-skip');
                        printHideState.push(label);
                    }
                });
            });
            var regionAny = regionSection.querySelector('.gc-region-row:not(.gc-print-skip)');
            if (!regionAny) {
                regionSection.classList.add('gc-print-skip');
                printHideState.push(regionSection);
            }
        }

        if (majorSection) {
            majorSection.querySelectorAll('.gc-major-discipline').forEach(function (disc) {
                if (!majorDisciplineHasSelectedCategory(disc)) {
                    disc.classList.add('gc-print-skip');
                    printHideState.push(disc);
                }
            });
            var majorAny = majorSection.querySelector('.gc-major-discipline:not(.gc-print-skip)');
            if (!majorAny) {
                majorSection.classList.add('gc-print-skip');
                printHideState.push(majorSection);
            }
        }

        if (earlySection) {
            var earlyAny = Object.keys(selectedEarlyGroups).some(function (k) {
                return selectedEarlyGroups[k];
            });
            if (!earlyAny) {
                earlySection.classList.add('gc-print-skip');
                printHideState.push(earlySection);
            }
        }

        var timelineSection = document.getElementById('gcTimelineSection');
        if (timelineSection) {
            updateTimelineVisibility();
            /* 「志愿填报时间」等 gc-timeline-block--always 始终导出 */
            timelineSection.classList.remove('gc-print-skip');
        }
    }

    function clearPrintVisibility() {
        printHideState.forEach(function (el) {
            el.classList.remove('gc-print-skip');
        });
        printHideState = [];
        form.querySelectorAll('.gc-collapse.gc-print-skip').forEach(function (wrap) {
            wrap.classList.remove('gc-print-skip');
        });
    }

    initCollapsibles();
    initRegionRowFooter();
    setRegionCollapseMode('auto');
    setMajorCollapseMode('auto');
    syncCollapseOpenFromContent();
    refreshPartClearButtons();

    if (btnRegionCollapseMode) {
        btnRegionCollapseMode.addEventListener('click', function () {
            setRegionCollapseMode(regionCollapseMode === 'auto' ? 'all' : 'auto');
        });
    }
    if (btnMajorCollapseMode) {
        btnMajorCollapseMode.addEventListener('click', function () {
            setMajorCollapseMode(majorCollapseMode === 'auto' ? 'all' : 'auto');
        });
    }

    form.querySelectorAll('.gc-region-row input[type="checkbox"]').forEach(function (cb) {
        cb.addEventListener('change', function () {
            var row = cb.closest('.gc-region-row');
            if (!row) return;
            if (cb.checked) {
                if (regionCollapseMode === 'auto') {
                    applyAutoCollapseInSection(regionSection, row);
                } else {
                    setCollapseOpen(row, true);
                    refreshCollapseLocks(regionSection);
                }
            } else {
                refreshCollapseLocks(regionSection);
            }
        });
    });

    function refreshMajorCollapseState(activeBlock) {
        if (!majorSection) return;
        majorSection.querySelectorAll('.gc-major-discipline.gc-collapse').forEach(function (block) {
            if (majorDisciplineHasSelection(block)) setCollapseOpen(block, true);
        });
        if (majorCollapseMode === 'auto' && activeBlock) {
            applyAutoCollapseInSection(majorSection, activeBlock);
        } else {
            refreshCollapseLocks(majorSection);
        }
    }

    function persistDraftQuiet() {
        try {
            localStorage.setItem(storageKey, JSON.stringify(collect()));
        } catch (e) { /* ignore */ }
    }

    function reselectRegionRow(row) {
        if (!row) return;
        row.querySelectorAll('input[type="checkbox"]').forEach(function (cb) {
            cb.checked = false;
        });
        row.querySelectorAll('.gc-region-favorite-cities').forEach(function (inp) {
            inp.value = '';
        });
        resetRegionNonCapitalButton(row);
        if (regionSection) refreshCollapseLocks(regionSection);
        persistDraftQuiet();
    }

    function reselectMajorDiscipline(block) {
        if (!block || !majorSection) return;
        block.querySelectorAll('[data-major-group]').forEach(function (btn) {
            var gid = btn.getAttribute('data-major-group');
            if (!gid) return;
            var panel = majorSection.querySelector('[data-major-panel="' + gid + '"]');
            if (panel) {
                panel.querySelectorAll('[data-major-item]').forEach(function (mb) {
                    var id = mb.getAttribute('data-major-item');
                    if (id) delete selectedMajorItems[id];
                    mb.classList.remove('gc-major-btn--on');
                });
                panel.querySelectorAll('input[data-field]').forEach(function (inp) {
                    inp.value = '';
                });
                if (window._gcClearScorePlansInPanel) window._gcClearScorePlansInPanel(panel);
            }
            delete selectedMajorGroups[gid];
            btn.classList.remove('gc-major-btn--on');
        });
        syncMajorGroupsHidden();
        syncMajorItemsHidden();
        updateMajorPanels();
        if (majorSection) refreshCollapseLocks(majorSection);
        refreshPartClearButtons(majorSection);
        persistDraftQuiet();
    }

    function reselectMajorPanel(panel) {
        if (!panel || !majorSection) return;
        panel.querySelectorAll('[data-major-item]').forEach(function (btn) {
            var id = btn.getAttribute('data-major-item');
            if (id) delete selectedMajorItems[id];
            btn.classList.remove('gc-major-btn--on');
        });
        panel.querySelectorAll('input[data-field]').forEach(function (inp) {
            inp.value = '';
        });
        syncMajorItemsHidden();
        updateMajorPanels();
        if (majorSection) refreshCollapseLocks(majorSection);
        refreshPartClearButtons(majorSection);
        if (window._gcClearScorePlansInPanel) window._gcClearScorePlansInPanel(panel);
        persistDraftQuiet();
    }

    function reselectEarlySubsec(subsec) {
        if (!subsec) return;
        subsec.querySelectorAll('[data-early-school]').forEach(function (btn) {
            var sid = btn.getAttribute('data-early-school');
            if (sid) delete selectedEarlySchools[sid];
            btn.classList.remove('gc-major-btn--on');
        });
        subsec.querySelectorAll('input[data-field]').forEach(function (inp) {
            inp.value = '';
        });
        syncEarlySchoolsHidden();
        updateEarlyPanels();
        syncEarlyPrintTags();
        refreshPartClearButtons(earlySection);
        persistDraftQuiet();
    }

    function reselectEarlyPanel(panel) {
        if (!panel) return;
        panel.querySelectorAll('[data-early-school]').forEach(function (btn) {
            var sid = btn.getAttribute('data-early-school');
            if (sid) delete selectedEarlySchools[sid];
            btn.classList.remove('gc-major-btn--on');
        });
        panel.querySelectorAll('input[data-field]').forEach(function (inp) {
            inp.value = '';
        });
        syncEarlySchoolsHidden();
        updateEarlyPanels();
        syncEarlyPrintTags();
        refreshPartClearButtons(earlySection);
        persistDraftQuiet();
    }

    form.addEventListener('input', function (e) {
        var t = e.target;
        if (!t || !t.matches) return;
        if (!t.matches('input[data-field], textarea[data-field]')) return;
        if (t.closest('.gc-region-row, .gc-major-panel, .gc-early-subsec, [data-early-panel], .gc-major-discipline')) {
            refreshPartClearButtons();
        }
    });

    form.addEventListener('click', function (e) {
        var clearBtn = e.target.closest('[data-clear-kind]');
        if (!clearBtn) return;
        e.preventDefault();
        e.stopPropagation();
        var kind = clearBtn.getAttribute('data-clear-kind');
        if (kind === 'region-row') {
            reselectRegionRow(clearBtn.closest('.gc-region-row'));
        } else if (kind === 'major-discipline') {
            reselectMajorDiscipline(clearBtn.closest('.gc-major-discipline'));
        } else if (kind === 'major-panel') {
            reselectMajorPanel(clearBtn.closest('.gc-major-panel'));
        } else if (kind === 'early-panel') {
            reselectEarlyPanel(clearBtn.closest('[data-early-panel]'));
        } else if (kind === 'early-subsec') {
            reselectEarlySubsec(clearBtn.closest('.gc-early-subsec'));
        }
    });

    function majorSearchMatches(btn, q, qLower) {
        if (!q) return true;
        var text = (btn.getAttribute('data-search-text') || btn.textContent || '').toLowerCase();
        return text.indexOf(qLower) >= 0 || text.indexOf(q) >= 0;
    }

    function filterMajorButtons(query) {
        if (!majorSection) return;
        var q = (query || '').trim();
        var qLower = q.toLowerCase();
        var totalCatVisible = 0;
        var totalCatButtons = 0;
        var totalMajorVisible = 0;
        var totalMajorButtons = 0;
        var panelMajorVisible = {};

        majorSection.querySelectorAll('[data-major-panel]').forEach(function (panel) {
            var gid = panel.getAttribute('data-major-panel');
            var visibleInPanel = 0;
            var items = panel.querySelectorAll('[data-major-item]');
            totalMajorButtons += items.length;
            items.forEach(function (btn) {
                var match = majorSearchMatches(btn, q, qLower);
                btn.classList.toggle('gc-major-btn--hidden', !match);
                if (match) visibleInPanel += 1;
            });
            if (gid) panelMajorVisible[gid] = visibleInPanel;
            panel.classList.toggle('gc-major-panel--filter-empty', !!q && visibleInPanel === 0);
            totalMajorVisible += visibleInPanel;
        });

        majorSection.querySelectorAll('.gc-major-bar').forEach(function (bar) {
            var visibleInBar = 0;
            var buttons = bar.querySelectorAll('[data-major-group]');
            totalCatButtons += buttons.length;
            buttons.forEach(function (btn) {
                var gid = btn.getAttribute('data-major-group');
                var title = (btn.textContent || '').trim();
                var titleMatch = !q || title.indexOf(q) >= 0 || title.toLowerCase().indexOf(qLower) >= 0;
                var majorMatch = !q || (gid && panelMajorVisible[gid] > 0);
                var match = !q || titleMatch || majorMatch;
                btn.classList.toggle('gc-major-btn--hidden', !match);
                if (match) visibleInBar += 1;
            });
            bar.classList.toggle('gc-major-bar--filter-empty', !!q && visibleInBar === 0);
            totalCatVisible += visibleInBar;
        });

        majorSection.querySelectorAll('.gc-major-discipline').forEach(function (block) {
            var visibleInDisc = 0;
            block.querySelectorAll('.gc-major-btn[data-major-group]').forEach(function (btn) {
                if (!btn.classList.contains('gc-major-btn--hidden')) visibleInDisc += 1;
            });
            block.classList.toggle('gc-major-discipline--filter-empty', !!q && visibleInDisc === 0);
            if (q && visibleInDisc > 0) setCollapseOpen(block, true);
        });

        var meta = document.getElementById('majorSearchMeta');
        var clearBtn = document.getElementById('majorGroupSearchClear');
        if (clearBtn) clearBtn.hidden = !q;
        if (meta) {
            if (!q) {
                meta.textContent = '';
            } else if (totalCatVisible === 0 && totalMajorVisible === 0) {
                meta.textContent = '未找到匹配类别或专业，请换个关键词';
            } else if (totalMajorVisible > 0) {
                meta.textContent = '找到 ' + totalMajorVisible + ' 个专业'
                    + (totalCatVisible > 0 ? '（' + totalCatVisible + ' 个相关类别）' : '');
            } else {
                meta.textContent = '找到 ' + totalCatVisible + ' 个类别';
            }
        }
    }

    function initMajorSearch() {
        var inp = document.getElementById('majorGroupSearch');
        var clearBtn = document.getElementById('majorGroupSearchClear');
        if (!inp) return;
        inp.addEventListener('input', function () {
            filterMajorButtons(inp.value);
        });
        if (clearBtn) {
            clearBtn.addEventListener('click', function () {
                inp.value = '';
                filterMajorButtons('');
                inp.focus();
            });
        }
    }

    initMajorSearch();

    if (majorSection) {
        majorSection.addEventListener('click', function (e) {
            var itemBtn = e.target.closest('[data-major-item]');
            if (itemBtn) {
                var itemId = itemBtn.getAttribute('data-major-item');
                if (!itemId) return;
                if (selectedMajorItems[itemId]) {
                    delete selectedMajorItems[itemId];
                } else {
                    selectedMajorItems[itemId] = true;
                }
                syncMajorItemsHidden();
                updateMajorPanels();
                refreshMajorCollapseState(null);
                refreshPartClearButtons(majorSection);
                var majorPanel = itemBtn.closest('.gc-major-panel');
                if (majorPanel && window._gcRefreshScorePlanDrafts) {
                    window._gcRefreshScorePlanDrafts(majorPanel);
                }
                try {
                    localStorage.setItem(storageKey, JSON.stringify(collect()));
                } catch (err) { /* ignore */ }
                return;
            }
            var btn = e.target.closest('[data-major-group]');
            if (!btn || btn.classList.contains('gc-major-btn--hidden')) return;
            var id = btn.getAttribute('data-major-group');
            if (!id) return;
            if (selectedMajorGroups[id]) {
                delete selectedMajorGroups[id];
            } else {
                selectedMajorGroups[id] = true;
            }
            syncMajorGroupsHidden();
            updateMajorPanels();
            var disc = btn.closest('.gc-major-discipline');
            refreshMajorCollapseState(disc);
            refreshPartClearButtons(majorSection);
            try {
                localStorage.setItem(storageKey, JSON.stringify(collect()));
            } catch (err) { /* ignore */ }
        });
    }

    if (earlySection) {
        earlySection.addEventListener('click', function (e) {
            var schoolBtn = e.target.closest('[data-early-school]');
            if (schoolBtn) {
                var sid = schoolBtn.getAttribute('data-early-school');
                if (!sid) return;
                if (selectedEarlySchools[sid]) {
                    delete selectedEarlySchools[sid];
                } else {
                    selectedEarlySchools[sid] = true;
                }
                syncEarlySchoolsHidden();
                updateEarlyPanels();
                refreshPartClearButtons(earlySection);
                try {
                    localStorage.setItem(storageKey, JSON.stringify(collect()));
                } catch (err) { /* ignore */ }
                return;
            }
            var btn = e.target.closest('[data-early-group]');
            if (!btn) return;
            var id = btn.getAttribute('data-early-group');
            if (!id) return;
            if (selectedEarlyGroups[id]) {
                delete selectedEarlyGroups[id];
            } else {
                selectedEarlyGroups[id] = true;
            }
            syncEarlyGroupsHidden();
            updateEarlyPanels();
            refreshPartClearButtons(earlySection);
            try {
                localStorage.setItem(storageKey, JSON.stringify(collect()));
            } catch (err) { /* ignore */ }
        });
    }

    function preparePrintTags(container, selector) {
        if (!container) return;
        container.querySelectorAll(selector).forEach(function (btn) {
            if (btn.dataset.printTagDone) return;
            var tag = document.createElement('span');
            tag.className = btn.className + ' gc-print-tag';
            tag.textContent = (btn.innerText || btn.textContent || '').trim();
            btn.parentNode.insertBefore(tag, btn);
            btn.dataset.printTagDone = '1';
        });
    }

    function syncPrintTagsIn(container, selector) {
        if (!container) return;
        container.querySelectorAll(selector || 'button[data-major-group]').forEach(function (btn) {
            var tag = btn.previousElementSibling;
            if (!tag || !tag.classList.contains('gc-print-tag')) return;
            tag.className = btn.className + ' gc-print-tag';
            tag.textContent = (btn.innerText || btn.textContent || '').trim();
        });
    }

    function syncEarlyPrintTags() {
        syncPrintTagsIn(document.getElementById('earlyGroupBtns'), 'button[data-early-group]');
    }

    function allMajorCatContainers() {
        return majorSection
            ? Array.prototype.slice.call(majorSection.querySelectorAll('.gc-major-cat-btns'))
            : [];
    }

    function prepareAllMajorCatPrintTags() {
        allMajorCatContainers().forEach(function (container) {
            preparePrintTags(container, '.gc-major-btn[data-major-group]');
        });
    }

    function syncMajorPrintTags() {
        allMajorCatContainers().forEach(function (container) {
            syncPrintTagsIn(container, 'button[data-major-group]');
        });
    }

    var savedDocumentTitle = document.title;

    function getExportPdfTitle() {
        var nameInp = form.querySelector('[data-field="name"]');
        var name = nameInp && nameInp.value.trim() ? nameInp.value.trim() : '童未来';
        return '高考测评表-' + name;
    }

    function expandAllForPrint() {
        preparePrintTags(document.getElementById('earlyGroupBtns'), '.gc-major-btn[data-early-group]');
        syncEarlyPrintTags();
        prepareAllMajorCatPrintTags();
        syncMajorPrintTags();
        updateMajorPanels();
        updateEarlyPanels();
        markPrintVisibility();
        expandCollapsiblesForPrint();
        savedDocumentTitle = document.title;
        document.title = getExportPdfTitle();
        document.body.classList.add('gc-print-prep');
    }

    function restoreAfterPrint() {
        document.title = savedDocumentTitle;
        document.body.classList.remove('gc-print-prep');
        clearPrintVisibility();
        restoreCollapsiblesAfterPrint();
        updateMajorPanels();
        updateEarlyPanels();
    }

    function exportPdf() {
        expandAllForPrint();
        window.print();
    }

    var pdfBtn = document.getElementById('gcExportPdf');
    if (pdfBtn) pdfBtn.addEventListener('click', exportPdf);

    function resetUiToInitialState() {
        form.querySelectorAll('.gc-major-btn').forEach(function (btn) {
            btn.classList.remove('gc-major-btn--on', 'gc-major-btn--hidden');
        });
        form.querySelectorAll('.gc-elec-btn').forEach(function (btn) {
            btn.classList.remove('gc-elec-btn--on');
        });
        form.querySelectorAll(
            '.gc-major-bar--filter-empty, .gc-major-discipline--filter-empty, .gc-major-panel--filter-empty'
        ).forEach(function (el) {
            el.classList.remove(
                'gc-major-bar--filter-empty',
                'gc-major-discipline--filter-empty',
                'gc-major-panel--filter-empty'
            );
        });
        form.querySelectorAll('[data-major-panel], [data-early-panel]').forEach(function (panel) {
            panel.hidden = true;
        });
        form.querySelectorAll('.gc-collapse').forEach(function (wrap) {
            wrap.classList.remove('gc-collapse--locked', 'gc-collapse--has-selection');
            updateCollapseIndicator(wrap, 0);
        });
        autoCalcManualOff = false;
        setAutoCalcUi(false);
        setTimelineShowAll(false);
        setRegionCollapseMode('auto');
        setMajorCollapseMode('auto');
        refreshPartClearButtons();
        syncAllRegionNonCapitalButtons();
    }

    function clearForm() {
        if (!window.confirm('确定清空全部填写内容？已保存的草稿也会被删除，此操作不可恢复。')) return;

        try {
            localStorage.removeItem(storageKey);
        } catch (e) { /* ignore */ }

        var defaultName = form.getAttribute('data-default-name') || '童未来';
        form.querySelectorAll('[data-field]').forEach(function (el) {
            var key = el.getAttribute('data-field');
            if (el.type === 'checkbox') {
                el.checked = false;
            } else if (el.tagName === 'SELECT') {
                el.selectedIndex = 0;
            } else if (key === 'name') {
                el.value = defaultName;
            } else if (key === 'timeline_show_all') {
                el.value = '0';
            } else {
                el.value = '';
            }
        });

        selectedEarlyGroups = {};
        selectedEarlySchools = {};
        selectedMajorGroups = {};
        selectedMajorItems = {};
        syncEarlyGroupsHidden();
        syncEarlySchoolsHidden();
        syncMajorGroupsHidden();
        syncMajorItemsHidden();
        updateEarlyPanels();
        updateMajorPanels();

        selectedElec = {};
        slotBindings = [null, null, null];
        if (electiveBtns) {
            electiveBtns.querySelectorAll('.gc-elec-btn').forEach(function (btn) {
                btn.classList.remove('gc-elec-btn--on');
            });
        }
        syncSubjectsHidden();
        updateElectiveSlots();
        resetElecActionButtons();

        clearTimeout(rankDebounce);

        var searchInp = document.getElementById('majorGroupSearch');
        if (searchInp) {
            searchInp.value = '';
            filterMajorButtons('');
        }

        resetUiToInitialState();

        if (majorSection) {
            majorSection.querySelectorAll('.gc-score-plan-drafts').forEach(function (el) {
                el.innerHTML = '';
            });
        }
        if (window._gcRestoreAllScorePlans) window._gcRestoreAllScorePlans();

        alert('已清空全部内容');
    }

    var clearBtn = document.getElementById('gcClearForm');
    if (clearBtn) clearBtn.addEventListener('click', clearForm);

    window.addEventListener('beforeprint', expandAllForPrint);
    window.addEventListener('afterprint', restoreAfterPrint);

    form.addEventListener('change', function () {
        try {
            localStorage.setItem(storageKey, JSON.stringify(collect()));
        } catch (e) { /* ignore */ }
    });

    function attachSearchCombobox(labelEl, config) {
        var combo = document.createElement('div');
        combo.className = 'gc-combobox ' + (config.comboClass || 'gc-score-plan-combo');

        var input = document.createElement('input');
        input.type = 'text';
        input.className = 'gc-combobox-input ' + (config.inputClass || '');
        input.placeholder = config.placeholder || '';
        input.autocomplete = 'off';
        input.setAttribute('role', 'combobox');
        input.setAttribute('aria-expanded', 'false');
            if (config.disabled) input.disabled = true;

        var searchTrigger = config.openOn === 'search';
        if (searchTrigger) combo.classList.add('gc-combobox--search-trigger');

        var toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'gc-combobox-btn' + (searchTrigger ? ' gc-combobox-btn--search' : '');
        toggle.setAttribute('aria-label', config.toggleLabel || (searchTrigger ? '搜索' : '展开列表'));
        toggle.tabIndex = -1;
        if (config.disabled) toggle.disabled = true;
            toggle.textContent = searchTrigger ? (config.searchButtonLabel || '搜索') : '▾';

        var listbox = document.createElement('ul');
        listbox.className = 'gc-combobox-dropdown';
        listbox.setAttribute('role', 'listbox');
        listbox.hidden = true;

        combo.appendChild(input);
        combo.appendChild(toggle);
        combo.appendChild(listbox);
        labelEl.appendChild(combo);

        var activeIndex = -1;
        var fetchTimer = null;
        var staticOptions = config.staticOptions ? config.staticOptions.slice() : null;

        function visibleOptions() {
            return Array.prototype.slice.call(
                listbox.querySelectorAll('li[role="option"]')
            ).filter(function (li) {
                return !li.classList.contains('gc-combobox-option--hidden')
                    && !li.classList.contains('gc-combobox-option--empty');
            });
        }

        function closeList() {
            listbox.hidden = true;
            input.setAttribute('aria-expanded', 'false');
            activeIndex = -1;
            listbox.querySelectorAll('li[role="option"]').forEach(function (li) {
                li.classList.remove('gc-combobox-option--active');
            });
        }

        function openList() {
            listbox.hidden = false;
            input.setAttribute('aria-expanded', 'true');
        }

        function openSearchList() {
            openList();
            clearTimeout(fetchTimer);
            fetchTimer = null;
            loadOptions(input.value.trim());
            input.focus();
        }

        function renderOptions(labels) {
            listbox.innerHTML = '';
            if (!labels.length) {
                var empty = document.createElement('li');
                empty.className = 'gc-combobox-option--empty';
                empty.textContent = config.emptyText || '无匹配项';
                listbox.appendChild(empty);
                return;
            }
            labels.forEach(function (label) {
                var li = document.createElement('li');
                li.setAttribute('role', 'option');
                li.setAttribute('data-value', label);
                li.textContent = label;
                listbox.appendChild(li);
            });
        }

        function loadOptions(q) {
            if (config.fetchOptions) {
                config.fetchOptions(q, renderOptions);
                return;
            }
            var query = (q || '').trim();
            var lower = query.toLowerCase();
            var source = staticOptions || [];
            var filtered = source.filter(function (label) {
                return !query
                    || label.indexOf(query) >= 0
                    || label.toLowerCase().indexOf(lower) >= 0;
            });
            renderOptions(filtered);
        }

        function scheduleLoad() {
            clearTimeout(fetchTimer);
            fetchTimer = setTimeout(function () {
                loadOptions(input.value.trim());
            }, config.debounceMs || 200);
        }

        function selectOption(li) {
            if (!li || li.classList.contains('gc-combobox-option--empty')) return;
            input.value = (li.textContent || '').trim();
            closeList();
            if (config.onChange) config.onChange(input.value.trim());
        }

        function highlightIndex(idx) {
            var visible = visibleOptions();
            listbox.querySelectorAll('li[role="option"]').forEach(function (li) {
                li.classList.remove('gc-combobox-option--active');
            });
            if (idx < 0 || idx >= visible.length) return;
            activeIndex = idx;
            visible[idx].classList.add('gc-combobox-option--active');
            visible[idx].scrollIntoView({ block: 'nearest' });
        }

        input.addEventListener('focus', function () {
            if (searchTrigger) return;
            openList();
            loadOptions(input.value.trim());
        });
        input.addEventListener('input', function () {
            if (config.onInput) config.onInput(input.value.trim());
            if (searchTrigger) {
                if (!listbox.hidden) {
                    scheduleLoad();
                    highlightIndex(0);
                }
                return;
            }
            openList();
            scheduleLoad();
            highlightIndex(0);
        });
        input.addEventListener('blur', function () {
            if (config.onChange) config.onChange(input.value.trim());
        });
        input.addEventListener('keydown', function (e) {
            var visible = visibleOptions();
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (listbox.hidden) {
                    if (searchTrigger) openSearchList();
                    else openList();
                    loadOptions(input.value.trim());
                }
                highlightIndex(activeIndex < visible.length - 1 ? activeIndex + 1 : 0);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                highlightIndex(activeIndex > 0 ? activeIndex - 1 : visible.length - 1);
            } else if (e.key === 'Enter') {
                if (!listbox.hidden && activeIndex >= 0 && visible[activeIndex]) {
                    e.preventDefault();
                    selectOption(visible[activeIndex]);
                }
            } else if (e.key === 'Escape') {
                closeList();
            }
        });
        toggle.addEventListener('click', function (e) {
            e.preventDefault();
            if (searchTrigger) {
                if (listbox.hidden) openSearchList();
                else closeList();
                return;
            }
            if (listbox.hidden) {
                openList();
                loadOptions(input.value.trim());
                input.focus();
            } else {
                closeList();
            }
        });
        listbox.addEventListener('mousedown', function (e) {
            var li = e.target.closest('li[role="option"]');
            if (li) {
                e.preventDefault();
                selectOption(li);
            }
        });
        document.addEventListener('click', function (e) {
            if (!combo.contains(e.target)) closeList();
        });

        if (config.initialValue) input.value = config.initialValue;

        return {
            input: input,
            setStaticOptions: function (opts) {
                staticOptions = (opts || []).slice();
                loadOptions(input.value.trim());
            },
            setValue: function (val) {
                input.value = val || '';
            },
            getValue: function () {
                return input.value.trim();
            },
            refresh: function () {
                loadOptions(input.value.trim());
            },
        };
    }

    function initScorePlanBuilder() {
        if (form.getAttribute('data-score-ref-enabled') !== '1') return;

        var lookupUrl = form.getAttribute('data-score-ref-lookup-url');
        var schoolsUrl = form.getAttribute('data-score-ref-schools-url');
        var scoreRefSection = document.getElementById('gcScoreRefSection');
        var PLAN_KEYS = [
            'required_subjects', 'school_name', 'major_name', 'major_note',
            'min_score', 'min_rank', 'max_score', 'max_rank',
        ];
        var AUTO_LABELS = {
            major_note: '专业备注',
            min_score: '最低分',
            min_rank: '最低位',
            max_score: '最高分',
            max_rank: '最高位',
        };
        var SEARCHING_PLACEHOLDER = '正在搜索中····';

        function getDraftSchool(draftEl) {
            var inp = draftEl.querySelector('.gc-score-plan-school');
            return inp ? inp.value.trim() : '';
        }

        function getDraftMajor(draftEl) {
            var inp = draftEl.querySelector('.gc-score-plan-major');
            return inp ? inp.value.trim() : '';
        }

        function getSubjectTrack() {
            if (selectedElec.his) return '历史';
            if (selectedElec.phy) return '物理';
            return '';
        }

        function getPanelFromBlock(block) {
            if (!block) return null;
            var gid = block.getAttribute('data-score-plan-block');
            return gid ? majorSection.querySelector('[data-major-panel="' + gid + '"]') : null;
        }

        function getBlockFromPanel(panel) {
            if (!panel) return null;
            var gid = panel.getAttribute('data-major-panel');
            return gid ? majorSection.querySelector('[data-score-plan-block="' + gid + '"]') : null;
        }

        function getHiddenInput(block) {
            return block ? block.querySelector('.gc-score-plan-hidden') : null;
        }

        function readPlans(block) {
            var inp = getHiddenInput(block);
            if (!inp || !inp.value.trim()) return [];
            try {
                var arr = JSON.parse(inp.value);
                return Array.isArray(arr) ? arr : [];
            } catch (e) {
                return [];
            }
        }

        function writePlans(block, plans) {
            var inp = getHiddenInput(block);
            if (inp) inp.value = plans.length ? JSON.stringify(plans) : '';
        }

        function selectedMajorsInPanel(panel) {
            var list = [];
            if (!panel) return list;
            panel.querySelectorAll('[data-major-item].gc-major-btn--on').forEach(function (btn) {
                list.push({
                    id: btn.getAttribute('data-major-item'),
                    label: (btn.textContent || '').trim(),
                });
            });
            return list;
        }

        function lookupScore(school, major) {
            if (!lookupUrl) return Promise.resolve(null);
            var params = 'school=' + encodeURIComponent(school) + '&major=' + encodeURIComponent(major);
            var track = getSubjectTrack();
            if (track) params += '&subject_track=' + encodeURIComponent(track);
            return fetch(lookupUrl + '?' + params).then(function (r) { return r.json(); });
        }

        function displayVal(val) {
            return val == null || val === '' ? '暂无数据' : String(val);
        }

        function parseRankNum(val) {
            if (val == null || val === '' || val === '暂无数据' || val === '—') return null;
            var n = parseInt(String(val).replace(/[,，\s]/g, ''), 10);
            return isNaN(n) || n < 0 ? null : n;
        }

        function getMyRank() {
            var inp = form.querySelector('[data-field="score_rank_' + SCORE_ROW + '"]');
            return parseRankNum(inp ? inp.value : '');
        }

        /** 位次越小越好；返回行渐变右端色（左白右色） */
        function rankRowEndColor(myRank, minRank, maxRank) {
            if (myRank == null || minRank == null || maxRank == null) return null;
            var lo = Math.min(minRank, maxRank);
            var hi = Math.max(minRank, maxRank);
            if (hi <= 0 && lo <= 0) return null;

            function clamp01(x) {
                return Math.max(0, Math.min(1, x));
            }
            function lerp(a, b, t) {
                return Math.round(a + (b - a) * clamp01(t));
            }
            function rgb(r, g, b) {
                return 'rgb(' + r + ',' + g + ',' + b + ')';
            }
            /** 压低最深一档饱和度（0～1，越大越深） */
            function depth(t) {
                return clamp01(t) * 0.78;
            }

            /* 大于最高位：红色，超出越多越深（最深档已调浅） */
            if (myRank > hi) {
                var over = depth((myRank - hi) / Math.max(hi, 1));
                return rgb(lerp(254, 251, over), lerp(202, 168, over), lerp(202, 168, over));
            }
            /* 最低位～最高位：蓝色，越接近最低位（越安全）越深 */
            if (myRank >= lo && myRank <= hi) {
                var safe = hi > lo ? depth((hi - myRank) / (hi - lo)) : 0.4;
                return rgb(lerp(219, 147, safe), lerp(234, 191, safe), lerp(254, 248, safe));
            }
            /* 低于最低位：绿色；低于最低位×0.15 统一色；0.15～最低位 另一档绿色按距离变浅 */
            if (myRank < lo) {
                var threshold = lo * 0.15;
                if (myRank < threshold) {
                    return rgb(134, 239, 172);
                }
                var t = lo > threshold ? depth((myRank - threshold) / (lo - threshold)) : 0;
                return rgb(lerp(134, 187, t), lerp(239, 247, t), lerp(172, 208, t));
            }
            return null;
        }

        function updatePlanResultVisibility(block) {
            var result = block.querySelector('.gc-score-plan-result');
            if (!result) return;
            result.hidden = readPlans(block).length === 0;
        }

        function renderPlanTable(block) {
            var tbody = block.querySelector('.gc-score-plan-list');
            if (!tbody) return;
            var plans = readPlans(block);
            tbody.innerHTML = '';
            if (!plans.length) {
                updatePlanResultVisibility(block);
                return;
            }
            var myRank = getMyRank();
            plans.forEach(function (rec, idx) {
                var tr = document.createElement('tr');
                var endColor = rankRowEndColor(
                    myRank,
                    parseRankNum(rec.min_rank),
                    parseRankNum(rec.max_rank)
                );
                if (endColor) {
                    tr.className = 'gc-score-plan-row--rank';
                    tr.style.setProperty('--rank-end', endColor);
                }
                var seqTd = document.createElement('td');
                seqTd.textContent = String(idx + 1);
                tr.appendChild(seqTd);
                PLAN_KEYS.forEach(function (key) {
                    var td = document.createElement('td');
                    if (key === 'major_note') td.className = 'gc-score-cell--major_note';
                    td.textContent = displayVal(rec[key]);
                    tr.appendChild(td);
                });
                var actTd = document.createElement('td');
                actTd.className = 'no-print';
                var actWrap = document.createElement('div');
                actWrap.className = 'gc-score-plan-actions';
                var upBtn = document.createElement('button');
                upBtn.type = 'button';
                upBtn.className = 'gc-btn gc-score-plan-move-btn';
                upBtn.textContent = '向上移动';
                if (idx === 0) upBtn.disabled = true;
                upBtn.addEventListener('click', function () {
                    movePlanUp(block, idx);
                });
                var delBtn = document.createElement('button');
                delBtn.type = 'button';
                delBtn.className = 'gc-btn gc-score-plan-delete-btn';
                var delProgress = document.createElement('span');
                delProgress.className = 'gc-score-plan-delete-progress';
                var delLabel = document.createElement('span');
                delLabel.className = 'gc-score-plan-delete-label';
                delLabel.textContent = '长按删除';
                delBtn.appendChild(delProgress);
                delBtn.appendChild(delLabel);
                attachLongPressDelete(delBtn, block, idx, tr);
                actWrap.appendChild(upBtn);
                actWrap.appendChild(delBtn);
                actTd.appendChild(actWrap);
                tr.appendChild(actTd);
                tbody.appendChild(tr);
            });
            updatePlanResultVisibility(block);
            refreshDraftPickButtons(block);
        }

        function movePlanUp(block, index) {
            if (index <= 0) return;
            var plans = readPlans(block);
            var tmp = plans[index - 1];
            plans[index - 1] = plans[index];
            plans[index] = tmp;
            writePlans(block, plans);
            renderPlanTable(block);
            persistDraftQuiet();
        }

        var PLAN_DELETE_HOLD_MS = 1500;

        function deletePlanAt(block, index) {
            var plans = readPlans(block);
            if (index < 0 || index >= plans.length) return;
            plans.splice(index, 1);
            writePlans(block, plans);
            renderPlanTable(block);
            persistDraftQuiet();
        }

        var PLAN_DELETE_ANIM_MS = 280;

        function deletePlanRowWithAnimation(block, index, tr) {
            if (!tr || tr.classList.contains('gc-score-plan-row--deleting')) return;
            tr.classList.add('gc-score-plan-row--deleting');
            requestAnimationFrame(function () {
                tr.classList.add('gc-score-plan-row--delete-out');
            });
            setTimeout(function () {
                deletePlanAt(block, index);
            }, PLAN_DELETE_ANIM_MS);
        }

        function attachLongPressDelete(btn, block, index, tr) {
            var progress = btn.querySelector('.gc-score-plan-delete-progress');
            var raf = null;
            var startTs = 0;
            var completed = false;

            function resetProgress() {
                if (completed) return;
                if (raf) cancelAnimationFrame(raf);
                raf = null;
                startTs = 0;
                btn.classList.remove('gc-score-plan-delete-btn--holding');
                if (progress) progress.style.width = '0%';
            }

            function tick() {
                if (!startTs) return;
                var elapsed = Date.now() - startTs;
                var pct = Math.min(100, (elapsed / PLAN_DELETE_HOLD_MS) * 100);
                if (progress) progress.style.width = pct + '%';
                if (elapsed >= PLAN_DELETE_HOLD_MS) {
                    completed = true;
                    if (raf) cancelAnimationFrame(raf);
                    raf = null;
                    btn.classList.remove('gc-score-plan-delete-btn--holding');
                    if (progress) progress.style.width = '100%';
                    btn.disabled = true;
                    deletePlanRowWithAnimation(block, index, tr);
                    return;
                }
                raf = requestAnimationFrame(tick);
            }

            function startHold(e) {
                if (btn.disabled || completed) return;
                if (e.type === 'mousedown' && e.button !== 0) return;
                e.preventDefault();
                resetProgress();
                btn.classList.add('gc-score-plan-delete-btn--holding');
                startTs = Date.now();
                raf = requestAnimationFrame(tick);
            }

            function onTouchMove(e) {
                if (startTs && !completed) e.preventDefault();
            }

            btn.addEventListener('mousedown', startHold);
            btn.addEventListener('touchstart', startHold, { passive: false });
            btn.addEventListener('touchmove', onTouchMove, { passive: false });
            btn.addEventListener('mouseup', resetProgress);
            btn.addEventListener('mouseleave', resetProgress);
            btn.addEventListener('touchend', resetProgress);
            btn.addEventListener('touchcancel', resetProgress);
            btn.addEventListener('contextmenu', function (e) { e.preventDefault(); });
        }

        function isPlanDuplicate(block, school, major, record) {
            var s = String(school || '').trim();
            var m = String(major || '').trim();
            if (!s && record) s = String(record.school_name || '').trim();
            if (!m && record) m = String(record.major_name || '').trim();
            if (!s || !m) return false;
            return readPlans(block).some(function (p) {
                return String(p.school_name || '').trim() === s
                    && String(p.major_name || '').trim() === m;
            });
        }

        function updateDraftPickButton(draftEl, block) {
            if (!draftEl || !block) return;
            var pickBtn = draftEl.querySelector('.gc-score-plan-pick-btn');
            if (!pickBtn) return;
            var dup = isPlanDuplicate(
                block,
                getDraftSchool(draftEl),
                getDraftMajor(draftEl),
                draftEl._scoreRecord
            );
            pickBtn.disabled = dup;
            pickBtn.classList.toggle('gc-score-plan-pick-btn--dup', dup);
        }

        function refreshDraftPickButtons(block) {
            if (!block) return;
            block.querySelectorAll('.gc-score-plan-draft').forEach(function (draft) {
                updateDraftPickButton(draft, block);
            });
        }

        function fillDraftAutoFields(draftEl, record) {
            draftEl.querySelectorAll('[data-auto-key]').forEach(function (el) {
                var key = el.getAttribute('data-auto-key');
                var val = record && record[key] != null ? record[key] : '暂无数据';
                if (el.tagName === 'SPAN') {
                    el.textContent = displayVal(val);
                    el.classList.remove('gc-score-auto--loading');
                }
            });
            draftEl._scoreRecord = record;
        }

        function setDraftAutoFieldsLoading(draftEl) {
            draftEl.querySelectorAll('[data-auto-key]').forEach(function (el) {
                if (el.tagName === 'SPAN') {
                    el.textContent = SEARCHING_PLACEHOLDER;
                    el.classList.add('gc-score-auto--loading');
                }
            });
            draftEl._scoreRecord = null;
        }

        function runDraftLookup(draftEl, immediate) {
            var block = draftEl._scorePlanBlock;
            if (draftEl._lookupTimer) {
                clearTimeout(draftEl._lookupTimer);
                draftEl._lookupTimer = null;
            }
            var school = getDraftSchool(draftEl);
            var major = getDraftMajor(draftEl);
            if (!school || !major) {
                draftEl._lookupSeq = (draftEl._lookupSeq || 0) + 1;
                fillDraftAutoFields(draftEl, null);
                draftEl._scoreRecord = null;
                updateDraftPickButton(draftEl, block);
                return;
            }
            setDraftAutoFieldsLoading(draftEl);
            updateDraftPickButton(draftEl, block);
            var delay = immediate ? 0 : 280;
            draftEl._lookupTimer = setTimeout(function () {
                draftEl._lookupTimer = null;
                var schoolNow = getDraftSchool(draftEl);
                var majorNow = getDraftMajor(draftEl);
                if (!schoolNow || !majorNow) {
                    fillDraftAutoFields(draftEl, null);
                    updateDraftPickButton(draftEl, block);
                    return;
                }
                var seq = (draftEl._lookupSeq = (draftEl._lookupSeq || 0) + 1);
                lookupScore(schoolNow, majorNow).then(function (data) {
                    if (draftEl._lookupSeq !== seq) return;
                    if (getDraftSchool(draftEl) !== schoolNow || getDraftMajor(draftEl) !== majorNow) return;
                    if (!data || !data.ok) {
                        fillDraftAutoFields(draftEl, null);
                        updateDraftPickButton(draftEl, block);
                        return;
                    }
                    fillDraftAutoFields(draftEl, data.record);
                    updateDraftPickButton(draftEl, block);
                }).catch(function () {
                    if (draftEl._lookupSeq !== seq) return;
                    if (getDraftSchool(draftEl) !== schoolNow || getDraftMajor(draftEl) !== majorNow) return;
                    fillDraftAutoFields(draftEl, null);
                    updateDraftPickButton(draftEl, block);
                });
            }, delay);
        }

        function createDraftRow(block) {
            var panel = getPanelFromBlock(block);
            var draft = document.createElement('div');
            draft.className = 'gc-score-plan-draft';
            draft._scorePlanBlock = block;

            var schoolWrap = document.createElement('div');
            schoolWrap.className = 'gc-score-plan-draft-field';
            var schoolLab = document.createElement('label');
            schoolLab.textContent = '院校';
            draft._schoolCombo = attachSearchCombobox(schoolLab, {
                inputClass: 'gc-score-plan-school',
                placeholder: '请填写院校',
                emptyText: '无匹配院校',
                openOn: 'search',
                toggleLabel: '搜索院校',
                debounceMs: 250,
                fetchOptions: function (q, done) {
                    if (!schoolsUrl) {
                        done([]);
                        return;
                    }
                    fetch(schoolsUrl + '?q=' + encodeURIComponent(q || '') + '&limit=80')
                        .then(function (r) { return r.json(); })
                        .then(function (data) {
                            done((data && data.ok) ? (data.schools || []) : []);
                        })
                        .catch(function () { done([]); });
                },
                onInput: function () { runDraftLookup(draft, false); },
                onChange: function () { runDraftLookup(draft, true); },
            });
            schoolWrap.appendChild(schoolLab);

            var majorLabels = selectedMajorsInPanel(panel).map(function (m) { return m.label; });
            var majorWrap = document.createElement('div');
            majorWrap.className = 'gc-score-plan-draft-field';
            var majorLab = document.createElement('label');
            majorLab.textContent = '专业';
            draft._majorCombo = attachSearchCombobox(majorLab, {
                inputClass: 'gc-score-plan-major',
                placeholder: majorLabels.length ? '输入或选择专业' : '请先在上方点选专业',
                emptyText: '无匹配专业',
                toggleLabel: '展开专业列表',
                staticOptions: majorLabels,
                initialValue: majorLabels.length === 1 ? majorLabels[0] : '',
                onInput: function () { runDraftLookup(draft, false); },
                onChange: function () { runDraftLookup(draft, true); },
            });
            majorWrap.appendChild(majorLab);

            draft.appendChild(schoolWrap);
            draft.appendChild(majorWrap);

            ['major_note', 'min_score', 'min_rank', 'max_score', 'max_rank'].forEach(function (key) {
                var wrap = document.createElement('div');
                wrap.className = 'gc-score-plan-draft-field gc-score-plan-draft-field--readonly';
                if (key !== 'major_note') wrap.classList.add('gc-score-plan-draft-field--stat');
                var lab = document.createElement('label');
                lab.textContent = AUTO_LABELS[key];
                var span = document.createElement('span');
                span.setAttribute('data-auto-key', key);
                span.textContent = '—';
                lab.appendChild(span);
                wrap.appendChild(lab);
                draft.appendChild(wrap);
            });

            var actWrap = document.createElement('div');
            actWrap.className = 'gc-score-plan-draft-actions';
            var pickBtn = document.createElement('button');
            pickBtn.type = 'button';
            pickBtn.className = 'gc-btn gc-score-plan-pick-btn';
            pickBtn.textContent = '优选';
            var dropBtn = document.createElement('button');
            dropBtn.type = 'button';
            dropBtn.className = 'gc-btn gc-score-plan-drop-btn';
            dropBtn.textContent = '放弃';
            actWrap.appendChild(pickBtn);
            actWrap.appendChild(dropBtn);
            draft.appendChild(actWrap);

            dropBtn.addEventListener('click', function () {
                if (draft.parentNode) draft.parentNode.removeChild(draft);
            });

            pickBtn.addEventListener('click', function () {
                if (pickBtn.disabled) return;
                var school = getDraftSchool(draft);
                var major = getDraftMajor(draft);
                if (!school || !major) {
                    alert('请先选择或填写院校，并选择专业');
                    return;
                }
                if (isPlanDuplicate(block, school, major, draft._scoreRecord)) {
                    updateDraftPickButton(draft, block);
                    return;
                }
                var rec = draft._scoreRecord;
                if (!rec) {
                    lookupScore(school, major).then(function (data) {
                        if (!data || !data.ok) {
                            alert('查询失败，请稍后重试');
                            return;
                        }
                        pushPlan(block, data.record, draft);
                    });
                    return;
                }
                pushPlan(block, rec, draft);
            });

            if (getDraftMajor(draft)) runDraftLookup(draft, true);
            else updateDraftPickButton(draft, block);
            return draft;
        }

        function pushPlan(block, record, draftEl) {
            var plans = readPlans(block);
            var school = String((record && record.school_name) || '').trim();
            var major = String((record && record.major_name) || '').trim();
            if (!school && draftEl) school = getDraftSchool(draftEl);
            if (!major && draftEl) major = getDraftMajor(draftEl);
            var isDup = plans.some(function (p) {
                return String(p.school_name || '').trim() === school
                    && String(p.major_name || '').trim() === major;
            });
            if (isDup) return;
            var row = {};
            PLAN_KEYS.forEach(function (key) {
                row[key] = record && record[key] != null ? record[key] : '暂无数据';
            });
            if (school && (!row.school_name || row.school_name === '暂无数据')) {
                row.school_name = school;
            }
            if (major && (!row.major_name || row.major_name === '暂无数据')) {
                row.major_name = major;
            }
            plans.push(row);
            writePlans(block, plans);
            renderPlanTable(block);
            if (draftEl && draftEl.parentNode) draftEl.parentNode.removeChild(draftEl);
            persistDraftQuiet();
        }

        function refreshDraftMajorSelects(panel) {
            var block = getBlockFromPanel(panel);
            if (!block) return;
            var majorLabels = selectedMajorsInPanel(panel).map(function (m) { return m.label; });
            block.querySelectorAll('.gc-score-plan-draft').forEach(function (draft) {
                if (!draft._majorCombo) return;
                var prev = draft._majorCombo.getValue();
                draft._majorCombo.setStaticOptions(majorLabels);
                if (prev && majorLabels.indexOf(prev) >= 0) {
                    draft._majorCombo.setValue(prev);
                } else if (majorLabels.length === 1) {
                    draft._majorCombo.setValue(majorLabels[0]);
                } else {
                    draft._majorCombo.setValue('');
                }
                runDraftLookup(draft, true);
            });
        }

        function clearScorePlansInPanel(panel) {
            var block = getBlockFromPanel(panel);
            if (!block) return;
            writePlans(block, []);
            renderPlanTable(block);
            var drafts = block.querySelector('.gc-score-plan-drafts');
            if (drafts) drafts.innerHTML = '';
        }

        function restoreAllScorePlans() {
            if (!majorSection) return;
            majorSection.querySelectorAll('.gc-score-plan-block').forEach(function (block) {
                renderPlanTable(block);
            });
        }

        function refreshAllScorePlanTables() {
            restoreAllScorePlans();
        }

        var myRankInp = form.querySelector('[data-field="score_rank_' + SCORE_ROW + '"]');
        if (myRankInp) {
            myRankInp.addEventListener('input', refreshAllScorePlanTables);
            myRankInp.addEventListener('change', refreshAllScorePlanTables);
        }

        majorSection.querySelectorAll('.gc-score-plan-add').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var block = btn.closest('.gc-score-plan-block');
                if (!block) return;
                var panel = getPanelFromBlock(block);
                if (!selectedMajorsInPanel(panel).length) {
                    alert('请先在上方点选至少一个专业');
                    return;
                }
                var drafts = block.querySelector('.gc-score-plan-drafts');
                if (!drafts) return;
                drafts.appendChild(createDraftRow(block));
            });
        });

        function clearAllScorePlans() {
            if (!majorSection) return;
            majorSection.querySelectorAll('.gc-score-plan-block').forEach(function (block) {
                writePlans(block, []);
                renderPlanTable(block);
                var drafts = block.querySelector('.gc-score-plan-drafts');
                if (drafts) drafts.innerHTML = '';
            });
            persistDraftQuiet();
        }

        function updateScoreRefProvincePlans() {
            var jilin = isJilinGaokaoProvince();
            if (!majorSection) return;
            majorSection.querySelectorAll('.gc-score-plan-block').forEach(function (block) {
                block.classList.toggle('gc-score-plan-block--off', !jilin);
                var addBtn = block.querySelector('.gc-score-plan-add');
                if (addBtn) addBtn.disabled = !jilin;
            });
            if (!jilin) clearAllScorePlans();
            else restoreAllScorePlans();
        }

        restoreAllScorePlans();
        window._gcUpdateScoreRefProvincePlans = updateScoreRefProvincePlans;

        function refreshAllDraftLookups() {
            if (!majorSection) return;
            majorSection.querySelectorAll('.gc-score-plan-draft').forEach(function (draft) {
                runDraftLookup(draft, true);
            });
        }

        window._gcRefreshScorePlanDrafts = refreshDraftMajorSelects;
        window._gcClearScorePlansInPanel = clearScorePlansInPanel;
        window._gcRestoreAllScorePlans = restoreAllScorePlans;
        window._gcRefreshAllScorePlanTables = refreshAllScorePlanTables;
        window._gcRefreshAllScorePlanLookups = refreshAllDraftLookups;
    }

    function initScoreRefSearch() {
        var apiUrl = form.getAttribute('data-score-ref-url');
        var schoolsUrl = form.getAttribute('data-score-ref-schools-url');
        var schoolLabel = document.getElementById('scoreRefSchoolLabel');
        var majorLabel = document.getElementById('scoreRefMajorLabel');
        var tbody = document.getElementById('scoreRefTbody');
        var meta = document.getElementById('scoreRefMeta');
        if (!apiUrl || !schoolLabel || !majorLabel || !tbody) return;

        var refDisabled = form.getAttribute('data-score-ref-enabled') !== '1';
        var debounce = null;
        var schoolCombo = attachSearchCombobox(schoolLabel, {
            comboClass: 'gc-score-ref-combo',
            inputClass: 'gc-score-ref-school-input',
            placeholder: '请填写院校',
            emptyText: '无匹配院校',
            openOn: 'search',
            toggleLabel: '搜索院校',
            debounceMs: 250,
            disabled: refDisabled,
            fetchOptions: schoolsUrl ? function (q, done) {
                fetch(schoolsUrl + '?q=' + encodeURIComponent(q || '') + '&limit=80')
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        done((data && data.ok) ? (data.schools || []) : []);
                    })
                    .catch(function () { done([]); });
            } : null,
            onInput: function () { scheduleSearch(); },
            onChange: function () { runSearch(); },
        });
        var majorCombo = attachSearchCombobox(majorLabel, {
            comboClass: 'gc-score-ref-combo',
            inputClass: 'gc-score-ref-major-input',
            placeholder: '请填写专业',
            emptyText: '无匹配专业',
            openOn: 'search',
            toggleLabel: '搜索专业',
            debounceMs: 250,
            disabled: refDisabled,
            fetchOptions: function (q, done) {
                var qq = (q || '').trim();
                var school = schoolCombo.getValue();
                if (!qq && !school) {
                    done([]);
                    return;
                }
                var params = 'limit=200';
                if (school) params += '&school=' + encodeURIComponent(school);
                if (qq) params += '&major=' + encodeURIComponent(qq);
                fetch(apiUrl + '?' + params)
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        if (!data || !data.ok) {
                            done([]);
                            return;
                        }
                        var seen = {};
                        var names = [];
                        (data.records || []).forEach(function (rec) {
                            var m = String(rec.major_name || '').trim();
                            if (!m || seen[m]) return;
                            seen[m] = true;
                            names.push(m);
                        });
                        names.sort();
                        done(names.slice(0, 80));
                    })
                    .catch(function () { done([]); });
            },
            onInput: function () { scheduleSearch(); },
            onChange: function () { runSearch(); },
        });

        var colCount = tbody.closest('table')
            ? tbody.closest('table').querySelectorAll('thead th').length
            : 9;

        function renderEmpty(msg) {
            tbody.innerHTML = '';
            var tr = document.createElement('tr');
            tr.className = 'gc-score-ref-empty';
            var td = document.createElement('td');
            td.colSpan = colCount || 9;
            td.textContent = msg;
            tr.appendChild(td);
            tbody.appendChild(tr);
        }

        function renderRows(records) {
            tbody.innerHTML = '';
            if (!records || !records.length) {
                renderEmpty('未找到匹配记录，请调整院校或专业关键词');
                return;
            }
            records.forEach(function (rec) {
                var tr = document.createElement('tr');
                [
                    'required_subjects', 'school_name', 'major_name', 'major_note',
                    'min_score', 'min_rank', 'max_score', 'max_rank',
                ].forEach(function (key) {
                    var td = document.createElement('td');
                    if (key === 'major_note') td.className = 'gc-score-cell--major_note';
                    var val = rec[key];
                    td.textContent = val == null || val === '' ? '—' : String(val);
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
        }

        function runSearch() {
            var school = schoolCombo.getValue();
            var major = majorCombo.getValue();
            if (!school && !major) {
                if (meta) meta.textContent = '';
                renderEmpty('输入院校或专业关键词开始查询');
                return;
            }
            if (meta) meta.textContent = '查询中…';
            var params = 'limit=80';
            if (school) params += '&school=' + encodeURIComponent(school);
            if (major) params += '&major=' + encodeURIComponent(major);
            fetch(apiUrl + '?' + params)
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (!data || !data.ok) {
                        if (meta) meta.textContent = '';
                        renderEmpty((data && data.message) || '查询失败');
                        return;
                    }
                    if (meta) {
                        meta.textContent = data.total > data.records.length
                            ? ('找到 ' + data.total + ' 条，显示前 ' + data.records.length + ' 条')
                            : ('找到 ' + data.total + ' 条');
                    }
                    renderRows(data.records);
                })
                .catch(function () {
                    if (meta) meta.textContent = '';
                    renderEmpty('查询失败，请稍后重试');
                });
        }

        function scheduleSearch() {
            clearTimeout(debounce);
            debounce = setTimeout(runSearch, 300);
        }
    }

    function initEnrollmentPlanSearch() {
        var apiUrl = form.getAttribute('data-enrollment-plan-url');
        var schoolsUrl = form.getAttribute('data-enrollment-plan-schools-url');
        var province = form.getAttribute('data-enrollment-plan-province') || '吉林';
        var schoolLabel = document.getElementById('enrollPlanSchoolLabel');
        var majorLabel = document.getElementById('enrollPlanMajorLabel');
        var tbody = document.getElementById('enrollPlanTbody');
        var meta = document.getElementById('enrollPlanMeta');
        if (!apiUrl || !schoolLabel || !majorLabel || !tbody) return;

        var refDisabled = form.getAttribute('data-enrollment-plan-enabled') !== '1';
        var debounce = null;
        var colKeys = [
            'major_code', 'school_name', 'major_name', 'batch', 'category',
            'duration', 'plan_count', 'reselect_subjects', 'enrollment_gender',
            'enrollment_remark', 'major_note',
        ];
        var colCount = tbody.closest('table')
            ? tbody.closest('table').querySelectorAll('thead th').length
            : colKeys.length;

        function provinceParam() {
            return '&province=' + encodeURIComponent(province);
        }

        var filterSelects = form.querySelectorAll('[data-enroll-filter]');

        function getFilterValues() {
            var out = {};
            filterSelects.forEach(function (sel) {
                var key = sel.getAttribute('data-enroll-filter');
                if (key) out[key] = (sel.value || '').trim();
            });
            return out;
        }

        function appendFilterParams(params) {
            var f = getFilterValues();
            if (f.batch) params += '&batch=' + encodeURIComponent(f.batch);
            if (f.category) params += '&category=' + encodeURIComponent(f.category);
            if (f.reselect_subjects) params += '&reselect=' + encodeURIComponent(f.reselect_subjects);
            if (f.enrollment_gender) params += '&gender=' + encodeURIComponent(f.enrollment_gender);
            return params;
        }

        function hasActiveFilters() {
            var f = getFilterValues();
            return !!(f.batch || f.category || f.reselect_subjects || f.enrollment_gender);
        }

        function hasActiveQuery(school, major) {
            return !!(school || major || hasActiveFilters());
        }

        filterSelects.forEach(function (sel) {
            sel.addEventListener('change', function () { runSearch(); });
        });

        var schoolCombo = attachSearchCombobox(schoolLabel, {
            comboClass: 'gc-score-ref-combo',
            inputClass: 'gc-score-ref-school-input',
            placeholder: '请填写院校',
            emptyText: '无匹配院校',
            openOn: 'search',
            toggleLabel: '搜索院校',
            debounceMs: 250,
            disabled: refDisabled,
            fetchOptions: schoolsUrl ? function (q, done) {
                fetch(schoolsUrl + '?q=' + encodeURIComponent(q || '') + '&limit=80' + provinceParam())
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        done((data && data.ok) ? (data.schools || []) : []);
                    })
                    .catch(function () { done([]); });
            } : null,
            onInput: function () { scheduleSearch(); },
            onChange: function () { runSearch(); },
        });
        var majorCombo = attachSearchCombobox(majorLabel, {
            comboClass: 'gc-score-ref-combo',
            inputClass: 'gc-score-ref-major-input',
            placeholder: '请填写专业',
            emptyText: '无匹配专业',
            openOn: 'search',
            toggleLabel: '搜索专业',
            debounceMs: 250,
            disabled: refDisabled,
            fetchOptions: function (q, done) {
                var qq = (q || '').trim();
                var school = schoolCombo.getValue();
                if (!qq && !school) {
                    done([]);
                    return;
                }
                var params = 'limit=200' + provinceParam();
                if (school) params += '&school=' + encodeURIComponent(school);
                if (qq) params += '&major=' + encodeURIComponent(qq);
                params = appendFilterParams(params);
                if (!hasActiveQuery(school, qq)) {
                    done([]);
                    return;
                }
                fetch(apiUrl + '?' + params)
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        if (!data || !data.ok) {
                            done([]);
                            return;
                        }
                        var seen = {};
                        var names = [];
                        (data.records || []).forEach(function (rec) {
                            var m = String(rec.major_name || '').trim();
                            if (!m || seen[m]) return;
                            seen[m] = true;
                            names.push(m);
                        });
                        names.sort();
                        done(names.slice(0, 80));
                    })
                    .catch(function () { done([]); });
            },
            onInput: function () { scheduleSearch(); },
            onChange: function () { runSearch(); },
        });

        function renderEmpty(msg) {
            tbody.innerHTML = '';
            var tr = document.createElement('tr');
            tr.className = 'gc-score-ref-empty';
            var td = document.createElement('td');
            td.colSpan = colCount || 11;
            td.textContent = msg;
            tr.appendChild(td);
            tbody.appendChild(tr);
        }

        function renderRows(records) {
            tbody.innerHTML = '';
            if (!records || !records.length) {
                renderEmpty('未找到匹配记录，请调整院校或专业关键词');
                return;
            }
            records.forEach(function (rec) {
                var tr = document.createElement('tr');
                colKeys.forEach(function (key) {
                    var td = document.createElement('td');
                    if (key === 'major_note') td.className = 'gc-score-cell--major_note';
                    if (key === 'enrollment_remark') td.className = 'gc-enroll-col--enroll-remark';
                    var val = rec[key];
                    td.textContent = val == null || val === '' ? '—' : String(val);
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
        }

        function runSearch() {
            var school = schoolCombo.getValue();
            var major = majorCombo.getValue();
            if (!hasActiveQuery(school, major)) {
                if (meta) meta.textContent = '';
                renderEmpty('输入院校或专业，或选择下方筛选条件开始查询');
                return;
            }
            if (meta) meta.textContent = '查询中…';
            var params = 'limit=100' + provinceParam();
            if (school) params += '&school=' + encodeURIComponent(school);
            if (major) params += '&major=' + encodeURIComponent(major);
            params = appendFilterParams(params);
            fetch(apiUrl + '?' + params)
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (!data || !data.ok) {
                        if (meta) meta.textContent = '';
                        renderEmpty((data && data.message) || '查询失败');
                        return;
                    }
                    if (meta) {
                        meta.textContent = data.total > data.records.length
                            ? ('找到 ' + data.total + ' 条，显示前 ' + data.records.length + ' 条')
                            : ('找到 ' + data.total + ' 条');
                    }
                    renderRows(data.records);
                })
                .catch(function () {
                    if (meta) meta.textContent = '';
                    renderEmpty('查询失败，请稍后重试');
                });
        }

        function scheduleSearch() {
            clearTimeout(debounce);
            debounce = setTimeout(runSearch, 300);
        }
    }

    initScorePlanBuilder();
    initScoreRefSearch();
    initEnrollmentPlanSearch();
    updateJilinOnlySectionsVisibility();
})();
