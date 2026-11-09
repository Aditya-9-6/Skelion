// src/utils/github.integration.test.ts
import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  GITHUB_TOKEN_KEY,
  setGitHubToken,
  getGitHubToken,
  removeGitHubToken,
  githubRequest,
  listRepos,
  listIssues,
  listPullRequests,
  getIssue,
  getPullRequest,
  createIssue,
  createPullRequest,
  mergePullRequest,
  closeIssue,
  reopenIssue,
  closePullRequest,
  reopenPullRequest,
  commentOn,
  listComments,
  listBranches,
  createBranch,
  commitFileAndCreatePR,
} from './github.ts';

// In-memory mock localStorage for Node.js test environment
const mockStorage: Record<string, string> = {};
(globalThis as any).localStorage = {
  getItem: (k: string) => mockStorage[k] ?? null,
  setItem: (k: string, v: string) => { mockStorage[k] = v; },
  removeItem: (k: string) => { delete mockStorage[k]; },
  clear: () => { Object.keys(mockStorage).forEach(k => delete mockStorage[k]); },
};

describe('GitHub Integration & Token Utilities', () => {
  const originalFetch = globalThis.fetch;
  let lastFetchUrl = '';
  let lastFetchOpts: RequestInit | undefined;

  beforeEach(() => {
    (globalThis as any).localStorage.clear();
    lastFetchUrl = '';
    lastFetchOpts = undefined;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('manages personal access token in localStorage', () => {
    assert.equal(getGitHubToken(), null);
    setGitHubToken('ghp_test_token_12345');
    assert.equal(getGitHubToken(), 'ghp_test_token_12345');
    assert.equal(localStorage.getItem(GITHUB_TOKEN_KEY), 'ghp_test_token_12345');
    removeGitHubToken();
    assert.equal(getGitHubToken(), null);
  });

  it('injects Authorization, Accept, and X-GitHub-Api-Version headers in githubRequest', async () => {
    setGitHubToken('ghp_secure_secret_token');

    globalThis.fetch = async (url: any, opts: any) => {
      lastFetchUrl = String(url);
      lastFetchOpts = opts;
      return new Response(JSON.stringify({ ok: true, url }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    };

    const res = await githubRequest('https://api.github.com/user');
    assert.equal(res.ok, true);
    assert.equal(lastFetchUrl, 'https://api.github.com/user');

    const headers = lastFetchOpts?.headers as Record<string, string>;
    assert.equal(headers['Accept'], 'application/vnd.github+json');
    assert.equal(headers['X-GitHub-Api-Version'], '2022-11-28');
    assert.equal(headers['Authorization'], 'Bearer ghp_secure_secret_token');
  });

  it('supports fine-grained personal access tokens (github_pat_...)', async () => {
    setGitHubToken('   github_pat_11ABCDEF_xyz987   ');
    assert.equal(getGitHubToken(), 'github_pat_11ABCDEF_xyz987');

    globalThis.fetch = async (url: any, opts: any) => {
      lastFetchUrl = String(url);
      lastFetchOpts = opts;
      return new Response(JSON.stringify({ login: 'octocat' }), { status: 200 });
    };

    await githubRequest('https://api.github.com/user');
    const headers = lastFetchOpts?.headers as Record<string, string>;
    assert.equal(headers['Authorization'], 'Bearer github_pat_11ABCDEF_xyz987');
  });

  it('handles 204 No Content responses correctly', async () => {
    globalThis.fetch = async () => new Response(null, { status: 204 });
    const res = await githubRequest('https://api.github.com/repos/test/test/subscription', { method: 'PUT' });
    assert.deepEqual(res, { success: true });
  });

  it('throws descriptive error on API failure', async () => {
    globalThis.fetch = async () =>
      new Response(JSON.stringify({ message: 'Bad credentials', documentation_url: 'https://docs.github.com' }), {
        status: 401,
        statusText: 'Unauthorized',
        headers: { 'Content-Type': 'application/json' },
      });

    await assert.rejects(
      async () => {
        await githubRequest('https://api.github.com/user');
      },
      /401: Bad credentials/
    );
  });

  it('listRepos targets /user/repos when authenticated and no specific user provided', async () => {
    setGitHubToken('ghp_authenticated_token');

    globalThis.fetch = async (url: any) => {
      lastFetchUrl = String(url);
      return new Response(JSON.stringify([{ name: 'repo-private', private: true }]), { status: 200 });
    };

    const repos = await listRepos();
    assert.equal(repos.length, 1);
    assert.equal(repos[0].name, 'repo-private');
    assert.ok(lastFetchUrl.includes('/user/repos'));
  });

  it('listRepos targets /users/:username/repos when user is passed', async () => {
    globalThis.fetch = async (url: any) => {
      lastFetchUrl = String(url);
      return new Response(JSON.stringify([{ name: 'public-repo' }]), { status: 200 });
    };

    const repos = await listRepos('octocat');
    assert.equal(repos.length, 1);
    assert.ok(lastFetchUrl.includes('/users/octocat/repos'));
  });

  it('listIssues targets /repos/:owner/:repo/issues with query params', async () => {
    globalThis.fetch = async (url: any) => {
      lastFetchUrl = String(url);
      return new Response(JSON.stringify([{ number: 42, title: 'Bug in edge mesh' }]), { status: 200 });
    };

    const issues = await listIssues('Aditya-9-6', 'Skelion', '?state=open');
    assert.equal(issues.length, 1);
    assert.equal(issues[0].number, 42);
    assert.equal(lastFetchUrl, 'https://api.github.com/repos/Aditya-9-6/Skelion/issues?state=open');
  });

  it('listPullRequests targets /repos/:owner/:repo/pulls', async () => {
    globalThis.fetch = async (url: any) => {
      lastFetchUrl = String(url);
      return new Response(JSON.stringify([{ number: 89, title: 'Fix zero-downtime rotation' }]), { status: 200 });
    };

    const prs = await listPullRequests('Aditya-9-6', 'Skelion');
    assert.equal(prs.length, 1);
    assert.equal(prs[0].number, 89);
    assert.equal(lastFetchUrl, 'https://api.github.com/repos/Aditya-9-6/Skelion/pulls');
  });

  it('createIssue posts new issue with payload', async () => {
    globalThis.fetch = async (url: any, opts: any) => {
      lastFetchUrl = String(url);
      lastFetchOpts = opts;
      return new Response(JSON.stringify({ number: 101, title: 'New Test Issue' }), { status: 201 });
    };

    const res = await createIssue('Aditya-9-6', 'Skelion', {
      title: 'New Test Issue',
      body: 'Detailed description',
      labels: ['bug', 'resilience'],
    });

    assert.equal(res.number, 101);
    assert.equal(lastFetchUrl, 'https://api.github.com/repos/Aditya-9-6/Skelion/issues');
    assert.equal(lastFetchOpts?.method, 'POST');
    const parsedBody = JSON.parse(lastFetchOpts?.body as string);
    assert.equal(parsedBody.title, 'New Test Issue');
    assert.deepEqual(parsedBody.labels, ['bug', 'resilience']);
  });

  it('createPullRequest posts new pull request with head and base', async () => {
    globalThis.fetch = async (url: any, opts: any) => {
      lastFetchUrl = String(url);
      lastFetchOpts = opts;
      return new Response(JSON.stringify({ number: 102, title: 'feat: add mesh' }), { status: 201 });
    };

    const res = await createPullRequest('Aditya-9-6', 'Skelion', {
      title: 'feat: add mesh',
      head: 'feature-mesh',
      base: 'main',
      body: 'PR description',
    });

    assert.equal(res.number, 102);
    assert.equal(lastFetchUrl, 'https://api.github.com/repos/Aditya-9-6/Skelion/pulls');
    assert.equal(lastFetchOpts?.method, 'POST');
    const parsed = JSON.parse(lastFetchOpts?.body as string);
    assert.equal(parsed.head, 'feature-mesh');
    assert.equal(parsed.base, 'main');
  });

  it('mergePullRequest sends PUT request to /pulls/:number/merge', async () => {
    globalThis.fetch = async (url: any, opts: any) => {
      lastFetchUrl = String(url);
      lastFetchOpts = opts;
      return new Response(JSON.stringify({ sha: 'abcdef123456', merged: true, message: 'Pull Request successfully merged' }), { status: 200 });
    };

    const res = await mergePullRequest('Aditya-9-6', 'Skelion', 89, 'Merged via Skelion IDE');
    assert.equal(res.merged, true);
    assert.equal(lastFetchUrl, 'https://api.github.com/repos/Aditya-9-6/Skelion/pulls/89/merge');
    assert.equal(lastFetchOpts?.method, 'PUT');
    const parsed = JSON.parse(lastFetchOpts?.body as string);
    assert.equal(parsed.commit_message, 'Merged via Skelion IDE');
  });

  it('closeIssue sends PATCH with state: closed', async () => {
    globalThis.fetch = async (url: any, opts: any) => {
      lastFetchUrl = String(url);
      lastFetchOpts = opts;
      return new Response(JSON.stringify({ number: 42, state: 'closed' }), { status: 200 });
    };

    const res = await closeIssue('Aditya-9-6', 'Skelion', 42);
    assert.equal(res.state, 'closed');
    assert.equal(lastFetchUrl, 'https://api.github.com/repos/Aditya-9-6/Skelion/issues/42');
    assert.equal(lastFetchOpts?.method, 'PATCH');
    const parsed = JSON.parse(lastFetchOpts?.body as string);
    assert.equal(parsed.state, 'closed');
  });

  it('commentOn posts comment body to /issues/:number/comments', async () => {
    globalThis.fetch = async (url: any, opts: any) => {
      lastFetchUrl = String(url);
      lastFetchOpts = opts;
      return new Response(JSON.stringify({ id: 999, body: 'Looking into this trace now' }), { status: 201 });
    };

    const res = await commentOn('Aditya-9-6', 'Skelion', 42, 'Looking into this trace now');
    assert.equal(res.id, 999);
    assert.equal(lastFetchUrl, 'https://api.github.com/repos/Aditya-9-6/Skelion/issues/42/comments');
    assert.equal(lastFetchOpts?.method, 'POST');
    const parsed = JSON.parse(lastFetchOpts?.body as string);
    assert.equal(parsed.body, 'Looking into this trace now');
  });

  it('reopenIssue sends PATCH with state: open', async () => {
    globalThis.fetch = async (url: any, opts: any) => {
      lastFetchUrl = String(url);
      lastFetchOpts = opts;
      return new Response(JSON.stringify({ number: 42, state: 'open' }), { status: 200 });
    };

    const res = await reopenIssue('Aditya-9-6', 'Skelion', 42);
    assert.equal(res.state, 'open');
    assert.equal(lastFetchUrl, 'https://api.github.com/repos/Aditya-9-6/Skelion/issues/42');
    assert.equal(lastFetchOpts?.method, 'PATCH');
    const parsed = JSON.parse(lastFetchOpts?.body as string);
    assert.equal(parsed.state, 'open');
  });

  it('closePullRequest sends PATCH with state: closed', async () => {
    globalThis.fetch = async (url: any, opts: any) => {
      lastFetchUrl = String(url);
      lastFetchOpts = opts;
      return new Response(JSON.stringify({ number: 88, state: 'closed' }), { status: 200 });
    };

    const res = await closePullRequest('Aditya-9-6', 'Skelion', 88);
    assert.equal(res.state, 'closed');
    assert.equal(lastFetchUrl, 'https://api.github.com/repos/Aditya-9-6/Skelion/pulls/88');
    assert.equal(lastFetchOpts?.method, 'PATCH');
    const parsed = JSON.parse(lastFetchOpts?.body as string);
    assert.equal(parsed.state, 'closed');
  });

  it('reopenPullRequest sends PATCH with state: open', async () => {
    globalThis.fetch = async (url: any, opts: any) => {
      lastFetchUrl = String(url);
      lastFetchOpts = opts;
      return new Response(JSON.stringify({ number: 88, state: 'open' }), { status: 200 });
    };

    const res = await reopenPullRequest('Aditya-9-6', 'Skelion', 88);
    assert.equal(res.state, 'open');
    assert.equal(lastFetchUrl, 'https://api.github.com/repos/Aditya-9-6/Skelion/pulls/88');
    assert.equal(lastFetchOpts?.method, 'PATCH');
    const parsed = JSON.parse(lastFetchOpts?.body as string);
    assert.equal(parsed.state, 'open');
  });

  it('getIssue fetches single issue by number', async () => {
    globalThis.fetch = async (url: any) => {
      lastFetchUrl = String(url);
      return new Response(JSON.stringify({ number: 7, title: 'Single Issue' }), { status: 200 });
    };

    const res = await getIssue('Aditya-9-6', 'Skelion', 7);
    assert.equal(res.number, 7);
    assert.equal(lastFetchUrl, 'https://api.github.com/repos/Aditya-9-6/Skelion/issues/7');
  });

  it('getPullRequest fetches single pull request by number', async () => {
    globalThis.fetch = async (url: any) => {
      lastFetchUrl = String(url);
      return new Response(JSON.stringify({ number: 12, title: 'Single PR', mergeable: true }), { status: 200 });
    };

    const res = await getPullRequest('Aditya-9-6', 'Skelion', 12);
    assert.equal(res.number, 12);
    assert.equal(res.mergeable, true);
    assert.equal(lastFetchUrl, 'https://api.github.com/repos/Aditya-9-6/Skelion/pulls/12');
  });

  it('listComments fetches discussion comments for issue/PR', async () => {
    globalThis.fetch = async (url: any) => {
      lastFetchUrl = String(url);
      return new Response(JSON.stringify([{ id: 1, body: 'First comment' }, { id: 2, body: 'Second comment' }]), { status: 200 });
    };

    const comments = await listComments('Aditya-9-6', 'Skelion', 42);
    assert.equal(comments.length, 2);
    assert.equal(comments[0].body, 'First comment');
    assert.equal(lastFetchUrl, 'https://api.github.com/repos/Aditya-9-6/Skelion/issues/42/comments');
  });

  it('listBranches targets /repos/:owner/:repo/branches', async () => {
    globalThis.fetch = async (url: any) => {
      lastFetchUrl = String(url);
      return new Response(
        JSON.stringify([
          { name: 'main', commit: { sha: '1111' } },
          { name: 'feat/ast-patch', commit: { sha: '2222' } }
        ]),
        { status: 200 }
      );
    };

    const branches = await listBranches('Aditya-9-6', 'Skelion');
    assert.equal(branches.length, 2);
    assert.equal(branches[0].name, 'main');
    assert.equal(branches[1].name, 'feat/ast-patch');
    assert.ok(lastFetchUrl.includes('/repos/Aditya-9-6/Skelion/branches'));
  });

  it('createBranch posts new git ref to /repos/:owner/:repo/git/refs', async () => {
    globalThis.fetch = async (url: any, opts: any) => {
      lastFetchUrl = String(url);
      lastFetchOpts = opts;
      if (lastFetchUrl.includes('/git/ref/heads/main')) {
        return new Response(JSON.stringify({ object: { sha: 'base_sha_123' } }), { status: 200 });
      }
      return new Response(JSON.stringify({ ref: 'refs/heads/feat/new-test', object: { sha: 'base_sha_123' } }), { status: 201 });
    };

    const res = await createBranch('Aditya-9-6', 'Skelion', 'feat/new-test', 'main');
    assert.equal(res.ref, 'refs/heads/feat/new-test');
    assert.equal(res.sha, 'base_sha_123');
  });

  it('createBranch correctly encodes multi-segment base branch paths', async () => {
    let requestedHeadUrl = '';
    globalThis.fetch = async (url: any, opts: any) => {
      lastFetchUrl = String(url);
      lastFetchOpts = opts;
      if (lastFetchUrl.includes('/git/ref/heads/')) {
        requestedHeadUrl = lastFetchUrl;
        return new Response(JSON.stringify({ object: { sha: 'branch_sha_456' } }), { status: 200 });
      }
      return new Response(JSON.stringify({ ref: 'refs/heads/patch/hotfix', object: { sha: 'branch_sha_456' } }), { status: 201 });
    };

    const res = await createBranch('Aditya-9-6', 'Skelion', 'patch/hotfix', 'feat/circuit-breaker');
    assert.equal(res.ref, 'refs/heads/patch/hotfix');
    assert.equal(res.sha, 'branch_sha_456');
    assert.ok(requestedHeadUrl.includes('/git/ref/heads/feat/circuit-breaker'));
  });

  it('commitFileAndCreatePR creates branch, commits file, and opens pull request', async () => {
    const urlsCalled: string[] = [];
    globalThis.fetch = async (url: any, opts: any) => {
      const urlStr = String(url);
      urlsCalled.push(urlStr);
      lastFetchOpts = opts;

      if (urlStr.includes('/git/ref/heads/main')) {
        return new Response(JSON.stringify({ object: { sha: 'sha_base' } }), { status: 200 });
      }
      if (urlStr.includes('/git/refs')) {
        return new Response(JSON.stringify({ ref: 'refs/heads/patch/test-branch', object: { sha: 'sha_base' } }), { status: 201 });
      }
      if (urlStr.includes('/contents/')) {
        return new Response(JSON.stringify({ content: { sha: 'sha_file_new' } }), { status: 200 });
      }
      if (urlStr.includes('/pulls')) {
        return new Response(
          JSON.stringify({
            number: 77,
            title: 'fix(resilienceGateway.ts): apply AST patch',
            head: { ref: 'patch/test-branch' },
            base: { ref: 'main' },
            state: 'open',
          }),
          { status: 201 }
        );
      }
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    };

    const pr = await commitFileAndCreatePR('Aditya-9-6', 'Skelion', {
      filename: 'src/services/resilienceGateway.ts',
      content: '// updated code',
      branchName: 'patch/test-branch',
      commitMessage: 'fix(resilienceGateway.ts): apply AST patch',
      prTitle: 'fix(resilienceGateway.ts): apply AST patch',
      prBody: 'Automated patch from review card',
    });

    assert.equal(pr.number, 77);
    assert.equal(pr.title, 'fix(resilienceGateway.ts): apply AST patch');
    assert.ok(urlsCalled.some(u => u.includes('/contents/src/services/resilienceGateway.ts')));
    assert.ok(urlsCalled.some(u => u.includes('/pulls')));
  });
});
