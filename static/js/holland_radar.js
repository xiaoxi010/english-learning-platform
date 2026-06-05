/**
 * 霍兰德六维雷达图（对齐小程序 hollandReport 雷达绘制）
 */
(function (global) {
  const W = 320, H = 320;

  function draw(canvas, labels, values, maxScore) {
    if (!canvas || !canvas.getContext) return;
    const n = Math.min(labels.length, values.length);
    if (n < 3) return;
    const max = maxScore > 0 ? maxScore : 15;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';
    ctx.scale(dpr, dpr);

    const cx = W / 2, cy = H / 2;
    const R = 118;
    ctx.clearRect(0, 0, W, H);

    ctx.strokeStyle = 'rgba(139, 139, 139, 0.35)';
    ctx.lineWidth = 1;
    for (let ring = 1; ring <= 3; ring++) {
      const rr = (R * ring) / 3;
      ctx.beginPath();
      for (let i = 0; i < n; i++) {
        const ang = -Math.PI / 2 + (i * 2 * Math.PI) / n;
        const x = cx + rr * Math.cos(ang);
        const y = cy + rr * Math.sin(ang);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.stroke();
    }

    ctx.strokeStyle = 'rgba(139, 139, 139, 0.45)';
    for (let i = 0; i < n; i++) {
      const ang = -Math.PI / 2 + (i * 2 * Math.PI) / n;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + R * Math.cos(ang), cy + R * Math.sin(ang));
      ctx.stroke();
    }

    const pts = [];
    for (let i = 0; i < n; i++) {
      const v = values[i] != null ? values[i] : 0;
      const u = Math.min(1, Math.max(0, v / max));
      const ang = -Math.PI / 2 + (i * 2 * Math.PI) / n;
      const r = R * u;
      pts.push({ x: cx + r * Math.cos(ang), y: cy + r * Math.sin(ang) });
    }

    ctx.beginPath();
    pts.forEach(function (p, i) {
      if (i === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    });
    ctx.closePath();
    ctx.fillStyle = 'rgba(62, 207, 142, 0.28)';
    ctx.fill();
    ctx.strokeStyle = '#3ecf8e';
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = '#000000';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const labelR = R + 22;
    for (let i = 0; i < n; i++) {
      const ang = -Math.PI / 2 + (i * 2 * Math.PI) / n;
      const lx = cx + labelR * Math.cos(ang);
      const ly = cy + labelR * Math.sin(ang);
      ctx.fillText(String(labels[i]), lx, ly);
    }
  }

  global.HollandRadar = { draw: draw };
})(typeof window !== 'undefined' ? window : this);
