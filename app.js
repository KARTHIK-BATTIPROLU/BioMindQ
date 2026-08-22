/**
 * BIOMINDQ // MULTI-SOURCE BIOMEDICAL EVIDENCE VERIFICATION LAYER
 * 48,000 Particle WebGL Engine & Real-Time Evidence Convergence Waveform
 */

let scene, camera, renderer, controls;
let autoOrbit = true;
let isSessionActive = true;
let audioCtx = null;
let clock = new THREE.Clock();

// Master 3D Objects
let dnaParticleMesh, dnaShaderMaterial;
let particleCount = 48000;

// Active Sequence State
const BASES = ['A', 'T', 'G', 'C'];
let activeSequence = [
  'A', 'T', 'G', 'C', 'C', 'G', 'T', 'A', 'A', 'T', 'C', 'G', 'T', 'A', 'G', 'C', 'A', 'T', 'G', 'C', 'G', 'C', 'A', 'T'
];

// Active Query State Data
const QUERY_DATA = {
  metformin: {
    title: "Metformin ↔ AMPK Interaction",
    desc: "Retrieved evidence indicates metformin activates AMPK indirectly via mitochondrial complex I inhibition. Confirmed independently across ChEMBL bioactivity records and 3 PubMed abstracts. No conflicting evidence found.",
    confidence: "94.2%",
    agreePct: "94.2%",
    conflictPct: "0.0%",
    responseTime: "4.1s",
    badge: "3/3 SOURCES AGREE",
    badgeClass: "badge-green",
    pubmed: "3 Abstracts Verified",
    chembl: "IC50 = 12.4 μM",
    drugbank: "Target DB00331",
    ticker: "CROSS-MATCHING PUBMED · ChEMBL · DRUGBANK · PUBCHEM"
  },
  alzheimers: {
    title: "Early-Stage Alzheimer's Compounds",
    desc: "Retrieved literature details anti-amyloid monoclonal antibodies (Lecanemab, Donanemab) and BACE1 inhibitors. Verified across 14 PubMed clinical trials and ChEMBL bioactivity assay datasets.",
    confidence: "91.8%",
    agreePct: "91.8%",
    conflictPct: "0.5%",
    responseTime: "3.8s",
    badge: "4/4 SOURCES AGREE",
    badgeClass: "badge-cyan",
    pubmed: "14 Clinical Trials",
    chembl: "287 Compounds",
    drugbank: "CID 11954316",
    ticker: "RETRIEVED 14 PUBMED TRIALS & 287 ChEMBL ASSAYS"
  },
  ibuprofen: {
    title: "Ibuprofen ↔ Lisinopril Interaction",
    desc: "NSAIDs like ibuprofen reduce the antihypertensive effect of ACE inhibitors like lisinopril and increase renal toxicity risk. Verified across DrugBank DB01050 & 5 PubMed clinical advisories.",
    confidence: "98.6%",
    agreePct: "98.6%",
    conflictPct: "12.4%",
    responseTime: "2.9s",
    badge: "HIGH-RISK CONFLICT",
    badgeClass: "badge-rose",
    pubmed: "5 Clinical Advisories",
    chembl: "ACE Inhibitor Target",
    drugbank: "DB01050 / DB00722",
    ticker: "WARNING: RENAL ANTAGONISM CONFLICT DETECTED"
  },
  glp1: {
    title: "GLP-1 Receptor Agonist Synthesis",
    desc: "Comprehensive literature scan reveals potent glycemic control, weight reduction, and cardiovascular risk reduction (Semaglutide, Tirzepatide). Grounded in 42 PubMed RCTs & ChEMBL binding affinity data.",
    confidence: "96.5%",
    agreePct: "96.5%",
    conflictPct: "0.0%",
    responseTime: "4.5s",
    badge: "3/3 SOURCES AGREE",
    badgeClass: "badge-gold",
    pubmed: "42 RCT Papers",
    chembl: "Ki = 0.21 nM",
    drugbank: "Target DB06655",
    ticker: "SYNTHESIZING 42 PUBMED PAPERS & ChEMBL BINDING DATA"
  }
};

let currentQueryKey = 'metformin';

// Mouse Tracking
let mouseX = 0, mouseY = 0;
let targetCamX = 0, targetCamY = 0;

// Telemetry Waveform Engine (4-Trace Source Agreement Signal)
let waveCanvas, waveCtx;
let waveX = 0;
let waveConvergenceProgress = 1.0; // 0 = split traces, 1 = converged
let convergenceAnimId = null;

/* ==========================================================================
   GLSL SHADERS FOR 48,000 MOLECULAR BIOPHOTON PARTICLES
   ========================================================================== */

const vertexShader = `
  uniform float uTime;
  uniform float uTurbulence;
  uniform float uDockSurge;
  uniform vec2 uMouse;

  attribute float aPhase;
  attribute vec3 aBaseColor;

  varying vec3 vColor;
  varying float vAlpha;

  // Simplex 3D Noise
  vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
  vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

  float snoise(vec3 v) {
    const vec2 C = vec2(1.0/6.0, 1.0/3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
    vec3 i  = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);
    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);
    vec3 x1 = x0 - i1 + C.xxx;
    vec3 x2 = x0 - i2 + C.yyy;
    vec3 x3 = x0 - D.yyy;
    i = mod289(i);
    vec4 p = permute(permute(permute(
              i.z + vec4(0.0, i1.z, i2.z, 1.0))
            + i.y + vec4(0.0, i1.y, i2.y, 1.0))
            + i.x + vec4(0.0, i1.x, i2.x, 1.0));
    float n_ = 0.142857142857;
    vec3 ns = n_ * D.wyz - D.xzx;
    vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
    vec4 x_ = floor(j * ns.z);
    vec4 y_ = floor(j - 7.0 * x_);
    vec4 x = x_ *ns.x + ns.yyyy;
    vec4 y = y_ *ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);
    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);
    vec4 s0 = floor(b0)*2.0 + 1.0;
    vec4 s1 = floor(b1)*2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));
    vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);
    vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
    p0 *= norm.x;
    p1 *= norm.y;
    p2 *= norm.z;
    p3 *= norm.w;
    vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
    m = m * m;
    return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
  }

  void main() {
    float t = uTime * 0.5 + aPhase;

    vec3 noiseVec = vec3(
      snoise(position * 0.6 + vec3(t * 0.25, 0.0, 0.0)),
      snoise(position * 0.6 + vec3(0.0, t * 0.25, 0.0)),
      snoise(position * 0.6 + vec3(0.0, 0.0, t * 0.25))
    );

    vec3 finalPos = position + noiseVec * (0.12 * uTurbulence);

    if (uDockSurge > 0.01) {
      float ripple = sin(length(finalPos.xz) * 6.0 - uTime * 10.0);
      finalPos += normalize(finalPos) * ripple * (uDockSurge * 0.35);
    }

    vec4 mvPosition = modelViewMatrix * vec4(finalPos, 1.0);
    gl_Position = projectionMatrix * mvPosition;

    float pSize = (16.0 / -mvPosition.z) * (1.0 + uDockSurge * 0.5);
    gl_PointSize = clamp(pSize, 1.5, 42.0);

    vColor = aBaseColor;
    if (uDockSurge > 0.01) {
      vColor = mix(vColor, vec3(1.0, 1.0, 1.0), uDockSurge * 0.7);
    }

    vAlpha = clamp(1.3 / (-mvPosition.z * 0.16), 0.25, 0.95);
  }
`;

const fragmentShader = `
  varying vec3 vColor;
  varying float vAlpha;

  void main() {
    vec2 coord = gl_PointCoord - vec2(0.5);
    float dist = length(coord);

    if (dist > 0.5) discard;

    float intensity = exp(-dist * 5.0);
    gl_FragColor = vec4(vColor, vAlpha * intensity);
  }
`;

/* ==========================================================================
   INITIALIZE THREE.JS
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initEngine();
  initCursor();
  initWaveformCanvas();
  renderCodonStrip();
  initArchitectureInteractivity();
  animate();

  window.addEventListener('resize', onResize);
  document.addEventListener('mousemove', onMouseMove);
});

function initEngine() {
  const container = document.getElementById('canvas-stage');
  if (!container) return;
  scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x05070c, 0.032);

  camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(0, 0.25, 8.6);

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.35;
  container.appendChild(renderer.domElement);

  if (typeof THREE.OrbitControls !== 'undefined') {
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.04;
    controls.maxDistance = 14;
    controls.minDistance = 3.2;
    controls.enablePan = false;
  }

  buildParticleDNAHelix();
}

function buildParticleDNAHelix() {
  if (dnaParticleMesh) scene.remove(dnaParticleMesh);

  const geo = new THREE.BufferGeometry();
  const pos = new Float32Array(particleCount * 3);
  const colors = new Float32Array(particleCount * 3);
  const phases = new Float32Array(particleCount);

  const turns = 3.2;
  const radius = 1.35;
  const height = 10.5;

  for (let i = 0; i < particleCount; i++) {
    const t = i / particleCount;
    const y = (t - 0.5) * height;
    const angle = t * Math.PI * 2 * turns;

    let x, z;
    let c = new THREE.Color(0x00f0ff);

    if (i < particleCount * 0.7) {
      const strand = (i % 2 === 0) ? 0 : Math.PI;
      const strandRad = radius + (Math.random() - 0.5) * 0.18;

      x = Math.cos(angle + strand) * strandRad;
      z = Math.sin(angle + strand) * strandRad;

      if (strand === 0) c = new THREE.Color(0x00f0ff);
      else c = new THREE.Color(0x00e676);
    } else if (i < particleCount * 0.9) {
      const interp = Math.random();
      const rad1 = Math.cos(angle) * radius;
      const rad2 = Math.cos(angle + Math.PI) * radius;
      const zrad1 = Math.sin(angle) * radius;
      const zrad2 = Math.sin(angle + Math.PI) * radius;

      x = rad1 * interp + rad2 * (1.0 - interp);
      z = zrad1 * interp + zrad2 * (1.0 - interp);

      const baseMod = Math.floor(t * activeSequence.length) % activeSequence.length;
      const base = activeSequence[baseMod];

      if (base === 'A') c = new THREE.Color(0x00f0ff);
      else if (base === 'T') c = new THREE.Color(0xff2d55);
      else if (base === 'G') c = new THREE.Color(0x00e676);
      else c = new THREE.Color(0xffd600);
    } else {
      const solAngle = Math.random() * Math.PI * 2;
      const solR = radius + 0.4 + Math.random() * 1.2;
      x = Math.cos(solAngle) * solR;
      z = Math.sin(solAngle) * solR;
      c = new THREE.Color(0xa855f7);
    }

    pos[i * 3] = x;
    pos[i * 3 + 1] = y;
    pos[i * 3 + 2] = z;

    colors[i * 3] = c.r;
    colors[i * 3 + 1] = c.g;
    colors[i * 3 + 2] = c.b;

    phases[i] = Math.random() * Math.PI * 2;
  }

  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('aBaseColor', new THREE.BufferAttribute(colors, 3));
  geo.setAttribute('aPhase', new THREE.BufferAttribute(phases, 1));

  dnaShaderMaterial = new THREE.ShaderMaterial({
    vertexShader: vertexShader,
    fragmentShader: fragmentShader,
    uniforms: {
      uTime: { value: 0.0 },
      uTurbulence: { value: 1.2 },
      uDockSurge: { value: 0.0 },
      uMouse: { value: new THREE.Vector2(0, 0) }
    },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending
  });

  dnaParticleMesh = new THREE.Points(geo, dnaShaderMaterial);
  dnaParticleMesh.position.set(1.4, 0, 0);
  scene.add(dnaParticleMesh);
}

/* ==========================================================================
   ANIMATION LOOP
   ========================================================================== */

function animate() {
  requestAnimationFrame(animate);

  const delta = clock.getDelta();
  const time = clock.getElapsedTime();

  if (dnaShaderMaterial) {
    dnaShaderMaterial.uniforms.uTime.value = time;
    const surge = dnaShaderMaterial.uniforms.uDockSurge.value;
    if (surge > 0.001) {
      dnaShaderMaterial.uniforms.uDockSurge.value = THREE.MathUtils.lerp(surge, 0.0, 0.05);
    }
  }

  if (autoOrbit && dnaParticleMesh) {
    dnaParticleMesh.rotation.y += delta * 0.25;
  }

  targetCamX = mouseX * 0.35;
  targetCamY = mouseY * 0.35;
  if (dnaParticleMesh) {
    dnaParticleMesh.rotation.x = THREE.MathUtils.lerp(dnaParticleMesh.rotation.x, targetCamY * 0.2, 0.05);
    dnaParticleMesh.rotation.z = THREE.MathUtils.lerp(dnaParticleMesh.rotation.z, targetCamX * 0.15, 0.05);
  }

  if (controls) controls.update();
  if (renderer && scene && camera) renderer.render(scene, camera);
}

function onResize() {
  if (!camera || !renderer) return;
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}

function onMouseMove(e) {
  mouseX = (e.clientX / window.innerWidth) * 2 - 1;
  mouseY = -(e.clientY / window.innerHeight) * 2 + 1;
}

/* ==========================================================================
   SAMPLE QUERY EXECUTION & VERIFICATION ENGINE
   ========================================================================== */

function runSampleQuery(key, evt) {
  currentQueryKey = key;
  const q = QUERY_DATA[key];
  if (!q) return;

  playAcousticTone(640, 0.1);

  if (evt && evt.currentTarget) {
    document.querySelectorAll('.shelf-card').forEach(c => c.classList.remove('active'));
    evt.currentTarget.classList.add('active');
  }

  // Update Telemetry Panel Numbers
  const confElem = document.getElementById('confidence-stat');
  if (confElem) confElem.innerHTML = `${parseFloat(q.confidence)}<span class="unit-text">%</span>`;

  const badgeElem = document.getElementById('agree-badge');
  if (badgeElem) {
    badgeElem.textContent = q.badge;
    badgeElem.className = `panel-badge ${q.badgeClass}`;
  }

  document.getElementById('agree-display').textContent = q.agreePct;
  document.getElementById('conflict-display').textContent = q.conflictPct;
  document.getElementById('time-display').textContent = q.responseTime;

  // Update Profile Card
  document.getElementById('query-title').textContent = q.title;
  document.getElementById('query-desc').textContent = q.desc;
  document.getElementById('spec-pubmed').textContent = q.pubmed;
  document.getElementById('spec-chembl').textContent = q.chembl;
  document.getElementById('spec-drugbank').textContent = q.drugbank;

  // Update Bottom Ticker
  document.getElementById('ticker-query-text').textContent = q.ticker;
  document.getElementById('ticker-agree-val').textContent = q.agreePct;

  // Pulse 3D DNA Mesh
  if (dnaShaderMaterial) {
    dnaShaderMaterial.uniforms.uDockSurge.value = 1.0;
  }

  // Trigger 4-Trace Convergence Animation (§5.1)
  triggerSourceCrossCheck();
}

function triggerSourceCrossCheck() {
  playAcousticTone(880, 0.2);
  waveConvergenceProgress = 0.0;
  
  if (convergenceAnimId) cancelAnimationFrame(convergenceAnimId);

  const startTime = Date.now();
  const duration = 800; // 800ms per spec §5.1

  function animateConvergence() {
    const elapsed = Date.now() - startTime;
    waveConvergenceProgress = Math.min(elapsed / duration, 1.0);

    if (waveConvergenceProgress < 1.0) {
      convergenceAnimId = requestAnimationFrame(animateConvergence);
    }
  }
  animateConvergence();
}

function reRunQuery() {
  runSampleQuery(currentQueryKey);
}

function resetQueryState() {
  runSampleQuery('metformin');
}

function toggleEvidenceView() {
  const card = document.getElementById('query-profile-card');
  if (card) {
    card.classList.toggle('highlight-evidence');
    playAcousticTone(520, 0.08);
  }
}

/* ==========================================================================
   2D SOURCE AGREEMENT SIGNAL WAVEFORM CANVAS (§5.1)
   ========================================================================== */

function initWaveformCanvas() {
  waveCanvas = document.getElementById('waveform-canvas');
  if (!waveCanvas) return;
  waveCtx = waveCanvas.getContext('2d');

  setInterval(drawMultiTraceWaveStep, 35);
}

function drawMultiTraceWaveStep() {
  if (!waveCtx || !waveCanvas) return;
  const w = waveCanvas.width;
  const h = waveCanvas.height;
  const midY = h / 2;

  waveCtx.clearRect(0, 0, w, h);

  const t = Date.now() / 1000;
  const sources = [
    { name: 'PubMed', color: '#00f0ff', offset: 0, amp: 16 },
    { name: 'ChEMBL', color: '#00e676', offset: 1.2, amp: 14 },
    { name: 'DrugBank', color: '#ffd600', offset: 2.4, amp: 18 },
    { name: 'PubChem', color: '#a855f7', offset: 3.6, amp: 12 }
  ];

  // Draw 4 overlapping traces sweeping in from left and converging smoothly
  sources.forEach((src, idx) => {
    waveCtx.beginPath();
    waveCtx.strokeStyle = src.color;
    waveCtx.lineWidth = 1.6;
    waveCtx.shadowBlur = 4;
    waveCtx.shadowColor = src.color;

    for (let x = 0; x < w; x += 3) {
      // Convergence factor: x/w ratio + animation progress
      const normX = x / w;
      const spread = (1.0 - Math.pow(normX, 1.5)) * (1.0 - waveConvergenceProgress);
      const phaseOffset = src.offset * spread;

      const y = midY + Math.sin(t * 4.5 + x * 0.06 + phaseOffset) * (src.amp * (0.3 + spread * 0.7));

      if (x === 0) waveCtx.moveTo(x, y);
      else waveCtx.lineTo(x, y);
    }
    waveCtx.stroke();
  });
}

/* ==========================================================================
   ARCHITECTURE SECTION INTERACTIVITY (§5.2)
   ========================================================================== */

function initArchitectureInteractivity() {
  // Ambient toggle between 3/3 Agree (Green) and Conflict Flagged (Amber) every 6s (§5.2)
  const verifyState = document.getElementById('arch-verify-state');
  const verifyText = document.getElementById('arch-verify-text');
  let isAgreeState = true;

  if (verifyState && verifyText) {
    setInterval(() => {
      isAgreeState = !isAgreeState;
      if (isAgreeState) {
        verifyText.textContent = '3/3 SOURCES AGREE (94.2%)';
        verifyState.className = 'verifier-live-badge state-agree';
      } else {
        verifyText.textContent = 'SOURCE CONFLICT FLAGGED';
        verifyState.className = 'verifier-live-badge state-conflict';
      }
    }, 6000);
  }

  // Scroll Observer for Architecture Nodes Sequential Glow
  const archNodes = document.querySelectorAll('.arch-stage-node');
  if ('IntersectionObserver' in window && archNodes.length > 0) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('node-active');
        }
      });
    }, { threshold: 0.2 });

    archNodes.forEach(node => observer.observe(node));
  }
}

function switchArchTab(tabType) {
  const evView = document.getElementById('tab-evidence-view');
  const sumView = document.getElementById('tab-summary-view');
  const buttons = document.querySelectorAll('.out-tab');

  if (!evView || !sumView) return;

  buttons.forEach(b => b.classList.remove('active'));

  if (tabType === 'evidence') {
    evView.classList.remove('hidden');
    sumView.classList.add('hidden');
    if (buttons[0]) buttons[0].classList.add('active');
  } else {
    sumView.classList.remove('hidden');
    evView.classList.add('hidden');
    if (buttons[1]) buttons[1].classList.add('active');
  }
  playAcousticTone(720, 0.08);
}

/* ==========================================================================
   SEQUENCE TRACK & CODONS
   ========================================================================== */

function renderCodonStrip() {
  const strip = document.getElementById('codons-strip');
  if (!strip) return;
  strip.innerHTML = '';

  let gcCount = 0;
  activeSequence.forEach((base, idx) => {
    if (base === 'G' || base === 'C') gcCount++;

    const pill = document.createElement('div');
    pill.className = `codon-pill c-${base.toLowerCase()}`;
    pill.innerHTML = `
      <span class="codon-pos">${idx + 1}</span>
      <span class="codon-base">${base}</span>
    `;
    pill.title = `Codon Pos ${idx + 1}: ${base} (Click to toggle)`;
    pill.onclick = () => cycleBase(idx);
    strip.appendChild(pill);
  });

  const gcPct = ((gcCount / activeSequence.length) * 100).toFixed(1);
  const gcElem = document.getElementById('gc-val');
  if (gcElem) gcElem.textContent = `${gcPct}%`;
}

function cycleBase(idx) {
  const cur = activeSequence[idx];
  const next = BASES[(BASES.indexOf(cur) + 1) % BASES.length];
  activeSequence[idx] = next;

  playAcousticTone(520 + idx * 15, 0.05);
  renderCodonStrip();
  buildParticleDNAHelix();
}

/* ==========================================================================
   AUDIO SYNTHESIZER & UTILS
   ========================================================================== */

function playAcousticTone(freq, dur) {
  if (!isSessionActive) return;
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
    gain.gain.setValueAtTime(0.04, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + dur);

    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + dur);
  } catch (e) {}
}

function toggleSessionState() {
  isSessionActive = !isSessionActive;
  const txt = document.getElementById('session-txt');
  if (txt) txt.textContent = isSessionActive ? 'SESSION: LIVE' : 'SESSION: MUTED';
}

function initCursor() {
  const dot = document.getElementById('cursor-dot');
  const ring = document.getElementById('cursor-ring');
  let cx = 0, cy = 0, rx = 0, ry = 0;

  document.addEventListener('mousemove', e => {
    cx = e.clientX;
    cy = e.clientY;
    if (dot) dot.style.transform = `translate(${cx}px, ${cy}px)`;
  });

  function updateRing() {
    rx += (cx - rx) * 0.15;
    ry += (cy - ry) * 0.15;
    if (ring) ring.style.transform = `translate(${rx}px, ${ry}px)`;
    requestAnimationFrame(updateRing);
  }
  updateRing();
}

function openPortal() {
  const modal = document.getElementById('portal-modal');
  if (modal) modal.classList.add('active');
}

function closePortal() {
  const modal = document.getElementById('portal-modal');
  if (modal) modal.classList.remove('active');
}

function handlePortalSubmit(e) {
  e.preventDefault();
  const queryVal = document.getElementById('console-query-input').value;
  alert(`Parallel verification initiated for query:\n"${queryVal}"\n\nQuerying PubMed, ChEMBL, DrugBank, and PubChem simultaneously.`);
  closePortal();
}
