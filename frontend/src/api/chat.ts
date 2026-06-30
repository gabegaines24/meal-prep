export interface ChatContext {
  scan_ingredients?: string[];
}

export interface ChatEvent {
  type:
    | "token"
    | "tool_call"
    | "tool_result"
    | "action"
    | "citation"
    | "memory"
    | "error"
    | "done";
  content?: string;
  name?: string;
  input?: Record<string, unknown>;
  result?: unknown;
  action?: string;
  recipe_id?: number;
  recipe_title?: string;
  title?: string;
  day?: number;
  day_name?: string;
  meal_type?: string;
  filename?: string;
  source?: string;
  summary?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  actions?: ChatEvent[];
  citations?: ChatEvent[];
}

const BASE = "/api/chat";

export async function* streamChat(
  sessionId: string,
  message: string,
  context?: ChatContext
): AsyncGenerator<ChatEvent> {
  const res = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message, context }),
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const event = JSON.parse(line.slice(6)) as ChatEvent;
        yield event;
      } catch {
        // skip malformed chunks
      }
    }
  }
}

export async function getChatHistory(sessionId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${BASE}/history/${sessionId}`);
  if (!res.ok) return [];
  const rows = await res.json();
  return rows.map((r: { role: string; content: string }) => ({
    role: r.role as "user" | "assistant",
    content: r.content,
  }));
}

export function newSessionId(): string {
  return crypto.randomUUID();
}
