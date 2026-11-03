import * as vscode from 'vscode';
import {
  Message,
  Block,
  Conversation,
  StreamingEvent,
} from '../shared/chat.js';

export interface ChatControllerOptions {
  apiBase: string;
  getToken: () => Promise<string | null>;
  postToWebview: (msg: unknown) => void;
}

export class ChatController {
  private activeAbortController: AbortController | null = null;
  private currentConversation: Conversation | null = null;

  constructor(private readonly options: ChatControllerOptions) {}

  public setConversation(conv: Conversation) {
    this.currentConversation = conv;
  }

  public getConversation(): Conversation | null {
    return this.currentConversation;
  }

  public async sendMessage(
    text: string,
    model: string = 'gpt-4o',
    mode: 'ask' | 'agent' = 'agent',
    conversationId?: string
  ): Promise<void> {
    this.stopActiveStream();

    const convId = conversationId || this.currentConversation?.id || `conv_${Date.now()}`;
    const userMsgId = `m_user_${Date.now()}`;
    const assistantMsgId = `m_asst_${Date.now()}`;
    const nowIso = new Date().toISOString();

    const userMsg: Message = {
      id: userMsgId,
      role: 'user',
      createdAt: nowIso,
      status: 'done',
      blocks: [{ type: 'markdown', id: `b_${userMsgId}_0`, text }],
    };

    if (!this.currentConversation || this.currentConversation.id !== convId) {
      this.currentConversation = {
        id: convId,
        title: text.slice(0, 32) + (text.length > 32 ? '...' : ''),
        createdAt: nowIso,
        updatedAt: nowIso,
        messages: [userMsg],
        model,
      };
    } else {
      this.currentConversation.messages.push(userMsg);
    }

    const assistantMsg: Message = {
      id: assistantMsgId,
      role: 'assistant',
      createdAt: nowIso,
      status: 'streaming',
      blocks: [],
      model,
    };
    this.currentConversation.messages.push(assistantMsg);

    this.emitEvent({
      event: 'message.start',
      messageId: assistantMsgId,
      model,
    });

    this.activeAbortController = new AbortController();
    const token = await this.options.getToken();

    try {
      const response = await fetch(`${this.options.apiBase}/v1/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token || 'dev'}`,
        },
        body: JSON.stringify({
          conversation_id: convId,
          messages: this.currentConversation.messages
            .slice(-10)
            .map(m => ({
              role: m.role,
              content: m.blocks.filter(b => b.type === 'markdown').map((b: any) => b.text).join('\n') || text,
            })),
          model,
        }),
        signal: this.activeAbortController.signal,
      });

      if (!response.ok) {
        const errJson: any = await response.json().catch(() => ({ detail: 'HTTP error ' + response.status }));
        assistantMsg.status = 'error';
        const errBlock: Block = {
          type: 'callout',
          id: `b_err_${Date.now()}`,
          level: 'danger',
          title: 'Request Failed',
          text: errJson.detail || 'Failed to communicate with Skelion API gateway.',
        };
        assistantMsg.blocks.push(errBlock);
        this.emitEvent({
          event: 'block.start',
          messageId: assistantMsgId,
          block: errBlock,
        });
        this.emitEvent({
          event: 'message.end',
          messageId: assistantMsgId,
          status: 'error',
        });
        return;
      }

      if (!response.body) {
        throw new Error('No response body returned from stream');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let markdownBuffer = '';
      const currentBlockId = `b_md_${Date.now()}`;
      let hasMarkdownBlockStarted = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data: ')) continue;
          const jsonStr = trimmed.slice(6);
          if (!jsonStr) continue;

          try {
            const data = JSON.parse(jsonStr);

            if (data.thought) {
              this.emitEvent({
                event: 'activity.update',
                steps: [{ label: `Thinking: ${data.thought}`, status: 'running' }],
              });
            } else if (data.title) {
              this.emitEvent({
                event: 'activity.update',
                steps: [{ label: data.title, status: (data.status as any) || 'done' }],
              });
            } else if (data.text) {
              if (!hasMarkdownBlockStarted) {
                hasMarkdownBlockStarted = true;
                const mdBlock: Block = {
                  type: 'markdown',
                  id: currentBlockId,
                  text: data.text,
                };
                assistantMsg.blocks.push(mdBlock);
                this.emitEvent({
                  event: 'block.start',
                  messageId: assistantMsgId,
                  block: mdBlock,
                });
                markdownBuffer = data.text;
              } else {
                markdownBuffer += data.text;
                const block = assistantMsg.blocks.find(b => b.id === currentBlockId);
                if (block && block.type === 'markdown') {
                  block.text = markdownBuffer;
                }
                this.emitEvent({
                  event: 'block.delta',
                  messageId: assistantMsgId,
                  blockId: currentBlockId,
                  op: 'append',
                  text: data.text,
                });
              }
            } else if (data.name === 'edit_file' || data.name === 'create_file') {
              const diffBlock: Block = {
                type: 'diff',
                id: `b_diff_${Date.now()}`,
                filename: data.args?.path || 'unknown.ts',
                patch: data.args?.patch || '',
                fix_id: `fix_${Date.now()}`,
              };
              assistantMsg.blocks.push(diffBlock);
              this.emitEvent({
                event: 'block.start',
                messageId: assistantMsgId,
                block: diffBlock,
              });
            } else if (data.limits) {
              this.emitEvent({
                event: 'usage',
                credits: data.tokens_deducted,
              });
            }
          } catch (pe) {
            // Incomplete JSON chunk, skip
          }
        }
      }

      if (hasMarkdownBlockStarted) {
        this.emitEvent({
          event: 'block.end',
          messageId: assistantMsgId,
          blockId: currentBlockId,
        });
      }

      assistantMsg.status = 'done';
      this.emitEvent({
        event: 'message.end',
        messageId: assistantMsgId,
        status: 'done',
      });
    } catch (err: any) {
      if (err.name === 'AbortError') {
        assistantMsg.status = 'stopped';
        this.emitEvent({
          event: 'message.end',
          messageId: assistantMsgId,
          status: 'stopped',
        });
      } else {
        assistantMsg.status = 'error';
        this.emitEvent({
          event: 'error',
          code: 'STREAM_ERROR',
          message: err?.message || String(err),
        });
      }
    } finally {
      this.activeAbortController = null;
    }
  }

  public stopActiveStream(): void {
    if (this.activeAbortController) {
      this.activeAbortController.abort();
      this.activeAbortController = null;
    }
  }

  private emitEvent(event: StreamingEvent): void {
    this.options.postToWebview({
      type: 'streamEvent',
      event,
    });
  }
}
