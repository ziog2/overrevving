const fs = require('fs');
const path = require('path');
const https = require('https');
const pdfjsLib = require('pdfjs-dist/legacy/build/pdf.js');

const BIN_ID = process.env.JSONBIN_BIN_ID;
const API_KEY = process.env.JSONBIN_API_KEY;
const BIN_URL = `https://api.jsonbin.io/v3/b/${BIN_ID}`;

const HEADERS_BASE = {
  'Content-Type': 'application/json',
  'User-Agent': 'Mozilla/5.0 (compatible; GitHubActions-MotorsportUpdater/1.0)'
};

function httpsGet(url, extraHeaders = {}) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const options = {
      hostname: parsed.hostname,
      path: parsed.pathname + parsed.search,
      method: 'GET',
      headers: { ...HEADERS_BASE, ...extraHeaders }
    };
    const req = https.request(options, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try { resolve(JSON.parse(data)); } catch(e) { resolve(data); }
        } else {
          reject(new Error(`HTTP ${res.statusCode}: ${data}`));
        }
      });
    });
    req.on('error', reject);
    req.setTimeout(15000, () => { req.destroy(); reject(new Error('Timeout ' + url)); });
    req.end();
  });
}

function httpsGetBuffer(url) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const options = {
      hostname: parsed.hostname,
      path: parsed.pathname + parsed.search,
      method: 'GET',
      headers: { 'User-Agent': 'Mozilla/5.0' }
    };
    const req = https.request(options, res => {
      const chunks = [];
      res.on('data', chunk => chunks.push(chunk));
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(Buffer.concat(chunks));
        } else {
          reject(new Error(`HTTP ${res.statusCode}`));
        }
      });
    });
    req.on('error', reject);
    req.setTimeout(15000, () => { req.destroy(); reject(new Error('Timeout ' + url)); });
    req.end();
  });
}

function httpsPut(url, bodyObj, extraHeaders = {}) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const bodyStr = JSON.stringify(bodyObj);
    const options = {
      hostname: parsed.hostname,
      path: parsed.pathname + parsed.search,
      method: 'PUT',
      headers: {
        ...HEADERS_BASE,
        'Content-Length': Buffer.byteLength(bodyStr),
        ...extraHeaders
      }
    };
    const req = https.request(options, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(data);
        } else {
          reject(new Error(`HTTP ${res.statusCode}: ${data}`));
        }
      });
    });
    req.on('error', reject);
    req.write(bodyStr);
    req.end();
  });
}

// ---- Parse Dorna PDF buffer for Constructors & Teams (exact admin.html algorithm) ----
async function parsePdfStatsBuffer(buffer) {
  const data = new Uint8Array(buffer);
  const pdf = await pdfjsLib.getDocument({ data }).promise;

  let targetPage = null;
  let targetTokens = null;
  for (let p = pdf.numPages; p >= 1; p--) {
    const page = await pdf.getPage(p);
    const content = await page.getTextContent();
    const fullText = content.items.map(it => it.str).join(' ');
    if (fullText.includes('Constructor') && fullText.includes('Team')) {
      targetPage = page;
      targetTokens = content;
      break;
    }
  }
  if (!targetPage) return { teams: [], constructors: [] };

  const pageH = targetPage.getViewport({ scale: 1 }).height;
  const tokens = targetTokens.items
    .filter(it => it.str && it.str.trim())
    .map(it => ({ text: it.str.trim(), x: it.transform[4], y: pageH - it.transform[5] }));

  return parseTeamsAndConstructors(tokens);
}

function parseTeamsAndConstructors(tokens) {
  const constructorHeaderTok = tokens.find(t => t.text === 'Constructor');
  const teamHeaderTok = tokens.find(t => t.text === 'Team');
  if (!constructorHeaderTok || !teamHeaderTok) return { teams: [], constructors: [] };

  const headerRowTokens = tokens
    .filter(t => Math.abs(t.y - constructorHeaderTok.y) <= 6 || Math.abs(t.y - teamHeaderTok.y) <= 6)
    .sort((a, b) => a.x - b.x);

  const constructorNames = [];
  const teamNames = [];
  let mode = null;
  for (const t of headerRowTokens) {
    if (t.text === 'Constructor') { mode = 'constructor'; continue; }
    if (t.text === 'Team') { mode = 'team'; continue; }
    if (mode === 'constructor') constructorNames.push({ x: t.x, name: t.text });
    else if (mode === 'team') teamNames.push({ x: t.x, name: t.text });
  }

  const pointsLabelToks = tokens.filter(t => t.text === 'Points');
  const pointsRowYmin = pointsLabelToks.length ? Math.min(...pointsLabelToks.map(t => t.y)) : 375;
  const pointsRowYmax = pointsLabelToks.length ? Math.max(...pointsLabelToks.map(t => t.y)) : 385;

  const pointsCandidates = tokens.filter(t =>
    /^\d{1,4}(\.\d+)?$/.test(t.text) && t.y > pointsRowYmin - 20 && t.y < pointsRowYmax + 5
  );

  function matchPoints(nameList) {
    return nameList.map(n => {
      let best = null, bestDist = Infinity;
      for (const p of pointsCandidates) {
        const dist = Math.abs(p.x - n.x);
        if (dist < bestDist) { bestDist = dist; best = p; }
      }
      return best && bestDist < 2 ? { name: n.name, pts: parseFloat(best.text) } : null;
    }).filter(Boolean);
  }

  const constructors = matchPoints(constructorNames).sort((a, b) => b.pts - a.pts);
  const teams = matchPoints(teamNames).sort((a, b) => b.pts - a.pts);

  return { teams, constructors };
}

// ---- Main Execution ----
async function main() {
  console.log('Avvio routine aggiornamento classifiche...');

  // 1. Carica bin attuale
  let current = {};
  try {
    const binData = await httpsGet(`${BIN_URL}/latest`, { 'X-Access-Key': API_KEY });
    current = binData.record || {};
  } catch (e) {
    console.warn('Errore lettura JSONBin:', e.message);
  }

  const results = {};

  // 2. API MotoGP / Moto2 / Moto3 Piloti + Session History
  const SEASON_2026 = "e88b4e43-2209-47aa-8e83-0e0b1cedde6e";
  const CATEGORY_CONFIG = {
    motogp: { uuid: "e8c110ad-64aa-4e8e-8a86-f2f152f6a942", localPdf: "data/MGP.pdf", pdfCat: "MotoGP", label: "MotoGP" },
    moto2:  { uuid: "549640b8-fd9c-4245-acfd-60e4bc38b25c", localPdf: "data/M2.pdf",  pdfCat: "Moto2",  label: "Moto2" },
    moto3:  { uuid: "954f7e65-2ef2-4423-b949-4961cc603e45", localPdf: "data/M3.pdf",  pdfCat: "Moto3",  label: "Moto3" },
  };

  for (const [catId, cfg] of Object.entries(CATEGORY_CONFIG)) {
    try {
      const eventsUrl = `https://api.motogp.pulselive.com/motogp/v1/results/events?seasonUuid=${SEASON_2026}&categoryUuid=${cfg.uuid}`;
      const events = await httpsGet(eventsUrl);
      const finishedEvents = (Array.isArray(events) ? events : []).filter(ev =>
        ev && ev.status === 'FINISHED' && !String(ev.short_name || '').endsWith('1') && !String(ev.short_name || '').endsWith('2') && !String(ev.short_name || '').endsWith('3')
      );
      const gpShortNames = finishedEvents.map(ev => ev.short_name);
      const gpEventsMap = {};
      finishedEvents.forEach(ev => { gpEventsMap[ev.short_name] = ev.id; });

      const standingsUrl = `https://api.motogp.pulselive.com/motogp/v1/results/standings?seasonUuid=${SEASON_2026}&categoryUuid=${cfg.uuid}`;
      const standingsData = await httpsGet(standingsUrl);
      const standings = standingsData.classification || [];

      const officialPts = {};
      for (const c of standings) {
        if (!c.rider || !c.rider.full_name) continue;
        let name = c.rider.full_name.trim();
        if (name.includes("Vinales") || name.includes("Vi.ales")) name = "Maverick Viñales";
        if (name.includes("Munoz") || name.includes("Mu.oz")) name = "Daniel Muñoz";
        if (name.includes("Oncu") || name.includes(".ncu")) name = "Deniz Öncü";
        officialPts[name] = parseFloat(c.points || 0);
      }

      const riderMatrix = {};
      Object.keys(officialPts).forEach(r => {
        riderMatrix[r] = {};
        gpShortNames.forEach(gp => { riderMatrix[r][gp] = { spr: 0.0, rac: 0.0 }; });
      });

      for (const shortName of gpShortNames) {
        const evId = gpEventsMap[shortName];
        if (!evId) continue;
        const sessionsUrl = `https://api.motogp.pulselive.com/motogp/v1/results/sessions?eventUuid=${evId}&categoryUuid=${cfg.uuid}`;
        let sessions = [];
        try { sessions = await httpsGet(sessionsUrl); } catch(e) { continue; }

        const sprSession = (Array.isArray(sessions) ? sessions : []).find(s => s && s.type === 'SPR' && s.status === 'FINISHED');
        const racSession = (Array.isArray(sessions) ? sessions : []).find(s => s && s.type === 'RAC' && s.status === 'FINISHED');

        if (sprSession) {
          try {
            const sprRes = await httpsGet(`https://api.motogp.pulselive.com/motogp/v1/results/session/${sprSession.id}/classification?categoryUuid=${cfg.uuid}`);
            for (const c of (sprRes.classification || [])) {
              if (!c.rider || !c.rider.full_name) continue;
              let name = c.rider.full_name.trim();
              if (name.includes("Vinales") || name.includes("Vi.ales")) name = "Maverick Viñales";
              if (name.includes("Munoz") || name.includes("Mu.oz")) name = "Daniel Muñoz";
              if (name.includes("Oncu") || name.includes(".ncu")) name = "Deniz Öncü";
              const ptsVal = parseFloat(c.points || 0);
              if (!riderMatrix[name]) {
                riderMatrix[name] = {};
                gpShortNames.forEach(gp => { riderMatrix[name][gp] = { spr: 0.0, rac: 0.0 }; });
              }
              riderMatrix[name][shortName].spr = ptsVal;
            }
          } catch(e) {}
        }

        if (racSession) {
          try {
            const racRes = await httpsGet(`https://api.motogp.pulselive.com/motogp/v1/results/session/${racSession.id}/classification?categoryUuid=${cfg.uuid}`);
            for (const c of (racRes.classification || [])) {
              if (!c.rider || !c.rider.full_name) continue;
              let name = c.rider.full_name.trim();
              if (name.includes("Vinales") || name.includes("Vi.ales")) name = "Maverick Viñales";
              if (name.includes("Munoz") || name.includes("Mu.oz")) name = "Daniel Muñoz";
              if (name.includes("Oncu") || name.includes(".ncu")) name = "Deniz Öncü";
              const ptsVal = parseFloat(c.points || 0);
              if (!riderMatrix[name]) {
                riderMatrix[name] = {};
                gpShortNames.forEach(gp => { riderMatrix[name][gp] = { spr: 0.0, rac: 0.0 }; });
              }
              riderMatrix[name][shortName].rac = ptsVal;
            }
          } catch(e) {}
        }
      }

      const cleanRiders = [];
      for (const [name, gpDict] of Object.entries(riderMatrix)) {
        const sprHist = gpShortNames.map(gp => gpDict[gp].spr);
        const racHist = gpShortNames.map(gp => gpDict[gp].rac);
        const totHist = sprHist.map((s, idx) => s + racHist[idx]);
        const sprPts = sprHist.reduce((a, b) => a + b, 0);
        const racPts = racHist.reduce((a, b) => a + b, 0);
        const officialTotal = officialPts[name] !== undefined ? officialPts[name] : totHist.reduce((a, b) => a + b, 0);

        const diff = officialTotal - totHist.reduce((a, b) => a + b, 0);
        if (Math.abs(diff) > 0.001 && totHist.length > 0) {
          totHist[totHist.length - 1] += diff;
        }

        cleanRiders.push({
          name: name,
          pts: Number.isInteger(officialTotal) ? officialTotal : officialTotal,
          history: totHist,
          sprint_pts: Number.isInteger(sprPts) ? sprPts : sprPts,
          sprint_history: sprHist,
          long_pts: Number.isInteger(racPts) ? racPts : racPts,
          long_history: racHist
        });
      }

      cleanRiders.sort((a, b) => b.pts - a.pts);
      results[catId] = cleanRiders;
      console.log(`✓ ${catId}: ${cleanRiders.length} piloti importati`);

      // ---- Estrazione PDF Costruttori e Team (da file locale o da URL Dorna) ----
      let pdfBuffer = null;
      if (gpShortNames.length) {
        const latestGp = gpShortNames[gpShortNames.length - 1];
        const remotePdfUrl = `https://resources.motogp.com/files/results/2026/${latestGp}/${cfg.pdfCat}/RAC/worldstanding.pdf`;
        try {
          pdfBuffer = await httpsGetBuffer(remotePdfUrl);
          console.log(`Scaricato PDF ufficiale Dorna da ${remotePdfUrl}`);
        } catch (e) {
          console.log(`Download remoto non riuscito (${e.message}), cerco file locale ${cfg.localPdf}`);
        }
      }

      if (!pdfBuffer && fs.existsSync(cfg.localPdf)) {
        pdfBuffer = fs.readFileSync(cfg.localPdf);
        console.log(`Caricato PDF locale da ${cfg.localPdf}`);
      }

      if (pdfBuffer) {
        const { teams, constructors } = await parsePdfStatsBuffer(pdfBuffer);
        if (constructors.length) {
          results[`${catId}_constructors`] = constructors;
          console.log(`✓ ${cfg.label} PDF: ${constructors.length} costruttori estratti dal PDF`);
        }
        if (teams.length) {
          results[`${catId}_teams`] = teams;
          console.log(`✓ ${cfg.label} PDF: ${teams.length} team estratti dal PDF`);
        }
      }

    } catch (err) {
      console.warn(`Errore ${catId}:`, err.message);
    }
  }

  // 3. MXGP
  try {
    const mxgpHtml = await httpsGet('https://mxgpresults.com/mxgp/standings');
    const rowRe = /<tr[^>]*>\s*<td[^>]*>\d+\s*<\/td>\s*<td[^>]*>#\d+\s*<\/td>\s*<td[^>]*>([\s\S]*?)<\/td>[\s\S]*?<td[^>]*>(\d+)\s*<\/td>\s*<\/tr>/g;
    const mxgpRiders = [];
    let m;
    while ((m = rowRe.exec(mxgpHtml)) !== null) {
      const name = m[1].replace(/<[^>]+>/g, '').trim();
      const pts = parseInt(m[2], 10);
      if (name && !isNaN(pts)) mxgpRiders.push({ name, pts });
    }
    if (mxgpRiders.length) {
      results['mxgp'] = mxgpRiders;
      console.log(`✓ MXGP: ${mxgpRiders.length} piloti importati`);
    }
  } catch (err) {
    console.warn('Errore MXGP:', err.message);
  }

  // 4. MX2
  try {
    const mx2Html = await httpsGet('https://mxgpresults.com/mx2/standings');
    const rowRe2 = /<tr[^>]*>\s*<td[^>]*>\d+\s*<\/td>\s*<td[^>]*>#\d+\s*<\/td>\s*<td[^>]*>([\s\S]*?)<\/td>[\s\S]*?<td[^>]*>(\d+)\s*<\/td>\s*<\/tr>/g;
    const mx2Riders = [];
    let m2;
    while ((m2 = rowRe2.exec(mx2Html)) !== null) {
      const name = m2[1].replace(/<[^>]+>/g, '').trim();
      const pts = parseInt(m2[2], 10);
      if (name && !isNaN(pts)) mx2Riders.push({ name, pts });
    }
    if (mx2Riders.length) {
      results['mx2'] = mx2Riders;
      console.log(`✓ MX2: ${mx2Riders.length} piloti importati`);
    }
  } catch (err) {
    console.warn('Errore MX2:', err.message);
  }

  // 5. F1
  try {
    const f1Data = await httpsGet('https://api.jolpi.ca/ergast/f1/2026/driverstandings.json');
    const lists = f1Data?.MRData?.StandingsTable?.StandingsLists || [];
    if (lists.length) {
      const standings = lists[0].DriverStandings || [];
      const f1Riders = standings.map(d => ({
        name: d.Driver.givenName + ' ' + d.Driver.familyName,
        pts: parseFloat(d.points)
      }));
      results['f1'] = f1Riders;
      console.log(`✓ F1: ${f1Riders.length} piloti importati`);
    }
  } catch (err) {
    console.warn('Errore F1:', err.message);
  }

  if (Object.keys(results).length === 0) {
    console.log('Nessun dato recuperato, esco.');
    return;
  }

  // 6. Unisci con il bin esistente e salva
  const keysToKeep = [
    "motogp", "motogp_constructors", "motogp_teams",
    "moto2", "moto2_constructors", "moto2_teams",
    "moto3", "moto3_constructors", "moto3_teams",
    "sbk", "sbk_constructors", "sbk_teams",
    "mxgp", "mx2", "f1", "_updated"
  ];
  const cleanCurrent = {};
  for (const k of keysToKeep) {
    if (current[k] !== undefined) cleanCurrent[k] = current[k];
  }
  Object.assign(cleanCurrent, results);

  const now = new Date();
  const itDate = new Date(now.getTime() + (2 * 60 * 60 * 1000));
  cleanCurrent['_updated'] = itDate.toISOString().replace('T', ' ').substring(0, 19) + ' · Auto (Domenica)';

  try {
    await httpsPut(BIN_URL, cleanCurrent, { 'X-Access-Key': API_KEY });
    console.log('✓ Salvato su JSONBin con successo!');
  } catch (e) {
    console.error('Errore salvataggio JSONBin:', e.message);
  }
}

main().catch(console.error);
