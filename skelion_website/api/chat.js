// api/chat.js — Skelion AI Agent Serverless Chat Endpoint
// Runs on Vercel Serverless Function using GPT-OSS 120B via Groq OpenAI-compatible API

function extractAllFileChanges(text) {
  if (!text) return [];
  // Match code blocks with optional file attribute or [FILE: ...]
  // e.g. ```typescript file="src/monitoring/metrics.ts"
  // e.g. ```typescript filename="src/monitoring/metrics.ts"
  // e.g. ```typescript [FILE: src/monitoring/metrics.ts]
  // e.g. ```typescript:src/monitoring/metrics.ts
  // e.g. ```typescript
  const blockRegex = /```([a-zA-Z0-9_\-+]*)(?:[ \t]+(?:file|filename)=["']?([^"'\n\r]+)["']?|[ \t]+\[FILE:\s*([^\]]+)\]|:([a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9]+))?[ \t]*\r?\n([\s\S]*?)```/g;
  const changes = [];
  let match;

  while ((match = blockRegex.exec(text)) !== null) {
    const rawLang = match[1] || 'typescript';
    let declaredFile = match[2] || match[3] || match[4] || '';
    const content = match[5].trim();
    let filename = declaredFile.trim();

    if (!filename) {
      // Check first line for comment like // src/... or # src/...
      const firstLine = content.split('\n')[0] || '';
      const fileMatch =
        firstLine.match(/\/\/\s*(?:filename:)?\s*([a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9]+)/i) ||
        firstLine.match(/#\s*(?:filename:)?\s*([a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9]+)/i) ||
        firstLine.match(/\/\*\s*(?:filename:)?\s*([a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9]+)\s*\*\//i);
      if (fileMatch && fileMatch[1]) {
        filename = fileMatch[1].trim();
      }
    }

    if (!filename) {
      if (rawLang.toLowerCase().includes('py')) {
        filename = 'src/services/resilience_patch.py';
      } else if (rawLang.toLowerCase().includes('sql')) {
        filename = 'migrations/auto_patch.sql';
      } else if (rawLang.toLowerCase().includes('yml') || rawLang.toLowerCase().includes('yaml')) {
        filename = '.github/workflows/canary.yml';
      } else if (rawLang.toLowerCase().includes('json')) {
        filename = 'package.json';
      } else {
        filename = `src/patches/patch-${changes.length + 1}.ts`;
      }
    }

    changes.push({
      filename,
      language: rawLang || 'typescript',
      action: 'modify',
      content,
    });
  }

  return changes;
}

function extractCodeSnippet(text) {
  const changes = extractAllFileChanges(text);
  return changes.length > 0 ? changes[0] : null;
}

export default async function handler(req, res) {
  const allowedOrigin = process.env.ALLOWED_ORIGIN || '';
  const origin = req.headers?.origin;
  if (allowedOrigin && origin === allowedOrigin) {
    res.setHeader('Access-Control-Allow-Origin', allowedOrigin);
    res.setHeader('Vary', 'Origin');
  }
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    if (allowedOrigin && origin !== allowedOrigin) {
      return res.status(403).json({ error: 'Origin not allowed' });
    }
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed. Use POST.' });
  }

  const startTime = Date.now();

  try {
    let body = req.body;
    if (typeof body === 'string') {
      try {
        body = JSON.parse(body);
      } catch (_) {
        body = {};
      }
    }

    const { messages, prompt } = body || {};

    const systemPrompt = `You are Skelion AI Agent, an autonomous incident intelligence and resilience engineering coding agent (similar to Google Antigravity, Cursor, and Devin).
You monitor production edge telemetry, validate zero-restart configurations, and automatically synthesize AST patches, feature implementations, and system modifications.

CRITICAL INSTRUCTIONS FOR CODE CHANGES & IMPLEMENTATION:
When the user asks to implement, build, patch, edit, create, or modify code, metrics, workflows, or files:
1. NEVER output mere conversational advice, tutorials, or numbered step-by-step instructions telling the user "how" to do it!
2. YOU MUST DIRECTLY SYNTHESIZE AND WRITE THE ACTUAL COMPLETE CODE FOR EACH TARGET FILE!
3. Format every file change in a structured markdown code block with the exact file path declared in the header, for example:
\`\`\`typescript file="src/monitoring/metrics.ts"
// complete production-grade implementation
\`\`\`
or
\`\`\`yaml file=".github/workflows/canary.yml"
# complete workflow
\`\`\`
4. If a task requires changes across multiple files, output each file as its own separate structured code block with its \`file="..."\` attribute.
5. Provide complete, production-ready code so the user can immediately review the diff and click "Accept & Apply Changes".
6. Keep conversational commentary minimal (1-2 crisp, high-signal sentences explaining the resolution). Let the structured code blocks drive the interactive review.
7. Focus on zero-downtime, circuit-breaker backoffs, AST hallmark validation, and PII-safe logging.
8. NEVER mention internal model names (such as GPT-OSS, Llama, Claude, DeepSeek, or Gemini). You are purely the native Skelion AI Agent.`;

    let formattedMessages = [];

    if (Array.isArray(messages) && messages.length > 0) {
      formattedMessages = [
        { role: 'system', content: systemPrompt },
        ...messages.map((m) => ({
          role: m.sender === 'user' || m.role === 'user' ? 'user' : 'assistant',
          content: m.text || m.content || '',
        })).filter((m) => m.content && m.content.trim().length > 0),
      ];
    } else if (prompt && typeof prompt === 'string') {
      formattedMessages = [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: prompt.trim() },
      ];
    } else {
      return res.status(400).json({ error: 'Missing prompt or messages in request body.' });
    }

    const apiKey = process.env.GROQ_API_KEY;
    if (!apiKey) {
      return res.status(503).json({
        error: 'AI chat is not configured. Set GROQ_API_KEY in the deployment environment.',
      });
    }

    const groqResponse = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
        'User-Agent': 'Skelion/1.0',
      },
      body: JSON.stringify({
        model: 'openai/gpt-oss-120b',
        messages: formattedMessages,
        temperature: 0.25,
        max_tokens: 2048,
      }),
    });

    if (!groqResponse.ok) {
      const errorText = await groqResponse.text();
      console.error('[Skelion API Chat] Groq upstream error:', groqResponse.status, errorText);
      return res.status(502).json({ error: 'The AI provider is temporarily unavailable.' });
    }

    const data = await groqResponse.json();
    const replyText =
      (data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content) ||
      'No response generated by Skelion Agent.';

    const latencyMs = Date.now() - startTime;
    const tokensUsed = (data.usage && data.usage.total_tokens) || Math.round(replyText.length / 4);

    const fileChanges = extractAllFileChanges(replyText);
    const codeSnippet = fileChanges.length > 0 ? fileChanges[0] : null;

    return res.status(200).json({
      id: `ast-${Date.now()}`,
      sender: 'assistant',
      model: 'Skelion AI Agent',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: replyText,
      codeSnippet: codeSnippet || undefined,
      fileChanges: fileChanges.length > 0 ? fileChanges : undefined,
      metrics: {
        latency: `${latencyMs}ms`,
        tokens: `${tokensUsed} tks`,
        failoverCount: 0,
      },
    });
  } catch (err) {
    console.error('[Skelion API Chat] Handler failed:', err);
    const latencyMs = Date.now() - startTime;
    return res.status(500).json({
      error: 'Unable to process the AI request.',
      metrics: { latency: `${latencyMs}ms` },
    });
  }
}
