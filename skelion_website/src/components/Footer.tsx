import React from 'react';
import { ExternalLink } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-white/85 backdrop-blur-xl border-t border-slate-200/90 py-16 text-slate-600 text-xs shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-10 mb-12">
          {/* Brand Col */}
          <div className="md:col-span-2 space-y-4">
            <div className="flex items-center gap-3">
              <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-cyan-400 to-purple-500 rounded-lg blur opacity-25 group-hover:opacity-60 transition duration-300"></div>
                <img
                  src="/icon.svg"
                  alt="Skelion"
                  className="relative w-8 h-8 rounded-lg bg-white p-1 border border-slate-200/90 shadow-sm object-contain"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = '/icon.png';
                  }}
                />
              </div>
              <span className="text-xl font-bold tracking-tight text-slate-950">SKELION</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-cyan-50 text-cyan-700 border border-cyan-200 font-mono">
                v0.1.4
              </span>
            </div>
            <p className="text-slate-600 text-xs leading-relaxed max-w-sm">
              Autonomous SaaS incident intelligence, fail-open resilience proxy, and self-healing
              AI developer agent. Built for engineering teams demanding zero-downtime reliability.
            </p>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 font-mono text-[11px]">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Edge Telemetry & Key-Pool Operational</span>
            </div>
          </div>

          {/* Product Links */}
          <div className="space-y-3">
            <span className="text-slate-900 font-bold uppercase tracking-wider text-[11px] font-mono block">
              Product & Tools
            </span>
            <ul className="space-y-2">
              <li>
                <a href="#console" className="hover:text-cyan-600 transition flex items-center gap-1">
                  <span>Cloud Agent Console</span>
                </a>
              </li>
              <li>
                <a href="#features" className="hover:text-cyan-600 transition">
                  Fail-Open Proxy
                </a>
              </li>
              <li>
                <a href="#simulator" className="hover:text-cyan-600 transition">
                  Live Incident Sandbox
                </a>
              </li>
              <li>
                <a href="#architecture" className="hover:text-cyan-600 transition">
                  Multi-LLM Key Pool
                </a>
              </li>
              <li>
                <a href="#pricing" className="hover:text-cyan-600 transition">
                  Razorpay Subscriptions
                </a>
              </li>
            </ul>
          </div>

          {/* Ecosystem / Packages */}
          <div className="space-y-3">
            <span className="text-slate-900 font-bold uppercase tracking-wider text-[11px] font-mono block">
              Ecosystem & SDKs
            </span>
            <ul className="space-y-2">
              <li>
                <a
                  href="https://pypi.org/project/skelion/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-cyan-600 transition flex items-center gap-1"
                >
                  <span>Python SDK (PyPI)</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://www.npmjs.com/package/skelion-node"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-cyan-600 transition flex items-center gap-1"
                >
                  <span>Node.js SDK (npm)</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/Aditya-9-6/Skelion"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-cyan-600 transition flex items-center gap-1"
                >
                  <span>Core GitHub Repo</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/Aditya-9-6/Skelion_website"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-cyan-600 transition flex items-center gap-1"
                >
                  <span>Website Repo</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
            </ul>
          </div>

          {/* Security & Legal */}
          <div className="space-y-3">
            <span className="text-slate-900 font-bold uppercase tracking-wider text-[11px] font-mono block">
              Security & Legal
            </span>
            <ul className="space-y-2">
              <li>
                <a href="#terms" className="hover:text-cyan-600 transition">
                  Terms of Service
                </a>
              </li>
              <li>
                <a href="#privacy" className="hover:text-cyan-600 transition">
                  Privacy Policy
                </a>
              </li>
              <li>
                <a href="#cookie" className="hover:text-cyan-600 transition">
                  Cookie Policy
                </a>
              </li>
              <li>
                <a href="#security" className="hover:text-cyan-600 transition">
                  Security Policy
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/Aditya-9-6/Skelion/blob/main/LICENSE"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-cyan-600 transition"
                >
                  Apache 2.0 / MIT License
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-slate-200/80 flex flex-wrap items-center justify-between gap-4">
          <div className="text-slate-500 text-[11px]">
            © {new Date().getFullYear()} Skelion Platform. All rights reserved. Deployed seamlessly to Vercel.
          </div>
          <div className="flex items-center gap-4 text-[11px] text-slate-500 font-mono">
            <span>Razorpay Active</span>
            <span>•</span>
            <span>Web Platform v0.1.4</span>
            <span>•</span>
            <span>Fail-Open Guarantee</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
