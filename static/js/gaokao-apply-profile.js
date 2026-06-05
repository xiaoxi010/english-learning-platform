(function () {
    var form = document.getElementById('gaokaoApplyForm');
    if (!form) return;

    var STORAGE_KEY = 'gaokao_apply_profile';
    var systemUrl = form.getAttribute('data-system-url');
    var provinceRegion = document.getElementById('gaProvinceRegion');
    var majorSection = document.getElementById('gaMajorSection');
    var majorDisciplines = document.getElementById('gaMajorDisciplines');
    var majorSearch = document.getElementById('gaMajorSearch');
    var majorSearchClear = document.getElementById('gaMajorSearchClear');

    function fields() {
        return form.querySelectorAll('[data-field]');
    }

    function getSelectedProvinces() {
        if (!provinceRegion) return [];
        var out = [];
        provinceRegion.querySelectorAll('input[type=checkbox]:checked').forEach(function (cb) {
            var code = cb.getAttribute('data-province-code') || cb.value;
            if (code && out.indexOf(code) < 0) out.push(code);
        });
        return out;
    }

    function getSelectedMajorGroups() {
        if (!majorDisciplines) return { ids: [], titles: [] };
        var ids = [];
        var titles = [];
        majorDisciplines.querySelectorAll('.gc-major-btn[data-major-group].gc-major-btn--on').forEach(function (btn) {
            var id = btn.getAttribute('data-major-group');
            var title = btn.getAttribute('data-major-title') || btn.textContent.trim();
            if (id && ids.indexOf(id) < 0) {
                ids.push(id);
                titles.push(title);
            }
        });
        return { ids: ids, titles: titles };
    }

    function readForm() {
        if (window.gaApplyScores && window.gaApplyScores.flush) {
            window.gaApplyScores.flush();
        }
        var majors = getSelectedMajorGroups();
        var data = {
            target_provinces: getSelectedProvinces(),
            target_major_groups: majors.ids,
            target_majors: majors.titles
        };
        fields().forEach(function (el) {
            data[el.getAttribute('data-field')] = el.value;
        });
        if (window.gaApplyScores && window.gaApplyScores.syncLegacyFields) {
            window.gaApplyScores.syncLegacyFields(data);
        }
        return data;
    }

    function loadRaw() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch (e) {
            return null;
        }
    }

    function saveForm(showTip) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(readForm()));
        updateProvinceSummary();
        syncMajorUi();
        if (showTip) alert('草稿已保存');
    }

    function syncProvinceChecks(list) {
        if (!provinceRegion) return;
        provinceRegion.querySelectorAll('input[type=checkbox]').forEach(function (cb) {
            var code = cb.getAttribute('data-province-code') || '';
            cb.checked = list.indexOf(code) >= 0;
        });
        syncRegionRowStates();
        updateProvinceSummary();
    }

    function syncMajorGroups(groupIds) {
        if (!majorDisciplines) return;
        var set = {};
        (groupIds || []).forEach(function (id) { set[id] = true; });
        majorDisciplines.querySelectorAll('.gc-major-btn[data-major-group]').forEach(function (btn) {
            btn.classList.toggle('gc-major-btn--on', !!set[btn.getAttribute('data-major-group')]);
        });
        syncMajorUi();
    }

    function updateProvinceSummary() {
        var countEl = document.getElementById('gaProvinceCount');
        var n = getSelectedProvinces().length;
        if (countEl) countEl.textContent = '已选 ' + n + ' 省';
    }

    function updateMajorSummary() {
        var countEl = document.getElementById('gaMajorCount');
        var n = getSelectedMajorGroups().ids.length;
        if (countEl) countEl.textContent = '已选 ' + n + ' 类';
    }

    function regionRowSelectionCount(row) {
        if (!row) return 0;
        return row.querySelectorAll('.gc-region-province-list input[type=checkbox]:checked').length;
    }

    function syncRegionRowStates() {
        if (!provinceRegion) return;
        provinceRegion.querySelectorAll('.gc-region-row').forEach(function (row) {
            var n = regionRowSelectionCount(row);
            row.classList.toggle('gc-collapse--has-selection', n > 0);
            var clearBtn = row.querySelector('.ga-region-clear');
            if (clearBtn) clearBtn.hidden = n <= 0;
        });
    }

    function disciplineSelectionCount(block) {
        if (!block) return 0;
        return block.querySelectorAll('.gc-major-btn[data-major-group].gc-major-btn--on').length;
    }

    function syncMajorDisciplineStates() {
        if (!majorDisciplines) return;
        majorDisciplines.querySelectorAll('.gc-major-discipline').forEach(function (block) {
            var n = disciplineSelectionCount(block);
            var countBadge = block.querySelector('.gc-collapse-count');
            if (countBadge) {
                countBadge.hidden = n <= 0;
                countBadge.textContent = String(n);
            }
            block.classList.toggle('gc-collapse--has-selection', n > 0);
            var clearBtn = block.querySelector('.ga-disc-clear');
            if (clearBtn) clearBtn.hidden = n <= 0;
        });
        updateMajorSummary();
    }

    function syncMajorUi() {
        syncMajorDisciplineStates();
    }

    function bindRegionSection() {
        if (!provinceRegion) return;
        provinceRegion.querySelectorAll('input[type=checkbox]').forEach(function (cb) {
            cb.addEventListener('change', function () {
                syncRegionRowStates();
                updateProvinceSummary();
                saveForm(false);
            });
        });
        provinceRegion.querySelectorAll('.ga-region-select-all').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var row = btn.closest('.gc-region-row');
                if (!row) return;
                row.querySelectorAll('.gc-region-province-list input[type=checkbox]').forEach(function (cb) {
                    cb.checked = true;
                });
                syncRegionRowStates();
                updateProvinceSummary();
                saveForm(false);
            });
        });
        provinceRegion.querySelectorAll('.ga-region-clear').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var row = btn.closest('.gc-region-row');
                if (!row) return;
                row.querySelectorAll('.gc-region-province-list input[type=checkbox]').forEach(function (cb) {
                    cb.checked = false;
                });
                syncRegionRowStates();
                updateProvinceSummary();
                saveForm(false);
            });
        });
    }

    function toggleCollapse(trigger) {
        var row = trigger.closest('.gc-collapse');
        if (!row) return;
        var body = row.querySelector('.gc-collapse-body');
        var expanded = trigger.getAttribute('aria-expanded') === 'true';
        trigger.setAttribute('aria-expanded', expanded ? 'false' : 'true');
        if (body) body.hidden = expanded;
    }

    function expandAllMajorDisciplines() {
        if (!majorDisciplines) return;
        majorDisciplines.querySelectorAll('.gc-major-discipline').forEach(function (block) {
            var trigger = block.querySelector('.gc-collapse-trigger');
            var body = block.querySelector('.gc-collapse-body');
            if (trigger) trigger.setAttribute('aria-expanded', 'true');
            if (body) body.hidden = false;
        });
    }

    function bindMajorSection() {
        if (!majorDisciplines) return;

        majorDisciplines.querySelectorAll('.gc-collapse-trigger').forEach(function (btn) {
            btn.addEventListener('click', function () {
                toggleCollapse(btn);
            });
        });

        majorDisciplines.querySelectorAll('.gc-major-btn[data-major-group]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                btn.classList.toggle('gc-major-btn--on');
                syncMajorUi();
                saveForm(false);
            });
        });

        majorDisciplines.querySelectorAll('.ga-disc-select-all').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var discId = btn.getAttribute('data-discipline');
                var block = majorDisciplines.querySelector('.gc-major-discipline[data-discipline="' + discId + '"]');
                if (!block) return;
                block.querySelectorAll('.gc-major-btn[data-major-group]').forEach(function (catBtn) {
                    if (!catBtn.classList.contains('gc-major-btn--hidden')) {
                        catBtn.classList.add('gc-major-btn--on');
                    }
                });
                syncMajorUi();
                saveForm(false);
                var trigger = block.querySelector('.gc-collapse-trigger');
                if (trigger && trigger.getAttribute('aria-expanded') !== 'true') {
                    toggleCollapse(trigger);
                }
            });
        });

        majorDisciplines.querySelectorAll('.ga-disc-clear').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var discId = btn.getAttribute('data-discipline');
                var block = majorDisciplines.querySelector('.gc-major-discipline[data-discipline="' + discId + '"]');
                if (!block) return;
                block.querySelectorAll('.gc-major-btn[data-major-group]').forEach(function (catBtn) {
                    catBtn.classList.remove('gc-major-btn--on');
                });
                syncMajorUi();
                saveForm(false);
            });
        });
    }

    function filterMajorSearch() {
        if (!majorDisciplines) return;
        var q = (majorSearch && majorSearch.value || '').trim().toLowerCase();
        if (majorSearchClear) majorSearchClear.hidden = !q;

        majorDisciplines.querySelectorAll('.gc-major-btn[data-major-group]').forEach(function (btn) {
            var text = (btn.getAttribute('data-search-text') || btn.textContent || '').toLowerCase();
            btn.classList.toggle('gc-major-btn--hidden', !!q && text.indexOf(q) < 0);
        });

        majorDisciplines.querySelectorAll('.gc-major-discipline').forEach(function (block) {
            var visible = 0;
            block.querySelectorAll('.gc-major-btn[data-major-group]').forEach(function (btn) {
                if (!btn.classList.contains('gc-major-btn--hidden')) visible += 1;
            });
            block.classList.toggle('gc-major-discipline--filter-empty', !!q && visible === 0);
            if (q && visible > 0) {
                var trigger = block.querySelector('.gc-collapse-trigger');
                var body = block.querySelector('.gc-collapse-body');
                if (trigger) trigger.setAttribute('aria-expanded', 'true');
                if (body) body.hidden = false;
            }
        });
    }

    if (majorSearch) {
        majorSearch.addEventListener('input', filterMajorSearch);
    }
    if (majorSearchClear) {
        majorSearchClear.addEventListener('click', function () {
            if (majorSearch) majorSearch.value = '';
            filterMajorSearch();
        });
    }

    function applyToForm(data) {
        if (!data) return;
        if (window.gaApplyScores && window.gaApplyScores.migrateDraft) {
            data = window.gaApplyScores.migrateDraft(Object.assign({}, data));
        }
        fields().forEach(function (el) {
            var key = el.getAttribute('data-field');
            if (data[key] != null && data[key] !== '') el.value = data[key];
        });
        if (window.gaApplyScores && window.gaApplyScores.restoreElectives) {
            window.gaApplyScores.restoreElectives();
        }
        syncProvinceChecks(data.target_provinces || []);
        var groupIds = data.target_major_groups || [];
        if (!groupIds.length && data.target_majors && data.target_majors.length) {
            syncMajorGroupsByTitles(data.target_majors);
        } else {
            syncMajorGroups(groupIds);
        }
    }

    function syncMajorGroupsByTitles(titles) {
        if (!majorDisciplines) return;
        var set = {};
        titles.forEach(function (t) { set[t] = true; });
        majorDisciplines.querySelectorAll('.gc-major-btn[data-major-group]').forEach(function (btn) {
            var title = btn.getAttribute('data-major-title') || btn.textContent.trim();
            btn.classList.toggle('gc-major-btn--on', !!set[title]);
        });
        syncMajorUi();
    }

    function clearValidationMarks() {
        form.querySelectorAll('.ga-field-missing').forEach(function (el) {
            el.classList.remove('ga-field-missing');
        });
    }

    function markMissing(el) {
        if (!el) return;
        el.classList.add('ga-field-missing');
    }

    function scrollToField(el) {
        if (!el) return;
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        var focusTarget = el.matches('input, select, textarea')
            ? el
            : el.querySelector('input, select, textarea, button');
        if (focusTarget && focusTarget.focus) {
            setTimeout(function () {
                focusTarget.focus({ preventScroll: true });
            }, 350);
        }
    }

    function validateRequired() {
        clearValidationMarks();
        if (window.gaApplyScores && window.gaApplyScores.flush) {
            window.gaApplyScores.flush();
        }

        var genderEl = form.querySelector('[data-field="gender"]');
        if (!genderEl || !String(genderEl.value || '').trim()) {
            markMissing(genderEl);
            scrollToField(genderEl);
            return false;
        }

        var provinceCombo = document.getElementById('gaokaoProvinceCombo');
        var provinceInp = form.querySelector('[data-field="gaokao_province"]');
        if (!provinceInp || !String(provinceInp.value || '').trim()) {
            markMissing(provinceCombo || provinceInp);
            scrollToField(provinceCombo || provinceInp);
            return false;
        }

        var electiveBar = document.querySelector('#gcScoresSection .gc-elective-bar');
        var subjHidden = form.querySelector('[data-field="score_subjects_0"]');
        if (!subjHidden || String(subjHidden.value || '').length < 3) {
            markMissing(electiveBar);
            scrollToField(electiveBar);
            return false;
        }

        var totalEl = form.querySelector('[data-field="score_total_0"]');
        if (!totalEl || !String(totalEl.value || '').trim()) {
            markMissing(totalEl);
            scrollToField(totalEl);
            return false;
        }

        var rankEl = form.querySelector('[data-field="score_rank_0"]');
        if (!rankEl || !String(rankEl.value || '').trim()) {
            markMissing(rankEl);
            scrollToField(rankEl);
            return false;
        }

        return true;
    }

    function bindValidationClear() {
        var genderEl = form.querySelector('[data-field="gender"]');
        if (genderEl) {
            genderEl.addEventListener('change', function () {
                genderEl.classList.remove('ga-field-missing');
            });
        }
        form.addEventListener('gaApplyScoresChange', function () {
            var provinceCombo = document.getElementById('gaokaoProvinceCombo');
            var provinceInp = form.querySelector('[data-field="gaokao_province"]');
            var electiveBar = document.querySelector('#gcScoresSection .gc-elective-bar');
            var totalEl = form.querySelector('[data-field="score_total_0"]');
            var rankEl = form.querySelector('[data-field="score_rank_0"]');
            if (provinceCombo) provinceCombo.classList.remove('ga-field-missing');
            if (provinceInp) provinceInp.classList.remove('ga-field-missing');
            if (electiveBar) electiveBar.classList.remove('ga-field-missing');
            if (totalEl) totalEl.classList.remove('ga-field-missing');
            if (rankEl) rankEl.classList.remove('ga-field-missing');
        });
    }

    function normalizeGaokaoProvince(raw) {
        if (window.gaApplyScores && window.gaApplyScores.normalizeProvince) {
            return window.gaApplyScores.normalizeProvince(raw);
        }
        raw = (raw || '').trim();
        if (!raw) return '';
        return raw
            .replace(/维吾尔自治区$/, '')
            .replace(/壮族自治区$/, '')
            .replace(/回族自治区$/, '')
            .replace(/自治区$/, '')
            .replace(/省$/, '')
            .replace(/市$/, '');
    }

    function systemUrlWithProvince(baseUrl, provinceCode) {
        if (!baseUrl) return '';
        var code = normalizeGaokaoProvince(provinceCode);
        if (!code) return baseUrl;
        var sep = baseUrl.indexOf('?') >= 0 ? '&' : '?';
        return baseUrl + sep + 'province=' + encodeURIComponent(code);
    }

    function enterSystem() {
        if (!validateRequired()) {
            return;
        }
        saveForm(false);
        var provinceInp = form.querySelector('[data-field="gaokao_province"]');
        var province = provinceInp ? provinceInp.value.trim() : '';
        window.location.href = systemUrlWithProvince(systemUrl, province);
    }

    document.getElementById('gaSaveDraft').addEventListener('click', function () { saveForm(true); });
    form.addEventListener('gaApplyScoresChange', function () { saveForm(false); });
    ['rank_float_up', 'rank_float_down'].forEach(function (fieldName) {
        var el = form.querySelector('[data-field="' + fieldName + '"]');
        if (!el) return;
        el.addEventListener('change', function () { saveForm(false); });
    });

    document.getElementById('gaEnterSystem').addEventListener('click', enterSystem);

    document.getElementById('gaProvinceSelectAll').addEventListener('click', function () {
        if (!provinceRegion) return;
        provinceRegion.querySelectorAll('input[type=checkbox]').forEach(function (cb) {
            cb.checked = true;
        });
        syncRegionRowStates();
        updateProvinceSummary();
        saveForm(false);
    });
    document.getElementById('gaProvinceClear').addEventListener('click', function () {
        if (!provinceRegion) return;
        provinceRegion.querySelectorAll('input[type=checkbox]').forEach(function (cb) {
            cb.checked = false;
        });
        syncRegionRowStates();
        updateProvinceSummary();
        saveForm(false);
    });

    bindRegionSection();
    bindMajorSection();
    bindValidationClear();
    applyToForm(loadRaw());
    expandAllMajorDisciplines();
})();
