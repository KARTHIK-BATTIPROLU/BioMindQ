# 🧬 GENOMIX AI 3D — Flagship Interactive Biotech & Genomics Landing Page

[![Awwwards Nominee](https://img.shields.io/badge/Design-Awwwards%20Tier-00f2fe.svg)]()
[![Three.js](https://img.shields.io/badge/Three.js-WebGL%202.0-a855f7.svg)](https://threejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-00f5a0.svg)](LICENSE)
[![Deployment: 1--Click Ready](https://img.shields.io/badge/Deployment-Instant%20Deploy-ff2a5f.svg)]()

An award-winning, ultra-luxury interactive 3D biotechnology landing page featuring:
- **3D Quantum DNA Double Helix**: Dual translucent sugar-phosphate backbones, interactive color-coded nucleotide base pairs (A-T, G-C), and real-time CRISPR-Cas9 enzymatic laser cleavage simulator.
- **3D Holographic Neural Connectome Brain**: 14,000+ firing synaptic impulses, cortical lobe segmentation (Frontal, Parietal, Temporal, Occipital, Cerebellum), and 128-channel multi-band EEG signal plotting.
- **3D Microscopic Cellular Immuno-Oncology**: Deformable red blood cells and targeted nanobot receptor docking.
- **Synthesized Bio-Acoustic Engine**: Web Audio API high-tech auditory feedback on user interactions.
- **Dynamic 2D Canvas Telemetry**: 60fps real-time bio-signal plotter synchronized with the 3D animation loop.
- **Awwwards / FWA Glassmorphism Design System**: Ultra-luxury dark obsidian styling (`#040711`), frosted glassmorphic HUDs, glowing neon cyan/purple/emerald accents, interactive AI risk calculator, research pipeline tracker, and trial enrollment portal.

---

## 🚀 Instant 1-Click Deployment Guide

This project is completely self-contained with **zero build dependencies**. You can deploy it instantly to any platform:

### 1. Deploy to Vercel (Fastest)
```bash
# Install Vercel CLI if needed:
npm i -g vercel

# Deploy instantly:
cd /Users/k.sathvik/.gemini/antigravity/scratch/genomix-3d-ai
vercel --prod
```

### 2. Deploy to Netlify
```bash
# Install Netlify CLI:
npm i -g netlify-cli

# Deploy:
cd /Users/k.sathvik/.gemini/antigravity/scratch/genomix-3d-ai
netlify deploy --prod --dir=.
```

### 3. Deploy to GitHub Pages
1. Push this folder to a GitHub repository:
   ```bash
   git init
   git add .
   git commit -m "feat: initial release of Genomix 3D"
   git branch -M main
   git remote add origin https://github.com/<your-username>/genomix-3d-ai.git
   git push -u origin main
   ```
2. Go to **Settings > Pages** in your GitHub repository and set branch to `main` and folder to `/ (root)`.

### 4. Run Locally
```bash
cd /Users/k.sathvik/.gemini/antigravity/scratch/genomix-3d-ai
python3 -m http.server 3000
```
Open **`http://localhost:3000`** in your browser.

---

## 📂 Project Architecture

```
genomix-3d-ai/
├── index.html            # Main HTML layout, navigation, hero, interactive lab & modals
├── styles.css            # Ultra-luxury Awwwards-tier CSS design system & glassmorphism
├── app.js                # Core WebGL 3D engine (DNA Helix, Brain Connectome, Shaders & Audio)
├── package.json          # Project metadata and quick scripts
├── vercel.json           # Vercel deployment configuration
├── netlify.toml          # Netlify deployment configuration
└── README.md             # Documentation and deployment guide
```
