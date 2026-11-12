import React, { useState, useEffect } from 'react';
import { 
  CreditCard, 
  CheckCircle, 
  AlertCircle, 
  LogOut, 
  Shield, 
  Zap, 
  ArrowLeft, 
  User, 
  Clock, 
  ExternalLink,
  RefreshCw,
  Lock
} from 'lucide-react';

interface Plan {
  id: string;
  name: string;
  price: number;
  currency: string;
  interval: string;
  credits: number;
  description: string;
  features: string[];
}

interface PurchaseRecord {
  planId: string;
  planName: string;
  userId: string;
  timestamp: string;
  paymentId: string;
  orderId: string;
  amount: number;
  currency: string;
}

interface UserSession {
  userId: string;
  name: string;
  email: string;
  phone: string;
}

export const PaymentPage: React.FC = () => {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loadingPlans, setLoadingPlans] = useState(true);
  const [errorPlans, setErrorPlans] = useState<string | null>(null);

  // User session state
  const [user, setUser] = useState<UserSession>(() => {
    const saved = localStorage.getItem('skelion_user_session');
    if (saved) {
      try { return JSON.parse(saved); } catch { /* fallback */ }
    }
    const defaultUser: UserSession = {
      userId: 'usr_skelion_' + Math.random().toString(36).substring(2, 9),
      name: 'Skelion Developer',
      email: 'developer@skelion.ai',
      phone: '9876543210'
    };
    localStorage.setItem('skelion_user_session', JSON.stringify(defaultUser));
    return defaultUser;
  });

  // Payment status state
  const [paymentStatus, setPaymentStatus] = useState<{
    status: 'idle' | 'processing' | 'success' | 'failed' | 'cancelled';
    message?: string;
    record?: PurchaseRecord;
  }>({ status: 'idle' });

  // Purchase history
  const [purchases, setPurchases] = useState<PurchaseRecord[]>(() => {
    const saved = localStorage.getItem('skelion_purchases');
    if (saved) {
      try { return JSON.parse(saved); } catch { return []; }
    }
    return [];
  });

  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [scriptLoaded, setScriptLoaded] = useState(false);

  // Load plans from data/plans.json
  useEffect(() => {
    const fetchPlans = async () => {
      try {
        setLoadingPlans(true);
        const res = await fetch('/data/plans.json');
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        const data = await res.json();
        setPlans(data.plans || []);
        setErrorPlans(null);
      } catch (err: any) {
        console.warn('Failed to fetch from /data/plans.json, trying fallback import/local data', err);
        // Fallback plans if fetch fails
        setPlans([
          {
            id: 'pilot',
            name: 'Pilot Community',
            price: 0,
            currency: 'INR',
            interval: 'month',
            credits: 100,
            description: 'For solo developers & evaluation',
            features: ['100 Credits quota', 'Fail-open edge proxy telemetry', 'Basic incident fingerprinting']
          },
          {
            id: 'developer',
            name: 'Skelion Developer',
            price: 799,
            currency: 'INR',
            interval: 'month',
            credits: 800,
            description: 'For active developers & small projects',
            features: ['800 Credits quota', 'Economy & Standard AI models', '3 Projects included']
          },
          {
            id: 'pro',
            name: 'Pro Team',
            price: 3999,
            currency: 'INR',
            interval: 'month',
            credits: 4500,
            description: 'For fast-growing teams & startups',
            features: ['4,500 Credits quota', 'Autonomous LLM incident fix generation', 'PR review bot diagnostic cards']
          },
          {
            id: 'enterprise',
            name: 'Enterprise Scale',
            price: 9999,
            currency: 'INR',
            interval: 'month',
            credits: 25000,
            description: 'For large engineering orgs & enterprises',
            features: ['25,000+ Credits quota', 'Custom enterprise contracts', 'SCIM directory sync & SSO']
          }
        ]);
      } finally {
        setLoadingPlans(false);
      }
    };

    fetchPlans();
  }, []);

  // Load Razorpay Checkout Script dynamically
  useEffect(() => {
    const scriptId = 'razorpay-checkout-js';
    if (document.getElementById(scriptId)) {
      setScriptLoaded(true);
      return;
    }

    const script = document.createElement('script');
    script.id = scriptId;
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.onload = () => setScriptLoaded(true);
    script.onerror = () => {
      console.error('Failed to load Razorpay Checkout script');
      setPaymentStatus({
        status: 'failed',
        message: 'Failed to load Razorpay checkout gateway script. Please check your network connection.'
      });
    };
    document.body.appendChild(script);

    return () => {
      // Cleanup script if component unmounts
      const existing = document.getElementById(scriptId);
      if (existing && existing.parentNode) {
        // keep script cached for usability
      }
    };
  }, []);

  // Handle Logout flow
  const handleLogout = () => {
    localStorage.removeItem('skelion_user_session');
    // Generate new guest session or reset
    const newGuest: UserSession = {
      userId: 'usr_guest_' + Math.random().toString(36).substring(2, 9),
      name: 'Guest User',
      email: 'guest@skelion.ai',
      phone: '0000000000'
    };
    setUser(newGuest);
    localStorage.setItem('skelion_user_session', JSON.stringify(newGuest));
    setPaymentStatus({
      status: 'idle',
      message: 'Logged out successfully. New guest session initialized.'
    });
  };

  // Handle checkout / payment processing
  const handleCheckout = (plan: Plan) => {
    setSelectedPlanId(plan.id);

    // If plan price is 0 (Pilot Community), bypass Razorpay and record purchase directly
    if (plan.price === 0) {
      const record: PurchaseRecord = {
        planId: plan.id,
        planName: plan.name,
        userId: user.userId,
        timestamp: new Date().toISOString(),
        paymentId: 'free_' + Math.random().toString(36).substring(2, 11),
        orderId: 'ord_free_' + Math.random().toString(36).substring(2, 11),
        amount: 0,
        currency: plan.currency
      };

      const updatedPurchases = [...purchases, record];
      setPurchases(updatedPurchases);
      localStorage.setItem('skelion_purchases', JSON.stringify(updatedPurchases));

      setPaymentStatus({
        status: 'success',
        message: `Successfully activated ${plan.name}! Quota assigned to user ${user.userId}.`,
        record
      });
      setSelectedPlanId(null);
      return;
    }

    if (!scriptLoaded) {
      setPaymentStatus({
        status: 'failed',
        message: 'Razorpay SDK is still loading. Please try again in a moment.'
      });
      setSelectedPlanId(null);
      return;
    }

    setPaymentStatus({ status: 'processing', message: `Initializing Razorpay secure checkout for ${plan.name}...` });

    try {
      const options = {
        key: import.meta.env.VITE_RAZORPAY_KEY_ID || '',
        amount: plan.price * 100, // amount in smallest currency unit (paise)
        currency: plan.currency || 'INR',
        name: 'Skelion SaaS Platform',
        description: `Subscription: ${plan.name} (${plan.credits} Credits/mo)`,
        image: '/skelion_logo_white.png',
        handler: function (response: any) {
          const paymentId = response.razorpay_payment_id;
          const orderId = response.razorpay_order_id || 'order_' + Math.random().toString(36).substring(2, 9);

          const record: PurchaseRecord = {
            planId: plan.id,
            planName: plan.name,
            userId: user.userId,
            timestamp: new Date().toISOString(),
            paymentId,
            orderId,
            amount: plan.price,
            currency: plan.currency
          };

          const updatedPurchases = [...purchases, record];
          setPurchases(updatedPurchases);
          localStorage.setItem('skelion_purchases', JSON.stringify(updatedPurchases));

          setPaymentStatus({
            status: 'success',
            message: `Payment successful via Razorpay! Payment ID: ${paymentId}`,
            record
          });
          setSelectedPlanId(null);
        },
        prefill: {
          name: user.name,
          email: user.email,
          contact: user.phone
        },
        notes: {
          userId: user.userId,
          planId: plan.id,
          credits: plan.credits.toString()
        },
        theme: {
          color: '#00f2fe'
        },
        modal: {
          ondismiss: function () {
            setPaymentStatus({
              status: 'cancelled',
              message: 'Payment popup was closed or cancelled by user.'
            });
            setSelectedPlanId(null);
          }
        }
      };

      const rzpInstance = new (window as any).Razorpay(options);
      rzpInstance.on('payment.failed', function (resp: any) {
        setPaymentStatus({
          status: 'failed',
          message: `Payment failed: ${resp.error?.description || 'Unknown error occurred during transaction.'}`
        });
        setSelectedPlanId(null);
      });
      rzpInstance.open();
    } catch (err: any) {
      console.error('Razorpay invocation error:', err);
      setPaymentStatus({
        status: 'failed',
        message: `Error opening Razorpay checkout: ${err.message || 'Unknown error'}`
      });
      setSelectedPlanId(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#050811] text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200 relative overflow-x-hidden">
      {/* Background ambient glowing gradient circles */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-violet-600/10 rounded-full blur-3xl pointer-events-none" />

      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-50 glass-panel border-b border-white/10 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <a 
            href="/" 
            className="flex items-center space-x-2 text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span className="font-semibold tracking-wide">Back to Skelion</span>
          </a>
        </div>

        <div className="flex items-center space-x-4">
          <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs text-slate-300">
            <User className="w-3.5 h-3.5 text-cyan-400" />
            <span>{user.name}</span>
            <span className="text-slate-500">({user.userId})</span>
          </div>

          <button
            onClick={handleLogout}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 transition-all text-xs font-medium cursor-pointer"
            title="Log out and reset session"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Logout</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-10 relative z-10">
        
        {/* Header Section */}
        <div className="text-center max-w-3xl mx-auto mb-12">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium mb-4">
            <Shield className="w-3.5 h-3.5" />
            <span>Secure Razorpay Gateway Integration</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white mb-4">
            Upgrade Your <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-violet-500">Skelion AI Subscription</span>
          </h1>
          <p className="text-slate-400 text-sm sm:text-base">
            Choose your tier and process secure INR payments via Razorpay using the deployment-configured public key.
          </p>
        </div>

        {/* Status Notification Banner */}
        {paymentStatus.status !== 'idle' && (
          <div className={`mb-8 p-4 rounded-xl glass-panel border flex items-start space-x-3 transition-all ${
            paymentStatus.status === 'success' ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200' :
            paymentStatus.status === 'failed' ? 'border-red-500/40 bg-red-500/10 text-red-200' :
            paymentStatus.status === 'cancelled' ? 'border-amber-500/40 bg-amber-500/10 text-amber-200' :
            'border-cyan-500/40 bg-cyan-500/10 text-cyan-200 animate-pulse'
          }`}>
            {paymentStatus.status === 'success' && <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />}
            {paymentStatus.status === 'failed' && <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />}
            {paymentStatus.status === 'cancelled' && <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />}
            {paymentStatus.status === 'processing' && <RefreshCw className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5 animate-spin" />}
            
            <div className="flex-1 text-sm">
              <p className="font-semibold capitalize">{paymentStatus.status} State</p>
              <p className="mt-0.5 opacity-90">{paymentStatus.message}</p>
              {paymentStatus.record && (
                <div className="mt-3 p-3 rounded bg-black/40 border border-white/10 text-xs font-mono space-y-1">
                  <div><span className="text-slate-400">Plan:</span> {paymentStatus.record.planName}</div>
                  <div><span className="text-slate-400">Payment ID:</span> <span className="text-cyan-300">{paymentStatus.record.paymentId}</span></div>
                  <div><span className="text-slate-400">Order ID:</span> {paymentStatus.record.orderId}</div>
                  <div><span className="text-slate-400">Timestamp:</span> {new Date(paymentStatus.record.timestamp).toLocaleString()}</div>
                </div>
              )}
            </div>
            
            <button 
              onClick={() => setPaymentStatus({ status: 'idle' })} 
              className="text-xs opacity-70 hover:opacity-100 underline shrink-0 cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Plans Grid */}
        {loadingPlans ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((n) => (
              <div key={n} className="glass-panel p-6 h-96 animate-pulse flex flex-col justify-between">
                <div className="space-y-4">
                  <div className="h-6 bg-white/10 rounded w-3/4" />
                  <div className="h-4 bg-white/10 rounded w-1/2" />
                  <div className="h-10 bg-white/10 rounded w-full my-6" />
                  <div className="space-y-2">
                    <div className="h-3 bg-white/10 rounded w-full" />
                    <div className="h-3 bg-white/10 rounded w-5/6" />
                    <div className="h-3 bg-white/10 rounded w-4/5" />
                  </div>
                </div>
                <div className="h-10 bg-white/10 rounded w-full" />
              </div>
            ))}
          </div>
        ) : errorPlans && plans.length === 0 ? (
          <div className="glass-panel p-8 text-center max-w-md mx-auto border-red-500/30">
            <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-white mb-2">Unable to Load Plans</h3>
            <p className="text-slate-400 text-sm mb-4">{errorPlans}</p>
            <button 
              onClick={() => window.location.reload()}
              className="px-4 py-2 rounded-lg bg-cyan-500 text-slate-950 font-semibold text-sm hover:bg-cyan-400 transition-colors"
            >
              Retry
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {plans.map((plan) => {
              const isSelected = selectedPlanId === plan.id;
              const isPopular = plan.id === 'pro';

              return (
                <div 
                  key={plan.id}
                  className={`glass-panel p-6 flex flex-col justify-between relative transition-all duration-300 ${
                    isPopular ? 'border-cyan-500/50 shadow-[0_0_30px_rgba(0,242,254,0.15)] bg-gradient-to-b from-[#0d1321] to-[#121b30]' : 'hover:border-white/20'
                  }`}
                >
                  {isPopular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-gradient-to-r from-cyan-500 to-violet-600 text-slate-950 font-bold text-[10px] tracking-wider uppercase shadow-lg">
                      Most Popular
                    </div>
                  )}

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-lg font-bold text-white">{plan.name}</h3>
                      <div className="p-2 rounded-lg bg-white/5 border border-white/10 text-cyan-400">
                        <Zap className="w-4 h-4" />
                      </div>
                    </div>
                    <p className="text-xs text-slate-400 min-h-[32px] mb-4">{plan.description}</p>

                    <div className="mb-6 pb-6 border-b border-white/10">
                      <div className="flex items-baseline space-x-1">
                        <span className="text-3xl font-extrabold text-white">
                          {plan.price === 0 ? 'Free' : `₹${plan.price.toLocaleString('en-IN')}`}
                        </span>
                        {plan.price > 0 && (
                          <span className="text-xs text-slate-400">/{plan.interval}</span>
                        )}
                      </div>
                      <div className="mt-1 text-xs text-cyan-400 font-medium">
                        ✨ {plan.credits} Credits Quota Included
                      </div>
                    </div>

                    <ul className="space-y-2.5 mb-8">
                      {plan.features.map((feature, idx) => (
                        <li key={idx} className="flex items-start text-xs text-slate-300">
                          <CheckCircle className="w-3.5 h-3.5 text-cyan-400 shrink-0 mr-2 mt-0.5" />
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <button
                    onClick={() => handleCheckout(plan)}
                    disabled={selectedPlanId !== null}
                    className={`w-full py-3 px-4 rounded-xl font-semibold text-sm flex items-center justify-center space-x-2 transition-all cursor-pointer ${
                      plan.price === 0
                        ? 'bg-white/10 hover:bg-white/20 text-white border border-white/15'
                        : isPopular
                        ? 'bg-gradient-to-r from-cyan-500 to-violet-600 text-slate-950 font-bold hover:opacity-95 shadow-[0_4px_20px_rgba(0,242,254,0.3)]'
                        : 'bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/30'
                    } ${selectedPlanId !== null && !isSelected ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    {isSelected ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>Processing...</span>
                      </>
                    ) : (
                      <>
                        <CreditCard className="w-4 h-4" />
                        <span>{plan.price === 0 ? 'Activate Free Tier' : 'Pay with Razorpay'}</span>
                      </>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* Purchase History Section (recording in data/purchases.json simulation via localStorage) */}
        <div className="mt-16">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-2">
              <Clock className="w-5 h-5 text-cyan-400" />
              <h2 className="text-xl font-bold text-white">Purchase & Subscription History</h2>
            </div>
            <div className="text-xs text-slate-400">
              Stored in <code className="text-cyan-300 bg-black/40 px-1.5 py-0.5 rounded">data/purchases.json</code> (localStorage)
            </div>
          </div>

          {purchases.length === 0 ? (
            <div className="glass-panel p-8 text-center text-slate-400 text-sm">
              No purchase records found yet. Complete a checkout above to record your subscription transaction.
            </div>
          ) : (
            <div className="glass-panel overflow-hidden border border-white/10">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-white/10 bg-white/5 text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      <th className="py-3.5 px-6">Plan Name</th>
                      <th className="py-3.5 px-6">User ID</th>
                      <th className="py-3.5 px-6">Amount</th>
                      <th className="py-3.5 px-6">Payment ID</th>
                      <th className="py-3.5 px-6">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-xs text-slate-300">
                    {purchases.slice().reverse().map((p, idx) => (
                      <tr key={idx} className="hover:bg-white/5 transition-colors">
                        <td className="py-4 px-6 font-semibold text-white flex items-center space-x-2">
                          <CheckCircle className="w-4 h-4 text-emerald-400" />
                          <span>{p.planName}</span>
                        </td>
                        <td className="py-4 px-6 font-mono text-slate-400">{p.userId}</td>
                        <td className="py-4 px-6 font-semibold text-cyan-300">
                          {p.amount === 0 ? 'Free' : `₹${p.amount.toLocaleString('en-IN')}`}
                        </td>
                        <td className="py-4 px-6 font-mono text-cyan-400">{p.paymentId}</td>
                        <td className="py-4 px-6 text-slate-400">{new Date(p.timestamp).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

      </main>

      {/* Footer */}
      <footer className="mt-20 border-t border-white/10 py-8 text-center text-xs text-slate-500 relative z-10 glass-panel">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <Shield className="w-4 h-4 text-cyan-400" />
            <span>Skelion SaaS Billing &bull; Razorpay Test Environment</span>
          </div>
          <div className="flex items-center space-x-4">
            <span>Key: <code className="text-cyan-400">Deployment configured</code></span>
            <span>&bull;</span>
            <a href="/" className="hover:text-cyan-400 transition-colors">Terms of Service</a>
            <a href="/" className="hover:text-cyan-400 transition-colors">Privacy Policy</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default PaymentPage;
