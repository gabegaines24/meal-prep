import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  type ChatEvent,
  type ChatMessage,
  getChatHistory,
  newSessionId,
  streamChat,
} from "../api/chat";
import { scanFridge } from "../api/scan";

interface ChatPanelProps {
  sessionId?: string;
  initialMessage?: string;
  scanIngredients?: string[];
  compact?: boolean;
}

function ActionCard({ event }: { event: ChatEvent }) {
  if (event.action === "assign_slot") {
    return (
      <div className="text-xs bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg px-3 py-2">
        Added <strong>{event.recipe_title}</strong> → {event.day_name} {event.meal_type} ✓
      </div>
    );
  }
  if (event.action === "clear_slot") {
    return (
      <div className="text-xs bg-gray-50 border border-gray-200 text-gray-700 rounded-lg px-3 py-2">
        Cleared {event.day_name} {event.meal_type}
      </div>
    );
  }
  if (event.action === "autogenerate_week") {
    return (
      <div className="text-xs bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg px-3 py-2">
        Auto-generated the week’s meal plan ✓
      </div>
    );
  }
  return null;
}

function CitationChip({ event }: { event: ChatEvent }) {
  const label = event.title ?? event.filename ?? "Source";
  return (
    <span className="inline-block text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded-full px-2 py-0.5 mr-1">
      {label}
    </span>
  );
}

export default function ChatPanel({
  sessionId: externalSessionId,
  initialMessage,
  scanIngredients,
  compact = false,
}: ChatPanelProps) {
  const queryClient = useQueryClient();
  const [sessionId] = useState(() => externalSessionId ?? newSessionId());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLInputElement>(null);
  const sentInitial = useRef(false);

  useEffect(() => {
    getChatHistory(sessionId).then(setMessages).catch(() => {});
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  useEffect(() => {
    if (initialMessage && !sentInitial.current) {
      sentInitial.current = true;
      sendMessage(initialMessage, scanIngredients);
    }
  }, [initialMessage, scanIngredients]);

  async function sendMessage(text: string, ingredients?: string[]) {
    const trimmed = text.trim();
    if (!trimmed || streaming) return;

    setError(null);
    setStreaming(true);
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);

    let assistantContent = "";
    const actions: ChatEvent[] = [];
    const citations: ChatEvent[] = [];

    try {
      const context = ingredients?.length ? { scan_ingredients: ingredients } : undefined;

      for await (const event of streamChat(sessionId, trimmed, context)) {
        if (event.type === "token" && event.content) {
          assistantContent += event.content;
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant" && streaming) {
              next[next.length - 1] = {
                ...last,
                content: assistantContent,
                actions,
                citations,
              };
            } else {
              next.push({
                role: "assistant",
                content: assistantContent,
                actions,
                citations,
              });
            }
            return next;
          });
        } else if (event.type === "action") {
          actions.push(event);
          queryClient.invalidateQueries({ queryKey: ["week"] });
          queryClient.invalidateQueries({ queryKey: ["grocery-list"] });
        } else if (event.type === "citation") {
          citations.push(event);
        } else if (event.type === "error") {
          setError(event.content ?? "Something went wrong");
        }
      }

      setMessages((prev) => {
        const next = [...prev];
        const idx = next.findIndex(
          (m, i) => m.role === "assistant" && i === next.length - 1
        );
        if (idx >= 0) {
          next[idx] = { role: "assistant", content: assistantContent, actions, citations };
        } else if (assistantContent) {
          next.push({ role: "assistant", content: assistantContent, actions, citations });
        }
        return next;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
    } finally {
      setStreaming(false);
      setInput("");
    }
  }

  async function handleImageUpload(file: File) {
    setError(null);
    setStreaming(true);
    try {
      const scan = await scanFridge(file);
      if (!scan.ingredients.length) {
        setError("No ingredients detected in the image.");
        return;
      }
      const prompt =
        scan.agent_prompt ??
        `I scanned my fridge and found: ${scan.ingredients.join(", ")}. Please plan meals using these.`;
      await sendMessage(prompt, scan.ingredients);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed");
      setStreaming(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    sendMessage(input);
  }

  return (
    <div className={`flex flex-col ${compact ? "h-[480px]" : "h-[calc(100vh-12rem)]"}`}>
      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {messages.length === 0 && !streaming && (
          <p className="text-sm text-gray-400 text-center py-8">
            Ask about your meal plan, swap recipes, hit macro goals, or upload a fridge photo.
          </p>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-emerald-600 text-white"
                  : "bg-white border border-gray-200 text-gray-800"
              }`}
            >
              {msg.content}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {msg.citations.map((c, j) => (
                    <CitationChip key={j} event={c} />
                  ))}
                </div>
              )}
              {msg.actions && msg.actions.length > 0 && (
                <div className="mt-2 space-y-1">
                  {msg.actions.map((a, j) => (
                    <ActionCard key={j} event={a} />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {streaming && messages[messages.length - 1]?.role !== "assistant" && (
          <div className="text-sm text-gray-400 animate-pulse">Thinking…</div>
        )}

        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 mb-2">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex gap-2 pt-3 border-t border-gray-100">
        <input
          ref={imageRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleImageUpload(file);
            e.target.value = "";
          }}
        />
        <button
          type="button"
          onClick={() => imageRef.current?.click()}
          disabled={streaming}
          className="shrink-0 text-gray-400 hover:text-emerald-600 px-2 disabled:opacity-50"
          title="Upload fridge photo"
        >
          📷
        </button>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask your meal planning copilot…"
          disabled={streaming}
          className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
        />
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
