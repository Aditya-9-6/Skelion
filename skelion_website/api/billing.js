// api/billing.js — Skelion Razorpay Billing & Subscriptions Serverless Endpoint
// Handles live Razorpay order generation, plan checkout, on-demand refills, and payment signature verification
// Supports dual-currency pricing in INR (₹) and USD ($) with competitive industry standards

import crypto from 'crypto';

const RAZORPAY_KEY_ID = process.env.RAZORPAY_KEY_ID || '';
const RAZORPAY_KEY_SECRET = process.env.RAZORPAY_KEY_SECRET || '';
const ALLOWED_ORIGIN = process.env.ALLOWED_ORIGIN || '';

const PLAN_PRICES = {
  pilot: { name: 'Hosted Community', amountINR: 0, amountUSD: 0, credits: '50 Credits', creditsNum: 50 },
  hosted_lite: { name: 'Developer Lite', amountINR: 749, amountUSD: 9, credits: '1,000 Credits', creditsNum: 1000 },
  hosted_developer: { name: 'Developer Lite', amountINR: 749, amountUSD: 9, credits: '1,000 Credits', creditsNum: 1000 },
  pro: { name: 'Pro Developer', amountINR: 1349, amountUSD: 16, credits: '3,500 Credits', creditsNum: 3500 },
  hosted_team: { name: 'Engineering Team', amountINR: 3799, amountUSD: 45, credits: '12,000 Credits', creditsNum: 12000 },
  hosted_business: { name: 'Business Scale', amountINR: 9999, amountUSD: 119, credits: '35,000 Credits', creditsNum: 35000 },
  enterprise: { name: 'Enterprise Custom', amountINR: 39999, amountUSD: 499, credits: '100,000+ Credits', creditsNum: 100000 },
  topup_small: { name: 'Starter Pack (500 Credits)', amountINR: 399, amountUSD: 5, credits: '500 Credits', creditsNum: 500 },
  topup_medium: { name: 'Growth Pack (1,500 Credits)', amountINR: 999, amountUSD: 12, credits: '1,500 Credits', creditsNum: 1500 },
  topup_large: { name: 'Power Pack (5,000 Credits)', amountINR: 2899, amountUSD: 35, credits: '5,000 Credits', creditsNum: 5000 },
};

const COUPONS = {
  FOUNDING50: 0.7, // 30% off
  STUDENT_OSS: 0.5, // 50% off
  EARLYBIRD: 0.8, // 20% off
};

function setCorsHeaders(req, res) {
  const origin = req.headers?.origin;
  if (ALLOWED_ORIGIN && origin === ALLOWED_ORIGIN) {
    res.setHeader('Access-Control-Allow-Origin', ALLOWED_ORIGIN);
    res.setHeader('Vary', 'Origin');
  }
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
}

function isRazorpayConfigured() {
  return Boolean(
    RAZORPAY_KEY_ID &&
      RAZORPAY_KEY_SECRET &&
      !RAZORPAY_KEY_ID.includes('placeholder') &&
      !RAZORPAY_KEY_SECRET.includes('placeholder')
  );
}

function parseBody(req) {
  if (!req.body) return {};
  if (typeof req.body === 'object') return req.body;
  try {
    const parsed = JSON.parse(req.body);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    const error = new Error('Request body must be valid JSON');
    error.statusCode = 400;
    throw error;
  }
}

function calculatePurchase({ planId, couponCode, currency, customAmount }) {
  const normalizedCurrency = currency === 'USD' ? 'USD' : 'INR';
  const normalizedCoupon = String(couponCode || '').trim().toUpperCase();
  const isCustom = planId === 'custom' || customAmount !== undefined;

  if (isCustom) {
    const requestedAmount = Number(customAmount);
    const minAmount = normalizedCurrency === 'USD' ? 2 : 100;
    if (!Number.isFinite(requestedAmount) || requestedAmount < minAmount) {
      const error = new Error(`Custom purchases must be at least ${minAmount} ${normalizedCurrency}`);
      error.statusCode = 400;
      throw error;
    }

    const finalAmount = Math.round(requestedAmount);
    const ratePerCredit = normalizedCurrency === 'USD' ? 0.013 : 1;
    const creditsNum = Math.floor(finalAmount / ratePerCredit);
    return {
      currency: normalizedCurrency,
      finalAmount,
      planDisplayName: 'Custom On-Demand Refill',
      creditsNum,
      creditsDisplay: `${creditsNum.toLocaleString()} Credits (${(creditsNum * 1000).toLocaleString()} Tokens)`,
      couponCode: '',
    };
  }

  const selectedPlan = PLAN_PRICES[planId];
  if (!selectedPlan) {
    const error = new Error(`Unknown plan: ${planId}`);
    error.statusCode = 400;
    throw error;
  }

  const couponMultiplier = COUPONS[normalizedCoupon] || 1;
  const baseAmount = normalizedCurrency === 'USD' ? selectedPlan.amountUSD : selectedPlan.amountINR;
  return {
    currency: normalizedCurrency,
    finalAmount: Math.round(baseAmount * couponMultiplier),
    planDisplayName: selectedPlan.name,
    creditsNum: selectedPlan.creditsNum,
    creditsDisplay: selectedPlan.credits,
    couponCode: normalizedCoupon,
  };
}

export default async function handler(req, res) {
  setCorsHeaders(req, res);

  if (req.method === 'OPTIONS') {
    if (ALLOWED_ORIGIN && req.headers?.origin !== ALLOWED_ORIGIN) {
      return res.status(403).json({ error: 'Origin not allowed' });
    }
    return res.status(200).end();
  }

  const { searchParams } = new URL(req.url, 'http://localhost');
  const action = searchParams.get('action') || 'config';

  try {
    // 1. Get Public Razorpay Configuration
    if (action === 'config' && req.method === 'GET') {
      return res.status(200).json({
        configured: isRazorpayConfigured(),
        keyId: isRazorpayConfigured() ? RAZORPAY_KEY_ID : null,
        defaultCurrency: 'INR',
        supportedCurrencies: ['INR', 'USD'],
        testMode: RAZORPAY_KEY_ID.startsWith('rzp_test_'),
        supportedCoupons: Object.keys(COUPONS),
      });
    }

    // 2. Create Razorpay Order
    if (action === 'create-order' && req.method === 'POST') {
      const body = parseBody(req);
      const { planId = 'pro', couponCode = '', notes = {}, customAmount } = body;
      const purchase = calculatePurchase({
        planId,
        couponCode,
        currency: String(body.currency || 'INR').toUpperCase(),
        customAmount,
      });
      const { currency, finalAmount, planDisplayName, creditsDisplay, creditsNum } = purchase;

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
          keyId: isRazorpayConfigured() ? RAZORPAY_KEY_ID : null,
          isFree: true,
        });
      }

      if (!isRazorpayConfigured()) {
        return res.status(503).json({
          error: 'Payments are not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET before accepting purchases.',
        });
      }

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
            couponCode: purchase.couponCode || 'NONE',
            currency,
            credits: creditsDisplay,
            creditsNum,
            ...notes,
          },
        }),
      });

      if (!rzpResponse.ok) {
        const providerError = await rzpResponse.text();
        console.error('[Billing API Error] Razorpay order creation failed:', providerError);
        return res.status(502).json({ error: 'Payment provider could not create the order.' });
      }

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

    // 3. Verify Payment Signature & Issue Entitlement
    if (action === 'verify-payment' && req.method === 'POST') {
      const body = parseBody(req);

      const {
        razorpay_payment_id,
        razorpay_order_id,
        razorpay_signature,
        planId = 'pro',
        currency = 'INR',
        couponCode = '',
        customAmount,
      } = body;

      if (!isRazorpayConfigured()) {
        return res.status(503).json({ error: 'Payment verification is not configured.' });
      }

      if (!razorpay_payment_id || !razorpay_order_id || !razorpay_signature) {
        return res.status(400).json({
          error: 'Payment verification requires payment ID, order ID, and signature.',
        });
      }

      const purchase = calculatePurchase({ planId, couponCode, currency, customAmount });
      const expectedSignature = crypto
        .createHmac('sha256', RAZORPAY_KEY_SECRET)
        .update(`${razorpay_order_id}|${razorpay_payment_id}`)
        .digest('hex');
      const providedSignature = Buffer.from(String(razorpay_signature), 'utf8');
      const expectedSignatureBuffer = Buffer.from(expectedSignature, 'utf8');
      const isVerified =
        providedSignature.length === expectedSignatureBuffer.length &&
        crypto.timingSafeEqual(expectedSignatureBuffer, providedSignature);
      if (!isVerified) {
        return res.status(400).json({ error: 'Payment signature verification failed.' });
      }

      const auth = Buffer.from(`${RAZORPAY_KEY_ID}:${RAZORPAY_KEY_SECRET}`).toString('base64');
      const orderResponse = await fetch(
        `https://api.razorpay.com/v1/orders/${encodeURIComponent(razorpay_order_id)}`,
        {
          headers: { Authorization: `Basic ${auth}` },
        }
      );
      if (!orderResponse.ok) {
        console.error('[Billing API Error] Unable to retrieve Razorpay order:', orderResponse.status);
        return res.status(502).json({ error: 'Payment provider order could not be verified.' });
      }

      const providerOrder = await orderResponse.json();
      if (
        providerOrder.amount !== purchase.finalAmount * 100 ||
        providerOrder.currency !== purchase.currency
      ) {
        return res.status(400).json({ error: 'Payment order does not match the selected purchase.' });
      }

      const invoiceNumber = `INV-${new Date().toISOString().slice(0, 7).replace('-', '')}-${Math.floor(
        1000 + Math.random() * 9000
      )}`;

      return res.status(200).json({
        success: true,
        verified: true,
        paymentId: razorpay_payment_id,
        orderId: razorpay_order_id,
        invoiceNumber,
        plan: purchase.planDisplayName,
        credits: purchase.creditsDisplay,
        creditsNum: purchase.creditsNum,
        amount: purchase.finalAmount,
        currency: purchase.currency,
        timestamp: new Date().toLocaleTimeString(),
      });
    }

    return res.status(400).json({ error: `Unknown action: ${action}` });
  } catch (err) {
    console.error('[Billing API Error]', err);
    const statusCode = Number.isInteger(err.statusCode) ? err.statusCode : 500;
    return res.status(statusCode).json({ error: err.message || 'Billing transaction failed' });
  }
}
