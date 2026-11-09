import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { StatsBar } from './components/StatsBar';
import { Features } from './components/Features';
import { ArchitectureFlow } from './components/ArchitectureFlow';
import { WhyChooseUs } from './components/WhyChooseUs';
import { PricingCalculator } from './components/PricingCalculator';
import { Faq } from './components/Faq';
import { Footer } from './components/Footer';
import { RazorpayModal } from './components/RazorpayModal';
import { LegalUpdateBanner } from './components/LegalUpdateBanner';
import { TermsOfServicePage } from './components/legal/TermsOfServicePage';
import { PrivacyPolicyPage } from './components/legal/PrivacyPolicyPage';
import { CookiePolicyPage } from './components/legal/CookiePolicyPage';
import { SecurityPolicyPage } from './components/legal/SecurityPolicyPage';
import { Canvas3DScene } from './components/Canvas3DScene';
import { ConsoleWorkspace } from './components/console/ConsoleWorkspace';
import { ConsentGate } from './components/ConsentGate';
import { UserProfile, getStoredUser, logoutUser, simulateMockLogin, getGitHubLoginUrl } from './utils/auth';

export const App: React.FC = () => {
  return (
    <ConsentGate>
      {/* Original App content will be rendered inside ConsentGate */}
      <AppInner />
    </ConsentGate>
  );
};

// Separate component to hold original app logic
const AppInner: React.FC = () => {
  // ----- original App code starts here -----
  const [selectedPlanForCheckout, setSelectedPlanForCheckout] = useState<{
    planId: string;
    coupon?: string;
    currency?: 'INR' | 'USD';
    customAmount?: number;
    customCredits?: number;
  } | null>(null);

  const [currentRoute, setCurrentRoute] = useState<string>(window.location.hash || '#home');
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(getStoredUser());
  const [viewLandingPageOverride, setViewLandingPageOverride] = useState<boolean>(false);

  useEffect(() => {
    const handleHashChange = () => {
      const rawHash = window.location.hash || '#home';
      const cleanAnchor = rawHash.startsWith('#') ? rawHash.slice(1) : rawHash;
      setCurrentRoute(rawHash);
      const user = getStoredUser();
      setCurrentUser(user);

      const landingAnchors = ['home', 'features', 'simulator', 'architecture', 'pricing', 'docs', 'faq', 'why-us', 'comparison'];
      const isLandingAnchor = landingAnchors.includes(cleanAnchor);

      if (rawHash === '#landing' || isLandingAnchor) {
        setViewLandingPageOverride(true);
        if (isLandingAnchor) {
          setTimeout(() => {
            const el = document.getElementById(cleanAnchor);
            if (el) {
              el.scrollIntoView({ behavior: 'smooth' });
            }
          }, 60);
          return;
        }
      } else if (
        rawHash === '#console' ||
        rawHash === '#dashboard' ||
        rawHash === '#ask' ||
        rawHash === '#incidents' ||
        rawHash === '#fixes' ||
        rawHash === '#history' ||
        rawHash === '#limits' ||
        rawHash === '#loop' ||
        rawHash === '#plugins'
      ) {
        setViewLandingPageOverride(false);
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleOpenCheckout = (
    planId: string = 'pro',
    coupon?: string,
    currency: 'INR' | 'USD' = 'INR',
    customData?: { customAmount: number; customCredits: number }
  ) => {
    setSelectedPlanForCheckout({
      planId,
      coupon,
      currency,
      customAmount: customData?.customAmount,
      customCredits: customData?.customCredits,
    });
  };

  const handleCloseCheckout = () => {
    setSelectedPlanForCheckout(null);
  };

  const handleLogin = async () => {
    try {
      const loginUrl = await getGitHubLoginUrl();
      window.location.href = loginUrl;
    } catch (_e: any) {
      window.dispatchEvent(new CustomEvent('skelion:open-oauth-modal'));
    }
  };

  const handleLogout = () => {
    logoutUser();
    setCurrentUser(null);
    setViewLandingPageOverride(false);
    window.location.hash = '#home';
  };

  const handleToggleLandingPage = () => {
    setViewLandingPageOverride(true);
    window.location.hash = '#landing';
  };

  const handleBackToConsole = () => {
    setViewLandingPageOverride(false);
    window.location.hash = '#console';
  };

  const renderContent = () => {
    // Priority 1: Legal policy pages
    if (currentRoute === '#terms') {
      return <TermsOfServicePage />;
    }
    if (currentRoute === '#privacy') {
      return <PrivacyPolicyPage />;
    }
    if (currentRoute === '#cookie') {
      return <CookiePolicyPage />;
    }
    if (currentRoute === '#security') {
      return <SecurityPolicyPage />;
    }

    // Priority 2: When logged in, default view is the Skelion Web Platform (ConsoleWorkspace)
    // unless user explicitly requested to view the public landing page.
    const isExplicitLandingRoute = currentRoute === '#landing';
    const isExplicitConsoleRoute = 
      currentRoute === '#console' || 
      currentRoute === '#dashboard' ||
      currentRoute === '#ask' ||
      currentRoute === '#incidents' ||
      currentRoute === '#fixes' ||
      currentRoute === '#history' ||
      currentRoute === '#limits' ||
      currentRoute === '#loop' ||
      currentRoute === '#plugins';

    if (currentUser && !viewLandingPageOverride && !isExplicitLandingRoute) {
      return (
        <main className="flex-1 relative z-10">
          <ConsoleWorkspace
            user={currentUser}
            onLogout={handleLogout}
            onOpenCheckout={(plan, coupon, currency) => handleOpenCheckout(plan, coupon, currency)}
            onViewLandingPage={handleToggleLandingPage}
          />
        </main>
      );
    }

    // If an unauthenticated user navigates directly to #console or #dashboard, provide effective demo user
    if (isExplicitConsoleRoute) {
      const effectiveUser: UserProfile = currentUser || {
        id: 999999,
        username: 'skelion-developer',
        name: 'Skelion Developer',
        avatar: 'https://avatars.githubusercontent.com/u/999999?v=4',
        email: 'developer@skelion.ai',
        bio: 'Skelion Autonomous Incident Intelligence & Resilience Engineer',
        html_url: 'https://github.com/skelion-developer',
        updatedAt: new Date().toISOString(),
      };

      return (
        <main className="flex-1 relative z-10">
          <ConsoleWorkspace
            user={effectiveUser}
            isGuest={!currentUser}
            onLogout={handleLogout}
            onOpenCheckout={(plan, coupon, currency) => handleOpenCheckout(plan, coupon, currency)}
            onViewLandingPage={handleToggleLandingPage}
          />
        </main>
      );
    }

    // Default Public Landing Page
    return (
      <main className="flex-1 relative z-10">
        {currentUser && (
          <div className="bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-600 text-white px-4 py-2.5 text-center text-xs font-semibold shadow-md flex items-center justify-center gap-2">
            <span>You are viewing the public landing page preview as <strong>{currentUser.name || currentUser.username}</strong>.</span>
            <button
              onClick={handleBackToConsole}
              className="bg-white text-slate-900 px-3 py-1 rounded-lg text-xs font-bold hover:bg-slate-100 transition shadow-xs"
            >
              Back to Web Platform →
            </button>
          </div>
        )}
        <Hero onOpenCheckout={handleOpenCheckout} />
        <StatsBar />
        <Features />
        <ArchitectureFlow />
        <WhyChooseUs />
        <PricingCalculator onSelectPlan={(plan, coupon, currency) => handleOpenCheckout(plan, coupon, currency)} />
        <Faq />
      </main>
    );
  };

  return (
    <div className="min-h-screen bg-[#FAFCFF] text-slate-900 flex flex-col font-sans relative selection:bg-cyan-500/20 selection:text-cyan-900">
      {/* 3D Scrolling Canvas & Floating Cyber Polyhedra Scene */}
      <Canvas3DScene />

      <div className="relative z-20">
        <LegalUpdateBanner />
        <Navbar
          onOpenCheckout={handleOpenCheckout}
          currentUser={currentUser}
          onUserChange={(u) => setCurrentUser(u)}
          onLogout={handleLogout}
        />
      </div>

      {renderContent()}

      <div className="relative z-10">
        <Footer />
      </div>

      {selectedPlanForCheckout && (
        <RazorpayModal
          planId={selectedPlanForCheckout.planId}
          couponCode={selectedPlanForCheckout.coupon}
          currency={selectedPlanForCheckout.currency}
          customAmount={selectedPlanForCheckout.customAmount}
          customCredits={selectedPlanForCheckout.customCredits}
          user={currentUser || undefined}
          onClose={handleCloseCheckout}
        />
      )}
    </div>
  );
};

export default App;
