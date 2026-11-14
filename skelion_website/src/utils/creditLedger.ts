// src/utils/creditLedger.ts
// Centralized persistent credit ledger for Skelion AI
// Tracks real-time credit balances, token equivalencies (1 Credit = 1,000 Tokens),
// and transaction history across subscription cycles and on-demand refills.

export interface CreditTransaction {
  id: string;
  date: string;
  type: 'subscription' | 'topup' | 'custom_refill' | 'free_grant';
  credits: number;
  tokens: number;
  amountPaid: number;
  currency: 'INR' | 'USD';
  invoiceNumber: string;
  description: string;
  status: 'verified' | 'completed';
}

export interface UserCreditState {
  balance: number; // in credits
  tokens: number; // balance * 1,000
  totalPurchased: number;
  activePlan: string;
  lastUpdated: string;
  transactions: CreditTransaction[];
}

const STORAGE_KEY = 'skelion_user_credit_state_v1';

const INITIAL_DEFAULT_STATE: UserCreditState = {
  balance: 0,
  tokens: 0,
  totalPurchased: 0,
  activePlan: 'None',
  lastUpdated: new Date().toISOString(),
  transactions: [],
};

/**
 * Retrieve current credit balance and ledger state
 */
export function getUserCreditState(): UserCreditState {
  if (typeof window === 'undefined') return INITIAL_DEFAULT_STATE;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(INITIAL_DEFAULT_STATE));
      return INITIAL_DEFAULT_STATE;
    }
    const parsed = JSON.parse(raw);
    parsed.tokens = (parsed.balance || 0) * 1000;
    return parsed;
  } catch (err) {
    console.error('Failed to load credit state from localStorage', err);
    return INITIAL_DEFAULT_STATE;
  }
}

/**
 * Grant credits to user after successful payment or plan activation
 */
export function grantUserCredits(params: {
  credits: number;
  planOrPackName: string;
  amountPaid: number;
  currency: 'INR' | 'USD';
  invoiceNumber: string;
  type?: 'subscription' | 'topup' | 'custom_refill';
}): UserCreditState {
  const current = getUserCreditState();
  const creditsToAdd = Math.max(0, Math.round(params.credits));
  const newBalance = current.balance + creditsToAdd;
  const newTokens = newBalance * 1000;

  const newTx: CreditTransaction = {
    id: `tx_${Date.now().toString(36)}_${Math.random().toString(36).substring(2, 6)}`,
    date: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
    type: params.type || 'topup',
    credits: creditsToAdd,
    tokens: creditsToAdd * 1000,
    amountPaid: params.amountPaid,
    currency: params.currency,
    invoiceNumber: params.invoiceNumber,
    description: params.planOrPackName,
    status: 'verified',
  };

  const updatedState: UserCreditState = {
    ...current,
    balance: newBalance,
    tokens: newTokens,
    totalPurchased: current.totalPurchased + creditsToAdd,
    activePlan: params.type === 'subscription' ? params.planOrPackName : current.activePlan,
    lastUpdated: new Date().toISOString(),
    transactions: [newTx, ...current.transactions],
  };

  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedState));
    // Emit custom event for instant cross-component synchronization
    window.dispatchEvent(new CustomEvent('skelion:credits-updated', { detail: updatedState }));
  }

  return updatedState;
}

/**
 * Consume credits for inference execution
 */
export function consumeUserCredits(creditsToDeduct: number, reason: string): boolean {
  const current = getUserCreditState();
  if (current.balance < creditsToDeduct) {
    return false;
  }

  const newBalance = Math.max(0, current.balance - creditsToDeduct);
  const updatedState: UserCreditState = {
    ...current,
    balance: newBalance,
    tokens: newBalance * 1000,
    lastUpdated: new Date().toISOString(),
    transactions: [
      {
        id: `tx_use_${Date.now().toString(36)}`,
        date: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
        type: 'custom_refill',
        credits: -creditsToDeduct,
        tokens: -creditsToDeduct * 1000,
        amountPaid: 0,
        currency: 'INR',
        invoiceNumber: `USAGE-${Date.now().toString(36).toUpperCase()}`,
        description: `Consumed: ${reason}`,
        status: 'completed',
      },
      ...current.transactions,
    ],
  };

  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedState));
    window.dispatchEvent(new CustomEvent('skelion:credits-updated', { detail: updatedState }));
  }

  return true;
}
