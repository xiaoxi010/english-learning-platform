(function () {
    var form = document.getElementById('gaokaoApplyForm');
    var section = document.getElementById('gcScoresSection');
    if (!form || !section) return;

    var lookupUrl = form.getAttribute('data-lookup-url') || '';
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

    function flushSlotsToStore() {
        for (var s = 0; s < 3; s++) {
            var key = slotBindings[s];
            var slotInp = elecSlotInput(s);
            var store = key ? storeField(key) : null;
            if (store && slotInp && !slotInp.disabled) {
                store.value = slotInp.value;
            }
        }
    }

    function updateElectiveSlots() {
        var list = getSelectedList();
        flushSlotsToStore();

        for (var s = 0; s < 3; s++) {
            var th = elecTh(s);
            var inp = elecSlotInput(s);
            var key = list[s] || null;
            slotBindings[s] = key;

            if (th) th.textContent = key ? ELEC_FULL[key] : '选考' + (s + 1);
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

    function formatGaokaoProvinceDisplay(raw) {
        raw = (raw || '').trim();
        if (!raw) return '';
        var label = '';
        eachProvinceOption(function (val, lbl) {
            if (!label && (raw === val || raw === lbl)) label = lbl;
        });
        return label || raw;
    }

    function syncRegionField() {
        var regionEl = fieldEl('region');
        var provInp = fieldEl('gaokao_province');
        if (!regionEl || !provInp) return;
        var code = normalizeGaokaoProvince(provInp.value);
        if (code && regionEl.querySelector('option[value="' + code + '"]')) {
            regionEl.value = code;
        }
    }

    function notifyChange() {
        form.dispatchEvent(new CustomEvent('gaApplyScoresChange', { bubbles: true }));
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

    function lookupRank(total, province, subject) {
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
            return;
        }
        if (rankInp) rankInp.value = data.rank != null ? String(data.rank) : '';
        if (sameInp) sameInp.value = data.same_score_count != null ? String(data.same_score_count) : '';
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

    function recalcScores() {
        var totalInp = fieldEl('score_total_' + SCORE_ROW);
        var provinceInp = fieldEl('gaokao_province');
        if (!totalInp) return;

        var total = sumSubjectScores();
        totalInp.value = total != null ? String(total) : '';

        if (!allSubjectsReady()) {
            applyRankResult(null);
            notifyChange();
            return;
        }

        var province = normalizeGaokaoProvince(provinceInp ? provinceInp.value.trim() : '');
        if (!province) {
            applyRankResult(null);
            notifyChange();
            return;
        }

        var subject = inferSubject(province);
        clearTimeout(rankDebounce);
        rankDebounce = setTimeout(function () {
            lookupRank(total, province, subject).then(function (data) {
                applyRankResult(data);
                notifyChange();
            });
        }, 300);
    }

    function runCalcIfAuto() {
        if (autoCalcOn) recalcScores();
    }

    function maybeEnableAutoByProvince() {
        var provinceInp = fieldEl('gaokao_province');
        var p = provinceInp ? provinceInp.value.trim() : '';
        if (p && !autoCalcManualOff) setAutoCalcUi(true);
    }

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
            var label = (li.textContent || '').trim();
            input.value = label || li.getAttribute('data-value') || '';
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
            syncRegionField();
            notifyChange();
        });
        input.addEventListener('change', function () {
            input.value = formatGaokaoProvinceDisplay(input.value.trim());
            syncRegionField();
            maybeEnableAutoByProvince();
            runCalcIfAuto();
            notifyChange();
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

        if (input.value.trim()) {
            input.value = formatGaokaoProvinceDisplay(input.value.trim());
        }
    }

    function bindScoreInputs() {
        form.querySelectorAll('[data-core-col]').forEach(function (inp) {
            inp.addEventListener('input', function () {
                var v = inp.value.replace(/[^\d.]/g, '');
                if (inp.value !== v) inp.value = v;
                runCalcIfAuto();
                notifyChange();
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
                notifyChange();
            });
        });
        var totalInp = fieldEl('score_total_' + SCORE_ROW);
        if (totalInp) {
            totalInp.addEventListener('input', runCalcIfAuto);
        }
        section.querySelectorAll('[data-field^="score_"]').forEach(function (inp) {
            if (inp.closest('.gc-score-store')) return;
            if (inp === totalInp) return;
            inp.addEventListener('input', notifyChange);
            inp.addEventListener('change', notifyChange);
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
            runCalcIfAuto();
            notifyChange();
        });
    }

    var regionEl = fieldEl('region');
    if (regionEl) {
        regionEl.addEventListener('change', function () {
            var provInp = fieldEl('gaokao_province');
            if (!provInp) return;
            provInp.value = formatGaokaoProvinceDisplay(regionEl.value);
            notifyChange();
        });
    }

    initProvinceCombobox();
    bindScoreInputs();
    restoreElectivesFromHidden();
    syncRegionField();
    setAutoCalcUi(false);
    maybeEnableAutoByProvince();
    if (autoCalcOn) setTimeout(recalcScores, 150);

    function migrateDraft(data) {
        if (!data) return data;
        if (!data.score_total_0 && data.score) data.score_total_0 = data.score;
        if (!data.score_rank_0 && data.province_rank) data.score_rank_0 = data.province_rank;
        if (!data.score_subjects_0 && data.subject_combo) data.score_subjects_0 = data.subject_combo;
        if (!data.gaokao_province && data.region) {
            data.gaokao_province = formatGaokaoProvinceDisplay(data.region);
        }
        return data;
    }

    window.gaApplyScores = {
        migrateDraft: migrateDraft,
        restoreElectives: restoreElectivesFromHidden,
        normalizeProvince: normalizeGaokaoProvince,
        formatProvinceDisplay: formatGaokaoProvinceDisplay,
        syncLegacyFields: function (data) {
            data.score = data.score_total_0 || data.score || '';
            data.province_rank = data.score_rank_0 || data.province_rank || '';
            if (data.score_subjects_0) data.subject_combo = data.score_subjects_0;
            return data;
        },
        validate: function () {
            var prov = fieldEl('gaokao_province');
            var total = fieldEl('score_total_0');
            var rank = fieldEl('score_rank_0');
            var subj = fieldEl('score_subjects_0');
            if (!prov || !String(prov.value || '').trim()) return false;
            if (!total || !String(total.value || '').trim()) return false;
            if (!rank || !String(rank.value || '').trim()) return false;
            if (!subj || String(subj.value || '').length < MAX_ELECTIVE) return false;
            return true;
        },
        flush: flushSlotsToStore,
    };
})();
