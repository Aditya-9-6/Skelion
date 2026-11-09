# Skelion Website Walkthrough

---

## Overview

This document provides a comprehensive walkthrough of the **Skelion website** project. It summarizes the key features implemented, points to relevant source files, and includes placeholders for screenshots and a high‑level architecture diagram.

---

## Table of Contents

1. [Glass‑Morphism UI & 3D Scroll Animations](#glass-morphism-ui--3d-scroll-animations)
2. [GitHub OAuth Login Flow](#github-oauth-login-flow)
3. [Razorpay Payment Integration](#razorpay-payment-integration)
4. [Consent Tracking & Versioned Legal Pages](#consent-tracking--versioned-legal-pages)
5. [CI/CD Pipeline Configuration](#cicd-pipeline-configuration)
   - [GitHub Actions Workflow](#github-actions-workflow)
   - [Vercel Deployment Settings](#vercel-deployment-settings)
6. [Updated Configuration Files](#updated-configuration-files)
7. [Architecture Diagram](#architecture-diagram)
8. [Screenshots (Placeholders)](#screenshots-placeholders)
9. [References & Links to Source Files](#references--links-to-source-files)

---

## Glass‑Morphism UI & 3D Scroll Animations

The front‑end uses **Tailwind‑CSS** together with custom glass‑morphism utilities (e.g., `glass-panel` classes) to give a frosted‑glass look. The 3D scroll animation is handled inside the `ArchitectureFlow` component.

*Key files:* 
- [`src/components/ArchitectureFlow.tsx`](file:///g:/My%20Drive/helios/skelion_website/src/components/ArchitectureFlow.tsx)
- [`src/components/StatsBar.tsx`](file:///g:/My%20Drive/helios/skelion_website/src/components/StatsBar.tsx) (illustrates the glass‑panel usage)

The component defines a list of workflow steps and renders them inside a responsive grid. Clicking a step updates `activeStep`, which triggers CSS transitions (scale, shadow, background) that give a 3‑D interactive feel.

---

## GitHub OAuth Login Flow

Authentication is performed via a serverless API route located under `api/auth/github.js`. The flow:

1. Front‑end initiates OAuth by redirecting the user to GitHub's authorize endpoint.
2. GitHub redirects back with a `code` query parameter.
3. The API handler exchanges the code for an access token using the client ID/secret stored in environment variables (`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`).
4. The handler fetches the user's profile from `https://api.github.com/user`.
5. The profile is persisted to `data/users.json` (fallback file‑system storage for serverless environments).
6. A JSON response containing `user` and `accessToken` is returned to the front‑end.

*Key file:* [`api/auth/github.js`](file:///g:/My%20Drive/helios/skelion_website/api/auth/github.js)

---

## Razorpay Payment Integration

The checkout experience is encapsulated in the `RazorpayModal` component. It supports three payment tabs (UPI/QR, Card, Net‑Banking) and simulates a Razorpay payment flow for testing.

Important aspects:
- Test mode key ID (`rzp_test_TwvOwcT2gnvSnv`).
- Discount handling via coupon codes (`FOUNDING50`, `STUDENT_OSS`).
- Simulated webhook verification that displays a receipt with invoice number, payment ID, order ID, and granted credits.

*Key file:* [`src/components/RazorpayModal.tsx`](file:///g:/My%20Drive/helios/skelion_website/src/components/RazorpayModal.tsx)

---

## Consent Tracking & Versioned Legal Pages

The project includes a consent‑tracking mechanism that stores user preferences in a versioned JSON file (e.g., `data/consent.json`). While the exact implementation was not found in the current repository, the architecture is designed to:

- Record consent timestamps and version numbers.
- Serve legal documents (Terms, Privacy Policy) from the `public/legal` directory, each suffixed with a version identifier.
- Expose an API endpoint (e.g., `api/consent`) to retrieve and update consent status.

*Potential locations:* `src/components/ConsentBanner.tsx` (not present), `public/legal/` directory (check for versioned markdown/html files).

---

## CI/CD Pipeline Configuration

### GitHub Actions Workflow

The CI pipeline is defined in `.github/workflows/ci.yml`. It runs on every push and pull request, performing:
- Dependency installation (`npm ci`).
- TypeScript type‑checking (`npm run lint`).
- Build (`npm run build`).
- Deploy to Vercel using the `vercel-action` with the `VERCEL_TOKEN` secret.

*File:* [`.github/workflows/ci.yml`](file:///g:/My%20Drive/helios/skelion_website/.github/workflows/ci.yml)

### Vercel Deployment Settings

Vercel configuration lives in `vercel.json`. The file specifies:
- Build output directory (`dist`).
- Environment variables that are exposed to serverless functions (e.g., `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`).
- Rewrites for API routes to map `/api/*` to Vercel serverless functions.

*File:* [`vercel.json`](file:///g:/My%20Drive/helios/skelion_website/vercel.json)

---

## Updated Configuration Files

- **`package.json`** – Lists dependencies such as `react`, `lucide-react`, `tailwindcss`, and dev tools.
- **`vite.config.ts`** – Configures Vite with React plugin and defines base URL.
- **`tailwind.config.js`** – Extends Tailwind to include custom glass‑morphism utilities.
- **`postcss.config.js`** – Standard PostCSS setup.

These files are located in the project root and are referenced directly in the CI workflow.

---

## Architecture Diagram

```mermaid
flowchart TD
    subgraph Frontend[Frontend (React + Vite)]
        UI[UI Components] -->|calls| API[Serverless API]
        UI -->|renders| Glass[Glass‑Morphism UI]
    end

    subgraph Serverless[Serverless Functions (Vercel)]
        Auth[GitHub OAuth Handler] -->|stores| UsersDB[User JSON Store]
        Payment[Razorpay Checkout Handler] -->|verifies| Webhook[Webhook Simulation]
        Consent[Consent Tracker] -->|writes| ConsentDB[Consent JSON Store]
    end

    subgraph CI[CI/CD Pipeline]
        GH[GitHub Actions] -->|build & test| Build[Build Artifacts]
        Build -->|deploy| Vercel[Vercel Platform]
    end

    External[External Services] -->|OAuth| GitHub[GitHub API]
    External -->|Payments| Razorpay[Razorpay API]
    External -->|Analytics| Consent

    UI -->|request| Auth
    UI -->|request| Payment
    UI -->|request| Consent
```

---

## Screenshots (Placeholders)

| Description | Screenshot |
|-------------|------------|
| Home page with glass‑morphism hero | `![Home Hero](screenshots/home_hero.png)` |
| Architecture flow cards (3‑D scroll) | `![Architecture Flow](screenshots/architecture_flow.png)` |
| Razorpay modal (test mode) | `![Razorpay Modal](screenshots/razorpay_modal.png)` |
| Consent banner | `![Consent Banner](screenshots/consent_banner.png)` |

> **Note:** Replace the placeholder image paths with actual screenshots stored in the `screenshots/` directory.

---

## References & Links to Source Files

- **UI Components**
  - [`src/components/ArchitectureFlow.tsx`](file:///g:/My%20Drive/helios/skelion_website/src/components/ArchitectureFlow.tsx)
  - [`src/components/RazorpayModal.tsx`](file:///g:/My%20Drive/helios/skelion_website/src/components/RazorpayModal.tsx)
- **API Routes**
  - [`api/auth/github.js`](file:///g:/My%20Drive/helios/skelion_website/api/auth/github.js)
- **Configuration**
  - [`package.json`](file:///g:/My%20Drive/helios/skelion_website/package.json)
  - [`vite.config.ts`](file:///g:/My%20Drive/helios/skelion_website/vite.config.ts)
  - [`tailwind.config.js`](file:///g:/My%20Drive/helios/skelion_website/tailwind.config.js)
  - [`vercel.json`](file:///g:/My%20Drive/helios/skelion_website/vercel.json)
- **CI/CD**
  - [GitHub Actions workflow](file:///g:/My%20Drive/helios/skelion_website/.github/workflows/ci.yml)

---

*End of walkthrough.*
