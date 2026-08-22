/**
 * PROTERA // LIGHT MODE 3D DNA DOCKING & PHARMACOGENOMICS ENGINE
 * Interactive Three.js WebGL DNA Strand, Ligand Docking & Codon Sequence Controls
 */

let scene, camera, renderer, controls;
let autoOrbit = true;
let isAudioActive = true;
let audioCtx = null;
let clock = new THREE.Clock();

// Master 3D Objects
let dnaGroup;
let particleMesh, shaderMaterial;
let drugLigandGroup;

// Active Sequence State
const BASES = ['A', 'T', 'G', 'C'];
let activeSequence = ['A', 'T', 'G', 'C', 'C', 'G', 'T', 'A'];

// Active Drug Data (Matching Screenshot)
const DRUG_DATA = {
  elexacaftor: {
    title: 'Elexacaftor-01',
    energy: '-14.2 kcal/mol',
    kd: 'Kd = 1.4 nM',
    res: 't1/2 = 4.8 hr',
    conf: 'BOUND (CFTR Exon 10)',
    color: 0x2563eb
  },
  nusinersen: {
    title: 'Nusinersen-X',
    energy: '-16.8 kcal/mol',
    kd: 'Kd = 0.8 nM',
    res: 't1/2 = 135d',
    conf: 'BOUND (SMN2 Exon 7)',
    color: 0x10b981
  },
  exacel: {
    title: 'Exa-cel Prime',
    energy: '-19.4 kcal/mol',
    kd: '99.98% Fidelity',
    res: 'Permanent Edit',
    conf: 'EDITED (BCL11A Enhancer)',
    color: 0x8b5cf6
  },
  patisiran: {
    title: 'Patisiran-RNAi',
    energy: '-12.6 kcal/mol',
    kd: 't1/2 = 4.8 hr',
    res: 't1/2 = 9.2 days',
    conf: 'SILENCED (TTR 3\' UTR)',
    color: 0xf59e0b
  }
};

let currentDrugKey = 'elexacaftor';

// Mouse Parallax
let mouseX = 0, mouseY = 0;
let targetCamX = 0, targetCamY = 0;

/* ==========================================================================
   INITIALIZE THREE.JS LIGHT SCENE
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initEngine();
  initCursor();
  renderCodonStrip();
  animate();

  window.addEventListener('resize', onResize);
  document.addEventListener('mousemove', onMouseMove);
});

function initEngine() {
  const container = document.getElementById('canvas-stage');
  if (!container) return;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf8fafc);
  scene.fog = new THREE.FogExp2(0xf8fafc, 0.04);

  camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(0.8, 0.2, 8.2);

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.2;
  container.appendChild(renderer.domElement);

  if (typeof THREE.OrbitControls !== 'undefined') {
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.04;
    controls.maxDistance = 14;
    controls.minDistance = 3.2;
    controls.enablePan = false;
  }

  // Lighting for Light Theme
  const ambientLight = new THREE.AmbientLight(0xffffff, 1.2);
  scene.add(ambientLight);

  const dirLight1 = new THREE.DirectionalLight(0x2563eb, 1.5);
  dirLight1.position.set(5, 10, 7);
  scene.add(dirLight1);

  const dirLight2 = new THREE.DirectionalLight(0xf43f5e, 1.2);
  dirLight2.position.set(-5, -5, -5);
  scene.add(dirLight2);

  build3DDNAHelix();
  build3DDrugLigand();
}

/* ==========================================================================
   BUILD 3D DNA DOUBLE HELIX MODEL (LIGHT THEME MATCHING SCREENSHOT)
   ========================================================================== */

function build3DDNAHelix() {
  if (dnaGroup) scene.remove(dnaGroup);

  dnaGroup = new THREE.Group();

  const turns = 2.8;
  const radius = 1.2;
  const height = 9.0;
  const count = 48; // Number of rungs

  const strand1Geo = [];
  const strand2Geo = [];

  const strandMat1 = new THREE.MeshPhysicalMaterial({
    color: 0x38bdf8,
    emissive: 0x0284c7,
    emissiveIntensity: 0.4,
    roughness: 0.1,
    metalness: 0.1,
    transmission: 0.6,
    thickness: 0.5
  });

  const strandMat2 = new THREE.MeshPhysicalMaterial({
    color: 0xf43f5e,
    emissive: 0xe11d48,
    emissiveIntensity: 0.4,
    roughness: 0.1,
    metalness: 0.1,
    transmission: 0.6,
    thickness: 0.5
  });

  const sphereGeo = new THREE.SphereGeometry(0.12, 16, 16);
  const rungMat = new THREE.MeshStandardMaterial({ roughness: 0.2, metalness: 0.3 });

  for (let i = 0; i <= count; i++) {
    const t = i / count;
    const y = (t - 0.5) * height;
    const angle = t * Math.PI * 2 * turns;

    const x1 = Math.cos(angle) * radius;
    const z1 = Math.sin(angle) * radius;

    const x2 = Math.cos(angle + Math.PI) * radius;
    const z2 = Math.sin(angle + Math.PI) * radius;

    const p1 = new THREE.Vector3(x1, y, z1);
    const p2 = new THREE.Vector3(x2, y, z2);

    strand1Geo.push(p1);
    strand2Geo.push(p2);

    // Render Helical Joints
    const joint1 = new THREE.Mesh(sphereGeo, strandMat1);
    joint1.position.copy(p1);
    dnaGroup.add(joint1);

    const joint2 = new THREE.Mesh(sphereGeo, strandMat2);
    joint2.position.copy(p2);
    dnaGroup.add(joint2);

    // Render Nucleotide Connecting Rungs
    const curve = new THREE.LineCurve3(p1, p2);
    const tubeGeo = new THREE.TubeGeometry(curve, 8, 0.05, 8, false);
    
    let rungColor = 0x38bdf8;
    if (i % 4 === 1) rungColor = 0xf43f5e;
    else if (i % 4 === 2) rungColor = 0x10b981;
    else if (i % 4 === 3) rungColor = 0xf59e0b;

    const rMat = new THREE.MeshStandardMaterial({ color: rungColor, roughness: 0.3 });
    const rungMesh = new THREE.Mesh(tubeGeo, rMat);
    dnaGroup.add(rungMesh);
  }

  // Render Dual Backbones
  const curve1 = new THREE.CatmullRomCurve3(strand1Geo);
  const tube1 = new THREE.TubeGeometry(curve1, 100, 0.08, 12, false);
  const backbone1 = new THREE.Mesh(tube1, strandMat1);
  dnaGroup.add(backbone1);

  const curve2 = new THREE.CatmullRomCurve3(strand2Geo);
  const tube2 = new THREE.TubeGeometry(curve2, 100, 0.08, 12, false);
  const backbone2 = new THREE.Mesh(tube2, strandMat2);
  dnaGroup.add(backbone2);

  // Position DNA Helix on the right side of the screen
  dnaGroup.position.set(1.6, -0.2, 0);
  scene.add(dnaGroup);
}

/* ==========================================================================
   BUILD 3D DRUG LIGAND
   ========================================================================== */

function build3DDrugLigand() {
  drugLigandGroup = new THREE.Group();

  const coreGeo = new THREE.IcosahedronGeometry(0.35, 2);
  const coreMat = new THREE.MeshPhysicalMaterial({
    color: 0x2563eb,
    emissive: 0x1d4ed8,
    emissiveIntensity: 0.8,
    metalness: 0.4,
    roughness: 0.1,
    clearcoat: 1.0
  });
  const core = new THREE.Mesh(coreGeo, coreMat);
  drugLigandGroup.add(core);

  const atomMat = new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 0.8, roughness: 0.1 });
  const offsets = [
    new THREE.Vector3(0.38, 0.2, 0.0),
    new THREE.Vector3(-0.38, -0.2, 0.0),
    new THREE.Vector3(0.0, 0.38, 0.25),
    new THREE.Vector3(0.0, -0.38, -0.25)
  ];
  offsets.forEach(pt => {
    const s = new THREE.Mesh(new THREE.SphereGeometry(0.08, 16, 16), atomMat);
    s.position.copy(pt);
    drugLigandGroup.add(s);
  });

  drugLigandGroup.position.set(3.5, 0.2, 1.2);
  drugLigandGroup.visible = false;
  if (dnaGroup) dnaGroup.add(drugLigandGroup);
}

/* ==========================================================================
   ANIMATION LOOP
   ========================================================================== */

function animate() {
  requestAnimationFrame(animate);

  const delta = clock.getDelta();

  if (autoOrbit && dnaGroup) {
    dnaGroup.rotation.y += delta * 0.25;
  }

  targetCamX = mouseX * 0.35;
  targetCamY = mouseY * 0.35;
  if (dnaGroup) {
    dnaGroup.rotation.x = THREE.MathUtils.lerp(dnaGroup.rotation.x, targetCamY * 0.15, 0.05);
    dnaGroup.rotation.z = THREE.MathUtils.lerp(dnaGroup.rotation.z, targetCamX * 0.1, 0.05);
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
   INTERACTIVE SELECTION & DOCKING
   ========================================================================== */

function dockTherapeutic(key, evt) {
  currentDrugKey = key;
  const d = DRUG_DATA[key];
  if (!d) return;

  playAcousticTone(580, 0.1);

  if (evt && evt.currentTarget) {
    document.querySelectorAll('.shelf-card').forEach(c => c.classList.remove('active'));
    evt.currentTarget.classList.add('active');
  }

  document.getElementById('stat-energy').textContent = d.energy;
  document.getElementById('stat-kd').textContent = d.kd;
  document.getElementById('stat-res').textContent = d.res;
  document.getElementById('stat-conf').textContent = d.conf;

  triggerDockingAnimation();
}

function triggerDockingAnimation() {
  playAcousticTone(880, 0.2);
  if (!drugLigandGroup) return;

  drugLigandGroup.visible = true;

  let t = 0;
  const interval = setInterval(() => {
    t += 0.04;
    drugLigandGroup.position.x = THREE.MathUtils.lerp(3.5, 0.1, t);
    drugLigandGroup.position.z = THREE.MathUtils.lerp(1.2, 0.6, t);
    drugLigandGroup.rotation.y += 0.12;

    if (t >= 1) {
      clearInterval(interval);
      playAcousticTone(1040, 0.25);
    }
  }, 25);
}

function injectMutation() {
  playAcousticTone(340, 0.15);
  activeSequence[3] = 'T';
  activeSequence[4] = 'A';
  renderCodonStrip();
  build3DDNAHelix();

  document.getElementById('stat-energy').textContent = '-8.4 kcal/mol';
  document.getElementById('stat-conf').textContent = 'MUTATED (Pathogenic Delta)';
}

function restoreWildtype() {
  playAcousticTone(640, 0.1);
  activeSequence = ['A', 'T', 'G', 'C', 'C', 'G', 'T', 'A'];
  renderCodonStrip();
  build3DDNAHelix();

  const d = DRUG_DATA[currentDrugKey];
  if (d) {
    document.getElementById('stat-energy').textContent = d.energy;
    document.getElementById('stat-conf').textContent = d.conf;
  }
}

function toggleAutoOrbit() {
  autoOrbit = !autoOrbit;
  const btn = document.getElementById('orbit-btn');
  if (btn) btn.textContent = autoOrbit ? 'Pause Orbit' : 'Resume Orbit';
}

function resetPerspective() {
  camera.position.set(0.8, 0.2, 8.2);
  if (controls) controls.target.set(0, 0, 0);
  if (dnaGroup) dnaGroup.rotation.set(0, 0, 0);
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
  build3DDNAHelix();
}

/* ==========================================================================
   AUDIO SYNTHESIZER & UTILS
   ========================================================================== */

function playAcousticTone(freq, dur) {
  if (!isAudioActive) return;
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

function toggleAudio() {
  isAudioActive = !isAudioActive;
  const txt = document.getElementById('sound-txt');
  if (txt) txt.textContent = isAudioActive ? 'AUDIO: ON' : 'AUDIO: MUTED';
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
  alert('Clinical access inquiry received. Coordinate files dispatched to your institutional address.');
  closePortal();
}
