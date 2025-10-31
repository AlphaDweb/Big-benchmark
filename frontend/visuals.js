// Minimal visualization helpers for the Big Benchmark dashboard
// Exposes a tiny API on window.BB used by index.html

(function () {
  const BB = (window.BB = window.BB || {});

  // Draw a simple sparkline (SVG path with dots).
  // svgEl: <svg> element
  // data: array<number>
  BB.drawSparkline = function drawSparkline(svgEl, data) {
    if (!svgEl) return;
    while (svgEl.firstChild) svgEl.removeChild(svgEl.firstChild);
    const width = svgEl.clientWidth || (svgEl.parentElement ? svgEl.parentElement.clientWidth : 300) || 300;
    const hAttr = svgEl.getAttribute('height');
    const height = hAttr ? parseInt(hAttr) : 40;
    svgEl.setAttribute('viewBox', `0 0 ${width} ${height}`);
    if (!data || data.length === 0) return;
    const max = Math.max.apply(null, data);
    const min = Math.min.apply(null, data);
    const pad = 2;
    const scaleX = (width - pad * 2) / Math.max(1, data.length - 1);
    const denom = Math.max(1e-6, (max - min) || 1);
    const scaleY = (height - pad * 2) / denom;
    let d = '';
    for (let i = 0; i < data.length; i++) {
      const v = data[i];
      const x = pad + i * scaleX;
      const y = height - pad - (v - min) * scaleY;
      d += (i === 0 ? 'M' : 'L') + x + ' ' + y + ' ';
    }
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', d.trim());
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', 'var(--accent)');
    path.setAttribute('stroke-width', '2');
    svgEl.appendChild(path);
    // Add dots for visibility on short series
    for (let i = 0; i < data.length; i++) {
      const v = data[i];
      const cx = pad + i * scaleX;
      const cy = height - pad - (v - min) * scaleY;
      const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      dot.setAttribute('cx', cx);
      dot.setAttribute('cy', cy);
      dot.setAttribute('r', 2.5);
      dot.setAttribute('fill', 'var(--accent)');
      svgEl.appendChild(dot);
    }
  };
})();


