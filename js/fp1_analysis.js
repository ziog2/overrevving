function normalizeFp1RiderKey(name) {
  if (!name) return '';
  return String(name)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

const FP1_FALLBACK_COLORS = [
  '#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6',
  '#1abc9c', '#e67e22', '#00b0ff', '#ec4899', '#84cc16'
];

function getFp1RiderStyle(rName, fallbackIdx) {
  if (typeof RIDER_STYLES !== 'undefined' && rName) {
    if (RIDER_STYLES[rName]) return RIDER_STYLES[rName];
    const target = normalizeFp1RiderKey(rName);
    for (const k of Object.keys(RIDER_STYLES)) {
      const nk = normalizeFp1RiderKey(k);
      if (nk === target) return RIDER_STYLES[k];
      // Handle abbreviated aliases like "Mario Aji" vs "Mario Suryo Aji" or "Zonta Vd Goorbergh" vs "Zonta Van Den Goorbergh"
      const kParts = nk.split(' ');
      const tParts = target.split(' ');
      if (kParts.length >= 2 && tParts.length >= 2 && kParts[0] === tParts[0] && kParts[kParts.length - 1] === tParts[tParts.length - 1]) {
        return RIDER_STYLES[k];
      }
    }
  }
  const idx = typeof fallbackIdx === 'number' ? fallbackIdx : Math.abs(Array.from(String(rName || '')).reduce((h, c) => ((h << 5) - h + c.charCodeAt(0)) | 0, 0));
  return { color: FP1_FALLBACK_COLORS[idx % FP1_FALLBACK_COLORS.length] };
}

if (typeof window.getRiderCode !== 'function') {
  window.getRiderCode = function getRiderCode(rName) {
    if (!rName) return '';
    const cur = window.CURRENT_EVENT_SHORT || (typeof gp !== 'undefined' && gp ? gp.short : null);
    const datasets = [
      typeof EVENT_FP1_STINTS_DATA !== 'undefined' ? EVENT_FP1_STINTS_DATA : null,
      typeof EVENT_PR_STINTS_DATA !== 'undefined' ? EVENT_PR_STINTS_DATA : null,
      typeof EVENT_FP2_STINTS_DATA !== 'undefined' ? EVENT_FP2_STINTS_DATA : null
    ];
    const target = normalizeFp1RiderKey(rName);
    if (cur) {
      for (const ds of datasets) {
        const gpObj = ds && ds[cur];
        if (!gpObj) continue;
        if (gpObj[rName] && gpObj[rName].code) return gpObj[rName].code;
        for (const k of Object.keys(gpObj)) {
          if (normalizeFp1RiderKey(k) === target && gpObj[k].code) return gpObj[k].code;
        }
      }
    }
    const parts = rName.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1].slice(0, 2)).toUpperCase();
    }
    return rName.slice(0, 3).toUpperCase();
  };
}

function hasFp1TyreCompounds(fp1Data) {
  if (!fp1Data) return false;
  for (const rName of Object.keys(fp1Data)) {
    const runs = (fp1Data[rName] && fp1Data[rName].runs) || [];
    for (const run of runs) {
      if ((run.front && run.front.trim()) || (run.rear && run.rear.trim())) {
        return true;
      }
    }
  }
  return false;
}

function getActiveFp1Riders(gpShort, fp1Data, staticKey) {
  if (!fp1Data) return [];
  const ridersPool = Object.keys(fp1Data);
  if (!ridersPool.length) return [];

  let active = ridersPool.filter(rName => typeof isRiderFavorite === 'function' && isRiderFavorite(rName));
  if (active.length > 0) return active;

  // Fallback when user has no favorites starred for this category: pick top 3 FP1 riders
  const fp1List = (typeof STATIC_EVENT_DATA !== 'undefined' && STATIC_EVENT_DATA[gpShort] && STATIC_EVENT_DATA[gpShort][staticKey || "fp1"]) || [];
  for (const item of fp1List) {
    const rName = item && (typeof item.rider === 'string' ? item.rider : (item.rider && item.rider.full_name));
    if (!rName) continue;
    const normTarget = normalizeFp1RiderKey(rName);
    const matched = ridersPool.find(k => normalizeFp1RiderKey(k) === normTarget);
    if (matched && !active.includes(matched)) {
      active.push(matched);
      if (active.length >= 3) break;
    }
  }
  if (active.length > 0) return active;

  // Secondary fallback: fastest 3 riders in fp1Data
  return ridersPool
    .map(rName => {
      const runs = (fp1Data[rName] && fp1Data[rName].runs) || [];
      const best = Math.min(...runs.map(r => (r.fastestSec > 0 ? r.fastestSec : Infinity)));
      return { rName, best };
    })
    .sort((a, b) => a.best - b.best)
    .slice(0, 3)
    .map(x => x.rName);
}

function createPracticeAnalysisController(cfg) {
  const p = cfg.prefix;
  const getStintsRoot = () => (typeof window !== 'undefined' && window[cfg.stintsGlobal]) ? window[cfg.stintsGlobal] : null;
  const getSectorsRoot = () => (typeof window !== 'undefined' && window[cfg.sectorsGlobal]) ? window[cfg.sectorsGlobal] : null;

  function toggleFp1AnalysisMinimize() {

    const section = document.getElementById(p + '-analysis-section');

    if (!section) return;

    const isMin = section.classList.toggle('minimized');

    try { localStorage.setItem(cfg.minStorageKey, isMin ? '1' : '0'); } catch(e) {}

    const btn = document.getElementById(p + '-analysis-min-btn');

    const icon = document.getElementById(p + '-analysis-min-icon');

    if (isMin) {

      if (btn) btn.setAttribute('title', 'Expand');

      if (icon) icon.innerHTML = '<rect x="2" y="2" width="8" height="8" rx="1" stroke="currentColor" stroke-width="1.6" fill="none"/>';

    } else {

      if (btn) btn.setAttribute('title', 'Minimize');

      if (icon) icon.innerHTML = '<path d="M2 6H10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>';

      const cur = window.CURRENT_EVENT_SHORT || (typeof gp !== 'undefined' && gp ? gp.short : null);

      if (cur) renderFp1AnalysisSection(cur);

    }

  }

  function drawFp1DummyChart(id, type) {

    const cvs = document.getElementById(id);

    if (!cvs) return;

    const ctx = cvs.getContext('2d');

    const w = cvs.clientWidth || 300;

    const h = cvs.clientHeight || 260;

    cvs.width = w;

    cvs.height = h;

    ctx.clearRect(0, 0, w, h);

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';

    ctx.lineWidth = 1;

    for (let y = 30; y < h - 20; y += 35) {

      ctx.beginPath(); ctx.moveTo(20, y); ctx.lineTo(w - 20, y); ctx.stroke();

    }

    if (type === 'line') {

      const colors = ['#e74c3c', '#d8ff00', '#ff6600', '#3498db'];

      colors.forEach((c, i) => {

        ctx.strokeStyle = c;

        ctx.lineWidth = 2.5;

        ctx.beginPath();

        let prevY = h / 2 + (i - 1.5) * 30;

        ctx.moveTo(30, prevY);

        for (let x = 70; x < w - 30; x += 40) {

          prevY += (Math.sin(x * 0.05 + i) * 15);

          ctx.lineTo(x, prevY);

        }

        ctx.stroke();

      });

    } else {

      const colors = ['#e74c3c', '#ff6600', '#d8ff00', '#3498db'];

      for (let x = 35; x < w - 35; x += 45) {

        colors.forEach((c, i) => {

          ctx.fillStyle = c;

          const bh = 50 + ((x * 7 + i * 31) % 120);

          ctx.fillRect(x + i * 8, h - 30 - bh, 6, bh);

        });

      }

    }

  }

  const FP1_TYRE_COLORS = {

    'S': '#ffd600', // Soft: Yellow

    'M': '#ffffff', // Medium: White

    'H': '#00b0ff'  // Hard: Light Blue

  };

  const FP1_STINT_COLOR_PACE = '#a855f7'; // Purple / Viola (distinct from green, red, white, yellow, blue)

  const FP1_STINT_COLOR_TA = '#ff7a00';   // Orange / Arancione (distinct from green, red, white, yellow, blue)

  function classifyFp1Runs(runs) {

    if (!runs || !runs.length) return [];

    const validFastest = runs.filter(r => r.fastestSec > 0).map(r => r.fastestSec);

    const pbSec = validFastest.length ? Math.min(...validFastest) : 999;

    return runs.map((r, idx) => {

      const flying = (r.flying || []).slice().sort((a, b) => a - b);

      const fastestSec = r.fastestSec || (flying[0] || 999);

      const rhythmLaps = flying.filter(s => s <= fastestSec + 1.25);

      const deltaToPB = +(fastestSec - pbSec).toFixed(3);

      const lapsCount = r.lapsCount || 0;

      let isTA = false;

      // 1) Push-cool-push or one-shot: <= 2 rhythm laps and within 0.45s of PB

      if (rhythmLaps.length <= 2 && deltaToPB <= 0.45) {

        isTA = true;

      }

      // 2) Final run attack: last run, <= 5 total laps, sets or matches PB, <= 3 rhythm laps

      else if (idx === runs.length - 1 && lapsCount <= 5 && deltaToPB <= 0.05 && rhythmLaps.length <= 3) {

        isTA = true;

      }

      // 3) Short dash: <= 4 total laps and within 0.30s of PB

      else if (lapsCount <= 4 && deltaToPB <= 0.30) {

        isTA = true;

      }

      return {

        ...r,

        isTA: isTA,

        stintType: isTA ? 'TA' : 'PACE'

      };

    });

  }

  let currentFp1DensityMode = 'runs';

  let fp1DensityChartInstance = null;

  function setFp1DensityMode(mode) {

    currentFp1DensityMode = mode;

    const btnRuns = document.getElementById(p + '-density-btn-runs');

    const btnOverall = document.getElementById(p + '-density-btn-overall');

    if (btnRuns) btnRuns.classList.toggle('active', mode === 'runs');

    if (btnOverall) btnOverall.classList.toggle('active', mode === 'overall');

    const cur = window.CURRENT_EVENT_SHORT || (typeof gp !== 'undefined' && gp ? gp.short : 'THA');

    const fp1Data = (getStintsRoot() && getStintsRoot()[cur]) ? getStintsRoot()[cur] : {};

    const activeFavRiders = getActiveFp1Riders(cur, fp1Data, cfg.staticKey);

    renderFp1DensityChart(cur, activeFavRiders);

  }

  function getSignificantFp1Laps(flying, runFastestSec, riderPbSec) {
    if (!flying || !flying.length) return [];
    const base = (riderPbSec && riderPbSec > 0 && riderPbSec < 990) ? riderPbSec : ((runFastestSec && runFastestSec > 0) ? runFastestSec : Math.min(...flying));
    const maxAllowed = Math.min(base * 1.035, base + 3.5);
    return flying.filter(s => s > 0 && s <= maxAllowed);
  }

  const fp1DensityTicksPlugin = {

    id: p + 'DensityTicks',

    afterDatasetsDraw: (chart) => {

      const ctx = chart.ctx;

      const meta = chart.getDatasetMeta(0);

      if (!meta || !meta.data) return;

      const yAxis = chart.scales.y;

      const items = chart.customDensityItems || [];

      // 1. In 'runs' mode: Draw subtle vertical dividers between different riders

      if (chart.customDensityMode === 'runs') {

        ctx.save();

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.10)';

        ctx.lineWidth = 1;

        ctx.setLineDash([2, 3]);

        for (let i = 0; i < meta.data.length - 1; i++) {

          const curIt = items[i];

          const nextIt = items[i + 1];

          if (curIt && nextIt && curIt.riderIdx !== nextIt.riderIdx) {

            const divX = (meta.data[i].x + meta.data[i + 1].x) / 2;

            ctx.beginPath();

            ctx.moveTo(divX, chart.chartArea.top);

            ctx.lineTo(divX, chart.chartArea.bottom);

            ctx.stroke();

          }

        }

        ctx.restore();

      }

      // 2. Draw Progression Trendlines between runs of the same rider (if mode == 'runs')

      if (chart.customDensityMode === 'runs') {

        const riderGroups = {};

        meta.data.forEach((bar, idx) => {

          const it = items[idx];

          if (!it) return;

          if (!riderGroups[it.code]) riderGroups[it.code] = [];

          riderGroups[it.code].push({ bar, it });

        });

        ctx.save();

        Object.keys(riderGroups).forEach(code => {

          const group = riderGroups[code];

          if (group.length >= 2) {

            const color = group[0].it.color;

            ctx.strokeStyle = color;

            ctx.lineWidth = 2.2;

            ctx.setLineDash([3, 3]);

            ctx.globalAlpha = 0.75;

            ctx.beginPath();

            group.forEach((pt, pIdx) => {

              const x = pt.bar.x;

              const y = yAxis.getPixelForValue(pt.it.avg);

              if (pIdx === 0) ctx.moveTo(x, y);

              else ctx.lineTo(x, y);

            });

            ctx.stroke();

            // Connecting dots at avg

            ctx.setLineDash([]);

            ctx.globalAlpha = 1.0;

            ctx.fillStyle = '#ffffff';

            group.forEach(pt => {

              const x = pt.bar.x;

              const y = yAxis.getPixelForValue(pt.it.avg);

              ctx.beginPath();

              ctx.arc(x, y, 3.5, 0, Math.PI * 2);

              ctx.fill();

            });

          }

        });

        ctx.restore();

      }

      // 3. Draw Pillars, Internal Ticks, White Median Line, Labels

      meta.data.forEach((bar, idx) => {

        const it = items[idx];

        if (!it || !it.laps || !it.laps.length) return;

        const left = bar.x - bar.width / 2;

        const right = bar.x + bar.width / 2;

        const width = bar.width;

        const top = Math.min(bar.y, bar.base);

        const height = Math.abs(bar.y - bar.base);

        if (width <= 0) return;

        // A. Draw Pillar Rounded Border & Fill

        ctx.save();

        ctx.strokeStyle = it.color;

        ctx.lineWidth = 1.8;

        ctx.fillStyle = it.color + '26'; // 15% opacity fill

        if (height < 2) {

          ctx.beginPath();

          ctx.moveTo(left, bar.base);

          ctx.lineTo(right, bar.base);

          ctx.stroke();

        } else {

          ctx.beginPath();

          ctx.roundRect(left, top, width, height, 4);

          ctx.fill();

          ctx.stroke();

        }

        ctx.restore();

        // B. Internal Lap Ticks

        ctx.save();

        ctx.strokeStyle = it.color;

        ctx.globalAlpha = 0.9;

        ctx.lineWidth = 1.4;

        it.laps.forEach(lSec => {

          const yTick = yAxis.getPixelForValue(lSec);

          if (yTick >= chart.chartArea.top && yTick <= chart.chartArea.bottom) {

            ctx.beginPath();

            ctx.moveTo(left + 2, yTick);

            ctx.lineTo(right - 2, yTick);

            ctx.stroke();

          }

        });

        ctx.restore();

        // C. White Average Line + Value

        const yAvg = yAxis.getPixelForValue(it.avg);

        if (yAvg >= chart.chartArea.top && yAvg <= chart.chartArea.bottom) {

          ctx.save();

          ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';

          ctx.shadowBlur = 4;

          ctx.strokeStyle = '#ffffff';

          ctx.lineWidth = 2.4;

          ctx.beginPath();

          ctx.moveTo(left - 3, yAvg);

          ctx.lineTo(right + 3, yAvg);

          ctx.stroke();

          const minHForAvgText = chart.customDensityMode === 'runs' ? 36 : 28;

          if (height >= minHForAvgText && width >= 18) {

            const avgText = formatLapTime(it.avg);

            ctx.font = '700 8.5px Inter, sans-serif';

            ctx.textAlign = 'center';

            ctx.textBaseline = 'bottom';

            ctx.strokeStyle = '#111114';

            ctx.lineWidth = 2.5;

            ctx.strokeText(avgText, bar.x, yAvg - 2);

            ctx.fillStyle = '#ffffff';

            ctx.fillText(avgText, bar.x, yAvg - 2);

          }

          ctx.restore();

        }

        // D. Fastest (Green top) and Slowest (Red bottom) with Collision Protection

        if (width >= 16) {

          ctx.save();

          ctx.font = '600 8.5px Inter, sans-serif';

          ctx.textAlign = 'center';

          const yFast = yAxis.getPixelForValue(it.fastest);

          const ySlow = yAxis.getPixelForValue(it.slowest);

          // Best lap on top

          ctx.fillStyle = '#00e676';

          let fastY = yFast - 4;

          if (fastY < chart.chartArea.top + 8) fastY = yFast + 11;

          ctx.fillText(formatLapTime(it.fastest), bar.x, fastY);

          // Worst lap at bottom

          if (height >= 20) {

            ctx.fillStyle = '#ff4d4d';

            let slowY = ySlow + 11;

            if (slowY > chart.chartArea.bottom - 2) slowY = ySlow - 4;

            ctx.fillText(formatLapTime(it.slowest), bar.x, slowY);

          }

          ctx.restore();

        }

      });

    }

  };

  let currentFp1TruePaceK = 5;
  let fp1TruePaceChartInstance = null;

  function setFp1TruePaceK(k) {
    currentFp1TruePaceK = k;
    const btn5 = document.getElementById(p + '-truepace-btn-top5');
    const btn8 = document.getElementById(p + '-truepace-btn-top8');
    if (btn5) btn5.classList.toggle('active', k === 5);
    if (btn8) btn8.classList.toggle('active', k === 8);
    const cur = window.CURRENT_EVENT_SHORT || (typeof gp !== 'undefined' && gp ? gp.short : 'THA');
    const fp1Data = (getStintsRoot() && getStintsRoot()[cur]) ? getStintsRoot()[cur] : {};
    const activeFavRiders = getActiveFp1Riders(cur, fp1Data, cfg.staticKey);
    renderFp1TruePaceChart(cur, activeFavRiders);
  }

  const fp1TruePaceForkPlugin = {
    id: p + 'TruePaceFork',
    afterDatasetsDraw: (chart) => {
      const ctx = chart.ctx;
      const meta = chart.getDatasetMeta(0);
      if (!meta || !meta.data) return;
      const yAxis = chart.scales.y;
      const items = chart.customPaceItems || [];

      meta.data.forEach((bar, idx) => {
        const it = items[idx];
        if (!it) return;

        const left = bar.x - bar.width / 2;
        const right = bar.x + bar.width / 2;
        const width = bar.width;

        const yPeak = yAxis.getPixelForValue(it.bestLap);
        const yPace = yAxis.getPixelForValue(it.truePace);
        const top = Math.min(yPeak, yPace);
        const bottom = Math.max(yPeak, yPace);
        const height = Math.max(4, bottom - top);

        // 1. Vertical Fork Capsule
        ctx.save();
        ctx.strokeStyle = it.color;
        ctx.lineWidth = 2;
        ctx.fillStyle = it.color + '2e'; // ~18% fill opacity

        ctx.beginPath();
        ctx.roundRect(left, top, width, height, 5);
        ctx.fill();
        ctx.stroke();
        ctx.restore();

        // 2. Top Peak Notch (Green line & text)
        ctx.save();
        ctx.strokeStyle = '#00e676';
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(left - 2, top);
        ctx.lineTo(right + 2, top);
        ctx.stroke();

        // Peak Label (Green, above)
        ctx.font = '700 8.5px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#00e676';
        let peakY = top - 4;
        if (peakY < chart.chartArea.top + 8) peakY = top + 11;
        ctx.fillText(formatLapTime(it.bestLap), bar.x, peakY);
        ctx.restore();

        // 3. Bottom Pace Notch (White line & text)
        ctx.save();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(left - 2, bottom);
        ctx.lineTo(right + 2, bottom);
        ctx.stroke();

        // Pace Label (White, below)
        ctx.font = '700 8.5px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#ffffff';
        let paceY = bottom + 11;
        if (paceY > chart.chartArea.bottom - 2) paceY = bottom - 4;
        ctx.fillText(formatLapTime(it.truePace), bar.x, paceY);
        ctx.restore();

        // 4. Center Delta (Gap Peak -> Pace)
        const diff = (it.truePace - it.bestLap).toFixed(3);
        if (height >= 24 && width >= 18) {
          ctx.save();
          const centerY = (top + bottom) / 2;
          ctx.font = '800 8.5px Inter, sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.strokeStyle = '#121318';
          ctx.lineWidth = 3;
          const deltaTxt = 'Δ ' + diff + 's';
          ctx.strokeText(deltaTxt, bar.x, centerY);
          ctx.fillStyle = '#ffb74d';
          ctx.fillText(deltaTxt, bar.x, centerY);
          ctx.restore();
        }
      });
    }
  };

  function renderFp1TruePaceChart(gpShort, favList) {
    const cvs = document.getElementById('chart-' + p + '-truepace');
    if (!cvs) return;
    const cardEl = document.getElementById(p + '-truepace-card');
    if (!cardEl) return;

    const rawFp1 = (getStintsRoot() && getStintsRoot()[gpShort]) ? getStintsRoot()[gpShort] : null;
    if (!rawFp1 || !favList || !favList.length) {
      if (fp1TruePaceChartInstance) {
        fp1TruePaceChartInstance.destroy();
        fp1TruePaceChartInstance = null;
      }
      return;
    }

    const k = currentFp1TruePaceK || 5;
    const ridersPace = [];

    favList.forEach((rName, rIdx) => {
      const rData = rawFp1[rName];
      if (!rData) return;
      const runs = (rData.runs || []).filter(r => r.lapsCount > 0);
      const validFastest = runs.filter(r => r.fastestSec > 0).map(r => r.fastestSec);
      if (!validFastest.length) return;
      const pb = Math.min(...validFastest);

      const sigLaps = [];
      runs.forEach(r => {
        const sig = getSignificantFp1Laps(r.flying, r.fastestSec, pb);
        const comp = (r.front || r.rear) ? ((r.front || 'M') + '-' + (r.rear || 'M')) : '';
        sig.forEach(s => sigLaps.push({ time: s, comp: comp }));
      });

      if (sigLaps.length < 2) return;
      sigLaps.sort((a, b) => a.time - b.time);

      const topK = sigLaps.slice(0, Math.min(k, sigLaps.length));
      const topKTimes = topK.map(x => x.time);
      const truePace = topKTimes.reduce((a, b) => a + b, 0) / topKTimes.length;
      const bestLap = topKTimes[0];
      const spread = topKTimes[topKTimes.length - 1] - topKTimes[0];

      // Dominant compound in top K (empty when category does not publish tyres)
      const compCounts = {};
      topK.forEach(x => { if (x.comp) compCounts[x.comp] = (compCounts[x.comp] || 0) + 1; });
      let dominantComp = '';
      let maxC = 0;
      Object.keys(compCounts).forEach(c => {
        if (compCounts[c] > maxC) { maxC = compCounts[c]; dominantComp = c; }
      });

      const style = getFp1RiderStyle(rName, rIdx);
      const color = style.color || '#3498db';
      const code = getRiderCode(rName);

      ridersPace.push({
        name: rName,
        code: code,
        color: color,
        bestLap: bestLap,
        truePace: truePace,
        spread: spread,
        comp: dominantComp,
        totalLaps: sigLaps.length
      });
    });

    if (!ridersPace.length) {
      if (fp1TruePaceChartInstance) {
        fp1TruePaceChartInstance.destroy();
        fp1TruePaceChartInstance = null;
      }
      return;
    }

    // Sort by true pace ascending (P1 = fastest race pace)
    ridersPace.sort((a, b) => a.truePace - b.truePace);
    const p1Pace = ridersPace[0].truePace;
    ridersPace.forEach((r, idx) => {
      r.rank = idx + 1;
      r.delta = +(r.truePace - p1Pace).toFixed(3);
    });

    if (fp1TruePaceChartInstance) {
      fp1TruePaceChartInstance.destroy();
      fp1TruePaceChartInstance = null;
    }

    const minT = Math.min(...ridersPace.map(x => x.bestLap));
    const maxT = Math.max(...ridersPace.map(x => x.truePace));
    const yMin = Math.floor((minT - 0.25) * 2) / 2;
    const yMax = Math.ceil((maxT + 0.35) * 2) / 2;

    const labels = ridersPace.map(it => [
      'P' + it.rank + ' ' + it.code,
      it.delta === 0 ? 'LEADER' : ('+' + it.delta.toFixed(2) + 's')
    ]);

    const ctx = cvs.getContext('2d');
    fp1TruePaceChartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          data: ridersPace.map(it => [it.bestLap, it.truePace]),
          backgroundColor: 'transparent',
          borderWidth: 0,
          borderRadius: 5,
          barPercentage: 0.58,
          categoryPercentage: 0.82
        }]
      },
      plugins: [watermarkPlugin, fp1TruePaceForkPlugin],
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 250 },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1b1c24',
            titleColor: '#fff',
            bodyColor: '#ddd',
            borderColor: '#2e2f3d',
            borderWidth: 1,
            padding: 10,
            callbacks: {
              title: (ctxList) => {
                const it = ridersPace[ctxList[0].dataIndex];
                return it ? ('P' + it.rank + ' ' + it.name + ' (' + it.code + ')') : '';
              },
              label: (c) => {
                const it = ridersPace[c.dataIndex];
                if (!it) return '';
                const rows = [
                  ' True Pace (Top ' + k + ' Avg): ' + formatLapTime(it.truePace),
                  ' Best Single Lap: ' + formatLapTime(it.bestLap),
                  ' Peak ➔ Pace Gap: +' + (it.truePace - it.bestLap).toFixed(3) + 's',
                  ' Gap to P1: ' + (it.delta === 0 ? 'LEADER' : ('+' + it.delta.toFixed(3) + 's'))
                ];
                if (it.comp) rows.push(' Prevailing compound: ' + it.comp);
                rows.push(' Consistency (Top ' + k + ' Spread): ' + it.spread.toFixed(3) + 's');
                return rows;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: {
              color: '#aaa',
              font: { family: 'Inter', size: 8, weight: '700' },
              maxRotation: 0,
              autoSkip: false
            }
          },
          y: {
            reverse: true, // Lower lap times on top
            min: yMin,
            max: yMax,
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: {
              color: '#888',
              font: { family: 'Inter', size: 9.5, weight: '600' },
              callback: (v) => {
                if (!v || isNaN(v)) return '';
                const m = Math.floor(v / 60);
                const s = (v % 60).toFixed(1);
                return m + "'" + (s < 10 ? '0' : '') + s;
              }
            }
          }
        }
      }
    });

    fp1TruePaceChartInstance.customPaceItems = ridersPace;
    fp1TruePaceChartInstance.update('none');
  }

  let currentFp1SectorRiderMode = 'favs';
  const fp1SectorChartInstances = { t1: null, t2: null, t3: null, t4: null };

  function setFp1SectorRiderMode(mode) {
    currentFp1SectorRiderMode = mode;
    const bFavs = document.getElementById(p + '-sec-btn-favs');
    const bTop5 = document.getElementById(p + '-sec-btn-top5');
    const bAll = document.getElementById(p + '-sec-btn-all');
    if (bFavs) bFavs.classList.toggle('active', mode === 'favs');
    if (bTop5) bTop5.classList.toggle('active', mode === 'top5');
    if (bAll) bAll.classList.toggle('active', mode === 'all');

    const cur = window.CURRENT_EVENT_SHORT || (typeof gp !== 'undefined' && gp ? gp.short : null);
    if (cur) {
      const rawFp1 = (getStintsRoot() && getStintsRoot()[cur]) ? getStintsRoot()[cur] : {};
      const activeFavRiders = getActiveFp1Riders(cur, rawFp1, cfg.staticKey);
      renderFp1SectorCharts(cur, activeFavRiders);
    }
  }

  function renderFp1SectorCharts(gpShort, favList) {
    const container = document.getElementById(p + '-sectors-container');
    if (!container) return;

    const rawSectors = (getSectorsRoot() && getSectorsRoot()[gpShort]) ? getSectorsRoot()[gpShort] : null;
    if (!rawSectors || Object.keys(rawSectors).length === 0) {
      container.style.display = 'none';
      return;
    }
    container.style.display = 'block';

    // Determine rider list based on currentFp1SectorRiderMode
    const allRiders = Object.keys(rawSectors);
    let targetRiders = [];

    if (currentFp1SectorRiderMode === 'top5') {
      targetRiders = allRiders.map(rName => {
        const rd = rawSectors[rName];
        let bestSec = Infinity;
        (rd.runs || []).forEach(rn => {
          (rn.laps || []).forEach((l, idx) => {
            if (idx > 0 && !l.pit && l.sec && l.sec < bestSec && l.sec > 60) bestSec = l.sec;
          });
        });
        return { name: rName, bestSec };
      }).sort((a, b) => a.bestSec - b.bestSec).slice(0, 5).map(x => x.name);
    } else if (currentFp1SectorRiderMode === 'all') {
      targetRiders = allRiders;
    } else {
      // 'favs' mode: active favorite riders that exist in this session
      targetRiders = (favList && favList.length) ? favList.filter(r => rawSectors[r]) : [];
      if (targetRiders.length === 0) {
        targetRiders = allRiders.map(rName => {
          const rd = rawSectors[rName];
          let bestSec = Infinity;
          (rd.runs || []).forEach(rn => {
            (rn.laps || []).forEach((l, idx) => {
              if (idx > 0 && !l.pit && l.sec && l.sec < bestSec && l.sec > 60) bestSec = l.sec;
            });
          });
          return { name: rName, bestSec };
        }).sort((a, b) => a.bestSec - b.bestSec).slice(0, 5).map(x => x.name);
      }
    }

    // Update button active state
    const bFavs = document.getElementById(p + '-sec-btn-favs');
    const bTop5 = document.getElementById(p + '-sec-btn-top5');
    const bAll = document.getElementById(p + '-sec-btn-all');
    if (bFavs) bFavs.classList.toggle('active', currentFp1SectorRiderMode === 'favs');
    if (bTop5) bTop5.classList.toggle('active', currentFp1SectorRiderMode === 'top5');
    if (bAll) bAll.classList.toggle('active', currentFp1SectorRiderMode === 'all');

    // 1. Extract clean flying laps per run for each target rider
    const riderRunsFlying = {};
    let maxRunNum = 0;

    targetRiders.forEach(rName => {
      const rd = rawSectors[rName];
      if (!rd) return;
      riderRunsFlying[rName] = {};

      let bestLapSec = Infinity;
      (rd.runs || []).forEach(r => {
        (r.laps || []).forEach((l, idx) => {
          if (idx > 0 && !l.pit && l.sec && l.sec < bestLapSec && l.sec > 60) {
            bestLapSec = l.sec;
          }
        });
      });
      const maxAllowedSec = bestLapSec < Infinity ? (bestLapSec * 1.045) : Infinity;

      (rd.runs || []).forEach(r => {
        const rNum = r.run;
        if (rNum > maxRunNum) maxRunNum = rNum;
        if (!riderRunsFlying[rName][rNum]) riderRunsFlying[rName][rNum] = [];

        (r.laps || []).forEach((l, idx) => {
          const isOutLap = (idx === 0);
          const isInLap = l.pit;
          const isSlow = l.sec > maxAllowedSec;
          if (!isOutLap && !isInLap && !isSlow) {
            riderRunsFlying[rName][rNum].push(l);
          }
        });
      });
    });

    // 2. Determine max laps per run across target riders
    const runMaxLaps = {};
    for (let r = 1; r <= maxRunNum; r++) {
      let m = 0;
      targetRiders.forEach(rName => {
        const laps = (riderRunsFlying[rName] && riderRunsFlying[rName][r]) || [];
        if (laps.length > m) m = laps.length;
      });
      runMaxLaps[r] = m;
    }

    // 3. Build unified X-axis labels with gaps between stints
    const labels = [];
    const runIndices = {};

    for (let r = 1; r <= maxRunNum; r++) {
      const count = runMaxLaps[r] || 0;
      if (count === 0) continue;
      runIndices[r] = [];

      for (let l = 1; l <= count; l++) {
        runIndices[r].push(labels.length);
        labels.push(`R${r}-L${l}`);
      }

      // Small gap between consecutive stints
      if (r < maxRunNum) {
        labels.push('');
      }
    }

    // Predefined color palette for "All Riders" mode
    const defaultColors = [
      '#ff4d4d', '#ff7a00', '#a0a0a8', '#00b0ff', '#e02424',
      '#ec4899', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4',
      '#84cc16', '#d946ef', '#14b8a6', '#f43f5e', '#6366f1',
      '#eab308', '#22c55e', '#a855f7', '#3b82f6', '#f97316',
      '#64748b', '#cbd5e1', '#e2e8f0'
    ];

    ['t1', 't2', 't3', 't4'].forEach(secKey => {
      const canvasId = 'chart-' + p + '-sec-' + secKey;
      const canvasEl = document.getElementById(canvasId);
      if (!canvasEl) return;

      if (fp1SectorChartInstances[secKey]) {
        try { fp1SectorChartInstances[secKey].destroy(); } catch(e) {}
        fp1SectorChartInstances[secKey] = null;
      }

      const datasets = targetRiders.map((rName, rIdx) => {
        const style = getFp1RiderStyle(rName, rIdx);
        const color = style.color || defaultColors[rIdx % defaultColors.length];

        const dataPoints = new Array(labels.length).fill(null);

        for (let r = 1; r <= maxRunNum; r++) {
          const laps = (riderRunsFlying[rName] && riderRunsFlying[rName][r]) || [];
          const indices = runIndices[r] || [];
          laps.forEach((l, idx) => {
            if (idx < indices.length) {
              const pos = indices[idx];
              const val = l[secKey];
              if (val && val > 0) {
                dataPoints[pos] = val;
              }
            }
          });
        }

        const ds = {
          label: getRiderCode(rName),
          data: dataPoints,
          borderColor: color,
          backgroundColor: color,
          borderWidth: (currentFp1SectorRiderMode === 'all') ? 1.8 : 2.2,
          pointRadius: (currentFp1SectorRiderMode === 'all') ? 2.5 : 3.5,
          pointHoverRadius: 6,
          tension: 0.15,
          spanGaps: false // CRITICAL: creates distinct line segments per stint with small gaps!
        };

        if (style.borderDash && currentFp1SectorRiderMode !== 'all') {
          ds.borderDash = style.borderDash;
        }

        return ds;
      });

      const ctx = canvasEl.getContext('2d');
      fp1SectorChartInstances[secKey] = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: datasets
        },
        plugins: (typeof watermarkPlugin !== 'undefined' ? [watermarkPlugin] : []),
        options: {
          responsive: true,
          maintainAspectRatio: false,
          layout: {
            padding: { left: 8, right: 8, top: 4, bottom: 4 }
          },
          plugins: {
            legend: {
              display: true,
              position: 'top',
              labels: {
                color: '#aaa',
                font: { family: 'Inter', size: (targetRiders.length > 8 ? 7.5 : 9), weight: '700' },
                boxWidth: 10,
                padding: (targetRiders.length > 8 ? 6 : 10)
              }
            },
            tooltip: {
              backgroundColor: '#1b1c24',
              titleColor: '#fff',
              bodyColor: '#ddd',
              borderColor: '#2e2f3d',
              borderWidth: 1,
              padding: 8,
              callbacks: {
                title: (items) => {
                  if (!items || !items.length) return '';
                  const lbl = labels[items[0].dataIndex];
                  return lbl ? ('Stint progression: ' + lbl) : '';
                },
                label: (c) => {
                  const y = c.parsed.y;
                  return ' ' + c.dataset.label + ': ' + (y ? y.toFixed(3) + 's' : '--');
                }
              }
            }
          },
          scales: {
            x: {
              grid: {
                color: (ctx) => {
                  if (ctx.tick && ctx.tick.label === '') return 'rgba(255, 255, 255, 0.14)';
                  return 'rgba(255, 255, 255, 0.04)';
                }
              },
              ticks: {
                color: '#888',
                font: { family: 'Inter', size: 9, weight: '600' },
                maxRotation: 0,
                callback: function(val, index) {
                  return labels[index] || '';
                }
              }
            },
            y: {
              grid: { color: 'rgba(255, 255, 255, 0.04)' },
              ticks: {
                color: '#888',
                font: { family: 'Inter', size: 9, weight: '600' },
                callback: (v) => v.toFixed(2) + 's'
              }
            }
          }
        }
      });
    });
  }

  function renderFp1DensityChart(gpShort, favList) {

    const cvs = document.getElementById('chart-' + p + '-density');

    if (!cvs) return;

    const cardEl = document.getElementById(p + '-density-card');

    if (!cardEl) return;

    const rawFp1 = (getStintsRoot() && getStintsRoot()[gpShort]) ? getStintsRoot()[gpShort] : null;

    if (!rawFp1 || !favList || !favList.length) {

      if (fp1DensityChartInstance) {

        fp1DensityChartInstance.destroy();

        fp1DensityChartInstance = null;

      }

      return;

    }

    const mode = currentFp1DensityMode;

    const items = [];

    let globalMin = 999;

    let globalMax = 0;

    if (mode === 'runs') {

      favList.forEach((rName, rIdx) => {

        const rData = rawFp1[rName];

        if (!rData) return;

        const style = getFp1RiderStyle(rName, rIdx);

        const color = style.color || '#3498db';

        const code = getRiderCode(rName);

        const runs = (rData.runs || []).filter(r => r.lapsCount > 0);
        const validFastest = runs.filter(r => r.fastestSec > 0).map(r => r.fastestSec);
        const riderPbSec = validFastest.length ? Math.min(...validFastest) : 999;

        runs.forEach((r, idx) => {

          const sig = getSignificantFp1Laps(r.flying, r.fastestSec, riderPbSec);

          if (!sig.length) return;

          const fastest = Math.min(...sig);

          const slowest = Math.max(...sig);

          const avg = sig.reduce((a, b) => a + b, 0) / sig.length;

          if (fastest < globalMin) globalMin = fastest;

          if (slowest > globalMax) globalMax = slowest;

          const hasComp = Boolean(r.front || r.rear);
          const compLabel = hasComp ? ((r.front || 'M') + '-' + (r.rear || 'M')) : '';

          items.push({

            riderName: rName,

            code: code,

            riderIdx: rIdx,

            color: color,

            runIdx: idx + 1,

            compound: compLabel,

            lapsCount: sig.length,

            laps: sig,

            fastest,

            slowest,

            avg,

            xLabel: [code, hasComp ? ('R' + (idx + 1) + ' · ' + compLabel) : ('R' + (idx + 1) + ' · ' + sig.length + 'L')]

          });

        });

      });

    } else {

      // Overall: 1 pillar per rider with all significant laps combined
      favList.forEach((rName, rIdx) => {
        const rData = rawFp1[rName];
        if (!rData) return;
        const style = getFp1RiderStyle(rName, rIdx);
        const color = style.color || '#3498db';
        const code = getRiderCode(rName);

        const runs = (rData.runs || []).filter(r => r.lapsCount > 0);
        const validFastest = runs.filter(r => r.fastestSec > 0).map(r => r.fastestSec);
        const riderPbSec = validFastest.length ? Math.min(...validFastest) : 999;

        const allLaps = [];
        runs.forEach(r => {
          const sig = getSignificantFp1Laps(r.flying, r.fastestSec, riderPbSec);
          allLaps.push(...sig);
        });

        if (!allLaps.length) return;

        const fastest = Math.min(...allLaps);

        const slowest = Math.max(...allLaps);

        const avg = allLaps.reduce((a, b) => a + b, 0) / allLaps.length;

        if (fastest < globalMin) globalMin = fastest;

        if (slowest > globalMax) globalMax = slowest;

        items.push({

          riderName: rName,

          code: code,

          riderIdx: rIdx,

          color: color,

          lapsCount: allLaps.length,

          laps: allLaps,

          fastest,

          slowest,

          avg,

          xLabel: [code, allLaps.length + ' laps']

        });

      });

    }

    if (!items.length) {

      if (fp1DensityChartInstance) {

        fp1DensityChartInstance.destroy();

        fp1DensityChartInstance = null;

      }

      return;

    }

    if (fp1DensityChartInstance) {

      fp1DensityChartInstance.destroy();

      fp1DensityChartInstance = null;

    }

    const yMin = Math.floor((globalMin - 0.25) * 2) / 2;

    const yMax = Math.ceil((globalMax + 0.35) * 2) / 2;

    const ctx = cvs.getContext('2d');

    fp1DensityChartInstance = new Chart(ctx, {

      type: 'bar',

      data: {

        labels: items.map(it => it.xLabel),

        datasets: [{

          data: items.map(it => [it.fastest, it.slowest]),

          backgroundColor: 'transparent',

          borderWidth: 0,

          borderRadius: 4,

          barPercentage: mode === 'runs' ? 0.72 : 0.6,

          categoryPercentage: 0.86

        }]

      },

      plugins: [watermarkPlugin, fp1DensityTicksPlugin],

      options: {

        responsive: true,

        maintainAspectRatio: false,

        animation: { duration: 250 },

        plugins: {

          legend: { display: false },

          tooltip: {

            backgroundColor: '#1b1c24',

            titleColor: '#fff',

            bodyColor: '#ddd',

            borderColor: '#2e2f3d',

            borderWidth: 1,

            padding: 10,

            callbacks: {

              title: (ctxList) => {

                const it = items[ctxList[0].dataIndex];

                return it ? (it.riderName + ' · ' + (mode === 'runs' ? ('Run ' + it.runIdx + (it.compound ? ' [' + it.compound + ']' : '')) : 'Overall')) : '';

              },

              label: (c) => {

                const it = items[c.dataIndex];

                if (!it) return '';

                return [

                  ' Average pace: ' + formatLapTime(it.avg),

                  ' Best lap: ' + formatLapTime(it.fastest),

                  ' Slowest lap: ' + formatLapTime(it.slowest),

                  ' Pace dispersion: +' + (it.slowest - it.fastest).toFixed(3) + 's',

                  ' Significant laps: ' + it.lapsCount

                ];

              }

            }

          }

        },

        scales: {

          x: {

            grid: { color: 'rgba(255, 255, 255, 0.05)' },

            ticks: {

              color: '#aaa',

              font: { family: 'Inter', size: mode === 'runs' ? 8.5 : 10, weight: '700' },

              maxRotation: 0

            }

          },

          y: {

            reverse: true,

            min: yMin,

            max: yMax,

            grid: { color: 'rgba(255, 255, 255, 0.05)' },

            ticks: {

              color: '#888',

              font: { family: 'Inter', size: 9.5, weight: '600' },

              callback: (v) => {

                if (!v || isNaN(v)) return '';

                const m = Math.floor(v / 60);

                const s = (v % 60).toFixed(1);

                return m + "'" + (s < 10 ? '0' : '') + s;

              }

            }

          }

        }

      }

    });

    fp1DensityChartInstance.customDensityItems = items;

    fp1DensityChartInstance.customDensityMode = mode;

    fp1DensityChartInstance.update('none');

  }

  function renderFp1StintsChart(gpShort, favList) {

    const cvs = document.getElementById('chart-' + p + '-stints');

    if (!cvs) return;

    const ctx = cvs.getContext('2d');

    const tooltipEl = document.getElementById(p + '-tooltip');

    const data = (getStintsRoot() && getStintsRoot()[gpShort]) ? getStintsRoot()[gpShort] : {};

    const riders = favList.filter(r => data[r]).map(r => ({

      name: r,

      ...data[r]

    }));

    if (!riders.length) return;

    const rect = cvs.parentElement.getBoundingClientRect();

    const dpr = window.devicePixelRatio || 1;

    const width = rect.width || 340;

    const height = rect.height || 320;

    cvs.width = width * dpr;

    cvs.height = height * dpr;

    cvs.style.width = width + 'px';

    cvs.style.height = height + 'px';

    ctx.scale(dpr, dpr);

    const leftPad = 54; // compact width: rider code stacked above colored line

    const rightPad = 16;

    const topPad = 25;

    const bottomPad = 16; // reduced since x-axis didascalia is removed

    const chartW = width - leftPad - rightPad;

    const chartH = height - topPad - bottomPad;

    const maxLaps = Math.max(...riders.map(r => r.totalLaps), 15);

    const xScale = (lap) => leftPad + (lap / maxLaps) * chartW;

    ctx.clearRect(0, 0, width, height);

    // Watermark

    ctx.save();

    ctx.font = '900 24px Inter, sans-serif';

    ctx.fillStyle = 'rgba(255, 255, 255, 0.025)';

    ctx.textAlign = 'center';

    ctx.textBaseline = 'middle';

    ctx.fillText('OVERREVVING', width / 2, height / 2);

    ctx.restore();

    // Small legend in alto nel grafico (Pace = Purple, Time Attack = Orange)

    const legW = 160;

    const legX = Math.max(leftPad + 10, width - rightPad - legW);

    const legY = 13;

    ctx.save();

    ctx.font = '600 10px Inter, sans-serif';

    ctx.textAlign = 'left';

    ctx.textBaseline = 'middle';

    // Pace

    ctx.fillStyle = FP1_STINT_COLOR_PACE;

    if (ctx.roundRect) {

      ctx.beginPath();

      ctx.roundRect(legX, legY - 2.5, 14, 5, 2);

      ctx.fill();

    } else {

      ctx.fillRect(legX, legY - 2.5, 14, 5);

    }

    ctx.fillStyle = '#cbd5e1';

    ctx.fillText('Pace', legX + 18, legY);

    // Time Attack

    ctx.fillStyle = FP1_STINT_COLOR_TA;

    if (ctx.roundRect) {

      ctx.beginPath();

      ctx.roundRect(legX + 62, legY - 2.5, 14, 5, 2);

      ctx.fill();

    } else {

      ctx.fillRect(legX + 62, legY - 2.5, 14, 5);

    }

    ctx.fillStyle = '#cbd5e1';

    ctx.fillText('Time Attack', legX + 80, legY);

    ctx.restore();

    // Draw faint vertical grid lines without x-axis didascalia

    ctx.save();

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';

    ctx.lineWidth = 1;

    const tickStep = maxLaps > 25 ? 5 : (maxLaps > 15 ? 3 : 2);

    for (let l = 0; l <= maxLaps; l += tickStep) {

      const x = xScale(l);

      ctx.beginPath();

      ctx.moveTo(x, topPad);

      ctx.lineTo(x, height - bottomPad);

      ctx.stroke();

    }

    ctx.restore();

    // Find global best and worst times across all displayed stints

    let allFastest = [];

    riders.forEach(r => {

      (r.runs || []).forEach(s => {

        if (s.lapsCount > 0 && s.fastestSec > 0) {

          allFastest.push(s.fastestSec);

        }

      });

    });

    const minFastest = allFastest.length ? Math.min(...allFastest) : 0;

    const maxFastest = allFastest.length ? Math.max(...allFastest) : 0;

    const hitAreas = [];

    const numRiders = riders.length;

    const rowGap = 10;

    const rowTotalH = Math.min(46, (chartH - (numRiders - 1) * rowGap) / numRiders);

    const narrowH = Math.round(rowTotalH * 0.38);

    const wideH = rowTotalH - narrowH;

    const stintGap = 4;

    riders.forEach((rider, rIdx) => {

      const rowY = topPad + rIdx * (rowTotalH + rowGap);

      const style = getFp1RiderStyle(rider.name, rIdx);

      const riderColor = style.color || '#3498db';

      // 1. Stacked rider identifier (Rider code on top, colored line underneath)

      const colCenterX = Math.round((leftPad - 8) / 2);

      ctx.save();

      // Rider Code

      ctx.font = '800 12px Inter, sans-serif';

      ctx.textAlign = 'center';

      ctx.textBaseline = 'middle';

      ctx.fillStyle = '#ffffff';

      ctx.fillText(rider.code, colCenterX, rowY + rowTotalH * 0.35);

      // Colored line underneath (width 26px, solid or dashed)

      const lineW = 26;

      const lineX = colCenterX - lineW / 2;

      const lineY = rowY + rowTotalH * 0.72;

      ctx.strokeStyle = riderColor;

      ctx.lineWidth = 3;

      ctx.lineCap = 'round';

      if (style.borderDash && Array.isArray(style.borderDash)) {

        ctx.setLineDash(style.borderDash);

      } else {

        ctx.setLineDash([]);

      }

      ctx.beginPath();

      ctx.moveTo(lineX, lineY);

      ctx.lineTo(lineX + lineW, lineY);

      ctx.stroke();

      ctx.restore();

      // 3. Draw Stints with Pace / Time Attack classification

      const runs = classifyFp1Runs((rider.runs || []).filter(s => s.lapsCount > 0));

      runs.forEach((stint, sIdx) => {

        const xStart = xScale(stint.startLap - 1) + (sIdx > 0 ? (stintGap / 2) : 0);

        const xEnd = xScale(stint.endLap) - (stintGap / 2);

        const blockW = Math.max(8, xEnd - xStart);

        const hasComp = Boolean(stint.front || stint.rear);

        const fColor = hasComp ? (FP1_TYRE_COLORS[stint.front] || FP1_TYRE_COLORS['M']) : '#475569';

        const rColor = hasComp ? (FP1_TYRE_COLORS[stint.rear] || FP1_TYRE_COLORS['M']) : '#e2e8f0';

        const isBest = (stint.fastestSec > 0 && stint.fastestSec === minFastest);

        const isWorst = (stint.fastestSec > 0 && stint.fastestSec === maxFastest);

        hitAreas.push({

          x: xStart,

          y: rowY,

          w: blockW,

          h: rowTotalH,

          rider: rider,

          stint: stint,

          runNum: sIdx + 1

        });

        ctx.save();

        // Upper narrow row: Front Tyre (MotoGP) or Run # & Laps (Moto2/Moto3)

        ctx.fillStyle = fColor;

        if (ctx.roundRect) {

          ctx.beginPath();

          ctx.roundRect(xStart, rowY, blockW, narrowH, [4, 4, 0, 0]);

          ctx.fill();

        } else {

          ctx.fillRect(xStart, rowY, blockW, narrowH);

        }

        ctx.fillStyle = hasComp ? '#111114' : '#f8fafc';

        ctx.textAlign = 'center';

        ctx.textBaseline = 'middle';

        ctx.font = '700 8.5px Inter, sans-serif';

        let fText = '';
        if (hasComp) {
          fText = stint.front;
          if (blockW >= 55) fText = stint.front + ' · ' + stint.lapsCount + ' laps';
          else if (blockW >= 32) fText = stint.front + ' · ' + stint.lapsCount + 'L';
          else if (blockW >= 18) fText = stint.front + stint.lapsCount;
        } else {
          if (blockW >= 58) fText = 'R' + (sIdx + 1) + ' · ' + stint.lapsCount + ' laps';
          else if (blockW >= 34) fText = 'R' + (sIdx + 1) + ' · ' + stint.lapsCount + 'L';
          else if (blockW >= 18) fText = 'R' + (sIdx + 1);
        }

        if (fText) ctx.fillText(fText, xStart + blockW / 2, rowY + narrowH / 2);

        // Divider

        ctx.strokeStyle = 'rgba(0, 0, 0, 0.25)';

        ctx.lineWidth = 1;

        ctx.beginPath();

        ctx.moveTo(xStart, rowY + narrowH);

        ctx.lineTo(xStart + blockW, rowY + narrowH);

        ctx.stroke();

        // Lower wide row: Rear Tyre + Fastest Lap (MotoGP) or Fastest Lap (Moto2/Moto3)

        ctx.fillStyle = rColor;

        if (ctx.roundRect) {

          ctx.beginPath();

          ctx.roundRect(xStart, rowY + narrowH, blockW, wideH, [0, 0, 4, 4]);

          ctx.fill();

        } else {

          ctx.fillRect(xStart, rowY + narrowH, blockW, wideH);

        }

        let rTime = stint.fastest || '-';

        if (blockW < 56 && rTime.includes("'")) {

          rTime = rTime.replace("1'", "'");

        }

        let rText = '';
        if (hasComp) {
          rText = stint.rear + ' · ' + rTime;
          if (blockW < 52) rText = stint.rear + ' ' + rTime;
          if (blockW < 40) rText = stint.rear;
          if (blockW < 16) rText = '';
        } else {
          rText = rTime;
          if (blockW < 26) rText = '';
        }

        const fontSize = blockW < 36 ? 8 : (blockW < 50 ? 9 : (blockW < 65 ? 10 : 10.5));

        ctx.font = `800 ${fontSize}px Inter, sans-serif`;

        if (isBest || isWorst) {

          const bgBadge = isBest ? '#063818' : '#4a0808';

          const borderBadge = isBest ? '#00e676' : '#ff4d4d';

          const textBadge = isBest ? '#00e676' : '#ff7979';

          const textMetrics = ctx.measureText(rText);

          const bW = Math.max(12, Math.min(blockW - 4, textMetrics.width + (rText.length > 2 ? 10 : 6)));

          const bH = wideH - 5;

          const bX = xStart + (blockW - bW) / 2;

          const bY = rowY + narrowH + (wideH - bH) / 2;

          ctx.fillStyle = bgBadge;

          ctx.strokeStyle = borderBadge;

          ctx.lineWidth = 1;

          if (ctx.roundRect) {

            ctx.beginPath();

            ctx.roundRect(bX, bY, bW, bH, 3);

            ctx.fill();

            ctx.stroke();

          } else {

            ctx.fillRect(bX, bY, bW, bH);

            ctx.strokeRect(bX, bY, bW, bH);

          }

          ctx.fillStyle = textBadge;

          if (rText && blockW >= 16) {

            ctx.fillText(rText, xStart + blockW / 2, rowY + narrowH + wideH / 2);

          }

        } else {

          ctx.fillStyle = '#111114';

          if (rText && blockW >= 16) {

            ctx.fillText(rText, xStart + blockW / 2, rowY + narrowH + wideH / 2);

          }

        }

        // Line at bottom of stint box indicating Pace vs Time Attack

        const stintTypeColor = stint.isTA ? FP1_STINT_COLOR_TA : FP1_STINT_COLOR_PACE;

        const lineH = 3.5;

        ctx.fillStyle = stintTypeColor;

        if (ctx.roundRect) {

          ctx.beginPath();

          ctx.roundRect(xStart, rowY + rowTotalH - lineH, blockW, lineH, [0, 0, 4, 4]);

          ctx.fill();

        } else {

          ctx.fillRect(xStart, rowY + rowTotalH - lineH, blockW, lineH);

        }

        // Border around stint

        ctx.strokeStyle = 'rgba(0, 0, 0, 0.35)';

        ctx.lineWidth = 1;

        if (ctx.roundRect) {

          ctx.beginPath();

          ctx.roundRect(xStart, rowY, blockW, rowTotalH, 4);

          ctx.stroke();

        }

        ctx.restore();

      });

    });

    // Tooltip mousemove handler

    cvs.onmousemove = (e) => {

      const cRect = cvs.getBoundingClientRect();

      const mouseX = e.clientX - cRect.left;

      const mouseY = e.clientY - cRect.top;

      const hit = hitAreas.find(ha => 

        mouseX >= ha.x && mouseX <= ha.x + ha.w &&

        mouseY >= ha.y && mouseY <= ha.y + ha.h

      );

      if (hit && tooltipEl) {

        const compoundNames = { 'S': 'Soft', 'M': 'Medium', 'H': 'Hard' };

        const hasComp = Boolean(hit.stint.front || hit.stint.rear);

        const fName = compoundNames[hit.stint.front] || hit.stint.front;

        const rName = compoundNames[hit.stint.rear] || hit.stint.rear;

        const stintTypeLabel = hit.stint.isTA ? 'Time Attack' : 'Pace';

        const stintTypeColor = hit.stint.isTA ? FP1_STINT_COLOR_TA : FP1_STINT_COLOR_PACE;

        const tyreRows = hasComp
          ? `<div class="tt-row"><span>Front Tyre:</span> <span class="tt-val">${fName} (${hit.stint.lapsCount} laps)</span></div>
             <div class="tt-row"><span>Rear Tyre:</span> <span class="tt-val">${rName} (${hit.stint.lapsCount} laps)</span></div>`
          : `<div class="tt-row"><span>Stint Length:</span> <span class="tt-val">${hit.stint.lapsCount} laps</span></div>`;

        tooltipEl.innerHTML = `

          <div class="tt-title">${hit.rider.code} &middot; ${hit.rider.name} &middot; Run #${hit.runNum}</div>

          <div class="tt-row"><span>Stint Type:</span> <span class="tt-val" style="color:${stintTypeColor}; font-weight:700;">${stintTypeLabel}</span></div>

          ${tyreRows}

          <div class="tt-row"><span>Fastest Lap in Stint:</span> <span class="tt-val" style="color:#2ecc71">${hit.stint.fastest}</span></div>

          <div class="tt-row"><span>Lap Range:</span> <span class="tt-val">L${hit.stint.startLap} - L${hit.stint.endLap}</span></div>

        `;

        tooltipEl.style.display = 'block';

        let ttX = mouseX + 15;

        let ttY = mouseY + 15;

        if (ttX + 220 > cRect.width) ttX = mouseX - 225;

        if (ttX < 10) ttX = 10;

        if (ttY + 110 > cRect.height) ttY = mouseY - 115;

        if (ttY < 10) ttY = 10;

        tooltipEl.style.left = ttX + 'px';

        tooltipEl.style.top = ttY + 'px';

      } else if (tooltipEl) {

        tooltipEl.style.display = 'none';

      }

    };

    cvs.onmouseleave = () => {

      if (tooltipEl) tooltipEl.style.display = 'none';

    };

  }

  let currentFp1HeatmapMode = 'matrix';

  try {

    const saved = localStorage.getItem(cfg.heatmapStorageKey);

    if (saved === 'matrix' || saved === 'riders') currentFp1HeatmapMode = saved;

  } catch(e) {}

  function setFp1HeatmapMode(mode) {

    if (mode !== 'matrix' && mode !== 'riders') return;

    currentFp1HeatmapMode = mode;

    try { localStorage.setItem(cfg.heatmapStorageKey, mode); } catch(e) {}

    const btnMatrix = document.getElementById(p + '-heatmap-btn-matrix');

    const btnRiders = document.getElementById(p + '-heatmap-btn-riders');

    if (btnMatrix) btnMatrix.classList.toggle('active', mode === 'matrix');

    if (btnRiders) btnRiders.classList.toggle('active', mode === 'riders');

    const cur = window.CURRENT_EVENT_SHORT || (typeof gp !== 'undefined' && gp ? gp.short : 'THA');

    const fp1Data = (getStintsRoot() && getStintsRoot()[cur]) ? getStintsRoot()[cur] : {};

    const activeFavRiders = getActiveFp1Riders(cur, fp1Data, cfg.staticKey);

    renderFp1HeatmapChart(cur, activeFavRiders);

  }

  let fp1HeatmapHitAreas = [];

  function renderFp1HeatmapChart(gpShort, favList) {

    const cvs = document.getElementById('chart-' + p + '-heatmap');

    if (!cvs) return;

    const ctx = cvs.getContext('2d');

    const tooltipEl = document.getElementById(p + '-heatmap-tooltip');

    fp1HeatmapHitAreas = [];

    const data = (getStintsRoot() && getStintsRoot()[gpShort]) ? getStintsRoot()[gpShort] : {};

    const riders = favList.filter(r => data[r]).map(r => ({

      name: r,

      ...data[r]

    }));

    if (!riders.length) return;

    const rect = cvs.parentElement.getBoundingClientRect();

    const dpr = window.devicePixelRatio || 1;

    const width = rect.width || 300;

    const height = rect.height || 270;

    cvs.width = width * dpr;

    cvs.height = height * dpr;

    cvs.style.width = width + 'px';

    cvs.style.height = height + 'px';

    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, width, height);

    // Watermark

    ctx.save();

    ctx.font = '900 20px Inter, sans-serif';

    ctx.fillStyle = 'rgba(255, 255, 255, 0.025)';

    ctx.textAlign = 'center';

    ctx.textBaseline = 'middle';

    ctx.fillText('OVERREVVING', width / 2, height / 2);

    ctx.restore();

    const compLabels = { 'S': 'SOFT', 'M': 'MED', 'H': 'HARD' };

    const compColors = { 'S': '#ffd600', 'M': '#ffffff', 'H': '#00b0ff' };

    function formatCellTime(sec, availW) {

      if (typeof sec !== 'number' || isNaN(sec) || sec <= 0) return '-';

      const mins = Math.floor(sec / 60);

      const rem = sec % 60;

      const remStr = rem < 10 ? '0' + rem.toFixed(3) : rem.toFixed(3);

      if (availW !== undefined && availW < 54 && mins > 0) {

        return "'" + remStr;

      }

      return mins > 0 ? (mins + "'" + remStr) : remStr;

    }

    if (currentFp1HeatmapMode === 'matrix') {

      // --- 1. MATRIX 3x3 VIEW ---

      const matrix = {

        'S': { 'S': 0, 'M': 0, 'H': 0 },

        'M': { 'S': 0, 'M': 0, 'H': 0 },

        'H': { 'S': 0, 'M': 0, 'H': 0 }

      };

      const cellDetails = {};

      let totalLapsAll = 0;

      let maxCellLaps = 0;

      riders.forEach(rider => {

        (rider.runs || []).forEach(run => {

          const f = run.front || 'M';

          const re = run.rear || 'M';

          const laps = run.lapsCount || 0;

          if (matrix[f] && matrix[f][re] !== undefined && laps > 0) {

            matrix[f][re] += laps;

            totalLapsAll += laps;

            if (matrix[f][re] > maxCellLaps) maxCellLaps = matrix[f][re];

            const key = f + '-' + re;

            if (!cellDetails[key]) {

              cellDetails[key] = { bestTime: run.fastest, bestSec: run.fastestSec, bestRider: rider.name, riders: {} };

            }

            if (run.fastestSec > 0 && run.fastestSec < cellDetails[key].bestSec) {

              cellDetails[key].bestSec = run.fastestSec;

              cellDetails[key].bestTime = run.fastest;

              cellDetails[key].bestRider = rider.name;

            }

            cellDetails[key].riders[rider.name] = (cellDetails[key].riders[rider.name] || 0) + laps;

          }

        });

      });

      const leftPad = 48;

      const topPad = 38;

      const rightPad = 12;

      const bottomPad = 16;

      const gridW = width - leftPad - rightPad;

      const gridH = height - topPad - bottomPad;

      const gap = 6;

      const cellW = (gridW - gap * 2) / 3;

      const cellH = (gridH - gap * 2) / 3;

      const comps = ['S', 'M', 'H'];

      // Headers

      ctx.font = '800 10px Inter, sans-serif';

      ctx.textAlign = 'center';

      ctx.textBaseline = 'middle';

      ctx.fillStyle = '#8b949e';

      ctx.fillText('REAR TYRE →', leftPad + gridW / 2, 12);

      comps.forEach((c, colIdx) => {

        const x = leftPad + colIdx * (cellW + gap) + cellW / 2;

        ctx.fillStyle = compColors[c];

        ctx.fillText(compLabels[c], x, 26);

      });

      ctx.save();

      ctx.translate(12, topPad + gridH / 2);

      ctx.rotate(-Math.PI / 2);

      ctx.fillStyle = '#8b949e';

      ctx.font = '800 10px Inter, sans-serif';

      ctx.textAlign = 'center';

      ctx.fillText('FRONT TYRE →', 0, 0);

      ctx.restore();

      comps.forEach((r, rowIdx) => {

        const y = topPad + rowIdx * (cellH + gap) + cellH / 2;

        ctx.fillStyle = compColors[r];

        ctx.textAlign = 'right';

        ctx.font = '800 10px Inter, sans-serif';

        ctx.fillText(compLabels[r], leftPad - 8, y);

      });

      // Cells

      comps.forEach((f, rowIdx) => {

        comps.forEach((re, colIdx) => {

          const x = leftPad + colIdx * (cellW + gap);

          const y = topPad + rowIdx * (cellH + gap);

          const laps = matrix[f][re];

          const ratio = maxCellLaps > 0 ? (laps / maxCellLaps) : 0;

          let bg = 'rgba(255, 255, 255, 0.03)';

          let border = 'rgba(255, 255, 255, 0.07)';

          if (laps > 0) {

            if (ratio >= 0.70) {

              bg = 'rgba(255, 214, 0, ' + (0.16 + ratio * 0.28) + ')';

              border = 'rgba(255, 214, 0, 0.55)';

            } else if (ratio >= 0.35) {

              bg = 'rgba(0, 176, 255, ' + (0.12 + ratio * 0.22) + ')';

              border = 'rgba(0, 176, 255, 0.45)';

            } else {

              bg = 'rgba(255, 255, 255, ' + (0.06 + ratio * 0.15) + ')';

              border = 'rgba(255, 255, 255, 0.2)';

            }

          }

          ctx.fillStyle = bg;

          ctx.strokeStyle = border;

          ctx.lineWidth = ratio >= 0.7 ? 1.5 : 1;

          if (ctx.roundRect) {

            ctx.beginPath();

            ctx.roundRect(x, y, cellW, cellH, 6);

            ctx.fill();

            ctx.stroke();

          } else {

            ctx.fillRect(x, y, cellW, cellH);

            ctx.strokeRect(x, y, cellW, cellH);

          }

          if (laps > 0) {

            ctx.font = '900 17px Inter, sans-serif';

            ctx.textAlign = 'center';

            ctx.textBaseline = 'middle';

            ctx.fillStyle = '#ffffff';

            ctx.fillText(laps, x + cellW / 2, y + cellH / 2 - 8);

            ctx.font = '700 10px Inter, sans-serif';

            ctx.fillStyle = '#a0aec0';

            const pct = totalLapsAll > 0 ? Math.round((laps / totalLapsAll) * 100) : 0;

            ctx.fillText(pct + '% laps', x + cellW / 2, y + cellH / 2 + 11);

          } else {

            ctx.font = '600 13px Inter, sans-serif';

            ctx.textAlign = 'center';

            ctx.textBaseline = 'middle';

            ctx.fillStyle = 'rgba(255, 255, 255, 0.14)';

            ctx.fillText('—', x + cellW / 2, y + cellH / 2);

          }

          if (laps > 0) {

            fp1HeatmapHitAreas.push({

              x, y, w: cellW, h: cellH,

              type: 'matrix',

              front: f, rear: re,

              laps, totalLapsAll,

              details: cellDetails[f + '-' + re]

            });

          }

        });

      });

    } else {

      // --- 2. RIDERS VIEW ---

      const comboSet = new Set();

      riders.forEach(r => {

        (r.runs || []).forEach(run => {

          if (run.lapsCount > 0) comboSet.add(run.front + '-' + run.rear);

        });

      });

      const combos = Array.from(comboSet);

      const leftPad = 54;

      const topPad = 32;

      const rightPad = 12;

      const bottomPad = 12;

      const chartW = width - leftPad - rightPad;

      const chartH = height - topPad - bottomPad;

      const rowCount = riders.length;

      const rowGap = 6;

      const rowH = (chartH - (rowCount - 1) * rowGap) / rowCount;

      const colGap = 6;

      const colW = (chartW - (combos.length - 1) * colGap) / (combos.length || 1);

      // Header: Combos

      ctx.font = '800 11px Inter, sans-serif';

      ctx.textAlign = 'center';

      ctx.textBaseline = 'middle';

      combos.forEach((c, colIdx) => {

        const x = leftPad + colIdx * (colW + colGap) + colW / 2;

        ctx.fillStyle = '#e2e8f0';

        ctx.fillText(c, x, topPad / 2);

      });

      riders.forEach((rider, rIdx) => {

        const y = topPad + rIdx * (rowH + rowGap);

        const style = (typeof RIDER_STYLES !== 'undefined' && RIDER_STYLES[rider.name]) || {};

        const riderColor = style.color || '#3498db';

        const colCenterX = Math.round((leftPad - 8) / 2);

        ctx.save();

        ctx.font = '800 11px Inter, sans-serif';

        ctx.textAlign = 'center';

        ctx.textBaseline = 'middle';

        ctx.fillStyle = '#ffffff';

        ctx.fillText(rider.code, colCenterX, y + rowH * 0.35);

        const lineW = 22;

        const lineX = colCenterX - lineW / 2;

        const lineY = y + rowH * 0.72;

        ctx.strokeStyle = riderColor;

        ctx.lineWidth = 2.5;

        ctx.lineCap = 'round';

        if (style.borderDash && Array.isArray(style.borderDash) && style.borderDash.length) {

          ctx.setLineDash(style.borderDash);

        } else {

          ctx.setLineDash([]);

        }

        ctx.beginPath();

        ctx.moveTo(lineX, lineY);

        ctx.lineTo(lineX + lineW, lineY);

        ctx.stroke();

        ctx.restore();

        const rCombos = {};

        const rBest = {};

        const rFlying = {};

        (rider.runs || []).forEach(run => {

          if (run.lapsCount > 0) {

            const k = run.front + '-' + run.rear;

            rCombos[k] = (rCombos[k] || 0) + run.lapsCount;

            if (!rBest[k] || (run.fastestSec > 0 && run.fastestSec < rBest[k].sec)) {

              rBest[k] = { time: run.fastest, sec: run.fastestSec };

            }

            if (run.flying && Array.isArray(run.flying)) {

              if (!rFlying[k]) rFlying[k] = [];

              rFlying[k].push(...run.flying);

            }

          }

        });

        combos.forEach((c, colIdx) => {

          const x = leftPad + colIdx * (colW + colGap);

          const laps = rCombos[c] || 0;

          const flyingList = (rFlying[c] || []).slice().sort((a, b) => a - b);

          const top3Laps = flyingList.slice(0, 3);

          const top3AvgSec = top3Laps.length > 0 ? (top3Laps.reduce((a, b) => a + b, 0) / top3Laps.length) : 0;

          const top3AvgStr = top3AvgSec > 0 ? formatCellTime(top3AvgSec, colW) : '-';

          const top3AvgFull = top3AvgSec > 0 ? formatCellTime(top3AvgSec, 999) : '-';

          const top3LapsFormatted = top3Laps.map(s => formatCellTime(s, 999));

          let bg = 'rgba(255, 255, 255, 0.03)';

          let border = 'rgba(255, 255, 255, 0.06)';

          if (laps > 0) {

            bg = 'rgba(0, 230, 118, ' + (0.12 + Math.min(laps / 18, 1) * 0.35) + ')';

            border = 'rgba(0, 230, 118, 0.45)';

          }

          ctx.fillStyle = bg;

          ctx.strokeStyle = border;

          ctx.lineWidth = 1;

          if (ctx.roundRect) {

            ctx.beginPath();

            ctx.roundRect(x, y, colW, rowH, 4);

            ctx.fill();

            ctx.stroke();

          } else {

            ctx.fillRect(x, y, colW, rowH);

            ctx.strokeRect(x, y, colW, rowH);

          }

          if (laps > 0) {

            if (top3AvgSec > 0) {

              const yShift = rowH >= 38 ? 8 : 6;

              const lapFont = rowH >= 38 ? '800 11px Inter, sans-serif' : '800 10px Inter, sans-serif';

              const avgFont = rowH >= 38 ? '700 10px Inter, sans-serif' : '700 9px Inter, sans-serif';

              ctx.font = lapFont;

              ctx.textAlign = 'center';

              ctx.textBaseline = 'middle';

              ctx.fillStyle = '#ffffff';

              ctx.fillText(laps + ' L', x + colW / 2, y + rowH / 2 - yShift);

              ctx.font = avgFont;

              ctx.fillStyle = '#e2e8f0';

              ctx.fillText(top3AvgStr, x + colW / 2, y + rowH / 2 + yShift);

            } else {

              ctx.font = '800 12px Inter, sans-serif';

              ctx.textAlign = 'center';

              ctx.textBaseline = 'middle';

              ctx.fillStyle = '#ffffff';

              ctx.fillText(laps + ' L', x + colW / 2, y + rowH / 2);

            }

          } else {

            ctx.font = '600 11px Inter, sans-serif';

            ctx.textAlign = 'center';

            ctx.textBaseline = 'middle';

            ctx.fillStyle = 'rgba(255, 255, 255, 0.12)';

            ctx.fillText('—', x + colW / 2, y + rowH / 2);

          }

          if (laps > 0) {

            fp1HeatmapHitAreas.push({

              x, y, w: colW, h: rowH,

              type: 'riders',

              riderName: rider.name,

              riderCode: rider.code,

              combo: c,

              laps,

              riderTotalLaps: rider.totalLaps,

              top3AvgStr: top3AvgFull,

              top3Count: top3Laps.length,

              top3LapsFormatted,

              bestTime: rBest[c] ? rBest[c].time : '-'

            });

          }

        });

      });

    }

    // TOOLTIP MOUSE HANDLER

    cvs.onmousemove = function(e) {

      if (!tooltipEl) return;

      const cRect = cvs.getBoundingClientRect();

      const mx = e.clientX - cRect.left;

      const my = e.clientY - cRect.top;

      const hit = fp1HeatmapHitAreas.find(a => mx >= a.x && mx <= a.x + a.w && my >= a.y && my <= a.y + a.h);

      if (hit) {

        cvs.style.cursor = 'pointer';

        let html = '';

        if (hit.type === 'matrix') {

          const fLabel = compLabels[hit.front];

          const rLabel = compLabels[hit.rear];

          const pct = hit.totalLapsAll > 0 ? Math.round((hit.laps / hit.totalLapsAll) * 100) : 0;

          html = `

            <div class="tt-title">Front: ${fLabel} · Rear: ${rLabel} (${hit.front}-${hit.rear})</div>

            <div class="tt-row"><span>Total Laps:</span><span class="tt-val">${hit.laps} laps (${pct}% of favorites)</span></div>

          `;

          if (hit.details && hit.details.bestTime) {

            html += `<div class="tt-row"><span>Best Lap:</span><span class="tt-val" style="color:#00e676;">${hit.details.bestTime} (${hit.details.bestRider})</span></div>`;

          }

          if (hit.details && hit.details.riders) {

            const riderList = Object.entries(hit.details.riders).map(([r, l]) => `${r}: ${l} L`).join(', ');

            html += `<div class="tt-row" style="margin-top:4px; font-size:10px;"><span>Riders:</span><span class="tt-val" style="font-weight:500;">${riderList}</span></div>`;

          }

        } else {

          const pct = hit.riderTotalLaps > 0 ? Math.round((hit.laps / hit.riderTotalLaps) * 100) : 0;

          const avgLabel = hit.top3Count && hit.top3Count < 3 ? `Top ${hit.top3Count} Avg:` : 'Top 3 Avg:';

          html = `

            <div class="tt-title">${hit.riderName} (${hit.riderCode})</div>

            <div class="tt-row"><span>Tyre Setup:</span><span class="tt-val">${hit.combo}</span></div>

            <div class="tt-row"><span>Laps Completed:</span><span class="tt-val">${hit.laps} L (${pct}% of rider)</span></div>

            <div class="tt-row"><span>${avgLabel}</span><span class="tt-val" style="color:#ffd600;">${hit.top3AvgStr}</span></div>

            <div class="tt-row"><span>Best Lap:</span><span class="tt-val" style="color:#00e676;">${hit.bestTime}</span></div>

          `;

          if (hit.top3LapsFormatted && hit.top3LapsFormatted.length > 1) {

            html += `<div class="tt-row" style="margin-top:3px; font-size:10px;"><span>Top Laps:</span><span class="tt-val" style="font-weight:500; color:#cbd5e1;">${hit.top3LapsFormatted.join(' · ')}</span></div>`;

          }

        }

        tooltipEl.innerHTML = html;

        tooltipEl.style.display = 'block';

        let tx = mx + 14;

        let ty = my + 14;

        const ttRect = tooltipEl.getBoundingClientRect();

        if (tx + ttRect.width > cRect.width) tx = mx - ttRect.width - 10;

        if (ty + ttRect.height > cRect.height) ty = my - ttRect.height - 10;

        tooltipEl.style.left = Math.max(0, tx) + 'px';

        tooltipEl.style.top = Math.max(0, ty) + 'px';

      } else {

        cvs.style.cursor = 'default';

        tooltipEl.style.display = 'none';

      }

    };

    cvs.onmouseleave = function() {

      if (tooltipEl) tooltipEl.style.display = 'none';

      cvs.style.cursor = 'default';

    };

  }

  // --- CARD 3: TYRE DEGRADATION (LINEAR REGRESSIONS ONLY) ---

  let currentFp1DegFilter = 'All';

  let fp1DegLinesData = [];

  function formatFp1AxisTime(sec) {

    if (typeof sec !== 'number' || isNaN(sec) || sec <= 0) return '-';

    const mins = Math.floor(sec / 60);

    const rem = sec % 60;

    const remStr = rem < 10 ? '0' + rem.toFixed(1) : rem.toFixed(1);

    return mins > 0 ? (mins + "'" + remStr) : remStr;

  }

  function formatFp1CellTime(sec, availW) {

    if (typeof sec !== 'number' || isNaN(sec) || sec <= 0) return '-';

    const mins = Math.floor(sec / 60);

    const rem = sec % 60;

    const remStr = rem < 10 ? '0' + rem.toFixed(3) : rem.toFixed(3);

    if (availW !== undefined && availW < 54 && mins > 0) return "'" + remStr;

    return mins > 0 ? (mins + "'" + remStr) : remStr;

  }

  function setFp1DegFilter(combo) {

    currentFp1DegFilter = combo;

    const cur = window.CURRENT_EVENT_SHORT || (typeof gp !== 'undefined' && gp ? gp.short : 'THA');

    const fp1Data = (getStintsRoot() && getStintsRoot()[cur]) ? getStintsRoot()[cur] : {};

    const activeFavRiders = getActiveFp1Riders(cur, fp1Data, cfg.staticKey);

    updateFp1DegFilterButtons(cur, activeFavRiders);

    renderFp1DegradationChart(cur, activeFavRiders);

  }

  function updateFp1DegFilterButtons(gpShort, favList) {

    const container = document.getElementById(p + '-deg-filter-group');

    if (!container) return;

    const rawFp1 = (getStintsRoot() && getStintsRoot()[gpShort]) ? getStintsRoot()[gpShort] : {};

    const hasTyres = hasFp1TyreCompounds(rawFp1);
    if (!hasTyres) {
      currentFp1DegFilter = 'All';
      container.innerHTML = '';
      container.style.display = 'none';
      return;
    }
    container.style.display = '';

    const comboSet = new Set();

    (favList || []).forEach(r => {

      const rData = rawFp1[r];

      if (rData) {

        (rData.runs || []).forEach(run => {

          if (run.lapsCount > 0 && run.front && run.rear) comboSet.add(`${run.front}-${run.rear}`);

        });

      }

    });

    if (currentFp1DegFilter !== 'All' && !comboSet.has(currentFp1DegFilter)) {

      currentFp1DegFilter = 'All';

    }

    const combos = ['All', ...Array.from(comboSet)];

    container.innerHTML = combos.map(c => `

      <button type="button" class="fp1-toggle-btn ${c === currentFp1DegFilter ? 'active' : ''}" onclick="set${cfg.capPrefix}DegFilter('${c}')">${c}</button>

    `).join('');

  }

  function renderFp1DegradationChart(gpShort, favList) {

    const cvs = document.getElementById('chart-' + p + '-deg');

    if (!cvs) return;

    const ctx = cvs.getContext('2d');

    const tooltipEl = document.getElementById(p + '-deg-tooltip');

    fp1DegLinesData = [];

    const rect = cvs.parentElement.getBoundingClientRect();

    const dpr = window.devicePixelRatio || 1;

    const width = rect.width || 340;

    const height = rect.height || 258;

    cvs.width = width * dpr;

    cvs.height = height * dpr;

    cvs.style.width = width + 'px';

    cvs.style.height = height + 'px';

    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, width, height);

    // Watermark

    ctx.save();

    ctx.font = '900 18px Inter, sans-serif';

    ctx.fillStyle = 'rgba(255, 255, 255, 0.025)';

    ctx.textAlign = 'center';

    ctx.textBaseline = 'middle';

    ctx.fillText('OVERREVVING', width / 2, height / 2);

    ctx.restore();

    const rawFp1 = (getStintsRoot() && getStintsRoot()[gpShort]) ? getStintsRoot()[gpShort] : {};
    const hasTyres = hasFp1TyreCompounds(rawFp1);

    // 1. Session baseline pace

    let sessionMin = 999;

    (favList || []).forEach(rName => {

      const rData = rawFp1[rName];

      if (!rData) return;

      (rData.runs || []).forEach(run => {

        if (run.fastestSec > 0 && run.fastestSec < sessionMin) sessionMin = run.fastestSec;

      });

    });

    if (sessionMin === 999) sessionMin = 118.0;

    const paceCeiling = sessionMin * 1.035;

    // 2. Extract linear regression for each rider

    const lines = [];

    (favList || []).forEach((rName, rIdx) => {

      const rData = rawFp1[rName];

      if (!rData) return;

      const style = getFp1RiderStyle(rName, rIdx);

      const riderColor = style.color || '#3b82f6';

      let targetCombo = hasTyres ? currentFp1DegFilter : '';

      if (hasTyres && targetCombo === 'All') {

        const comboCounts = {};

        (rData.runs || []).forEach(run => {

          const c = `${run.front}-${run.rear}`;

          const count = (run.flying || []).filter(sec => sec > 0 && sec <= paceCeiling).length;

          comboCounts[c] = (comboCounts[c] || 0) + count;

        });

        let maxC = null, maxCount = 0;

        for (const [c, cnt] of Object.entries(comboCounts)) {

          if (cnt > maxCount) { maxCount = cnt; maxC = c; }

        }

        targetCombo = maxC;

      }

      if (hasTyres && !targetCombo) return;

      const pts = [];

      (rData.runs || []).forEach((run) => {

        const c = `${run.front}-${run.rear}`;

        const matchCombo = !hasTyres || (c === targetCombo);

        if (matchCombo && run.flying && run.flying.length) {

          run.flying.forEach((sec, idx) => {

            const age = (run.startLap || 1) + 1 + idx;

            if (sec <= paceCeiling && sec > 0) {

              pts.push({ age, sec });

            }

          });

        }

      });

      if (pts.length >= 2) {

        pts.sort((a, b) => a.age - b.age);

        const xs = pts.map(p => p.age);

        const ys = pts.map(p => p.sec);

        const xM = xs.reduce((a, b) => a + b, 0) / xs.length;

        const yM = ys.reduce((a, b) => a + b, 0) / ys.length;

        const num = xs.reduce((sum, x, i) => sum + (x - xM) * (ys[i] - yM), 0);

        const den = xs.reduce((sum, x) => sum + (x - xM) ** 2, 0);

        const slope = den !== 0 ? (num / den) : 0;

        const intercept = yM - slope * xM;

        const minAge = xs[0];

        const maxAge = xs[xs.length - 1];

        const startPace = intercept + slope * minAge;

        const endPace = intercept + slope * maxAge;

        lines.push({

          name: rName,

          code: rData.code,

          color: riderColor,

          combo: targetCombo,

          minAge,

          maxAge,

          lapsCount: pts.length,

          slope,

          intercept,

          startPace,

          endPace,

          deg10: slope * 10

        });

      }

    });

    if (!lines.length) {

      ctx.font = '600 11px Inter, sans-serif';

      ctx.fillStyle = 'rgba(255, 255, 255, 0.2)';

      ctx.textAlign = 'center';

      ctx.textBaseline = 'middle';

      ctx.fillText(`No long runs recorded on ${currentFp1DegFilter}`, width / 2, height / 2);

      const stripEl = document.getElementById(cfg.degStripId);

      if (stripEl) stripEl.innerHTML = '';

      return;

    }

    // 3. Coordinate bounds

    let globalMinAge = 1, globalMaxAge = 18;

    lines.forEach(l => {

      if (l.maxAge > globalMaxAge) globalMaxAge = Math.ceil(l.maxAge);

    });

    globalMaxAge = Math.max(globalMaxAge, 16);

    const allPaces = [];

    lines.forEach(l => {

      allPaces.push(l.startPace, l.endPace);

    });

    let minPace = Math.floor(Math.min(...allPaces) * 2) / 2;

    let maxPace = Math.ceil(Math.max(...allPaces) * 2) / 2;

    if (maxPace - minPace < 2.0) maxPace = minPace + 2.0;

    const padLeft = 56, padRight = 44, padTop = 16, padBottom = 24;

    const plotW = width - padLeft - padRight;

    const plotH = height - padTop - padBottom;

    const getX = (age) => padLeft + ((age - globalMinAge) / (globalMaxAge - globalMinAge)) * plotW;

    const getY = (val) => padTop + ((val - minPace) / (maxPace - minPace)) * plotH;

    // 4. Draw Grid

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';

    ctx.lineWidth = 1;

    // Y grid (pace)

    const yStep = maxPace - minPace > 4 ? 1.0 : 0.5;

    ctx.font = '600 9px Inter, sans-serif';

    ctx.textAlign = 'right';

    ctx.textBaseline = 'middle';

    for (let yVal = minPace; yVal <= maxPace + 0.001; yVal += yStep) {

      const y = getY(yVal);

      ctx.beginPath();

      ctx.moveTo(padLeft, y);

      ctx.lineTo(width - padRight, y);

      ctx.stroke();

      ctx.fillStyle = '#64748b';

      ctx.fillText(formatFp1AxisTime(yVal), padLeft - 6, y);

    }

    // X grid (tyre age)

    ctx.textAlign = 'center';

    ctx.textBaseline = 'top';

    for (let age = 2; age <= globalMaxAge; age += 2) {

      const x = getX(age);

      ctx.beginPath();

      ctx.moveTo(x, padTop);

      ctx.lineTo(x, height - padBottom);

      ctx.stroke();

      ctx.fillStyle = '#64748b';

      ctx.fillText(age, x, height - padBottom + 5);

    }

    // Axes Labels

    ctx.font = '800 9px Inter, sans-serif';

    ctx.fillStyle = '#8b949e';

    ctx.textAlign = 'center';

    ctx.fillText(hasTyres ? 'TYRE AGE (LAPS) →' : 'SESSION LAPS →', padLeft + plotW / 2, height - 9);

    ctx.save();

    ctx.translate(11, padTop + plotH / 2);

    ctx.rotate(-Math.PI / 2);

    ctx.fillText('PACE ↑ FAST', 0, 0);

    ctx.restore();

    // 5. Draw ONLY LINEAR REGRESSIONS

    lines.sort((a, b) => a.endPace - b.endPace);

    lines.forEach((l, idx) => {

      const x1 = getX(l.minAge);

      const y1 = getY(l.startPace);

      const x2 = getX(l.maxAge);

      const y2 = getY(l.endPace);

      // Soft glow under line

      ctx.save();

      ctx.strokeStyle = l.color;

      ctx.lineWidth = 5;

      ctx.globalAlpha = 0.18;

      ctx.beginPath();

      ctx.moveTo(x1, y1);

      ctx.lineTo(x2, y2);

      ctx.stroke();

      ctx.restore();

      // Solid linear regression line

      ctx.save();

      ctx.strokeStyle = l.color;

      ctx.lineWidth = 2.5;

      ctx.lineCap = 'round';

      ctx.beginPath();

      ctx.moveTo(x1, y1);

      ctx.lineTo(x2, y2);

      ctx.stroke();

      // Start dot

      ctx.fillStyle = l.color;

      ctx.beginPath();

      ctx.arc(x1, y1, 3.5, 0, Math.PI * 2);

      ctx.fill();

      // End dot

      ctx.beginPath();

      ctx.arc(x2, y2, 4, 0, Math.PI * 2);

      ctx.fill();

      ctx.strokeStyle = '#ffffff';

      ctx.lineWidth = 1;

      ctx.stroke();

      // Label at end of line with collision check

      let labelY = y2;

      if (idx > 0) {

        const prevY = getY(lines[idx - 1].endPace);

        if (Math.abs(labelY - prevY) < 11) {

          labelY = prevY + 11;

        }

      }

      ctx.font = '800 10px Inter, sans-serif';

      ctx.fillStyle = l.color;

      ctx.textAlign = 'left';

      ctx.textBaseline = 'middle';

      ctx.fillText(l.code, x2 + 5, labelY);

      ctx.restore();

      fp1DegLinesData.push({

        line: l,

        x1, y1, x2, y2,

        getX, getY

      });

    });

    // 6. Update stat pills underneath

    const stripEl = document.getElementById(cfg.degStripId);

    if (stripEl) {

      stripEl.innerHTML = lines.map(l => {

        const slopeStr = l.slope >= 0 ? `+${l.slope.toFixed(3)}s/l` : `${l.slope.toFixed(3)}s/l`;

        const deg10Str = l.deg10 >= 0 ? `+${l.deg10.toFixed(2)}s` : `${l.deg10.toFixed(2)}s`;

        const pillMeta = l.combo ? l.combo : `${l.lapsCount}L`;

        return `

          <div class="deg-stat-pill">

            <div class="deg-stat-head">

              <span class="deg-stat-dot" style="background:${l.color};"></span>

              <span>${l.code}</span>

              <span style="font-size:7px; color:#64748b; margin-left:auto;">${pillMeta}</span>

            </div>

            <div class="deg-stat-val" style="color:${l.slope > 0.05 ? '#f87171' : (l.slope <= 0.01 ? '#00e676' : '#ffd600')};">

              ${slopeStr}

            </div>

            <div class="deg-stat-sub">${l.maxAge}L max (${deg10Str}/10L)</div>

          </div>

        `;

      }).join('');

    }

    // 7. Tooltip interaction along the regression lines

    cvs.onmousemove = function(e) {

      if (!tooltipEl) return;

      const cRect = cvs.getBoundingClientRect();

      const mx = e.clientX - cRect.left;

      const my = e.clientY - cRect.top;

      let bestLine = null;

      let minD = 24;

      fp1DegLinesData.forEach(item => {

        const l = item.line;

        if (mx >= item.x1 - 10 && mx <= item.x2 + 20) {

          const t = (mx - item.x1) / (item.x2 - item.x1);

          const clampedT = Math.max(0, Math.min(1, t));

          const projY = item.y1 + clampedT * (item.y2 - item.y1);

          const dist = Math.abs(my - projY);

          if (dist < minD) {

            minD = dist;

            bestLine = {

              item,

              clampedT,

              age: Math.round(l.minAge + clampedT * (l.maxAge - l.minAge)),

              pace: l.startPace + clampedT * (l.endPace - l.startPace)

            };

          }

        }

      });

      if (bestLine) {

        cvs.style.cursor = 'pointer';

        const l = bestLine.item.line;

        const slopeSign = l.slope >= 0 ? '+' : '';

        const deg10Str = l.deg10 >= 0 ? `+${l.deg10.toFixed(2)}s` : `${l.deg10.toFixed(2)}s`;

        const comboBadge = l.combo ? `<span style="font-size:10px; color:#94a3b8;">${l.combo}</span>` : '';
        const rangeLabel = hasTyres ? 'Tyre Age Range:' : 'Lap Range:';

        tooltipEl.innerHTML = `

          <div class="tt-title">

            <span style="color:${l.color};">${l.name} (${l.code})</span>

            ${comboBadge}

          </div>

          <div class="tt-row"><span>${rangeLabel}</span><span class="tt-val">Lap ${l.minAge} &rarr; ${l.maxAge} (${l.lapsCount} laps)</span></div>

          <div class="tt-row"><span>At Lap ${bestLine.age}:</span><span class="tt-val" style="color:#ffd600;">${formatFp1CellTime(bestLine.pace, 999)}</span></div>

          <div class="tt-row"><span>Starting Pace (L${l.minAge}):</span><span class="tt-val">${formatFp1CellTime(l.startPace, 999)}</span></div>

          <div class="tt-row"><span>Degradation Slope:</span><span class="tt-val" style="color:#38bdf8;">${slopeSign}${l.slope.toFixed(3)} s/lap</span></div>

          <div class="tt-row"><span>Projected 10-Lap Deg:</span><span class="tt-val" style="color:${l.slope > 0.05 ? '#f87171' : '#00e676'};">${deg10Str}</span></div>

        `;

        tooltipEl.style.display = 'block';

        let tx = mx + 14;

        let ty = my + 14;

        const ttRect = tooltipEl.getBoundingClientRect();

        if (tx + ttRect.width > cRect.width) tx = mx - ttRect.width - 10;

        if (ty + ttRect.height > cRect.height) ty = my - ttRect.height - 10;

        tooltipEl.style.left = Math.max(0, tx) + 'px';

        tooltipEl.style.top = Math.max(0, ty) + 'px';

      } else {

        cvs.style.cursor = 'default';

        tooltipEl.style.display = 'none';

      }

    };

    cvs.onmouseleave = function() {

      if (tooltipEl) tooltipEl.style.display = 'none';

      cvs.style.cursor = 'default';

    };

  }

  function renderFp1AnalysisSection(currentGpShort) {

    if (!currentGpShort) currentGpShort = (window.CURRENT_EVENT_SHORT || (typeof gp !== 'undefined' && gp ? gp.short : 'THA'));

    const sectionEl = document.getElementById(p + '-analysis-section');

    if (!sectionEl) return;

    const stintsRoot = getStintsRoot(); if (!stintsRoot) {

      sectionEl.style.display = 'none';

      return;

    }

    const fp1Data = stintsRoot[currentGpShort];

    if (!fp1Data || Object.keys(fp1Data).length === 0) {

      sectionEl.style.display = 'none';

      return;

    }

    const activeFavRiders = getActiveFp1Riders(currentGpShort, fp1Data, cfg.staticKey);

    if (activeFavRiders.length === 0) {

      sectionEl.style.display = 'none';

      return;

    }

    sectionEl.style.display = 'block';

    if (localStorage.getItem(cfg.minStorageKey) === '1' && !sectionEl.classList.contains('minimized')) {

      toggleFp1AnalysisMinimize();

    }

    // Adapt layout and labels automatically when Dorna does not publish tyre compounds (Moto2 / Moto3)
    const hasTyres = hasFp1TyreCompounds(fp1Data);
    const gridEl = document.getElementById(p + '-analysis-grid');
    const heatmapCard = document.getElementById(p + '-heatmap-card');
    if (heatmapCard) heatmapCard.style.display = hasTyres ? '' : 'none';
    if (gridEl) gridEl.classList.toggle('no-heatmap', !hasTyres);

    const titleEl = document.getElementById(p + '-section-title-text');
    if (titleEl) {
      titleEl.textContent = hasTyres
        ? cfg.titleWithTyres
        : cfg.titleNoTyres;
    }
    const subEl = document.getElementById(p + '-section-subtitle');
    if (subEl) {
      subEl.textContent = hasTyres
        ? 'Comparing favorite riders (\u2605) \u00B7 Stints progression, compound choices (Front & Rear) & fastest lap per run'
        : 'Comparing favorite riders (\u2605) \u00B7 Stints progression, pace degradation, lap times density & fastest lap per run';
    }
    const stintsTitleEl = document.getElementById(p + '-stints-title');
    if (stintsTitleEl) stintsTitleEl.textContent = hasTyres ? 'Stints & Tyre Strategy' : 'Stints Progression';
    const stintsBadgeEl = document.getElementById(p + '-stints-badge');
    if (stintsBadgeEl) stintsBadgeEl.textContent = hasTyres ? 'Run by Run \u00B7 Laps & Compound' : 'Run by Run \u00B7 Laps & Pace';
    const degTitleEl = document.getElementById(p + '-deg-title');
    if (degTitleEl) degTitleEl.textContent = hasTyres ? 'Tyre Degradation' : 'Pace Degradation';

    // Environmental conditions (Weather: condition, air temp, track temp)

    const weatherData = (typeof SESSION_WEATHER_DATA !== 'undefined' && SESSION_WEATHER_DATA[currentGpShort]) ? SESSION_WEATHER_DATA[currentGpShort] : {};

    const rawFp1W = weatherData[cfg.weatherKey] || '';

    const cleanFp1W = rawFp1W.replace(/&#xB0;/g, '°').replace(/Â°/g, '°').replace(/Â/g, '').replace(/°C°C/g, '°C').trim();

    const weatherEl = document.getElementById(p + '-section-weather');

    if (weatherEl) {

      if (cleanFp1W && cleanFp1W !== 'Dry | Air: -- | Track: --') {

        weatherEl.textContent = cleanFp1W;

        weatherEl.style.display = 'inline-flex';

      } else {

        weatherEl.style.display = 'none';

      }

    }

    const btnMatrix = document.getElementById(p + '-heatmap-btn-matrix');

    const btnRiders = document.getElementById(p + '-heatmap-btn-riders');

    if (btnMatrix) btnMatrix.classList.toggle('active', currentFp1HeatmapMode === 'matrix');

    if (btnRiders) btnRiders.classList.toggle('active', currentFp1HeatmapMode === 'riders');

    renderFp1StintsChart(currentGpShort, activeFavRiders);

    if (hasTyres) {
      renderFp1HeatmapChart(currentGpShort, activeFavRiders);
    }

    updateFp1DegFilterButtons(currentGpShort, activeFavRiders);

    renderFp1DegradationChart(currentGpShort, activeFavRiders);

    renderFp1DensityChart(currentGpShort, activeFavRiders);
    renderFp1TruePaceChart(currentGpShort, activeFavRiders);
    renderFp1SectorCharts(currentGpShort, activeFavRiders);

  }

  return {
    toggleMinimize: toggleFp1AnalysisMinimize,
    setDensityMode: setFp1DensityMode,
    setTruePaceK: setFp1TruePaceK,
    setSectorRiderMode: setFp1SectorRiderMode,
    setHeatmapMode: setFp1HeatmapMode,
    setDegFilter: setFp1DegFilter,
    renderSection: renderFp1AnalysisSection,
    redrawCanvases: function(cur) {
      const sec = document.getElementById(p + '-analysis-section');
      if (cur && sec && sec.style.display !== 'none' && !sec.classList.contains('minimized')) {
        const root = getStintsRoot();
        const sData = root && root[cur];
        if (sData) {
          const active = getActiveFp1Riders(cur, sData, cfg.staticKey);
          if (active.length) {
            renderFp1StintsChart(cur, active);
            if (hasFp1TyreCompounds(sData)) renderFp1HeatmapChart(cur, active);
            renderFp1DegradationChart(cur, active);
          }
        }
      }
    }
  };
}

const PRACTICE_ANALYSIS_CONTROLLERS = {
  fp1: createPracticeAnalysisController({
    prefix: 'fp1',
    capPrefix: 'Fp1',
    stintsGlobal: 'EVENT_FP1_STINTS_DATA',
    sectorsGlobal: 'EVENT_FP1_SECTORS_DATA',
    weatherKey: 'fp1',
    staticKey: 'fp1',
    degStripId: 'deg-stats-strip',
    titleWithTyres: '\u23F1 FP1 - Free Practice 1 Analysis & Tyre Strategy',
    titleNoTyres: '\u23F1 FP1 - Free Practice 1 Analysis & Stints Strategy',
    minStorageKey: 'overrevving_fp1_analysis_minimized',
    heatmapStorageKey: 'overrevving_fp1_heatmap_mode'
  }),
  pr: createPracticeAnalysisController({
    prefix: 'pr',
    capPrefix: 'Pr',
    stintsGlobal: 'EVENT_PR_STINTS_DATA',
    sectorsGlobal: 'EVENT_PR_SECTORS_DATA',
    weatherKey: 'pr',
    staticKey: 'pr',
    degStripId: 'pr-deg-stats-strip',
    titleWithTyres: '\u23F1 PR - Practice Analysis & Tyre Strategy',
    titleNoTyres: '\u23F1 PR - Practice Analysis & Stints Strategy',
    minStorageKey: 'overrevving_pr_analysis_minimized',
    heatmapStorageKey: 'overrevving_pr_heatmap_mode'
  }),
  fp2: createPracticeAnalysisController({
    prefix: 'fp2',
    capPrefix: 'Fp2',
    stintsGlobal: 'EVENT_FP2_STINTS_DATA',
    sectorsGlobal: 'EVENT_FP2_SECTORS_DATA',
    weatherKey: 'fp2',
    staticKey: 'fp2',
    degStripId: 'fp2-deg-stats-strip',
    titleWithTyres: '\u23F1 FP2 - Free Practice 2 Analysis & Tyre Strategy',
    titleNoTyres: '\u23F1 FP2 - Free Practice 2 Analysis & Stints Strategy',
    minStorageKey: 'overrevving_fp2_analysis_minimized',
    heatmapStorageKey: 'overrevving_fp2_heatmap_mode'
  })
};

function toggleFp1AnalysisMinimize() { return PRACTICE_ANALYSIS_CONTROLLERS.fp1.toggleMinimize(); }
function setFp1DensityMode(m) { return PRACTICE_ANALYSIS_CONTROLLERS.fp1.setDensityMode(m); }
function setFp1TruePaceK(k) { return PRACTICE_ANALYSIS_CONTROLLERS.fp1.setTruePaceK(k); }
function setFp1SectorRiderMode(m) { return PRACTICE_ANALYSIS_CONTROLLERS.fp1.setSectorRiderMode(m); }
function setFp1HeatmapMode(m) { return PRACTICE_ANALYSIS_CONTROLLERS.fp1.setHeatmapMode(m); }
function setFp1DegFilter(c) { return PRACTICE_ANALYSIS_CONTROLLERS.fp1.setDegFilter(c); }
function renderFp1AnalysisSection(cur) { return PRACTICE_ANALYSIS_CONTROLLERS.fp1.renderSection(cur); }

function togglePrAnalysisMinimize() { return PRACTICE_ANALYSIS_CONTROLLERS.pr.toggleMinimize(); }
function setPrDensityMode(m) { return PRACTICE_ANALYSIS_CONTROLLERS.pr.setDensityMode(m); }
function setPrTruePaceK(k) { return PRACTICE_ANALYSIS_CONTROLLERS.pr.setTruePaceK(k); }
function setPrSectorRiderMode(m) { return PRACTICE_ANALYSIS_CONTROLLERS.pr.setSectorRiderMode(m); }
function setPrHeatmapMode(m) { return PRACTICE_ANALYSIS_CONTROLLERS.pr.setHeatmapMode(m); }
function setPrDegFilter(c) { return PRACTICE_ANALYSIS_CONTROLLERS.pr.setDegFilter(c); }
function renderPrAnalysisSection(cur) { return PRACTICE_ANALYSIS_CONTROLLERS.pr.renderSection(cur); }

function toggleFp2AnalysisMinimize() { return PRACTICE_ANALYSIS_CONTROLLERS.fp2.toggleMinimize(); }
function setFp2DensityMode(m) { return PRACTICE_ANALYSIS_CONTROLLERS.fp2.setDensityMode(m); }
function setFp2TruePaceK(k) { return PRACTICE_ANALYSIS_CONTROLLERS.fp2.setTruePaceK(k); }
function setFp2SectorRiderMode(m) { return PRACTICE_ANALYSIS_CONTROLLERS.fp2.setSectorRiderMode(m); }
function setFp2HeatmapMode(m) { return PRACTICE_ANALYSIS_CONTROLLERS.fp2.setHeatmapMode(m); }
function setFp2DegFilter(c) { return PRACTICE_ANALYSIS_CONTROLLERS.fp2.setDegFilter(c); }
function renderFp2AnalysisSection(cur) { return PRACTICE_ANALYSIS_CONTROLLERS.fp2.renderSection(cur); }

function renderAllPracticeAnalysisSections(cur) {
  renderFp1AnalysisSection(cur);
  renderPrAnalysisSection(cur);
  renderFp2AnalysisSection(cur);
}

let practiceAnalysisResizeTimer = null;
window.addEventListener('resize', () => {
  clearTimeout(practiceAnalysisResizeTimer);
  practiceAnalysisResizeTimer = setTimeout(() => {
    const cur = window.CURRENT_EVENT_SHORT || (typeof gp !== 'undefined' && gp ? gp.short : null);
    if (!cur) return;
    Object.values(PRACTICE_ANALYSIS_CONTROLLERS).forEach(ctrl => ctrl.redrawCanvases(cur));
  }, 150);
});
