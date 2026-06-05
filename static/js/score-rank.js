(function () {
    var root = document.getElementById('scoreRankApp');
    if (!root) return;

    var defaultProvince = root.getAttribute('data-default-province') || '吉林';
    var apiLookup = root.getAttribute('data-api-lookup');

    var provinceTags = document.getElementById('provinceTags');
    var subjectRow = document.getElementById('subjectRow');
    var singleSubjectRow = document.getElementById('singleSubjectRow');
    var btnA = document.getElementById('btnSubjectA');
    var btnB = document.getElementById('btnSubjectB');
    var singleLabel = document.getElementById('singleSubjectLabel');
    var scoreInput = document.getElementById('scoreInput');
    var rankResult = document.getElementById('rankResult');
    var sameScoreRow = document.getElementById('sameScoreRow');
    var sameScoreResult = document.getElementById('sameScoreResult');
    var srTip = document.getElementById('srTip');
    var srDataError = document.getElementById('srDataError');
    var srFormWrap = document.getElementById('srFormWrap');
    var srMissingFile = document.getElementById('srMissingFile');
    var srDataErrorText = document.getElementById('srDataErrorText');

    var state = {
        province: defaultProvince,
        subject: 'physics',
        debounce: null,
    };

    function getActiveTag() {
        return provinceTags.querySelector('.sr-tag--active');
    }

    function applySubjectLabels(tag) {
        if (!tag) return;
        var labelA = tag.getAttribute('data-label-a') || '物理';
        var labelB = tag.getAttribute('data-label-b') || '';
        var showRow = tag.getAttribute('data-show-subject') === '1';
        if (showRow) {
            subjectRow.hidden = false;
            singleSubjectRow.hidden = true;
            btnA.textContent = labelA;
            btnB.textContent = labelB;
            btnB.hidden = !labelB;
            state.subject = 'physics';
            btnA.classList.add('sr-subject--active');
            btnB.classList.remove('sr-subject--active');
        } else {
            subjectRow.hidden = true;
            singleSubjectRow.hidden = false;
            singleLabel.textContent = labelA;
            state.subject = 'physics';
        }
    }

    function setProvince(name) {
        var tag = provinceTags.querySelector('[data-province="' + name + '"]');
        if (!tag) return;
        provinceTags.querySelectorAll('.sr-tag').forEach(function (t) {
            t.classList.toggle('sr-tag--active', t === tag);
        });
        state.province = name;
        applySubjectLabels(tag);
        var available = tag.getAttribute('data-available') === '1';
        if (!available) {
            srDataError.hidden = false;
            srFormWrap.hidden = true;
            srMissingFile.textContent = tag.getAttribute('data-file') || '';
            srDataErrorText.textContent = name + ' 一分一段数据尚未导入。';
            rankResult.textContent = '--';
            sameScoreRow.hidden = true;
            return;
        }
        srDataError.hidden = true;
        srFormWrap.hidden = false;
        srTip.textContent = '* 数据来源于' + name + '2025年高考一分一段表';
        doLookup();
    }

    function doLookup() {
        var score = scoreInput.value.trim();
        if (!score) {
            rankResult.textContent = '--';
            sameScoreRow.hidden = true;
            return;
        }
        fetch(apiLookup, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                province: state.province,
                subject: state.subject,
                score: parseInt(score, 10),
            }),
        })
            .then(function (r) {
                return r.json().then(function (data) {
                    return { status: r.status, data: data };
                });
            })
            .then(function (res) {
                var data = res.data;
                if (data.ok) {
                    rankResult.textContent = data.rank || '--';
                    if (data.same_score_count) {
                        sameScoreRow.hidden = false;
                        sameScoreResult.textContent = data.same_score_count;
                    } else {
                        sameScoreRow.hidden = true;
                    }
                    return;
                }
                rankResult.textContent = '--';
                sameScoreRow.hidden = true;
                if (res.status === 503 && data.error === 'data_missing') {
                    srDataError.hidden = false;
                    srFormWrap.hidden = true;
                    srDataErrorText.textContent = data.message || '数据未导入';
                }
            })
            .catch(function () {
                rankResult.textContent = '--';
            });
    }

    provinceTags.addEventListener('click', function (e) {
        var btn = e.target.closest('.sr-tag');
        if (!btn) return;
        setProvince(btn.getAttribute('data-province'));
    });

    subjectRow.addEventListener('click', function (e) {
        var btn = e.target.closest('.sr-subject');
        if (!btn) return;
        subjectRow.querySelectorAll('.sr-subject').forEach(function (b) {
            b.classList.toggle('sr-subject--active', b === btn);
        });
        state.subject = btn.getAttribute('data-subject');
        doLookup();
    });

    scoreInput.addEventListener('input', function () {
        var v = scoreInput.value.replace(/\D/g, '').slice(0, 3);
        if (scoreInput.value !== v) scoreInput.value = v;
        clearTimeout(state.debounce);
        state.debounce = setTimeout(doLookup, 280);
    });

    setProvince(defaultProvince);
})();
