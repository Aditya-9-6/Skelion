export interface UserProfile {
  id: number;
  username: string;
  name: string;
  avatar: string;
  email?: string | null;
  bio?: string | null;
  html_url?: string;
  updatedAt?: string;
}

let dynamicClientId: string | null = null;
const CUSTOM_CLIENT_ID_KEY = 'skelion_github_client_id';

export const setCustomGitHubClientId = (clientId: string): void => {
  if (typeof window === 'undefined') return;
  const trimmed = clientId.trim();
  if (trimmed) {
    localStorage.setItem(CUSTOM_CLIENT_ID_KEY, trimmed);
    dynamicClientId = trimmed;
  } else {
    localStorage.removeItem(CUSTOM_CLIENT_ID_KEY);
    dynamicClientId = null;
  }
};

export const initAuthConfig = async (): Promise<void> => {
  if (typeof window === 'undefined') return;
  // 1. Check local storage override first
  try {
    const saved = localStorage.getItem(CUSTOM_CLIENT_ID_KEY);
    if (saved && saved.trim()) {
      dynamicClientId = saved.trim();
      return;
    }
  } catch (_) {}

  // 2. Fetch from backend API
  try {
    const res = await fetch('/api/auth/github?action=config');
    if (res.ok) {
      const data = await res.json();
      if (data && data.clientId) {
        dynamicClientId = data.clientId;
      }
    }
  } catch (_) {
    // Ignore offline or dev server without API endpoint
  }
};

export const getGitHubClientId = (): string => {
  if (dynamicClientId) return dynamicClientId;
  if (typeof window !== 'undefined') {
    try {
      const saved = localStorage.getItem(CUSTOM_CLIENT_ID_KEY);
      if (saved && saved.trim()) {
        dynamicClientId = saved.trim();
        return dynamicClientId;
      }
    } catch (_) {}
  }
  try {
    return (
      (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_GITHUB_CLIENT_ID) ||
      ''
    );
  } catch {
    return '';
  }
};

export const isLiveGitHubConfigured = (): boolean => {
  const clientId = getGitHubClientId();
  return Boolean(
    clientId &&
    !clientId.startsWith('Iv1.mock') &&
    clientId !== 'your_github_client_id_here' &&
    clientId.trim().length > 4
  );
};

export const getGitHubLoginUrl = async (): Promise<string> => {
  // Ensure we attempt to discover the server-side configured client ID if not yet loaded
  if (!dynamicClientId) {
    await initAuthConfig();
  }

  const clientId = getGitHubClientId();
  const redirectUri = window.location.origin + window.location.pathname;

  if (!isLiveGitHubConfigured()) {
    throw new Error(
      'GitHub Client ID is not configured yet. Please configure GITHUB_CLIENT_ID in your environment or enter your OAuth App Client ID.'
    );
  }

  return `https://github.com/login/oauth/authorize?client_id=${encodeURIComponent(
    clientId
  )}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=read:user,user:email`;
};

export const handleOAuthRedirect = async (): Promise<UserProfile | null> => {
  if (typeof window === 'undefined') return null;

  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get('code');
  const error = urlParams.get('error');
  const errorDescription = urlParams.get('error_description');

  if (error) {
    // Clean URL query parameters and preserve hash
    const targetHash = window.location.hash || '#home';
    window.history.replaceState({}, document.title, window.location.pathname + targetHash);
    throw new Error(errorDescription || `GitHub login was cancelled or denied: ${error}`);
  }

  if (!code) return null;

  // Clean URL query parameters so page refresh does not re-trigger OAuth exchange
  const targetHash = window.location.hash || '#dashboard';
  window.history.replaceState({}, document.title, window.location.pathname + targetHash);

  try {
    const currentClientId = getGitHubClientId();
    const response = await fetch('/api/auth/github', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, clientId: currentClientId || undefined }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || `Authentication failed (${response.status})`);
    }

    const data = await response.json();
    if (data.success && data.user) {
      localStorage.setItem('skelion_user', JSON.stringify(data.user));
      if (data.accessToken) {
        localStorage.setItem('skelion_github_token', data.accessToken);
      }
      return data.user;
    } else {
      throw new Error(data.error || 'Server returned invalid user profile data');
    }
  } catch (err: any) {
    console.error('GitHub OAuth error:', err);
    throw err;
  }
};

export const getStoredUser = (): UserProfile | null => {
  if (typeof window === 'undefined') return null;
  try {
    const stored = localStorage.getItem('skelion_user');
    if (!stored) return null;
    const user = JSON.parse(stored);
    // Purge any legacy fake mock user from earlier silent bypasses
    if (user && (user.id === 999999 || user.username === 'skelion-developer')) {
      const token = localStorage.getItem('skelion_github_token');
      if (!token || token.startsWith('gho_mock_') || token.includes('mock')) {
        localStorage.removeItem('skelion_user');
        localStorage.removeItem('skelion_github_token');
        return null;
      }
    }
    return user;
  } catch {
    return null;
  }
};

export const logoutUser = (): void => {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem('skelion_user');
    localStorage.removeItem('skelion_github_token');
  } catch (e) {
    console.error('Failed to clear user from localStorage:', e);
  }
};

export const simulateMockLogin = (): UserProfile => {
  const mockUser: UserProfile = {
    id: 1337001,
    username: 'github-explorer',
    name: 'GitHub Explorer',
    avatar: 'https://avatars.githubusercontent.com/u/583231?v=4',
    email: 'explorer@github.com',
    bio: 'Resilience Architecture Specialist',
    html_url: 'https://github.com/github-explorer',
    updatedAt: new Date().toISOString(),
  };
  if (typeof window !== 'undefined') {
    localStorage.setItem('skelion_user', JSON.stringify(mockUser));
    localStorage.setItem('skelion_github_token', 'gho_mock_token_demo_mode');
  }
  return mockUser;
};
