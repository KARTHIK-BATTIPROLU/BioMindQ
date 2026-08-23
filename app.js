/**
 * BIOMINDQ // LANDING PAGE V2 3D SCROLL & CHATBOT ENGINE
 */

// Master Chatbot Console URL Constant pointing to BioMindQ backend
const CHATBOT_URL = "http://localhost:3001"; 

let scene, camera, renderer, controls;
let autoOrbit = true;
let clock = new THREE.Clock();

// Master 3D DNA Object
let dnaGroup;

// Scroll Animation State
let targetScrollProgress = 0;
let currentScrollProgress = 0;

// Mouse Parallax
let mouseX = 0, mouseY = 0;
let targetCamX = 0, targetCamY = 0;

document.addEventListener('DOMContentLoaded', () => {
  // Bind all CTA chatbot links to CHATBOT_URL
  bindChatbotLinks();

  initEngine();
  animate();

  window.addEventListener('resize', onResize);
  document.addEventListener('mousemove', onMouseMove);
  window.addEventListener('scroll', onScroll);

  // Touchpad & Mouse Wheel listener:
  // Scroll DOWN (deltaY > 0) -> Zoom IN, Shift to Right, Blur DNA background
  // Scroll UP (deltaY < 0) -> Zoom OUT, Center DNA, Unblur DNA
  window.addEventListener('wheel', (e) => {
    if (e.deltaY > 0) {
      targetScrollProgress = Math.min(1, targetScrollProgress + 0.2);
    } else if (e.deltaY < 0) {
      targetScrollProgress = Math.max(0, targetScrollProgress - 0.2);
    }
  }, { passive: true });

  // Initial scroll calculation
  onScroll();
});

function bindChatbotLinks() {
  document.querySelectorAll('.cta-chatbot-link').forEach(link => {
    link.href = CHATBOT_URL;
  });
}

function initEngine() {
  const container = document.getElementById('canvas-stage');
  if (!container) return;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf8fafc);
  scene.fog = new THREE.FogExp2(0xf8fafc, 0.04);

  camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(0, 0.2, 8.2);

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

  // Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 1.2);
  scene.add(ambientLight);

  const dirLight1 = new THREE.DirectionalLight(0x2563eb, 1.5);
  dirLight1.position.set(5, 10, 7);
  scene.add(dirLight1);

  const dirLight2 = new THREE.DirectionalLight(0xf43f5e, 1.2);
  dirLight2.position.set(-5, -5, -5);
  scene.add(dirLight2);

  build3DDNAHelix();
}

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

    // Helical Joints
    const joint1 = new THREE.Mesh(sphereGeo, strandMat1);
    joint1.position.copy(p1);
    dnaGroup.add(joint1);

    const joint2 = new THREE.Mesh(sphereGeo, strandMat2);
    joint2.position.copy(p2);
    dnaGroup.add(joint2);

    // Nucleotide Connecting Rungs
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

  // Dual Backbones
  const curve1 = new THREE.CatmullRomCurve3(strand1Geo);
  const tube1 = new THREE.TubeGeometry(curve1, 100, 0.08, 12, false);
  const backbone1 = new THREE.Mesh(tube1, strandMat1);
  dnaGroup.add(backbone1);

  const curve2 = new THREE.CatmullRomCurve3(strand2Geo);
  const tube2 = new THREE.TubeGeometry(curve2, 100, 0.08, 12, false);
  const backbone2 = new THREE.Mesh(tube2, strandMat2);
  dnaGroup.add(backbone2);

  // Initial State: Centered & Smaller
  dnaGroup.position.set(0.0, -0.2, 0);
  dnaGroup.scale.set(0.65, 0.65, 0.65);
  scene.add(dnaGroup);
}

function onScroll() {
  const scrollThreshold = window.innerHeight * 0.4;
  if (scrollThreshold > 0) {
    targetScrollProgress = Math.min(1, Math.max(0, window.scrollY / scrollThreshold));
  }
}

function animate() {
  requestAnimationFrame(animate);

  const delta = clock.getDelta();

  // Smooth lerp for scroll animation
  currentScrollProgress += (targetScrollProgress - currentScrollProgress) * 0.08;

  if (dnaGroup) {
    // Transition position.x: centered (0.0) -> far right side (3.2) when scrolling DOWN
    const targetX = window.innerWidth < 768 ? 1.0 : 3.2;
    dnaGroup.position.x = THREE.MathUtils.lerp(0.0, targetX, currentScrollProgress);
    
    // Transition scale: smaller (0.65) -> full close-up zoom (2.7) when scrolling DOWN
    const scale = THREE.MathUtils.lerp(0.65, 2.7, currentScrollProgress);
    dnaGroup.scale.set(scale, scale, scale);

    // Continuous 3D rotation around Y axis
    if (autoOrbit) {
      dnaGroup.rotation.y += delta * 0.25;
    }

    // Mouse Parallax tilt effect
    targetCamX = mouseX * 0.35;
    targetCamY = mouseY * 0.35;
    dnaGroup.rotation.x = THREE.MathUtils.lerp(dnaGroup.rotation.x, targetCamY * 0.15, 0.05);
    dnaGroup.rotation.z = THREE.MathUtils.lerp(dnaGroup.rotation.z, targetCamX * 0.1, 0.05);
  }

  // Smoothly blur background canvas as DNA shifts to the right side
  const canvasStage = document.getElementById('canvas-stage');
  if (canvasStage) {
    const blurPx = THREE.MathUtils.lerp(0, 10, currentScrollProgress);
    const canvasOpacity = THREE.MathUtils.lerp(1.0, 0.55, currentScrollProgress);
    canvasStage.style.filter = `blur(${blurPx}px)`;
    canvasStage.style.opacity = canvasOpacity;
  }

  // BioMindQ Title: Enlarge smoothly when scrolling DOWN
  const brandTitle = document.getElementById('brand-title');
  if (brandTitle) {
    const titleScale = THREE.MathUtils.lerp(1.0, 1.4, currentScrollProgress);
    brandTitle.style.transform = `scale(${titleScale})`;
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
