/**
 * 测评答题页：选项、右侧总览（固定）、左侧题目区滚动
 */
(function (global) {
  var CELL_CLASSES = [
    'assess-cell--none', 'assess-cell--yes', 'assess-cell--no', 'assess-cell--maybe', 'assess-cell--optc', 'assess-cell--optd',
    'assess-cell--s1', 'assess-cell--s2', 'assess-cell--s3', 'assess-cell--s4', 'assess-cell--s5',
    'assess-cell--l1', 'assess-cell--l2', 'assess-cell--l3', 'assess-cell--l4', 'assess-cell--l5',
  ];
  var JUMP_HIGHLIGHT_MS = 10000;
  var jumpHighlight = { timer: null, qi: null };

  function isQuestionAnswered(form, qi) {
    return !!form.querySelector('input[name="ans_' + qi + '"]:checked');
  }

  function clearJumpHighlight() {
    if (jumpHighlight.timer) {
      clearTimeout(jumpHighlight.timer);
      jumpHighlight.timer = null;
    }
    if (jumpHighlight.qi != null) {
      var prev = document.getElementById('q-' + jumpHighlight.qi);
      if (prev) prev.classList.remove('assess-q-card--jump');
      jumpHighlight.qi = null;
    }
  }

  /** 未作答题被强制跳转时：淡黄色边框，作答或 10s 后恢复 */
  function applyJumpHighlight(form, qi) {
    if (!form || isQuestionAnswered(form, qi)) return;
    clearJumpHighlight();
    var card = document.getElementById('q-' + qi);
    if (!card) return;
    card.classList.add('assess-q-card--jump');
    jumpHighlight.qi = qi;
    jumpHighlight.timer = setTimeout(clearJumpHighlight, JUMP_HIGHLIGHT_MS);
  }

  function syncOptGroup(input) {
    var form = input.form;
    if (!form) return;
    var name = input.name;
    form.querySelectorAll('input[type="radio"][name="' + name + '"]').forEach(function (r) {
      var lab = r.closest('.assess-opt');
      if (lab) lab.classList.toggle('assess-opt--on', r.checked);
    });
  }

  function answerToCellClass(value, valueMap) {
    if (!value) return 'assess-cell--none';
    var key = valueMap[value];
    if (key === 'yes') return 'assess-cell--yes';
    if (key === 'no') return 'assess-cell--no';
    if (key === 'maybe') return 'assess-cell--maybe';
    if (key === 'optc') return 'assess-cell--optc';
    if (key === 'optd') return 'assess-cell--optd';
    if (key === 's1') return 'assess-cell--s1';
    if (key === 's2') return 'assess-cell--s2';
    if (key === 's3') return 'assess-cell--s3';
    if (key === 's4') return 'assess-cell--s4';
    if (key === 's5') return 'assess-cell--s5';
    if (key === 'l1') return 'assess-cell--l1';
    if (key === 'l2') return 'assess-cell--l2';
    if (key === 'l3') return 'assess-cell--l3';
    if (key === 'l4') return 'assess-cell--l4';
    if (key === 'l5') return 'assess-cell--l5';
    return 'assess-cell--none';
  }

  function canScroll(el) {
    return el && el.scrollHeight > el.clientHeight + 2;
  }

  /** 优先使用可滚动的 .content-area */
  function getScrollContainer(el) {
    if (el && el.closest) {
      var main = el.closest('.content-area');
      if (main && canScroll(main)) return main;
    }
    var node = el;
    while (node && node !== document.body) {
      var st = global.getComputedStyle(node);
      var oy = st.overflowY;
      if ((oy === 'auto' || oy === 'scroll') && canScroll(node)) return node;
      node = node.parentElement;
    }
    return null;
  }

  /** 整道题（题干+选项）是否已在可视区内完整显示 */
  function isQuestionFullyVisible(card, padTop, bottomPad) {
    if (!card) return true;
    var top = padTop != null ? padTop : 20;
    var bottom = bottomPad != null ? bottomPad : 24;
    var cRect = card.getBoundingClientRect();
    var scroller = getScrollContainer(card);
    if (!scroller) {
      return cRect.top >= top && cRect.bottom <= global.innerHeight - bottom;
    }
    var sRect = scroller.getBoundingClientRect();
    return cRect.top >= sRect.top + top && cRect.bottom <= sRect.bottom - bottom;
  }

  /**
   * 把整道题滚入可视区（force=true 时双击题号，始终跳转）
   */
  function scrollQuestionFullyVisible(card, padTop, force) {
    if (!card) return;
    var topPad = padTop != null ? padTop : 20;

    if (!force && isQuestionFullyVisible(card, topPad, 24)) {
      return;
    }

    var scroller = getScrollContainer(card);
    if (!scroller) {
      card.scrollIntoView({ behavior: 'smooth', block: 'start', inline: 'nearest' });
      return;
    }

    var sRect = scroller.getBoundingClientRect();
    var cRect = card.getBoundingClientRect();
    var targetScroll = scroller.scrollTop + (cRect.top - sRect.top) - topPad;
    targetScroll = Math.max(0, Math.round(targetScroll));

    scroller.scrollTo({ top: targetScroll, behavior: 'smooth' });
  }

  function jumpToQuestionIndex(qi, cells, force, form) {
    if (!Number.isFinite(qi)) return;
    setActiveOverviewCell(cells, qi);
    var card = document.getElementById('q-' + qi);
    if (!card) return;
    if (force && form) applyJumpHighlight(form, qi);
    requestAnimationFrame(function () {
      scrollQuestionFullyVisible(card, 20, !!force);
    });
  }

  /** 作答后：下一题未完整显示时才滚动 */
  function scrollToNextQuestion(nextCard) {
    if (!nextCard) return;
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        scrollQuestionFullyVisible(nextCard, 20, false);
      });
    });
  }

  function formatElapsed(ms) {
    var s = Math.floor(ms / 1000);
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var sec = s % 60;
    function z(n) { return n < 10 ? '0' + n : String(n); }
    if (h > 0) return h + ':' + z(m) + ':' + z(sec);
    return z(m) + ':' + z(sec);
  }

  /** 右侧总览钉在视口内（不随题目区滚动） */
  function pinQuizSidebar() {
    var bar = document.querySelector('.assess-quiz-sidebar');
    var content = document.querySelector('.content-area');
    if (!bar || !content) return;

    function place() {
      if (global.innerWidth <= 960) {
        bar.classList.remove('is-pinned');
        bar.style.top = '';
        bar.style.right = '';
        bar.style.left = '';
        bar.style.maxHeight = '';
        return;
      }
      var cRect = content.getBoundingClientRect();
      var topBar = document.querySelector('.top-bar');
      var top = topBar ? topBar.getBoundingClientRect().bottom + 8 : cRect.top + 8;
      var bottomGap = 16;
      bar.style.top = Math.round(top) + 'px';
      bar.style.left = 'auto';
      bar.style.right = Math.round(global.innerWidth - cRect.right + 12) + 'px';
      bar.style.width = '280px';
      bar.style.maxHeight = Math.round(global.innerHeight - top - bottomGap) + 'px';
      bar.classList.add('is-pinned');
    }

    place();
    global.addEventListener('resize', place);
    content.addEventListener('scroll', place, { passive: true });
  }

  function setActiveOverviewCell(cells, qi) {
    cells.forEach(function (c) { c.classList.remove('assess-overview-cell--active'); });
    if (!Number.isFinite(qi)) return;
    var cell = null;
    cells.forEach(function (c) {
      if (parseInt(c.getAttribute('data-qi'), 10) === qi) cell = c;
    });
    if (cell) cell.classList.add('assess-overview-cell--active');
  }

  function initOverview(form, total, options) {
    var grid = document.getElementById('assessOverviewGrid');
    if (!grid) return null;

    var valueMap = options.valueMap || {};
    var answeredEl = document.getElementById('assessOverviewAnswered');
    var clockEl = document.getElementById('assessOverviewClock');
    var cells = grid.querySelectorAll('.assess-overview-cell');
    var startedAt = Date.now();
    var clockTimer = null;

    function setCellClass(cell, cls) {
      CELL_CLASSES.forEach(function (c) { cell.classList.remove(c); });
      cell.classList.add(cls);
    }

    function getAnswerValue(qi) {
      var inp = form.querySelector('input[name="ans_' + qi + '"]:checked');
      return inp ? inp.value : '';
    }

    function updateOverview() {
      var n = 0;
      cells.forEach(function (cell) {
        var qi = parseInt(cell.getAttribute('data-qi'), 10);
        if (!Number.isFinite(qi)) return;
        var val = getAnswerValue(qi);
        if (val) n++;
        setCellClass(cell, answerToCellClass(val, valueMap));
      });
      if (answeredEl) answeredEl.textContent = String(n);
      if (typeof form._assessOnProgress === 'function') form._assessOnProgress();
      return n;
    }

    if (clockEl) {
      clockEl.textContent = '00:00';
      clockTimer = setInterval(function () {
        clockEl.textContent = formatElapsed(Date.now() - startedAt);
      }, 1000);
    }

    cells.forEach(function (cell) {
      cell.addEventListener('click', function () {
        var qi = parseInt(cell.getAttribute('data-qi'), 10);
        if (!Number.isFinite(qi)) return;
        setActiveOverviewCell(cells, qi);
      });
      cell.addEventListener('dblclick', function (e) {
        e.preventDefault();
        e.stopPropagation();
        var qi = parseInt(cell.getAttribute('data-qi'), 10);
        jumpToQuestionIndex(qi, cells, true, form);
      });
    });

    return {
      update: updateOverview,
      clearJumpHighlight: clearJumpHighlight,
      afterAnswer: function (qi) {
        updateOverview();
        var next = qi + 1;
        if (next < total) {
          setActiveOverviewCell(cells, next);
          setTimeout(function () {
            scrollToNextQuestion(document.getElementById('q-' + next));
          }, 80);
        } else {
          setActiveOverviewCell(cells, qi);
        }
      },
      destroy: function () {
        if (clockTimer) clearInterval(clockTimer);
        clearJumpHighlight();
      },
    };
  }

  function initQuizForm(formId, total, options) {
    options = options || {};
    var form = document.getElementById(formId);
    if (!form || !total) return;

    pinQuizSidebar();
    var overview = initOverview(form, total, options);

    form.querySelectorAll('.assess-opt input[type="radio"]').forEach(function (inp) {
      if (inp.checked) syncOptGroup(inp);
      inp.addEventListener('change', function () {
        syncOptGroup(inp);
        var m = inp.name.match(/^ans_(\d+)$/);
        var qi = m ? parseInt(m[1], 10) : NaN;
        if (Number.isFinite(qi) && jumpHighlight.qi === qi) clearJumpHighlight();
        if (overview) overview.afterAnswer(qi);
        else if (typeof form._assessOnProgress === 'function') form._assessOnProgress();
      });
    });

    form.querySelectorAll('.assess-opt').forEach(function (lab) {
      lab.addEventListener('click', function (e) {
        var inp = lab.querySelector('input[type="radio"]');
        if (!inp || inp.disabled) return;
        if (e.target === inp) return;
        inp.checked = true;
        inp.dispatchEvent(new Event('change', { bubbles: true }));
      });
    });

    form.addEventListener('submit', function (e) {
      for (var i = 0; i < total; i++) {
        if (!form.querySelector('input[name="ans_' + i + '"]:checked')) {
          e.preventDefault();
          var card = document.getElementById('q-' + i);
          if (card) scrollToNextQuestion(card);
          applyJumpHighlight(form, i);
          if (overview) overview.update();
          setActiveOverviewCell(
            document.querySelectorAll('.assess-overview-cell'),
            i
          );
          return;
        }
      }
    });

    if (overview) overview.update();
  }

  global.AssessmentQuiz = {
    init: initQuizForm,
    syncOpt: syncOptGroup,
    scrollQuestion: scrollQuestionFullyVisible,
  };
})(typeof window !== 'undefined' ? window : this);
