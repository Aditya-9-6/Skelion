# UI Skeleton & Animation Recommendations for Skelion VS Code Extension

This document outlines lightweight skeleton placeholders and subtle CSS animations that can be injected while panel data is loading. The goal is to improve perceived performance and give developers a familiar “shimmer” experience similar to YouTube, Facebook, or other modern web apps.

---

## Common CSS (add to `media/skeleton.css` or inline in the panel HTML)
```css
/* Skeleton base */
.skeleton {
  background-color: var(--vscode-editorWidget-background, #2c2c2c);
  background-image: linear-gradient(
    90deg,
    rgba(255,255,255,0.05) 0%,
    rgba(255,255,255,0.15) 50%,
    rgba(255,255,255,0.05) 100%
  );
  background-size: 200% 100%;
  animation: skeleton-pulse 1.2s ease-in-out infinite;
  border-radius: 4px;
}

@keyframes skeleton-pulse {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Text line placeholder */
.skeleton-text {
  height: 0.9rem;
  margin: 0.4rem 0;
}

/* Card placeholder (e.g., chat message, incident item) */
.skeleton-card {
  padding: 0.8rem;
  margin-bottom: 0.6rem;
}
```

---

## Panel‑Specific Recommendations

### 1. **Auth Panel**
- **Skeleton element:** Centered rectangular stub for the sign‑in button and a couple of lines for the title/description.
- **HTML snippet:**
```html
<div class="skeleton-card">
  <div class="skeleton skeleton-text" style="width: 60%;"></div>
  <div class="skeleton skeleton-text" style="width: 80%;"></div>
  <div class="skeleton" style="width: 120px; height: 36px; margin-top: 1rem;"></div>
</div>
```
- **When to replace:** After the OAuth flow is ready or when the panel determines the user is already authenticated.

### 2. **Limits Panel**
- **Skeleton element:** Grid of 3‑4 metric cards (quota, usage, reset time).
- **HTML snippet:**
```html
<div class="skeleton-grid" style="display: flex; gap: 0.8rem;">
  <div class="skeleton-card" style="flex:1; height: 80px;"></div>
  <div class="skeleton-card" style="flex:1; height: 80px;"></div>
  <div class="skeleton-card" style="flex:1; height: 80px;"></div>
</div>
```
- **Animation:** Same pulse defined globally.

### 3. **Chat Panel**
- **Skeleton element:** List of message bubbles with gray bars.
- **HTML snippet:**
```html
<div class="skeleton-chat">
  <div class="skeleton-card" style="width: 70%; height: 1.2rem;"></div>
  <div class="skeleton-card" style="width: 55%; height: 1.2rem; margin-left:auto;"></div>
  <div class="skeleton-card" style="width: 65%; height: 1.2rem;"></div>
</div>
```
- **Tip:** Add a tiny fade‑in when real messages appear to keep the motion smooth.

### 4. **Incidents Panel**
- **Skeleton element:** Table‑like rows – icon placeholder + two text lines.
- **HTML snippet:**
```html
<div class="skeleton-incident" style="display:flex; gap:0.6rem; align-items:center;">
  <div class="skeleton" style="width:24px; height:24px;"></div>
  <div class="skeleton-text" style="width:40%;"></div>
  <div class="skeleton-text" style="width:30%;"></div>
</div>
```
- **Repeat** this block 5‑6 times while fetching the incident list.

### 5. **Autofix Panel**
- **Skeleton element:** Vertical list of suggestion cards.
- **HTML snippet:**
```html
<div class="skeleton-autofix" style="display:flex; flex-direction:column; gap:0.8rem;">
  <div class="skeleton-card" style="height:70px;"></div>
  <div class="skeleton-card" style="height:70px;"></div>
  <div class="skeleton-card" style="height:70px;"></div>
</div>
```
- **Replace** each card with the real suggestion once the analysis finishes.

### 6. **History Panel**
- **Skeleton element:** Timeline entries – small circle + line of text.
- **HTML snippet:**
```html
<div class="skeleton-history" style="display:flex; gap:0.8rem; align-items:center;">
  <div class="skeleton" style="width:12px; height:12px; border-radius:50%;"></div>
  <div class="skeleton-text" style="width:70%;"></div>
</div>
```
- **Loop** for ~8 entries.

### 7. **Autonomous Panel**
- **Skeleton element:** Large card showing “agent initializing…” with a spinner.
- **HTML snippet:**
```html
<div class="skeleton-autonomous" style="text-align:center; padding:2rem;">
  <div class="skeleton" style="width:80px; height:80px; margin:auto; border-radius:50%;"></div>
  <div class="skeleton-text" style="width:40%; margin-top:1rem; margin:auto;"></div>
</div>
```
- Use VS Code’s native loading spinner if you prefer (`$(loading~spin)`), otherwise the pulse works.

### 8. **Plugins Panel**
- **Skeleton element:** Grid of plugin tiles (icon + title).
- **HTML snippet:**
```html
<div class="skeleton-plugins" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(120px,1fr)); gap:0.8rem;">
  <div class="skeleton-card" style="height:100px;" ></div>
  <div class="skeleton-card" style="height:100px;" ></div>
  <div class="skeleton-card" style="height:100px;" ></div>
</div>
```
- Replace each tile with the real plugin card when the list is fetched.

### 9. **Billing Panel**
- **Skeleton element:** Summary sections – total, plan cards, usage chart placeholder.
- **HTML snippet:**
```html
<div class="skeleton-billing" style="display:flex; flex-direction:column; gap:1rem;">
  <div class="skeleton-card" style="height:40px; width:30%;"></div>
  <div class="skeleton-card" style="height:120px; width:100%;"></div>
  <div class="skeleton" style="height:150px; width:100%;"></div> <!-- chart placeholder -->
</div>
```
- Show the real chart once the billing API returns data.

---

## Integration Tips
1. **Inject early** – Call the skeleton rendering function before any asynchronous request begins (e.g., in `renderLimitsUI()` before `fetchLimits()`).
2. **Replace in‑place** – When the real payload arrives, replace the skeleton container’s `innerHTML` with the actual markup; keep the same element ID so CSS transitions stay smooth.
3. **Avoid extra dependencies** – The CSS above uses only built‑in VS Code theme variables, so it works for both light and dark themes without extra NPM packages.
4. **Performance** – Skeletons are simple `<div>` elements; they cost virtually nothing to render and disappear instantly on data receipt.
5. **Accessibility** – Add `aria-busy="true"` to the panel while the skeleton is visible and switch to `false` after content loads.

---

## References & Inspirations
- **YouTube loading cards:** https://www.youtube.com/watch?v=KcG1R9JgLZc (search “YouTube shimmer UI”) 
- **Facebook “shimmer” placeholders:** https://developers.facebook.com/docs/design-system
- **Tailwind CSS loading skeleton:** https://tailwindcss.com/docs/animation#skeleton-loading (useful for class naming ideas)
- **VS Code Webview best practices:** https://code.visualstudio.com/api/extension-guides/webview

---

*Add the above CSS to a dedicated stylesheet (`media/skeleton.css`) and import it in each panel’s HTML (`<link rel="stylesheet" href="media/skeleton.css">`). The snippets can be copied directly into the panel’s rendering functions.*
