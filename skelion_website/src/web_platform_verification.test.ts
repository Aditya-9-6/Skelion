// src/web_platform_verification.test.ts
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe('Web Platform & Enterprise Pricing Verification', () => {
  it('formats Enterprise Custom plan price with + sign across currencies and discounts', () => {
    const formatPrice = (planId: string, currency: 'INR' | 'USD', baseINR: number, baseUSD: number, discountPercent: number = 0) => {
      const isUSD = currency === 'USD';
      const baseMonthly = isUSD ? baseUSD : baseINR;
      let finalPrice = baseMonthly;
      if (discountPercent > 0) {
        finalPrice = Math.round(baseMonthly * (1 - discountPercent / 100));
      }
      const currencySymbol = isUSD ? '$' : '₹';
      const formatted = finalPrice === 0 
        ? 'Free' 
        : `${planId === 'enterprise' ? '+' : ''}${currencySymbol}${finalPrice.toLocaleString('en-IN')}`;
      return formatted;
    };

    // 1. Base Enterprise Monthly INR
    assert.equal(formatPrice('enterprise', 'INR', 39999, 499, 0), '+₹39,999');

    // 2. Base Enterprise Monthly USD
    assert.equal(formatPrice('enterprise', 'USD', 39999, 499, 0), '+$499');

    // 3. Discounted Enterprise with 30% off (FOUNDING50 coupon)
    assert.equal(formatPrice('enterprise', 'INR', 39999, 499, 30), '+₹27,999');
    assert.equal(formatPrice('enterprise', 'USD', 39999, 499, 30), '+$349');

    // 4. Other plans do NOT get a + sign
    assert.equal(formatPrice('pro', 'INR', 1349, 16, 0), '₹1,349');
    assert.equal(formatPrice('pro', 'USD', 1349, 16, 0), '$16');
  });

  it('ensures PricingCalculator.tsx places + sign before enterprise plan price', () => {
    const pricingCalcPath = path.resolve(__dirname, 'components/PricingCalculator.tsx');
    const content = fs.readFileSync(pricingCalcPath, 'utf-8');

    assert.ok(
      content.includes("${plan.id === 'enterprise' ? '+' : ''}${currencySymbol}"),
      'PricingCalculator must place + sign before currency symbol for enterprise'
    );
  });

  it('ensures RazorpayModal.tsx places + sign before enterprise plan total due and Pay button', () => {
    const modalPath = path.resolve(__dirname, 'components/RazorpayModal.tsx');
    const content = fs.readFileSync(modalPath, 'utf-8');

    assert.ok(
      content.includes("{planId === 'enterprise' ? '+' : ''}{currencySymbol}{finalAmount.toLocaleString('en-IN')}"),
      'RazorpayModal must place + sign before currency symbol for enterprise plan total due'
    );

    assert.ok(
      content.includes("Pay {planId === 'enterprise' ? '+' : ''}{currencySymbol}{finalAmount.toLocaleString('en-IN')} with Razorpay"),
      'RazorpayModal Pay button must include + sign for enterprise plan'
    );
  });

  it('ensures Dashboard.tsx includes + sign in enterprise pricing callout', () => {
    const dashPath = path.resolve(__dirname, 'components/Dashboard.tsx');
    const content = fs.readFileSync(dashPath, 'utf-8');

    assert.ok(
      content.includes('+₹39,999/mo'),
      'Dashboard must place + sign before enterprise plan cost'
    );
  });

  it('verifies ConsoleWorkspace.tsx includes Dashboard tab and renders <Dashboard', () => {
    const consolePath = path.resolve(__dirname, 'components/console/ConsoleWorkspace.tsx');
    const content = fs.readFileSync(consolePath, 'utf-8');

    assert.ok(content.includes("id: 'dashboard', label: 'Dashboard'"), 'ConsoleWorkspace tabItems must include Dashboard');
    assert.ok(content.includes("activeTab === 'dashboard'"), 'ConsoleWorkspace must conditionally render Dashboard panel');
    assert.ok(content.includes('<Dashboard'), 'ConsoleWorkspace must instantiate Dashboard component');
    assert.ok(content.includes("if (raw === 'dashboard') return 'dashboard';"), 'ConsoleWorkspace hash parser must recognize #dashboard');
  });

  it('verifies Navbar.tsx hides marketing links and shows console links when user is authenticated', () => {
    const navbarPath = path.resolve(__dirname, 'components/Navbar.tsx');
    const content = fs.readFileSync(navbarPath, 'utf-8');

    // Check desktop conditional rendering
    assert.ok(
      content.includes('!user ? (') && content.includes('href="#features"'),
      'Desktop marketing links must be gated by !user'
    );

    // Check desktop console navigation links when logged in
    assert.ok(content.includes('href="#dashboard"'), 'Desktop nav must provide #dashboard link when user is logged in');
    assert.ok(content.includes('href="#ask"'), 'Desktop nav must provide #ask link when user is logged in');
    assert.ok(content.includes('href="#incidents"'), 'Desktop nav must provide #incidents link when user is logged in');
    assert.ok(content.includes('href="#fixes"'), 'Desktop nav must provide #fixes link when user is logged in');
    assert.ok(content.includes('href="#limits"'), 'Desktop nav must provide #limits link when user is logged in');

    // Check mobile conditional rendering
    assert.ok(
      content.includes('user ? (') && content.includes('Web Platform Console'),
      'Mobile menu must render console navigation when user is logged in'
    );

    // Ensure announcement banner does not mention native VS Code extension
    assert.ok(
      !content.includes('Native VS Code Extension'),
      'Navbar announcement banner must not mention Native VS Code Extension'
    );

    // Ensure no marketplace.visualstudio.com links
    assert.ok(
      !content.includes('marketplace.visualstudio.com'),
      'Navbar must not contain VS Code marketplace links'
    );
  });

  it('verifies Hero.tsx and Footer.tsx have no VS Code marketplace links or extension install buttons', () => {
    const heroPath = path.resolve(__dirname, 'components/Hero.tsx');
    const heroContent = fs.readFileSync(heroPath, 'utf-8');

    assert.ok(!heroContent.includes('Install VS Code Extension'), 'Hero must not have Install VS Code Extension button');
    assert.ok(!heroContent.includes('marketplace.visualstudio.com'), 'Hero must not link to VS Code marketplace');
    assert.ok(heroContent.includes('Launch Web Console'), 'Hero must feature Launch Web Console button');

    const footerPath = path.resolve(__dirname, 'components/Footer.tsx');
    const footerContent = fs.readFileSync(footerPath, 'utf-8');

    assert.ok(!footerContent.includes('VS Code Extension'), 'Footer must not have VS Code Extension link');
    assert.ok(!footerContent.includes('marketplace.visualstudio.com'), 'Footer must not link to VS Code marketplace');
    assert.ok(footerContent.includes('Cloud Agent Console'), 'Footer must link to Cloud Agent Console');
  });

  it('verifies Features, Faq, and ExtensionShowcase rebrand cleanly as Web Platform', () => {
    const featuresPath = path.resolve(__dirname, 'components/Features.tsx');
    const featuresContent = fs.readFileSync(featuresPath, 'utf-8');
    assert.ok(!featuresContent.includes('code --install-extension'), 'Features must not contain code --install-extension');
    assert.ok(featuresContent.includes('Cloud Agent Console'), 'Features must feature Cloud Agent Console');

    const faqPath = path.resolve(__dirname, 'components/Faq.tsx');
    const faqContent = fs.readFileSync(faqPath, 'utf-8');
    assert.ok(!faqContent.includes('VS Code extension synchronize'), 'FAQ must not ask about VS Code extension sync');
    assert.ok(faqContent.includes('Web Platform synchronize'), 'FAQ must discuss Web Platform synchronization');

    const showcasePath = path.resolve(__dirname, 'components/ExtensionShowcase.tsx');
    const showcaseContent = fs.readFileSync(showcasePath, 'utf-8');
    assert.ok(!showcaseContent.includes('OFFICIAL VS CODE EXTENSION'), 'Showcase must not claim Official VS Code Extension');
    assert.ok(!showcaseContent.includes('marketplace.visualstudio.com'), 'Showcase must not link to VS Code marketplace');
    assert.ok(showcaseContent.includes('CLOUD AGENT WEB PLATFORM'), 'Showcase must feature Cloud Agent Web Platform');
  });

  it('verifies legal pages reference web platform and cloud agent console', () => {
    const tosPath = path.resolve(__dirname, 'components/legal/TermsOfServicePage.tsx');
    const tosContent = fs.readFileSync(tosPath, 'utf-8');
    assert.ok(!tosContent.includes('VS Code extension'), 'TermsOfServicePage must not mention VS Code extension');
    assert.ok(tosContent.includes('web platform'), 'TermsOfServicePage must mention web platform');

    const privacyPath = path.resolve(__dirname, 'components/legal/PrivacyPolicyPage.tsx');
    const privacyContent = fs.readFileSync(privacyPath, 'utf-8');
    assert.ok(!privacyContent.includes('VS Code extension'), 'PrivacyPolicyPage must not mention VS Code extension');

    const secPath = path.resolve(__dirname, 'components/legal/SecurityPolicyPage.tsx');
    const secContent = fs.readFileSync(secPath, 'utf-8');
    assert.ok(!secContent.includes('VS Code extension'), 'SecurityPolicyPage must not mention VS Code extension');
  });

  it('verifies zero vscode selectors in skeleton.css and zero VS Code badges in README.md', () => {
    const skeletonPath = path.resolve(__dirname, '../public/skeleton.css');
    const skeletonContent = fs.readFileSync(skeletonPath, 'utf-8');
    assert.ok(!skeletonContent.includes('body.vscode-'), 'skeleton.css must not contain body.vscode- selectors');
    assert.ok(!skeletonContent.includes('--vscode-'), 'skeleton.css must not contain --vscode- variables');

    const readmePath = path.resolve(__dirname, '../README.md');
    const readmeContent = fs.readFileSync(readmePath, 'utf-8');
    assert.ok(!readmeContent.includes('VS Code Marketplace'), 'README.md must not contain VS Code Marketplace badge');
  });
});
