/**
 * 艾克森报告：七维条形图 + 雷达图
 */
(function (global) {
  var rows = global.EYSENCK_CHART_ROWS || [];

  function drawBar(canvas) {
    if (!canvas || !rows.length) return;
    var ctx = canvas.getContext('2d');
    var W = 360, H = Math.max(220, rows.length * 36 + 40);
    var dpr = global.devicePixelRatio || 1;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, W, H);

    var left = 100, right = W - 50, barH = 14;
    ctx.font = '11px sans-serif';
    rows.forEach(function (row, i) {
      var y = 28 + i * 36;
      var max = Math.max(1, row.chart_max || 30);
      var raw = Number(row.raw_score) || 0;
      var pct = Math.min(1, raw / max);
      var high = row.score_band_high === true || row.is_unstable;
      ctx.fillStyle = '#333333';
      ctx.textAlign = 'right';
      ctx.fillText(String(row.name).slice(0, 8), left - 8, y + 10);
      ctx.fillStyle = '#b8cdd4';
      ctx.fillRect(left, y, right - left, barH);
      ctx.fillStyle = high ? '#f87171' : '#3ecf8e';
      ctx.fillRect(left, y, (right - left) * pct, barH);
      ctx.fillStyle = '#000000';
      ctx.textAlign = 'left';
      ctx.fillText(row.score_text || '', right + 6, y + 10);
    });
  }

  function drawRadar(canvas) {
    if (!canvas || rows.length < 3) return;
    var n = rows.length;
    var W = 320, H = 320, R = 100;
    var ctx = canvas.getContext('2d');
    var dpr = global.devicePixelRatio || 1;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';
    ctx.scale(dpr, dpr);
    var cx = W / 2, cy = H / 2;
    ctx.clearRect(0, 0, W, H);

    for (var ring = 1; ring <= 3; ring++) {
      var rr = (R * ring) / 3;
      ctx.beginPath();
      for (var i = 0; i < n; i++) {
        var ang = -Math.PI / 2 + (i * 2 * Math.PI) / n;
        var x = cx + rr * Math.cos(ang);
        var y = cy + rr * Math.sin(ang);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.strokeStyle = 'rgba(139,139,139,0.35)';
      ctx.stroke();
    }

    var pts = [];
    for (i = 0; i < n; i++) {
      var row = rows[i];
      var max = Math.max(1, row.chart_max || 30);
      var u = Math.min(1, (Number(row.raw_score) || 0) / max);
      ang = -Math.PI / 2 + (i * 2 * Math.PI) / n;
      pts.push({ x: cx + R * u * Math.cos(ang), y: cy + R * u * Math.sin(ang) });
    }
    ctx.beginPath();
    pts.forEach(function (p, idx) {
      if (idx === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    });
    ctx.closePath();
    ctx.fillStyle = 'rgba(62, 207, 142, 0.25)';
    ctx.fill();
    ctx.strokeStyle = '#3ecf8e';
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = '#000000';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    for (i = 0; i < n; i++) {
      ang = -Math.PI / 2 + (i * 2 * Math.PI) / n;
      var lx = cx + (R + 22) * Math.cos(ang);
      var ly = cy + (R + 22) * Math.sin(ang);
      var label = String(rows[i].name || '').replace(/-.*/, '');
      ctx.fillText(label, lx, ly);
    }
  }

  function init() {
    drawBar(document.getElementById('eyBar'));
    drawRadar(document.getElementById('eyRadar'));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(typeof window !== 'undefined' ? window : this);
