// api/rates.js — Skelion Credit Rates & Token Pricing API
// Dual-currency rates for INR and USD credit packs and custom on-demand refills.

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    if (typeof res.status === 'function') return res.status(200).end();
    res.statusCode = 200;
    return res.end();
  }

  const ratesData = {
    rates: {
      INR: {
        creditPerCurrency: 1,
        pricePerCredit: 1.0,
        currencySymbol: "₹"
      },
      USD: {
        creditPerCurrency: 1,
        pricePerCredit: 0.013,
        currencySymbol: "$"
      }
    },
    creditToToken: 1000,
    description: "Base rates for purchasing credits. No bulk discounts are applied for custom on‑demand refills."
  };

  if (typeof res.status === 'function' && typeof res.json === 'function') {
    return res.status(200).json(ratesData);
  }

  res.statusCode = 200;
  res.setHeader('Content-Type', 'application/json');
  return res.end(JSON.stringify(ratesData));
}
