import React, { useState, useEffect } from 'react';
import { ThreeCanvas } from './components/ThreeCanvas';
import { Header } from './components/Header';
import { TrustHubOverview } from './components/TrustHubOverview';
import { LegalSection } from './components/LegalSection';
import { SearchModal } from './components/SearchModal';
import { Footer } from './components/Footer';
import { LEGAL_DOCUMENTS } from './types/legal';

export const App: React.FC = () => {
  const [activeSection, setActiveSection] = useState('overview');
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  // Set up IntersectionObserver to track which legal section is in view
  useEffect(() => {
    const sectionIds = ['overview', ...LEGAL_DOCUMENTS.map((d) => d.slug)];
    const observers: IntersectionObserver[] = [];

    sectionIds.forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              setActiveSection(id);
            }
          });
        },
        { threshold: 0.25 }
      );

      observer.observe(el);
      observers.push(observer);
    });

    return () => {
      observers.forEach((obs) => obs.disconnect());
    };
  }, []);

  // Global shortcut to open/close search modal (Ctrl+K or Cmd+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleScrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleSelectClause = (documentSlug: string, clauseId: string) => {
    const el = document.getElementById(`${documentSlug}-${clauseId}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Temporary highlight
      el.classList.add('ring-2', 'ring-cyan-400');
      setTimeout(() => {
        el.classList.remove('ring-2', 'ring-cyan-400');
      }, 2500);
    } else {
      handleScrollToSection(documentSlug);
    }
  };

  return (
    <div className="min-h-screen bg-[#050811] text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200 relative overflow-x-hidden">
      {/* 3D WebGL Canvas with Three.js & GSAP ScrollTrigger */}
      <ThreeCanvas />

      {/* Top Glassmorphic Navigation Header with Logo */}
      <Header
        onOpenSearch={() => setIsSearchOpen(true)}
        activeSection={activeSection}
      />

      {/* Main Content: Full-Screen Legal Sections with 3D Scroll Animations */}
      <main className="flex-1 relative z-10">
        <TrustHubOverview onScrollToSection={handleScrollToSection} />

        {LEGAL_DOCUMENTS.map((doc) => (
          <LegalSection key={doc.id} document={doc} />
        ))}
      </main>

      {/* Glassmorphic Footer */}
      <Footer />

      {/* Global Clause Search Modal */}
      <SearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onSelectClause={handleSelectClause}
      />
    </div>
  );
};

export default App;
