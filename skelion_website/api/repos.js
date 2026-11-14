// api/repos.js — GitHub Repositories & Tree Proxy for Skelion Workspace
// Enables live repository exploration and file inspection without client CORS or rate-limit issues

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const { searchParams } = new URL(req.url, 'http://localhost');
  const action = searchParams.get('action') || 'list';
  const username = searchParams.get('username') || 'Aditya-9-6';
  const owner = searchParams.get('owner') || username;
  const repo = searchParams.get('repo') || 'Skelion_website';
  const branch = searchParams.get('branch') || 'main';
  const filePath = searchParams.get('path') || '';

  const clientAuth = req.headers.authorization;
  const configuredToken = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
  const authHeader =
    clientAuth && !clientAuth.includes('mock')
      ? clientAuth
      : configuredToken
        ? `Bearer ${configuredToken}`
        : undefined;

  const defaultHeaders = {
    'User-Agent': 'Skelion-Web-Workspace/1.0',
    Accept: 'application/vnd.github.v3+json',
    ...(authHeader ? { Authorization: authHeader } : {}),
  };

  try {
    if (action === 'list') {
      // 1. Fetch user repos
      const ghUrl = `https://api.github.com/users/${encodeURIComponent(username)}/repos?sort=updated&per_page=30`;
      const ghRes = await fetch(ghUrl, { headers: defaultHeaders });

      if (ghRes.ok) {
        const data = await ghRes.json();
        const repos = data.map((r) => ({
          name: r.name,
          full_name: r.full_name,
          description: r.description || 'Autonomous resilience repository',
          default_branch: r.default_branch || 'main',
          language: r.language || 'TypeScript',
          stars: r.stargazers_count || 0,
          updated_at: r.updated_at,
          private: r.private,
        }));
        return res.status(200).json({ success: true, repos });
      }

      // If user repos fails (e.g. org or 404), try authenticated /user/repos
      const authUserRes = await fetch('https://api.github.com/user/repos?sort=updated&per_page=30', {
        headers: defaultHeaders,
      });

      if (authUserRes.ok) {
        const data = await authUserRes.json();
        const repos = data.map((r) => ({
          name: r.name,
          full_name: r.full_name,
          description: r.description || 'Autonomous resilience repository',
          default_branch: r.default_branch || 'main',
          language: r.language || 'TypeScript',
          stars: r.stargazers_count || 0,
          updated_at: r.updated_at,
          private: r.private,
        }));
        return res.status(200).json({ success: true, repos });
      }

      throw new Error(`GitHub API error: ${ghRes.status}`);
    }

    if (action === 'tree') {
      // 2. Fetch git tree recursively
      const ghTreeUrl = `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/git/trees/${encodeURIComponent(branch)}?recursive=1`;
      const treeRes = await fetch(ghTreeUrl, { headers: defaultHeaders });

      if (treeRes.ok) {
        const treeData = await treeRes.json();
        const items = (treeData.tree || [])
          .filter((item) => !item.path.startsWith('.git/'))
          .map((item) => ({
            path: item.path,
            type: item.type === 'tree' ? 'dir' : 'file',
            size: item.size || 0,
          }));
        return res.status(200).json({ success: true, tree: items });
      }

      // Fallback to top-level contents
      const contentsUrl = `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/contents`;
      const contentsRes = await fetch(contentsUrl, { headers: defaultHeaders });

      if (contentsRes.ok) {
        const cData = await contentsRes.json();
        const items = cData.map((item) => ({
          path: item.path,
          type: item.type === 'dir' ? 'dir' : 'file',
          size: item.size || 0,
        }));
        return res.status(200).json({ success: true, tree: items });
      }

      throw new Error(`GitHub Tree error: ${treeRes.status}`);
    }

    if (action === 'file') {
      if (!filePath) {
        return res.status(400).json({ error: 'Missing path parameter' });
      }

      const fileUrl = `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/contents/${filePath}?ref=${encodeURIComponent(branch)}`;
      const fileRes = await fetch(fileUrl, { headers: defaultHeaders });

      if (fileRes.ok) {
        const fileData = await fileRes.json();
        let content = '';
        if (fileData.encoding === 'base64' && fileData.content) {
          content = Buffer.from(fileData.content, 'base64').toString('utf8');
        } else if (fileData.download_url) {
          const rawRes = await fetch(fileData.download_url);
          content = await rawRes.text();
        }
        return res.status(200).json({
          success: true,
          path: filePath,
          content,
          size: fileData.size,
        });
      }

      throw new Error(`GitHub File error: ${fileRes.status}`);
    }

    return res.status(400).json({ error: `Unknown action: ${action}` });
  } catch (err) {
    console.error('[Skelion API Repos] GitHub request failed:', err);
    return res.status(502).json({ error: 'GitHub API request failed.' });
  }
}
