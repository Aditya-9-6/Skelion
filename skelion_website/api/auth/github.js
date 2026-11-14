import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function saveUserToFile(userProfile) {
  try {
    const possibleBases = [
      process.cwd(),
      path.join(process.cwd(), 'skelion_website'),
      path.resolve(__dirname, '..'),
      path.resolve(__dirname, '../..'),
    ];

    let baseDir = process.cwd();
    for (const b of possibleBases) {
      const pkgPath = path.join(b, 'package.json');
      if (fs.existsSync(pkgPath)) {
        try {
          const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
          if (pkg.name === 'skelion-website') {
            baseDir = b;
            break;
          }
        } catch (_) {}
      }
    }

    const dataDir = path.join(baseDir, 'data');
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }

    const usersFile = path.join(dataDir, 'users.json');
    let users = [];
    if (fs.existsSync(usersFile)) {
      try {
        const fileContent = fs.readFileSync(usersFile, 'utf8');
        users = JSON.parse(fileContent);
        if (!Array.isArray(users)) users = [];
      } catch (_) {
        users = [];
      }
    }

    const existingIndex = users.findIndex((u) => u.id === userProfile.id);
    if (existingIndex >= 0) {
      users[existingIndex] = { ...users[existingIndex], ...userProfile };
    } else {
      users.push(userProfile);
    }

    fs.writeFileSync(usersFile, JSON.stringify(users, null, 2), 'utf8');
    return true;
  } catch (fsErr) {
    console.warn('File system storage warning (e.g. read-only serverless environment):', fsErr.message);
    return false;
  }
}

export default async function handler(req, res) {
  const allowedOrigin = process.env.ALLOWED_ORIGIN || '';
  const origin = req.headers?.origin;
  if (allowedOrigin && origin === allowedOrigin) {
    res.setHeader('Access-Control-Allow-Origin', allowedOrigin);
    res.setHeader('Vary', 'Origin');
  }
  // Setup helper methods for environments where res is standard Node http.ServerResponse
  const sendJson = (statusCode, data) => {
    if (typeof res.status === 'function') {
      res.status(statusCode);
    } else {
      res.statusCode = statusCode;
    }

    if (typeof res.json === 'function') {
      return res.json(data);
    }
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify(data));
  };

  if (req.method !== 'POST' && req.method !== 'GET') {
    return sendJson(405, { error: 'Method not allowed. Use POST or GET.' });
  }

  // Parse body or query
  let body = req.body;
  if (typeof body === 'string') {
    try {
      body = JSON.parse(body);
    } catch (_) {
      body = {};
    }
  }

  let code = (body && body.code) || (req.query && req.query.code);

  if (!code && req.url) {
    try {
      const parsedUrl = new URL(req.url, 'http://localhost');
      code = parsedUrl.searchParams.get('code');
    } catch (_) {}
  }

  // Support public config query for frontend to discover configured client ID
  let action = (req.query && req.query.action);
  if (!action && req.url) {
    try {
      const parsedUrl = new URL(req.url, 'http://localhost');
      action = parsedUrl.searchParams.get('action');
    } catch (_) {}
  }

  const clientId = (body && body.clientId) || (req.query && req.query.clientId) || process.env.GITHUB_CLIENT_ID || process.env.VITE_GITHUB_CLIENT_ID;
  const clientSecret = process.env.GITHUB_CLIENT_SECRET;

  if (action === 'config') {
    return sendJson(200, {
      configured: Boolean(clientId && clientSecret),
      clientId: clientId || null,
    });
  }

  if (!code) {
    return sendJson(400, { error: 'Missing GitHub OAuth code' });
  }

  // Handle mock/test codes (useful for dev and CI environments)
  if (process.env.ALLOW_DEMO_AUTH === 'true' && (code.startsWith('mock_') || code.startsWith('test_'))) {
    const isErrorTest = code.includes('error');
    if (isErrorTest) {
      return sendJson(400, { error: 'Invalid or expired authorization code' });
    }

    const mockUser = {
      id: 999999,
      username: 'skelion-developer',
      name: 'Skelion Developer',
      avatar: 'https://avatars.githubusercontent.com/u/999999?v=4',
      email: 'developer@skelion.ai',
      bio: 'Skelion Autonomous Resilience Engineer',
      html_url: 'https://github.com/skelion-developer',
      updatedAt: new Date().toISOString(),
    };

    saveUserToFile(mockUser);

    return sendJson(200, {
      success: true,
      user: mockUser,
      accessToken: 'gho_mock_access_token_for_testing',
    });
  }

  if (!clientId || !clientSecret) {
    return sendJson(500, {
      error: 'GitHub OAuth credentials not configured on server (GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET required)',
    });
  }

  try {
    // 1. Exchange code for access token
    const tokenResponse = await fetch('https://github.com/login/oauth/access_token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        client_id: clientId,
        client_secret: clientSecret,
        code,
      }),
    });

    if (!tokenResponse.ok) {
      return sendJson(502, { error: `GitHub OAuth service error (${tokenResponse.status})` });
    }

    const tokenData = await tokenResponse.json();

    if (tokenData.error || !tokenData.access_token) {
      return sendJson(400, {
        error: tokenData.error_description || tokenData.error || 'Failed to obtain access token from GitHub',
      });
    }

    const accessToken = tokenData.access_token;

    // 2. Fetch user profile from GitHub API
    const userResponse = await fetch('https://api.github.com/user', {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'User-Agent': 'Skelion-OAuth-App',
        Accept: 'application/vnd.github.v3+json',
      },
    });

    if (!userResponse.ok) {
      return sendJson(userResponse.status || 502, {
        error: 'Failed to fetch user profile from GitHub API',
      });
    }

    const githubUser = await userResponse.json();

    const userProfile = {
      id: githubUser.id,
      username: githubUser.login,
      name: githubUser.name || githubUser.login,
      avatar: githubUser.avatar_url,
      email: githubUser.email || null,
      bio: githubUser.bio || null,
      html_url: githubUser.html_url || `https://github.com/${githubUser.login}`,
      updatedAt: new Date().toISOString(),
    };

    // 3. Store user in data/users.json
    saveUserToFile(userProfile);

    return sendJson(200, {
      success: true,
      user: userProfile,
      accessToken,
    });
  } catch (err) {
    console.error('GitHub OAuth error:', err);
    return sendJson(500, {
      error: err.message || 'Internal server error during GitHub authentication',
    });
  }
}
