/*
 * Plan 06 §3.7 / AC12: drive the real frontend (http://localhost:3000, Vite dev server + proxy to the backend) in
 * Edge through puppeteer-core, with the fake webcam fed by a Y4M made from a real clip.
 *
 *   node scripts/e2e_browser.cjs --scenario fingerspell|word --y4m <file.y4m> --out <observations.json>
 *        [--url http://localhost:3000/] [--clip-seconds S] [--max-loops 3]
 *
 * Browser: env VSL_E2E_BROWSER, default = the Edge path of scripts/take_screenshots.cjs.
 * Flags: --use-fake-ui-for-media-stream --use-fake-device-for-media-stream --use-file-for-fake-video-capture=<y4m>
 * (the browser plays the file in a loop; one loop lasts --clip-seconds).
 *
 * The script only OBSERVES and writes facts (no pass/fail verdict: scripts/e2e_fullstack.py evaluates AC12):
 * console `error`, `pageerror`, `requestfailed`, HTTP >= 400, every WebSocket URL (CDP Network.webSocketCreated) and
 * the `type` of every message received (CDP Network.webSocketFrameReceived), the facts of every
 * POST /api/fingerspelling/sequence body (lengths, non-null frames, |v| max, ...; NEVER the landmarks) and the
 * status + JSON of the /sequence and /compose responses, and what the UI shows (data-testid elements).
 * Nothing random, no generated data: the only input is the Y4M of a real clip.
 */
'use strict';

const path = require('path');
const fs = require('fs');
const puppeteer = require(path.join(__dirname, '..', 'frontend', 'node_modules', 'puppeteer-core'));

const DEFAULT_BROWSER = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const TEXT_CUT = 300;
const SEQUENCE_PATH = '/api/fingerspelling/sequence';
const COMPOSE_PATH = '/api/fingerspelling/compose';
const STATUS_PATH = '/api/fingerspelling/status';
const OLD_IMAGE_ENDPOINT = '/api/fingerspelling';
const QUIET_MS = 2000;

function parseArgs(argv) {
  const args = { url: 'http://localhost:3000/', clipSeconds: null, maxLoops: 3 };
  for (let i = 0; i < argv.length; i += 1) {
    const k = argv[i];
    const v = argv[i + 1];
    if (k === '--scenario') { args.scenario = v; i += 1; }
    else if (k === '--y4m') { args.y4m = v; i += 1; }
    else if (k === '--out') { args.out = v; i += 1; }
    else if (k === '--url') { args.url = v; i += 1; }
    else if (k === '--clip-seconds') { args.clipSeconds = Number(v); i += 1; }
    else if (k === '--max-loops') { args.maxLoops = Number(v); i += 1; }
    else throw new Error(`unknown argument: ${k}`);
  }
  if (!['fingerspell', 'word'].includes(args.scenario)) throw new Error('--scenario must be fingerspell or word');
  if (!args.y4m || !fs.existsSync(args.y4m)) throw new Error('--y4m file not found');
  if (!args.out) throw new Error('--out is required');
  if (!(args.clipSeconds > 0)) throw new Error('--clip-seconds must be > 0');
  if (!(args.maxLoops >= 1)) throw new Error('--max-loops must be >= 1');
  return args;
}

const cut = (s) => String(s ?? '').slice(0, TEXT_CUT);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const now = () => performance.now();

function pathOf(url) {
  try { return new URL(url).pathname; } catch { return String(url); }
}

// ---------------------------------------------------------------------------------------------------------------
// facts of a /sequence body (the landmarks themselves never leave this function)
function sequenceBodyFacts(body) {
  const L = Array.isArray(body.landmarks) ? body.landmarks : [];
  const H = Array.isArray(body.handedness) ? body.handedness : [];
  const T = Array.isArray(body.timestamps_ms) ? body.timestamps_ms : [];
  let nonNull = 0; let identical21 = 0; let badShape = 0; let nonFinite = 0; let maxAbs = 0; let allZero = 0;
  for (const fr of L) {
    if (fr === null || (Array.isArray(fr) && fr.length === 0)) continue;
    nonNull += 1;
    if (!Array.isArray(fr) || fr.length !== 21 || fr.some((p) => !Array.isArray(p) || p.length !== 3)) {
      badShape += 1;
      continue;
    }
    const first = JSON.stringify(fr[0]);
    if (fr.every((p) => JSON.stringify(p) === first)) identical21 += 1;
    if (fr.every((p) => p.every((v) => v === 0))) allZero += 1;
    for (const p of fr) {
      for (const v of p) {
        if (typeof v !== 'number' || !Number.isFinite(v)) nonFinite += 1;
        else maxAbs = Math.max(maxAbs, Math.abs(v));
      }
    }
  }
  let tsNonDecreasing = true;
  for (let i = 1; i < T.length; i += 1) if (!(T[i] >= T[i - 1])) tsNonDecreasing = false;
  return {
    keys: Object.keys(body).sort(),
    n_landmarks: L.length,
    n_handedness: H.length,
    n_timestamps_ms: T.length,
    n_non_null_frames: nonNull,
    n_frames_21_identical_points: identical21,
    n_frames_all_zero: allZero,
    n_frames_bad_shape: badShape,
    n_non_finite_values: nonFinite,
    max_abs_value: maxAbs,
    timestamps_non_decreasing: tsNonDecreasing,
    handedness_values: [...new Set(H)].sort(),
    source_mirrored: body.source_mirrored,
    top_k: body.top_k ?? null,
    frame_width: body.frame_width ?? null,
    frame_height: body.frame_height ?? null,
  };
}

function sequenceResponseFacts(data) {
  if (!data || typeof data !== 'object') return data;
  const out = {};
  for (const [k, v] of Object.entries(data)) {
    if (k === 'candidates' && Array.isArray(v)) {
      out.candidates = v.map((c) => ({ class: c.class, confidence: c.confidence, kind: c.kind ?? null }));
    } else if (v === null || ['string', 'number', 'boolean'].includes(typeof v)) {
      out[k] = v;
    } else {
      out[k] = `<${Array.isArray(v) ? 'array' : typeof v} omitted>`;
    }
  }
  return out;
}

// JS string of a top-5 entry, exactly as PredictionDisplay.jsx writes data-gloss / data-confidence
function top5Strings(top5) {
  if (!Array.isArray(top5)) return [];
  return top5.slice(0, 5).map((item) => {
    const g = typeof item === 'object' && !Array.isArray(item) ? item.gloss : item[0];
    const c = typeof item === 'object' && !Array.isArray(item) ? item.confidence : item[1];
    return [String(g), String(c)];
  });
}

// ---------------------------------------------------------------------------------------------------------------
function newWs(url) {
  return {
    url,
    protocol: null,
    handshake_status: null,
    closed: false,
    n_messages: 0,
    n_non_json: 0,
    first_type: null,
    count_by_type: {},
    session_info: null,
    frame_result: {
      status_counts: {}, pipelines: {}, prediction_non_null: 0, prediction_key_missing: 0,
    },
    last_frame_result: null,
    hand_frame: { n: 0, with_hand: 0 },
    reset_done: [],
    sign_results: [],
    sign_discarded: [],
    errors: [],
    last_message_ms: null,
  };
}

function recordWsMessage(ws, payload) {
  ws.n_messages += 1;
  ws.last_message_ms = now();
  let msg;
  try {
    msg = JSON.parse(payload);
  } catch {
    ws.n_non_json += 1;
    return;
  }
  const type = msg && typeof msg === 'object' ? String(msg.type) : String(msg);
  if (ws.first_type === null) ws.first_type = type;
  ws.count_by_type[type] = (ws.count_by_type[type] || 0) + 1;
  if (type === 'session_info') {
    ws.session_info = msg; // small; carries no landmark
  } else if (type === 'frame_result') {
    const fr = ws.frame_result;
    fr.status_counts[msg.status] = (fr.status_counts[msg.status] || 0) + 1;
    fr.pipelines[msg.pipeline] = (fr.pipelines[msg.pipeline] || 0) + 1;
    if (!Object.prototype.hasOwnProperty.call(msg, 'prediction')) fr.prediction_key_missing += 1;
    else if (msg.prediction !== null) fr.prediction_non_null += 1;
    ws.last_frame_result = {
      pipeline: msg.pipeline ?? null,
      status: msg.status ?? null,
      gloss: msg.gloss ?? null,
      prediction: msg.prediction ?? null,
      confidence: msg.confidence ?? null,
      top5: msg.top5 ?? null,
      top5_js_strings: top5Strings(msg.top5),
    };
  } else if (type === 'hand_frame') {
    ws.hand_frame.n += 1;
    if (Array.isArray(msg.landmarks)) ws.hand_frame.with_hand += 1;
  } else if (type === 'reset_done') {
    ws.reset_done.push(msg.segment_id);
  } else if (type === 'sign_result') {
    ws.sign_results.push({
      segment_id: msg.segment_id ?? null,
      gloss: msg.gloss ?? null,
      prediction: msg.prediction ?? null,
      confidence: msg.confidence ?? null,
      top5: msg.top5 ?? null,
      top5_js_strings: top5Strings(msg.top5),
      end_reason: msg.end_reason ?? null,
      segment: msg.segment ?? null,
    });
  } else if (type === 'sign_discarded') {
    ws.sign_discarded.push({ segment_id: msg.segment_id ?? null, reason: msg.reason ?? null, segment: msg.segment ?? null });
  } else if (type === 'error') {
    ws.errors.push({ code: msg.code ?? null, detail: cut(msg.detail) });
  }
}

// ---------------------------------------------------------------------------------------------------------------
async function main() {
  const args = parseArgs(process.argv.slice(2));
  const executablePath = process.env.VSL_E2E_BROWSER || DEFAULT_BROWSER;
  const obs = {
    scenario: args.scenario,
    url: args.url,
    clip_seconds: args.clipSeconds,
    max_loops: args.maxLoops,
    node_version: process.version,
    browser_version: null,
    steps: [],
    console_errors: [],
    page_errors: [],
    request_failed: [],
    http_errors: [],
    requests_old_image_endpoint: [],
    ws: [],
    fingerspelling_status: null,
    sequence_posts: [],
    compose_posts: [],
    dom: {},
    fatal_error: null,
  };
  const wsById = new Map();
  let recording = true; // listeners stop recording before the browser is closed
  const step = (name, extra) => obs.steps.push({ t_s: Number((now() / 1000).toFixed(3)), name, ...(extra || {}) });

  const browser = await puppeteer.launch({
    executablePath,
    headless: true,
    defaultViewport: { width: 1366, height: 900 },
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      `--use-file-for-fake-video-capture=${args.y4m}`,
      '--autoplay-policy=no-user-gesture-required',
      '--window-size=1366,900',
    ],
  });
  try {
    obs.browser_version = await browser.version();
    const page = await browser.newPage();

    // -- page-level observations
    page.on('console', (m) => {
      if (recording && m.type() === 'error') {
        const loc = m.location() || {};
        obs.console_errors.push({ text: cut(m.text()), url: cut(loc.url ? pathOf(loc.url) : '') });
      }
    });
    page.on('pageerror', (e) => { if (recording) obs.page_errors.push(cut(e && e.message ? e.message : e)); });
    page.on('requestfailed', (r) => {
      if (recording) {
        obs.request_failed.push({ method: r.method(), path: cut(pathOf(r.url())), error: cut(r.failure()?.errorText) });
      }
    });
    const pending = [];
    page.on('request', (r) => {
      if (!recording) return;
      const p = pathOf(r.url());
      if (p === OLD_IMAGE_ENDPOINT) obs.requests_old_image_endpoint.push({ method: r.method(), path: p });
      if (r.method() === 'POST' && p === SEQUENCE_PATH) {
        let facts = null;
        try { facts = sequenceBodyFacts(JSON.parse(r.postData() || 'null') || {}); } catch (e) { facts = { parse_error: cut(e.message) }; }
        r.__e2eIndex = obs.sequence_posts.length;
        obs.sequence_posts.push({ body_facts: facts, status: null, response: null });
      } else if (r.method() === 'POST' && p === COMPOSE_PATH) {
        let tokens = null;
        try { tokens = (JSON.parse(r.postData() || 'null') || {}).tokens ?? null; } catch { tokens = null; }
        r.__e2eIndex = obs.compose_posts.length;
        obs.compose_posts.push({ tokens, status: null, response: null });
      }
    });
    page.on('response', (resp) => {
      if (!recording) return;
      const r = resp.request();
      const p = pathOf(resp.url());
      const status = resp.status();
      if (status >= 400) obs.http_errors.push({ method: r.method(), path: cut(p), status });
      const target = r.method() === 'POST' && p === SEQUENCE_PATH ? obs.sequence_posts
        : r.method() === 'POST' && p === COMPOSE_PATH ? obs.compose_posts : null;
      if (target && r.__e2eIndex !== undefined) {
        const entry = target[r.__e2eIndex];
        entry.status = status;
        pending.push(resp.json().then((data) => {
          entry.response = target === obs.sequence_posts ? sequenceResponseFacts(data)
            : { text: data?.text ?? null, warnings: data?.warnings ?? null, keys: data ? Object.keys(data).sort() : [] };
        }).catch((e) => { entry.response = { json_error: cut(e.message) }; }));
      }
      if (r.method() === 'GET' && p === STATUS_PATH) {
        pending.push(resp.json().then((data) => {
          obs.fingerspelling_status = {
            http_status: status, available: data?.available ?? null, num_classes: data?.num_classes ?? null,
            model_type: data?.model_type ?? null,
          };
        }).catch(() => {}));
      }
    });

    // -- WebSocket observations through CDP
    const cdp = await page.createCDPSession();
    await cdp.send('Network.enable');
    cdp.on('Network.webSocketCreated', (e) => {
      if (!recording) return;
      const ws = newWs(e.url);
      wsById.set(e.requestId, ws);
      obs.ws.push(ws);
    });
    cdp.on('Network.webSocketWillSendHandshakeRequest', (e) => {
      const ws = wsById.get(e.requestId);
      if (ws) {
        const h = e.request?.headers || {};
        const proto = Object.entries(h).find(([k]) => k.toLowerCase() === 'sec-websocket-protocol');
        ws.protocol = proto ? proto[1] : null;
      }
    });
    cdp.on('Network.webSocketHandshakeResponseReceived', (e) => {
      const ws = wsById.get(e.requestId);
      if (ws) ws.handshake_status = e.response?.status ?? null;
    });
    cdp.on('Network.webSocketFrameReceived', (e) => {
      const ws = wsById.get(e.requestId);
      if (ws && recording && e.response && e.response.opcode === 1) recordWsMessage(ws, e.response.payloadData);
    });
    cdp.on('Network.webSocketClosed', (e) => {
      const ws = wsById.get(e.requestId);
      if (ws) ws.closed = true;
    });

    // DOM appearances of live-recording (the harmonized recording bar)
    await page.evaluateOnNewDocument(() => {
      window.__e2e = { recordingAppearances: 0 };
      let present = false;
      const check = () => {
        const on = Boolean(document.querySelector('[data-testid="live-recording"]'));
        if (on && !present) window.__e2e.recordingAppearances += 1;
        present = on;
      };
      new MutationObserver(check).observe(document, { childList: true, subtree: true });
    });

    step('goto');
    const resp = await page.goto(args.url, { waitUntil: 'load', timeout: 120000 });
    obs.page_status = resp ? resp.status() : null;

    const loopMs = args.clipSeconds * 1000;
    const text = (sel) => page.$eval(sel, (el) => el.textContent.trim()).catch(() => null);
    const attr = (sel, name) => page.$eval(sel, (el, n) => el.getAttribute(n), name).catch(() => null);
    const wsFor = (suffix) => obs.ws.filter((w) => pathOf(w.url) === suffix);
    const lastWsFor = (suffix) => { const l = wsFor(suffix); return l.length ? l[l.length - 1] : null; };
    const waitFor = async (pred, timeoutMs, pollMs = 100) => {
      const t0 = now();
      while (now() - t0 < timeoutMs) {
        if (await pred()) return true;
        await sleep(pollMs);
      }
      return Boolean(await pred());
    };
    const waitQuiet = async (ws, capMs) => {
      const t0 = now();
      while (now() - t0 < capMs) {
        const last = ws && ws.last_message_ms !== null ? ws.last_message_ms : t0;
        if (now() - Math.max(last, t0) >= QUIET_MS) return true;
        await sleep(100);
      }
      return false;
    };

    if (args.scenario === 'fingerspell') {
      // tab "Bảng Chữ Cái" (Navbar button; no data-testid on the tabs)
      const clicked = await page.evaluate(() => {
        const b = [...document.querySelectorAll('header nav button')].find((x) => x.textContent.includes('Bảng Chữ Cái'));
        if (!b) return false;
        b.click();
        return true;
      });
      step('tab_alphabet', { clicked });
      await page.waitForSelector('[data-testid="fs-status"]', { timeout: 30000 });
      await waitFor(async () => (await attr('[data-testid="fs-status"]', 'data-available')) === 'true', 60000);
      await waitFor(async () => (await attr('[data-testid="fs-ws"]', 'data-status')) === 'connected', 60000);
      await waitFor(async () => Boolean(lastWsFor('/ws/hand-landmarks')?.session_info), 30000);
      obs.dom.fs_status_available = await attr('[data-testid="fs-status"]', 'data-available');
      obs.dom.fs_ws_status = await attr('[data-testid="fs-ws"]', 'data-status');
      step('ready', { available: obs.dom.fs_status_available, ws: obs.dom.fs_ws_status });

      const recordEnabled = await waitFor(async () => page.$eval('[data-testid="fs-record"]', (el) => !el.disabled).catch(() => false), 30000);
      if (!recordEnabled) throw new Error('fs-record stays disabled');
      const nSeqBefore = obs.sequence_posts.length;
      await page.click('[data-testid="fs-record"]');
      step('record_clicked');
      const recStarted = await waitFor(async () => page.$eval('[data-testid="fs-stop"]', (el) => !el.disabled).catch(() => false), 30000, 20);
      step('recording', { started: recStarted });
      await sleep(loopMs); // one loop of the clip
      const stopEnabled = await page.$eval('[data-testid="fs-stop"]', (el) => !el.disabled).catch(() => false);
      if (stopEnabled) await page.click('[data-testid="fs-stop"]');
      step('stop_clicked', { stop_button_enabled: stopEnabled });

      await waitFor(async () => obs.sequence_posts.length > nSeqBefore
        && obs.sequence_posts[obs.sequence_posts.length - 1].status !== null, 60000);
      await Promise.allSettled(pending);
      const lastSeq = obs.sequence_posts[obs.sequence_posts.length - 1] || null;
      if (lastSeq && lastSeq.status === 200 && lastSeq.response) {
        const want = String(lastSeq.response.prediction);
        await waitFor(async () => (await text('[data-testid="fs-prediction"]')) === want, 10000);
      } else {
        await waitFor(async () => Boolean(await page.$('[data-testid="fs-error"]')), 10000);
      }
      obs.dom.fs_prediction = await text('[data-testid="fs-prediction"]');
      obs.dom.fs_confidence_value = await attr('[data-testid="fs-confidence"]', 'data-value');
      obs.dom.fs_confidence_text = await text('[data-testid="fs-confidence"]');
      obs.dom.fs_frames = await attr('[data-testid="fs-frames"]', 'data-frames');
      obs.dom.fs_frames_text = await text('[data-testid="fs-frames"]');
      obs.dom.fs_error = await text('[data-testid="fs-error"]');
      if (lastSeq && lastSeq.response && typeof lastSeq.response.confidence === 'number') {
        // the strings the UI is expected to show for that response (JS formatting, as in Fingerspelling.jsx)
        obs.dom.expected_confidence_value = String(lastSeq.response.confidence);
        obs.dom.expected_confidence_text = `${(lastSeq.response.confidence * 100).toFixed(1)}%`;
      }
      const hw = lastWsFor('/ws/hand-landmarks');
      step('sequence_done', { status: lastSeq ? lastSeq.status : null, hand_frames: hw ? hw.hand_frame.n : null });

      // composer: add the selected (top-1) candidate
      const nComposeBefore = obs.compose_posts.length;
      const addEnabled = await page.$eval('[data-testid="fs-add"]', (el) => !el.disabled).catch(() => false);
      if (addEnabled) await page.click('[data-testid="fs-add"]');
      step('add_clicked', { add_button_enabled: addEnabled });
      await waitFor(async () => obs.compose_posts.length > nComposeBefore
        && obs.compose_posts[obs.compose_posts.length - 1].status !== null, 30000);
      await Promise.allSettled(pending);
      const lastCompose = obs.compose_posts[obs.compose_posts.length - 1] || null;
      if (lastCompose && lastCompose.response && typeof lastCompose.response.text === 'string') {
        const want = lastCompose.response.text.trim();
        await waitFor(async () => (await text('[data-testid="fs-composed"]')) === want, 10000);
      }
      obs.dom.fs_composed = await text('[data-testid="fs-composed"]');
      obs.dom.fs_warnings = await text('[data-testid="fs-warnings"]');
      step('compose_done', { status: lastCompose ? lastCompose.status : null });
    } else {
      // "Ký từ" (default tab)
      await page.waitForSelector('[data-testid="live-connection"]', { timeout: 30000 });
      await waitFor(async () => (await attr('[data-testid="live-connection"]', 'data-status')) === 'connected', 60000);
      await waitFor(async () => Boolean(lastWsFor('/ws/live-stream')?.session_info), 30000);
      step('ready', { connection: await attr('[data-testid="live-connection"]', 'data-status') });
      const live = () => lastWsFor('/ws/live-stream');
      const harmonized = live()?.session_info?.pipeline === 'harmonized_v1';

      await waitFor(async () => page.$eval('[data-testid="camera-start"]', (el) => !el.disabled).catch(() => false), 30000);
      await page.click('[data-testid="camera-start"]');
      const tStart = now();
      step('camera_started', { harmonized });
      // run at least one loop of the clip; stop as soon as the scenario has what it needs; at most max-loops loops
      const enough = () => {
        const w = live();
        if (!w) return false;
        if (harmonized) return w.sign_results.length + w.sign_discarded.length >= 1;
        return (w.count_by_type.frame_result || 0) >= 30;
      };
      while (now() - tStart < args.maxLoops * loopMs) {
        if (now() - tStart >= loopMs && enough()) break;
        await sleep(100);
      }
      const ranMs = now() - tStart;
      const stopExists = Boolean(await page.$('[data-testid="camera-stop"]'));
      if (stopExists) await page.click('[data-testid="camera-stop"]');
      step('camera_stopped', { ran_s: Number((ranMs / 1000).toFixed(3)), loops: Number((ranMs / loopMs).toFixed(3)) });
      obs.ran_seconds = Number((ranMs / 1000).toFixed(3));
      obs.ran_loops = Number((ranMs / loopMs).toFixed(3));
      obs.quiet_after_stop = await waitQuiet(live(), 30000);
      await sleep(300); // let React render the last message

      obs.dom.live_pipeline = await text('[data-testid="live-pipeline"]');
      obs.dom.live_model_type = await attr('[data-testid="live-model"]', 'data-model-type');
      obs.dom.live_model_is_default = await attr('[data-testid="live-model"]', 'data-is-default');
      obs.dom.live_status = await attr('[data-testid="live-status"]', 'data-status');
      obs.dom.live_gloss = await text('[data-testid="live-gloss"]');
      obs.dom.live_confidence_value = await attr('[data-testid="live-confidence"]', 'data-value');
      obs.dom.live_top5 = await page.$$eval('[data-testid="live-top5-item"]',
        (els) => els.map((el) => [el.getAttribute('data-gloss'), el.getAttribute('data-confidence')])).catch(() => null);
      obs.dom.live_words = await page.$$eval('[data-testid="live-word"]', (els) => els.map((el) => el.textContent.trim()))
        .catch(() => null);
      obs.dom.live_error = await attr('[data-testid="live-error"]', 'data-code');
      obs.dom.live_discard = await attr('[data-testid="live-discard"]', 'data-reason');
      obs.dom.live_recording_appearances = await page.evaluate(() => window.__e2e.recordingAppearances);
    }
    await Promise.allSettled(pending);
    step('done');
  } catch (e) {
    obs.fatal_error = cut(e && e.stack ? e.stack : e);
  } finally {
    recording = false;
    for (const w of obs.ws) delete w.last_message_ms;
    fs.writeFileSync(args.out, JSON.stringify(obs, null, 2));
    await browser.close().catch(() => {});
  }
  process.exit(obs.fatal_error ? 2 : 0);
}

main().catch((e) => {
  console.error(e && e.stack ? e.stack : e);
  process.exit(3);
});
