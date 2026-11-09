// api/billing.js — Skelion Razorpay Billing & Subscriptions Serverless Endpoint
// Handles live Razorpay order generation, plan checkout, on-demand refills, and payment signature verification
// Supports dual-currency pricing in INR (₹) and USD ($) with competitive industry standards

import crypto from 'crypto';

const RAZORPAY_KEY_ID = process.env.RAZORPAY_KEY_ID || 'rzp_test_TwvOwcT2gnvSnv';
const RAZORPAY_KEY_SECRET = process.env.RAZORPAY_KEY_SECRET || '';

const PLAN_PRICES = {
  pilot: { name: 'Developer Tier', amountINR: 0, amountUSD: 0, credits: '50 Credits', creditsNum: 50 },
  hosted_lite: { name: 'Developer Tier', amountINR: 749, amountUSD: 9, credits: '1,000 Credits', creditsNum: 1000 },
  hosted_developer: { name: 'Developer Tier', amountINR: 749, amountUSD: 9, credits: '1,000 Credits', creditsNum: 1000 },
  pro: { name: 'Pro Developer Tier', amountINR: 1349, amountUSD: 16, credits: '3,500 Credits', creditsNum: 3500 },
  hosted_team: { name: 'Engineering Team Tier', amountINR: 3799, amountUSD: 45, credits: '12,000 Credits', creditsNum: 12000 },
  hosted_business: { name: 'Engineering Team Tier (Scale)', amountINR: 9999, amountUSD: 119, credits: '35,000 Credits', creditsNum: 35000 },
  enterprise: { name: 'Custom Tier', amountINR: 25000, amountUSD: 299, credits: 'Custom Credits (100k+)', creditsNum: 100000 },
  custom: { name: 'Custom Tier', amountINR: 25000, amountUSD: 299, credits: 'Custom Credits (100k+)', creditsNum: 100000 },
  topup_small: { name: 'Starter Pack (500 Credits)', amountINR: 399, amountUSD: 5, credits: '500 Credits', creditsNum: 500 },
  topup_medium: { name: 'Growth Pack (1,500 Credits)', amountINR: 999, amountUSD: 12, credits: '1,500 Credits', creditsNum: 1500 },
  topup_large: { name: 'Power Pack (5,000 Credits)', amountINR: 2899, amountUSD: 35, credits: '5,000 Credits', creditsNum: 5000 },
  autonomous_dev_loop: { name: 'Autonomous Dev Loop (24/7)', amountINR: 1499, amountUSD: 19, credits: '5,000 Credits', creditsNum: 5000 },
  reverse_proxy_loop: { name: 'Reverse Proxy Loop (24/7)', amountINR: 999, amountUSD: 12, credits: '2,500 Credits', creditsNum: 2500 },
};

const COUPONS = {
  FOUNDING50: 0.7, // 30% off
  STUDENT_OSS: 0.5, // 50% off
  EARLYBIRD: 0.8, // 20% off
};

export default async function handler(req, res) {
  if (!res.status) {
    res.status = function(code) {
      this.statusCode = code;
      return this;
    };
  }
  if (!res.json) {
    res.json = function(data) {
      this.setHeader('Content-Type', 'application/json');
      this.end(JSON.stringify(data));
      return this;
    };
  }

  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const { searchParams } = new URL(req.url, 'http://localhost');
  const action = searchParams.get('action') || 'config';

  try {
    // 0. Get Public Rates Configuration
    if ((action === 'rates' || action === 'credit-rates') && req.method === 'GET') {
      return res.status(200).json({
        rates: {
          INR: { creditPerCurrency: 1, pricePerCredit: 1.0, currencySymbol: "₹" },
          USD: { creditPerCurrency: 1, pricePerCredit: 0.013, currencySymbol: "$" }
        },
        creditToToken: 1000,
        description: "Base rates for purchasing credits. No bulk discounts are applied for custom on‑demand refills."
      });
    }

    // 1. Get Public Razorpay Configuration
    if (action === 'config' && req.method === 'GET') {
      return res.status(200).json({
        keyId: RAZORPAY_KEY_ID,
        defaultCurrency: 'INR',
        supportedCurrencies: ['INR', 'USD'],
        testMode: RAZORPAY_KEY_ID.startsWith('rzp_test_'),
        supportedCoupons: Object.keys(COUPONS),
      });
    }

    // 2. Create Razorpay Order
    if (action === 'create-order' && req.method === 'POST') {
      let body = {};
      try {
        body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body || {};
      } catch (_) {
        body = {};
      }

      const { planId = 'pro', couponCode = '', notes = {}, customAmount, customCredits } = body;
      const currency = (body.currency || 'INR').toUpperCase() === 'USD' ? 'USD' : 'INR';

      let finalAmount = 0;
      let planDisplayName = '';
      let creditsDisplay = '';
      let creditsNum = 0;

      // Handle custom on-demand refill amounts
      if (planId === 'custom' || customAmount) {
        const minAmount = currency === 'USD' ? 2 : 100;
        finalAmount = Math.max(minAmount, Math.round(Number(customAmount) || minAmount));
        // Custom rate: ₹1.00 / credit in INR, $0.013 / credit in USD (no discounts)
        const ratePerCredit = currency === 'USD' ? 0.013 : 1.0;
        creditsNum = customCredits ? Math.round(Number(customCredits)) : Math.floor(finalAmount / ratePerCredit);
        planDisplayName = 'Custom On-Demand Refill';
        creditsDisplay = `${creditsNum.toLocaleString()} Credits (${(creditsNum * 1000).toLocaleString()} Tokens)`;
      } else {
        const selectedPlan = PLAN_PRICES[planId] || PLAN_PRICES['pro'];
        const couponMultiplier = COUPONS[couponCode?.toUpperCase()] || 1.0;
        const baseAmount = currency === 'USD' ? selectedPlan.amountUSD : selectedPlan.amountINR;
        finalAmount = Math.round(baseAmount * couponMultiplier);
        planDisplayName = selectedPlan.name;
        creditsDisplay = selectedPlan.credits;
        creditsNum = selectedPlan.creditsNum || 1000;
      }

      const amountInSubunits = finalAmount * 100;

      // Free tier
      if (finalAmount <= 0) {
        return res.status(200).json({
          orderId: `order_free_${Date.now()}`,
          amount: 0,
          currency,
          plan: planDisplayName,
          credits: creditsDisplay,
          creditsNum,
          keyId: RAZORPAY_KEY_ID,
          isFree: true,
        });
      }

      // If Razorpay secret is present in environment, create official order via Razorpay API
      if (RAZORPAY_KEY_SECRET) {
        const auth = Buffer.from(`${RAZORPAY_KEY_ID}:${RAZORPAY_KEY_SECRET}`).toString('base64');
        const rzpResponse = await fetch('https://api.razorpay.com/v1/orders', {
          method: 'POST',
          headers: {
            Authorization: `Basic ${auth}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            amount: amountInSubunits,
            currency,
            receipt: `rcpt_${Date.now().toString(36)}`,
            notes: {
              planId,
              couponCode: couponCode || 'NONE',
              currency,
              credits: creditsDisplay,
              creditsNum,
              ...notes,
            },
          }),
        });

        if (rzpResponse.ok) {
          const rzpOrder = await rzpResponse.json();
          return res.status(200).json({
            orderId: rzpOrder.id,
            amount: finalAmount,
            amountInPaise: rzpOrder.amount,
            currency: rzpOrder.currency,
            plan: planDisplayName,
            credits: creditsDisplay,
            creditsNum,
            keyId: RAZORPAY_KEY_ID,
          });
        }
      }

      // Fallback for test mode: generate standard test order
      const fallbackOrderId = `order_${Date.now().toString(36)}_${Math.random().toString(36).substring(2, 7)}`;
      return res.status(200).json({
        orderId: fallbackOrderId,
        amount: finalAmount,
        amountInPaise: amountInSubunits,
        currency,
        plan: planDisplayName,
        credits: creditsDisplay,
        creditsNum,
        keyId: RAZORPAY_KEY_ID,
      });
    }

    // 3. Verify Payment Signature & Issue Entitlement
    if (action === 'verify-payment' && req.method === 'POST') {
      let body = {};
      try {
        body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body || {};
      } catch (_) {
        body = {};
      }

      const {
        razorpay_payment_id,
        razorpay_order_id,
        razorpay_signature,
        planId = 'pro',
        currency = 'INR',
        customAmount,
        customCredits,
      } = body;

      let planDisplayName = '';
      let creditsDisplay = '';
      let creditsNum = 0;
      let finalAmount = 0;

      if (planId === 'custom' || customAmount) {
        finalAmount = Math.round(Number(customAmount) || 100);
        creditsNum = customCredits ? Math.round(Number(customCredits)) : (currency === 'USD' ? Math.floor(finalAmount / 0.013) : finalAmount);
        planDisplayName = 'Custom On-Demand Refill';
        creditsDisplay = `${creditsNum.toLocaleString()} Credits`;
      } else {
        const selectedPlan = PLAN_PRICES[planId] || PLAN_PRICES['pro'];
        planDisplayName = selectedPlan.name;
        creditsDisplay = selectedPlan.credits;
        creditsNum = selectedPlan.creditsNum || 1000;
        finalAmount = currency === 'USD' ? selectedPlan.amountUSD : selectedPlan.amountINR;
      }

      let isVerified = false;

      // Verify HMAC-SHA256 signature if secret is available
      if (RAZORPAY_KEY_SECRET) {
        if (!razorpay_order_id || !razorpay_payment_id || !razorpay_signature) {
          isVerified = false;
        } else {
          const text = `${razorpay_order_id}|${razorpay_payment_id}`;
          const generatedSignature = crypto
            .createHmac('sha256', RAZORPAY_KEY_SECRET)
            .update(text)
            .digest('hex');
          isVerified = (generatedSignature === razorpay_signature);
        }
      } else {
        // Test mode simulation: accept unless explicitly marked invalid
        isVerified = Boolean(razorpay_payment_id && razorpay_order_id && razorpay_signature !== 'invalid_signature');
      }

      if (!isVerified) {
        return res.status(400).json({
          success: false,
          verified: false,
          error: 'Invalid or missing Razorpay payment signature',
        });
      }

      const invoiceNumber = `INV-${new Date().toISOString().slice(0, 7).replace('-', '')}-${Math.floor(
        1000 + Math.random() * 9000
      )}`;

      return res.status(200).json({
        success: true,
        verified: true,
        paymentId: razorpay_payment_id || `pay_${Date.now().toString(36)}`,
        orderId: razorpay_order_id || `order_${Date.now().toString(36)}`,
        invoiceNumber,
        plan: planDisplayName,
        credits: creditsDisplay,
        creditsNum,
        amount: finalAmount,
        currency,
        timestamp: new Date().toLocaleTimeString(),
      });
    }

    return res.status(400).json({ error: `Unknown action: ${action}` });
  } catch (err) {
    console.error('[Billing API Error]', err);
    return res.status(500).json({ error: err.message || 'Billing transaction failed' });
  }
}
