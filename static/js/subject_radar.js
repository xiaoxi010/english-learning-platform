/**
 * 学科雷达图（Web 版，对齐 subjectRadarCanvas.js）
 */
(function (global) {
  const W = 320, H = 320, R = 88;
  const GRADE_ORDER = ['D', 'C-', 'C', 'C+', 'B-', 'B', 'B+', 'A-', 'A', 'A+', 'S'];

  function gradeToUnit(g) {
    const s = String(g || '').trim();
    let i = GRADE_ORDER.indexOf(s);
    if (i < 0) i = 5;
    const L = 1 + Math.round((i / (GRADE_ORDER.length - 1)) * 11);
    return (L - 1) / 11;
  }

  function drawRadar(canvas, labels, grades, title) {
    if (!canvas || !canvas.getContext) return;
    const n = Math.min(labels.length, grades.length);
    if (n < 3) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';
    ctx.scale(dpr, dpr);
    const cx = W / 2, cy = H / 2;
    ctx.clearRect(0, 0, W, H);

    for (let k = 1; k <= 5; k++) {
      const rr = (R * k) / 5;
      ctx.beginPath();
      for (let i = 0; i < n; i++) {
        const ang = -Math.PI / 2 + (i * 2 * Math.PI) / n;
        const x = cx + rr * Math.cos(ang);
        const y = cy + rr * Math.sin(ang);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.strokeStyle = k === 5 ? '#5a5a5a' : '#3a3a3a';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    const pts = [];
    for (let i = 0; i < n; i++) {
      const ang = -Math.PI / 2 + (i * 2 * Math.PI) / n;
      const u = 0.15 + 0.85 * gradeToUnit(grades[i]);
      const rr = R * u;
      pts.push({ x: cx + rr * Math.cos(ang), y: cy + rr * Math.sin(ang) });
    }
    ctx.beginPath();
    pts.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y)));
    ctx.closePath();
    ctx.fillStyle = 'rgba(62, 207, 142, 0.25)';
    ctx.fill();
    ctx.strokeStyle = '#3ecf8e';
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = '#000000';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    const labelR = R + 28;
    for (let i = 0; i < n; i++) {
      const ang = -Math.PI / 2 + (i * 2 * Math.PI) / n;
      const x = cx + labelR * Math.cos(ang);
      const y = cy + labelR * Math.sin(ang);
      ctx.fillText(String(labels[i]), x, y + 4);
    }
    if (title) {
      ctx.fillStyle = '#333333';
      ctx.font = '11px sans-serif';
      ctx.fillText(title, cx, 14);
    }
  }

  function initReportRadars(report) {
    document.querySelectorAll('[data-radar]').forEach(function (el) {
      const type = el.getAttribute('data-radar');
      const idx = parseInt(el.getAttribute('data-index') || '0', 10);
      let labels = [], grades = [], title = '';
      if (type === 'thinking') {
        labels = report.thinking_labels || [];
        grades = report.thinking_grades || [];
        title = '能力评级';
      } else if (type === 'nine') {
        labels = (report.nine_radar || []).map(function (x) { return x.name; });
        grades = (report.nine_radar || []).map(function (x) { return x.grade; });
        title = '全学科综测';
      } else if (type === 'group') {
        const g = (report.group_modules || [])[idx];
        if (g) { labels = g.labels; grades = g.grades; title = g.title; }
      } else if (type === 'subject') {
        const s = (report.subjects || [])[idx];
        if (s) { labels = s.labels; grades = s.grades; title = s.name; }
      }
      if (labels.length >= 3) drawRadar(el, labels, grades, title);
    });
  }

  global.SubjectRadar = { drawRadar: drawRadar, initReportRadars: initReportRadars };
})(window);
