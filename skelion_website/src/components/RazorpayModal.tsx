import React, { useState, useEffect } from 'react';
import { 
  X, 
  ShieldCheck, 
  CreditCard, 
  CheckCircle2, 
  Lock, 
  Building2, 
  Smartphone,
  ExternalLink,
  Loader2,
  AlertCircle,
  Zap
} from 'lucide-react';
import { UserProfile } from '../utils/auth';
import { grantUserCredits } from '../utils/creditLedger';

interface RazorpayModalProps {
  planId: string;
  couponCode?: string;
  currency?: 'INR' | 'USD';
  customAmount?: number;
  customCredits?: number;
  user?: UserProfile;
  onClose: () => void;
}

export const RazorpayModal: React.FC<RazorpayModalProps> = ({ 
  planId, 
  couponCode, 
  currency: initialCurrency = 'INR',
  customAmount,
  customCredits,
  user, 
  onClose 
}) => {
  const [currency, setCurrency] = useState<'INR' | 'USD'>(initialCurrency);
  const [tab, setTab] = useState<'razorpay' | 'upi' | 'card' | 'netbanking'>('razorpay');
  const [upiId, setUpiId] = useState('developer@okaxis');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [receiptData, setReceiptData] = useState<any>(null);
  const [razorpayKeyId, setRazorpayKeyId] = useState('');
  const sandboxEnabled = import.meta.env.VITE_ENABLE_PAYMENT_SANDBOX === 'true';

  // Load configured key from backend config on mount
  useEffect(() => {
    fetch('/api/billing?action=config')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.keyId) {
          setRazorpayKeyId(data.keyId);
        }
      })
      .catch(() => {
        setErrorMessage('Unable to load payment configuration. Please try again later.');
      });
  }, []);

  const planPrices: Record<string, { name: string; amountINR: number; amountUSD: number; credits: string; creditsNum: number }> = {
    pilot: { name: 'Hosted Community', amountINR: 0, amountUSD: 0, credits: '50 Credits (50k Tokens)', creditsNum: 50 },
    hosted_lite: { name: 'Developer Lite', amountINR: 749, amountUSD: 9, credits: '1,000 Credits (1M Tokens)', creditsNum: 1000 },
    hosted_developer: { name: 'Developer Lite', amountINR: 749, amountUSD: 9, credits: '1,000 Credits (1M Tokens)', creditsNum: 1000 },
    pro: { name: 'Pro Developer', amountINR: 1349, amountUSD: 16, credits: '3,500 Credits (3.5M Tokens)', creditsNum: 3500 },
    hosted_team: { name: 'Engineering Team', amountINR: 3799, amountUSD: 45, credits: '12,000 Credits (12M Tokens)', creditsNum: 12000 },
    hosted_business: { name: 'Business Scale', amountINR: 9999, amountUSD: 119, credits: '35,000 Credits (35M Tokens)', creditsNum: 35000 },
    enterprise: { name: 'Enterprise Custom', amountINR: 39999, amountUSD: 499, credits: '100,000+ Credits (100M+ Tokens)', creditsNum: 100000 },
    topup_small: { name: 'Starter Pack', amountINR: 399, amountUSD: 5, credits: '500 Credits (500k Tokens)', creditsNum: 500 },
    topup_medium: { name: 'Growth Pack', amountINR: 999, amountUSD: 12, credits: '1,500 Credits (1.5M Tokens)', creditsNum: 1500 },
    topup_large: { name: 'Power Pack', amountINR: 2899, amountUSD: 35, credits: '5,000 Credits (5M Tokens)', creditsNum: 5000 },
  };

  const isCustom = planId === 'custom' || typeof customAmount === 'number';

  let selectedName = '';
  let selectedCredits = '';
  let selectedCreditsNum = 0;
  let finalAmount = 0;
  let discountMultiplier = 1.0;

  if (isCustom) {
    const minAmount = currency === 'USD' ? 2 : 100;
    finalAmount = Math.max(minAmount, customAmount || minAmount);
    const ratePerCredit = currency === 'USD' ? 0.013 : 1.0;
    selectedCreditsNum = customCredits || Math.floor(finalAmount / ratePerCredit);
    selectedName = 'Custom On-Demand Refill';
    selectedCredits = `${selectedCreditsNum.toLocaleString()} Credits (${(selectedCreditsNum * 1000).toLocaleString()} Tokens)`;
    // No coupon discount applies to custom on-demand refills (adhering strictly to base pricing requirement)
    discountMultiplier = 1.0;
  } else {
    const selected = planPrices[planId] || planPrices['pro'];
    selectedName = selected.name;
    selectedCredits = selected.credits;
    selectedCreditsNum = selected.creditsNum;
    discountMultiplier = couponCode?.toUpperCase() === 'FOUNDING50' ? 0.7 : couponCode?.toUpperCase() === 'STUDENT_OSS' ? 0.5 : 1.0;
    const basePrice = currency === 'USD' ? selected.amountUSD : selected.amountINR;
    finalAmount = Math.round(basePrice * discountMultiplier);
  }

  const currencySymbol = currency === 'USD' ? '$' : '₹';

  // Helper to ensure Razorpay checkout SDK script is loaded
  const ensureRazorpayLoaded = (): Promise<boolean> => {
    return new Promise((resolve) => {
      if ((window as any).Razorpay) {
        resolve(true);
        return;
      }
      const existing = document.querySelector('script[src*="checkout.razorpay.com"]');
      if (existing) {
        existing.addEventListener('load', () => resolve(true));
        existing.addEventListener('error', () => resolve(false));
        return;
      }
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.async = true;
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.body.appendChild(script);
    });
  };

  // Launch official Razorpay Standard Checkout SDK
  const handleLaunchRazorpayCheckout = async () => {
    setErrorMessage(null);
    setIsProcessing(true);

    try {
      const isLoaded = await ensureRazorpayLoaded();
      if (!isLoaded || !(window as any).Razorpay) {
        throw new Error('Razorpay Checkout SDK failed to load. Please check your internet connection.');
      }

      // 1. Create order on serverless backend
      let orderData: any = {};
      try {
        const orderRes = await fetch('/api/billing?action=create-order', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            planId,
            couponCode: isCustom ? '' : couponCode,
            currency,
            customAmount: isCustom ? finalAmount : undefined,
            customCredits: isCustom ? selectedCreditsNum : undefined,
            customerEmail: user?.email,
            customerName: user?.name || user?.username,
          }),
        });

        const responseBody = await orderRes.json().catch(() => ({}));
        if (!orderRes.ok) {
          throw new Error(responseBody.error || `Unable to create payment order (${orderRes.status})`);
        }
        orderData = responseBody;
      } catch (err) {
        throw err;
      }

      // If free tier
      if (finalAmount <= 0) {
        setIsProcessing(false);
        setIsSuccess(true);
        const invNum = `INV-${new Date().toISOString().slice(0, 7).replace('-', '')}-${Math.floor(1000 + Math.random() * 9000)}`;
        const updatedLedger = grantUserCredits({
          credits: selectedCreditsNum,
          planOrPackName: selectedName,
          amountPaid: 0,
          currency,
          invoiceNumber: invNum,
          type: 'subscription',
        });
        setReceiptData({
          paymentId: `free_${Date.now().toString(36)}`,
          orderId: orderData.orderId || `order_free_${Date.now().toString(36)}`,
          invoiceNumber: invNum,
          timestamp: new Date().toLocaleTimeString(),
          credits: selectedCredits,
          creditsNum: selectedCreditsNum,
          newBalance: updatedLedger.balance,
          amount: 0,
          currency,
          method: 'Community Tier (Free)',
        });
        return;
      }

      const activeKey = orderData.keyId || razorpayKeyId;
      if (!activeKey || !orderData.orderId) {
        throw new Error('Payment gateway is not configured for this environment.');
      }

      // 2. Configure official Razorpay Checkout options
      const options: any = {
        key: activeKey,
        amount: (orderData.amountInPaise || finalAmount * 100),
        currency: orderData.currency || currency,
        name: 'Skelion AI',
        description: `${selectedName} (${selectedCredits})`,
        image: '/icon.svg',
        order_id: orderData.orderId?.startsWith('order_') && !orderData.orderId.includes('fallback') && !orderData.orderId.includes('free')
          ? orderData.orderId 
          : undefined,
        prefill: {
          name: user?.name || user?.username || 'Skelion Developer',
          email: user?.email || 'developer@skelion.ai',
          contact: '',
        },
        theme: {
          color: '#0891b2', // Brand Cyan-600
        },
        handler: async function (response: any) {
          setIsProcessing(true);
          try {
            // Verify payment on backend
            const verifyRes = await fetch('/api/billing?action=verify-payment', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_order_id: response.razorpay_order_id || orderData.orderId,
                razorpay_signature: response.razorpay_signature,
                planId,
                couponCode: isCustom ? '' : couponCode,
                currency,
                customAmount: isCustom ? finalAmount : undefined,
                customCredits: isCustom ? selectedCreditsNum : undefined,
              }),
            });

            const verifyResult = await verifyRes.json().catch(() => ({}));
            if (!verifyRes.ok || !verifyResult.success || !verifyResult.verified) {
              throw new Error(verifyResult.error || 'Payment verification failed. Credits were not activated.');
            }
            const invNum = verifyResult.invoiceNumber;

            // Grant credits into persistent ledger
            const updatedLedger = grantUserCredits({
              credits: selectedCreditsNum,
              planOrPackName: selectedName,
              amountPaid: finalAmount,
              currency,
              invoiceNumber: invNum,
              type: isCustom ? 'custom_refill' : planId.startsWith('topup_') ? 'topup' : 'subscription',
            });

            setIsProcessing(false);
            setIsSuccess(true);
            setReceiptData({
              paymentId: response.razorpay_payment_id || `pay_${Date.now().toString(36)}`,
              orderId: response.razorpay_order_id || orderData.orderId || `order_${Date.now().toString(36)}`,
              invoiceNumber: invNum,
              timestamp: new Date().toLocaleTimeString(),
              credits: selectedCredits,
              creditsNum: selectedCreditsNum,
              newBalance: updatedLedger.balance,
              amount: finalAmount,
              currency,
              method: 'Razorpay Gateway Verified',
            });
          } catch (vErr) {
            console.error('Signature verification error', vErr);
            setIsProcessing(false);
            setErrorMessage(vErr instanceof Error ? vErr.message : 'Payment verification failed. Credits were not activated.');
          }
        },
        modal: {
          ondismiss: function () {
            setIsProcessing(false);
          },
        },
      };

      const rzpInstance = new (window as any).Razorpay(options);
      rzpInstance.on('payment.failed', function (resp: any) {
        setIsProcessing(false);
        setErrorMessage(resp.error?.description || 'Payment was declined or cancelled.');
      });

      rzpInstance.open();
    } catch (err: any) {
      console.error('Razorpay launch failure', err);
      setIsProcessing(false);
      setErrorMessage(err.message || 'Unable to open Razorpay Checkout window.');
    }
  };

  // Fallback direct simulator for sandbox testing
  const handleSimulatePayment = () => {
    setIsProcessing(true);
    setErrorMessage(null);
    setTimeout(() => {
      const invNum = `INV-${new Date().toISOString().slice(0, 7).replace('-', '')}-${Math.floor(1000 + Math.random() * 9000)}`;
      const updatedLedger = grantUserCredits({
        credits: selectedCreditsNum,
        planOrPackName: selectedName,
        amountPaid: finalAmount,
        currency,
        invoiceNumber: invNum,
        type: isCustom ? 'custom_refill' : planId.startsWith('topup_') ? 'topup' : 'subscription',
      });

      setIsProcessing(false);
      setIsSuccess(true);
      setReceiptData({
        paymentId: `pay_${Math.random().toString(36).substring(2, 12)}`,
        orderId: `order_${Math.random().toString(36).substring(2, 12)}`,
        invoiceNumber: invNum,
        timestamp: new Date().toLocaleTimeString(),
        credits: selectedCredits,
        creditsNum: selectedCreditsNum,
        newBalance: updatedLedger.balance,
        amount: finalAmount,
        currency,
        method: 'Direct Sandbox Simulator Test (Verified)',
      });
    }, 1000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md animate-fade-in">
      <div className="glass-panel w-full max-w-lg rounded-2xl border border-slate-200 shadow-2xl overflow-hidden relative bg-white/95">
        {/* Header with Razorpay Branding */}
        <div className="bg-slate-50 p-5 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <img
                src="/icon.svg"
                alt="Skelion"
                className="w-9 h-9 rounded-lg bg-white p-1 border border-slate-200 shadow-sm object-contain"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = '/icon.png';
                }}
              />
              <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-[9px] shadow-sm">
                {currencySymbol}
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-slate-900 tracking-wide">Skelion • Razorpay Checkout</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 border border-emerald-300 font-medium">
                  {razorpayKeyId.startsWith('rzp_test_') ? 'TEST MODE' : 'LIVE'}
                </span>
              </div>
              <div className="text-[11px] text-slate-500 font-mono">
                Key ID: {razorpayKeyId}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Currency Selector Pill */}
            <div className="inline-flex items-center p-0.5 rounded-lg bg-slate-200/80 text-[11px] font-semibold">
              <button
                onClick={() => setCurrency('INR')}
                className={`px-2 py-0.5 rounded-md transition ${
                  currency === 'INR'
                    ? 'bg-white text-slate-900 font-bold shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                ₹ INR
              </button>
              <button
                onClick={() => setCurrency('USD')}
                className={`px-2 py-0.5 rounded-md transition ${
                  currency === 'USD'
                    ? 'bg-white text-slate-900 font-bold shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                $ USD
              </button>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        {!isSuccess ? (
          <div className="p-6 space-y-6">
            {/* Error Banner */}
            {errorMessage && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Order Summary Card */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-mono uppercase text-slate-500 block">
                  {isCustom ? 'Custom On-Demand Refill' : 'Selected Tier'}
                </span>
                <span className="text-sm font-bold text-slate-900">{selectedName}</span>
                <span className="text-xs text-cyan-700 font-medium block mt-0.5 font-mono">
                  {selectedCredits}
                </span>
              </div>
              <div className="text-right">
                <span className="text-[10px] font-mono uppercase text-slate-500 block">Total Due</span>
                <span className="text-2xl font-extrabold text-slate-950">
                  {currencySymbol}{finalAmount.toLocaleString('en-IN')}
                </span>
                {!isCustom && discountMultiplier < 1 && (
                  <span className="text-[10px] text-emerald-700 font-mono font-semibold block">
                    Coupon ({couponCode}) Applied
                  </span>
                )}
                {isCustom && (
                  <span className="text-[10px] text-slate-500 font-mono block">
                    Standard Rate (No Discounts)
                  </span>
                )}
              </div>
            </div>

            {/* Payment Method Selector */}
            <div>
              <div className="text-xs font-semibold text-slate-700 mb-2">Select Checkout Mode</div>
              <div className="grid grid-cols-4 gap-2">
                <button
                  onClick={() => setTab('razorpay')}
                  className={`p-2 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1.5 transition ${
                    tab === 'razorpay'
                      ? 'bg-cyan-50 border-cyan-400 text-cyan-800 shadow-sm'
                      : 'bg-white border-slate-200 text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Lock className="w-4 h-4 text-cyan-600" />
                  <span className="truncate">Official Popup</span>
                </button>
                <button
                  onClick={() => setTab('upi')}
                  className={`p-2 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1.5 transition ${
                    tab === 'upi'
                      ? 'bg-cyan-50 border-cyan-400 text-cyan-800 shadow-sm'
                      : 'bg-white border-slate-200 text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Smartphone className="w-4 h-4 text-purple-600" />
                  <span className="truncate">UPI Intent</span>
                </button>
                <button
                  onClick={() => setTab('card')}
                  className={`p-2 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1.5 transition ${
                    tab === 'card'
                      ? 'bg-cyan-50 border-cyan-400 text-cyan-800 shadow-sm'
                      : 'bg-white border-slate-200 text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <CreditCard className="w-4 h-4 text-blue-600" />
                  <span className="truncate">Card / Net</span>
                </button>
                <button
                  onClick={() => setTab('netbanking')}
                  className={`p-2 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1.5 transition ${
                    tab === 'netbanking'
                      ? 'bg-cyan-50 border-cyan-400 text-cyan-800 shadow-sm'
                      : 'bg-white border-slate-200 text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Building2 className="w-4 h-4 text-emerald-600" />
                  <span className="truncate">NetBanking</span>
                </button>
              </div>
            </div>

            {/* Method Details */}
            {tab === 'razorpay' && (
              <div className="p-3.5 rounded-xl bg-cyan-50/60 border border-cyan-200/80 text-xs text-cyan-900 flex items-start gap-2.5">
                <ShieldCheck className="w-4 h-4 text-cyan-600 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold">Official Standard Razorpay Gateway</div>
                  <div className="text-[11px] text-cyan-800 mt-0.5">
                    Opens the secure Razorpay Checkout dialog supporting UPI (GPay/PhonePe), Credit/Debit Cards, NetBanking, and International Wallets.
                  </div>
                </div>
              </div>
            )}

            {tab === 'upi' && (
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                <div className="flex items-center justify-between text-xs font-medium text-slate-700">
                  <span>Enter UPI ID / VPA</span>
                  <span className="text-[10px] text-slate-500 font-mono">Instant QR / App Verification</span>
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={upiId}
                    onChange={(e) => setUpiId(e.target.value)}
                    placeholder="username@okhdfcbank"
                    className="flex-1 px-3 py-2 rounded-lg text-xs bg-white border border-slate-300 text-slate-900 focus:outline-none focus:border-cyan-500 shadow-sm font-mono"
                  />
                </div>
              </div>
            )}

            {tab === 'card' && (
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2 text-xs">
                <div className="text-slate-600 font-medium">Card Information</div>
                <input
                  type="text"
                  placeholder="Card Number (4111 2222 3333 4444)"
                  className="w-full px-3 py-2 rounded-lg bg-white border border-slate-300 text-slate-900 focus:outline-none focus:border-blue-500 shadow-sm font-mono"
                />
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="MM/YY"
                    className="w-1/2 px-3 py-2 rounded-lg bg-white border border-slate-300 text-slate-900 focus:outline-none focus:border-blue-500 shadow-sm font-mono"
                  />
                  <input
                    type="password"
                    placeholder="CVV"
                    maxLength={4}
                    className="w-1/2 px-3 py-2 rounded-lg bg-white border border-slate-300 text-slate-900 focus:outline-none focus:border-blue-500 shadow-sm"
                  />
                </div>
              </div>
            )}

            {tab === 'netbanking' && (
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 space-y-2">
                <div className="text-slate-600 font-medium">Select Bank:</div>
                <select className="w-full px-3 py-2 rounded-lg bg-white border border-slate-300 text-slate-900 focus:outline-none focus:border-blue-500 shadow-sm">
                  <option>HDFC Bank</option>
                  <option>ICICI Bank</option>
                  <option>State Bank of India (SBI)</option>
                  <option>Axis Bank</option>
                  <option>Kotak Mahindra Bank</option>
                </select>
              </div>
            )}

            {/* Payment Action Buttons */}
            <div className="space-y-2">
              <button
                onClick={handleLaunchRazorpayCheckout}
                disabled={isProcessing}
                className="w-full py-3.5 rounded-xl text-sm font-bold bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-600 hover:from-cyan-500 hover:to-blue-500 text-white transition flex items-center justify-center gap-2 shadow-xl shadow-cyan-600/20 cursor-pointer disabled:opacity-50"
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Connecting to Razorpay Gateway...</span>
                  </>
                ) : (
                  <>
                    <Lock className="w-4 h-4" />
                    <span>Pay {currencySymbol}{finalAmount.toLocaleString('en-IN')} with Razorpay</span>
                    <ExternalLink className="w-3.5 h-3.5 opacity-80" />
                  </>
                )}
              </button>

              {sandboxEnabled && (
                <button
                  type="button"
                  onClick={handleSimulatePayment}
                  disabled={isProcessing}
                  className="w-full py-2 rounded-xl text-[11px] font-medium text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition"
                >
                  Or test via Instant Sandbox Simulator (1-Click)
                </button>
              )}
            </div>
          </div>
        ) : (
          /* Payment Success & Webhook Confirmation Screen */
          <div className="p-8 text-center space-y-5">
            <div className="w-14 h-14 rounded-full bg-emerald-50 border border-emerald-300 text-emerald-600 flex items-center justify-center mx-auto shadow-sm">
              <CheckCircle2 className="w-8 h-8" />
            </div>

            <div>
              <h3 className="text-xl font-bold text-slate-950">Payment Verified &amp; Credits Activated!</h3>
              <p className="text-xs text-slate-600 mt-1">
                Razorpay captured the payment and verified the transaction. Credits are added to your ledger.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-left font-mono text-xs space-y-2">
              <div className="flex justify-between text-slate-500">
                <span>INVOICE NUMBER:</span>
                <span className="text-slate-900 font-semibold">{receiptData.invoiceNumber}</span>
              </div>
              <div className="flex justify-between text-slate-500">
                <span>PAYMENT ID:</span>
                <span className="text-cyan-700 font-semibold">{receiptData.paymentId}</span>
              </div>
              <div className="flex justify-between text-slate-500">
                <span>ORDER ID:</span>
                <span className="text-slate-800">{receiptData.orderId}</span>
              </div>
              <div className="flex justify-between text-slate-500">
                <span>CREDITS GRANTED:</span>
                <span className="text-emerald-700 font-bold">{receiptData.credits}</span>
              </div>
              <div className="flex justify-between text-slate-500 pt-1 border-t border-slate-200">
                <span>NEW AVAILABLE BALANCE:</span>
                <span className="text-cyan-800 font-bold">
                  {receiptData.newBalance?.toLocaleString()} Credits ({(receiptData.newBalance * 1000)?.toLocaleString()} Tokens)
                </span>
              </div>
              <div className="flex justify-between text-slate-500">
                <span>AMOUNT PAID:</span>
                <span className="text-slate-950 font-bold">
                  {currencySymbol}{receiptData.amount.toLocaleString('en-IN')} ({currency})
                </span>
              </div>
            </div>

            <div className="flex items-center justify-center gap-1.5 text-[11px] text-emerald-700 font-medium">
              <Zap className="w-3.5 h-3.5 text-emerald-600" />
              <span>Instantly synced with Console IDE and persistent ledger across sessions.</span>
            </div>

            <button
              onClick={onClose}
              className="w-full py-3 rounded-xl text-xs font-bold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white transition shadow-md cursor-pointer"
            >
              Continue to Console
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
