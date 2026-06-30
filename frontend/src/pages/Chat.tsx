import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";
import ChatPanel from "../components/ChatPanel";
import {
  deleteDocument,
  listDocuments,
  uploadDocument,
} from "../api/ingest";

interface LocationState {
  initialMessage?: string;
  scanIngredients?: string[];
}

export default function Chat() {
  const location = useLocation();
  const state = (location.state ?? {}) as LocationState;
  const fileRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const [uploadError, setUploadError] = useState<string | null>(null);

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
  });

  const upload = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      setUploadError(null);
    },
    onError: (err: Error) => setUploadError(err.message),
  });

  const remove = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
        <h1 className="text-xl font-bold text-gray-800 mb-1">Meal Copilot</h1>
        <p className="text-sm text-gray-500 mb-4">
          Chat with your AI assistant to plan meals, swap recipes, and build grocery lists.
        </p>
        <ChatPanel
          initialMessage={state.initialMessage}
          scanIngredients={state.scanIngredients}
        />
      </div>

      <aside className="space-y-4">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
          <h2 className="font-semibold text-gray-700 mb-2">Your Documents</h2>
          <p className="text-xs text-gray-500 mb-3">
            Upload family recipes or notes — the copilot can search them when planning.
          </p>

          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.txt,.md,.csv,text/plain,application/pdf"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) upload.mutate(file);
              e.target.value = "";
            }}
          />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={upload.isPending}
            className="w-full text-sm bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg py-2 disabled:opacity-50"
          >
            {upload.isPending ? "Uploading…" : "+ Upload PDF or text"}
          </button>

          {uploadError && (
            <p className="text-xs text-red-600 mt-2">{uploadError}</p>
          )}

          {isLoading ? (
            <p className="text-xs text-gray-400 mt-3">Loading…</p>
          ) : documents.length === 0 ? (
            <p className="text-xs text-gray-400 mt-3">No documents indexed yet.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {documents.map((doc) => (
                <li
                  key={doc.doc_id}
                  className="flex items-center justify-between gap-2 text-xs bg-gray-50 rounded-lg px-2 py-1.5"
                >
                  <span className="truncate text-gray-700" title={doc.filename}>
                    {doc.filename}
                  </span>
                  <button
                    onClick={() => remove.mutate(doc.doc_id)}
                    className="text-gray-400 hover:text-red-500 shrink-0"
                    title="Remove"
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </div>
  );
}
