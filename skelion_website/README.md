# Skelion Official Website 🚀

The official production website for **Skelion** — Autonomous SaaS Incident Intelligence, Resilience Proxy & Self-Healing Dev Agent.

[![Build & Typecheck Website](https://github.com/Aditya-9-6/Skelion_website/actions/workflows/ci.yml/badge.svg)](https://github.com/Aditya-9-6/Skelion_website/actions/workflows/ci.yml)
[![Vercel Deployment](https://img.shields.io/badge/Deploy-Vercel-black?logo=vercel)](https://vercel.com)

---

## 🌟 Key Features

- **Interactive Incident Simulator**: Watch live playback of an edge incident being intercepted, sandboxed, reproduced, and synthesized into a self-healing GitHub PR.
- **Fail-Open Resilience Proxy Showcase**: Sub-5ms edge telemetry, automatic circuit breakers, and zero-drop reliability guarantees.
- **Multi-Provider LLM Key Pool**: Demonstrates transparent rotation across OpenAI, Claude 3.5 Sonnet, Gemini, Groq, and DeepSeek.
- **Autonomous Cloud Agent Console & Web Platform**: Live browser-based IDE workspace, fail-open resilience proxy, and automated incident self-healing.
- **Pocket-Friendly Pricing & Razorpay Checkout**: Configure payment credentials only through deployment environment variables.
- **CI / CD Ready**: Automated GitHub Actions workflow testing TypeScript types and verifying production builds.

---

## 🛠️ Tech Stack

- **Framework**: [React 18](https://react.dev/) + [Vite 5](https://vitejs.dev/) + [TypeScript](https://www.typescriptlang.org/)
- **Styling**: [Tailwind CSS 3](https://tailwindcss.com/) with Cyberpunk / Dark Mode aesthetic
- **Icons**: [Lucide React](https://lucide.dev/)
- **Target Platform**: [Vercel](https://vercel.com/) (Zero-config deployment with `vercel.json`)
- **CI/CD**: GitHub Actions (`.github/workflows/ci.yml`)

---

## 🚀 Local Development

```bash
# 1. Install dependencies
npm install

# 2. Run local dev server (port 3000)
npm run dev

# 3. Typecheck
npm run lint

# 4. Build for production
npm run build

# 5. Preview production build
npm run preview
```

---

## 🌐 Deploying to Vercel

1. Push your changes to `main` branch.
2. In Vercel, click **Add New Project** and import `https://github.com/Aditya-9-6/Skelion_website`.
3. Vercel automatically detects the Vite framework with output directory `dist`.
4. Click **Deploy**!

---

## 📄 License

Licensed under the Apache 2.0 / MIT License.
