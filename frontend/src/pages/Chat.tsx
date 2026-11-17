import clsx from "clsx";
import { motion } from "framer-motion";
import { Bot, Database, Plus, Send, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Card, ErrorBox, PageHeader, Toggle } from "../components/ui";
import { api, type ChatMessage } from "../lib/api";
import { fmtDate, useApi } from "../lib/hooks";

const SUGGESTIONS = [
  "Meri fasal mein kaun sa keeda laga hai?",
  "Meri cotton crop ke liye kya treatment karu?",
  "Neem oil ka use kaise hota hai?",
  "Mere farm mein pest infestation high hai, ab kya karna chahiye?",
  "Organic pesticide ke options kya hain?",
  "माहू (aphids) का जैविक इलाज क्या है?",
];

/** Minimal, safe markdown: **bold**, _italic_, bullet/numbered lists, paragraphs. */
function Markdown({ text }: { text: string }) {
  const inline = (s: string): ReactNode[] => s.split(/(\*\*[^*]+\*\*|_[^_]+_)/g).map((p, i) =>
    p.startsWith("**") ? <strong key={i}>{p.slice(2, -2)}</strong> : p.startsWith("_") && p.endsWith("_") && p.length > 2 ? <em key={i}>{p.slice(1, -1)}</em> : p);
  const blocks: ReactNode[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  const flush = () => { if (list) { const L = list.ordered ? "ol" : "ul"; blocks.push(<L key={blocks.length}>{list.items.map((it, i) => <li key={i}>{inline(it)}</li>)}</L>); list = null; } };
  for (const line of text.split("\n")) {
    const b = line.match(/^\s*[-*•]\s+(.*)/); const n = line.match(/^\s*\d+[.)]\s+(.*)/);
    if (b || n) { const ordered = !!n; if (!list || list.ordered !== ordered) { flush(); list = { ordered, items: [] }; } list.items.push((b ?? n)![1]); }
    else { flush(); if (line.trim()) blocks.push(<p key={blocks.length}>{inline(line.replace(/^#+\s*/, ""))}</p>); }
  }
  flush();
  return <div className="prose-chat text-sm leading-relaxed">{blocks}</div>;
}

export default function Chat() {
  const status = useApi<{ llm_enabled: boolean; provider: string }>("/api/chat/status");
  const convs = useApi<{ id: number; title: string; updated_at: string }[]>("/api/chat/conversations");
  const [cid, setCid] = useState<number | null>(null);
  const [msgs, setMsgs] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [typing, setTyping] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [useDetections, setUseDetections] = useState(true);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, typing]);
  useEffect(() => {
    if (cid == null) { setMsgs([]); return; }
    api.get<ChatMessage[]>(`/api/chat/history?conversation_id=${cid}`).then(setMsgs).catch((e) => setErr(e.message));
  }, [cid]);

  const send = async (msg: string) => {
    if (!msg.trim() || typing) return;
    setErr(null); setText("");
    const temp: ChatMessage = { id: -Date.now(), role: "user", content: msg, language: null, source: null, created_at: new Date().toISOString() };
    setMsgs((m) => [...m, temp]); setTyping(true);
    try {
      const r = await api.post<{ conversation_id: number; user_message: ChatMessage; reply: ChatMessage }>("/api/chat/message", { message: msg, conversation_id: cid, include_detections: useDetections });
      setMsgs((m) => [...m.filter((x) => x.id !== temp.id), r.user_message, r.reply]);
      if (cid !== r.conversation_id) { setCid(r.conversation_id); convs.reload(); }
    } catch (e) { setErr((e as Error).message); setMsgs((m) => m.filter((x) => x.id !== temp.id)); setText(msg); }
    setTyping(false);
  };
  const submit = (e: FormEvent) => { e.preventDefault(); send(text); };
  const del = async (id: number) => { await api.del(`/api/chat/conversations/${id}`); if (id === cid) setCid(null); convs.reload(); };

  return (
    <div>
      <PageHeader eyebrow="AI Kisan · एआई किसान" title="Farming assistant" subtitle="Ask in Hindi, Hinglish or English. Answers follow IPM and never suggest pesticide brands or doses." />
      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <Card className="h-fit !p-3">
          <button className="btn-primary w-full" onClick={() => setCid(null)}><Plus className="h-4 w-4" />New chat</button>
          <div className="mt-3 max-h-[50vh] space-y-1 overflow-y-auto">
            {convs.data?.map((c) => (
              <div key={c.id} className={clsx("group flex items-center gap-1 rounded-xl px-2 py-2 text-sm", c.id === cid ? "bg-forest-100 dark:bg-white/10" : "hover:bg-forest-50 dark:hover:bg-white/5")}>
                <button className="min-w-0 flex-1 text-left" onClick={() => setCid(c.id)}><div className="truncate font-medium">{c.title}</div><div className="muted text-[11px]">{fmtDate(c.updated_at)}</div></button>
                <button className="opacity-0 transition group-hover:opacity-100" onClick={() => del(c.id)} aria-label="Delete conversation"><Trash2 className="h-3.5 w-3.5 text-red-600" /></button>
              </div>
            ))}
            {!convs.data?.length && <p className="muted px-2 py-3 text-xs">No conversations yet.</p>}
          </div>
        </Card>
        <Card className="flex h-[calc(100vh-14rem)] min-h-[520px] flex-col !p-0">
          <div className="flex items-center justify-between border-b border-forest-900/[.07] px-4 py-3 text-xs dark:border-white/10">
            <span className="flex items-center gap-1.5">{status.data?.llm_enabled ? <><Sparkles className="h-3.5 w-3.5 text-forest-600" />AI model: {status.data.provider}</> : <><Database className="h-3.5 w-3.5 text-amber-600" />Knowledge-base mode (AI model not configured)</>}</span>
            <Toggle checked={useDetections} onChange={setUseDetections} label="Use my scans" />
          </div>
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            {!msgs.length && (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <div className="grid h-14 w-14 place-items-center rounded-2xl bg-forest-100 text-forest-700 dark:bg-forest-500/15 dark:text-forest-300"><Bot className="h-7 w-7" /></div>
                <h3 className="mt-3 text-lg font-semibold">Namaste! Main AI Kisan hoon 🌾</h3>
                <p className="muted mt-1 max-w-md text-sm">Keede, unke ilaj, neem oil ya apne scan ke baare mein puchiye.</p>
                <div className="mt-5 flex max-w-2xl flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((s) => <button key={s} onClick={() => send(s)} className="rounded-full border border-forest-900/15 px-3 py-1.5 text-xs hover:bg-forest-50 dark:border-white/10 dark:hover:bg-white/5">{s}</button>)}
                </div>
              </div>
            )}
            {msgs.map((m) => (
              <motion.div key={m.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className={clsx("flex gap-2", m.role === "user" && "justify-end")}>
                {m.role === "assistant" && <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-forest-800 text-white"><Bot className="h-4 w-4" /></div>}
                <div className={clsx("max-w-[85%] rounded-2xl px-4 py-2.5", m.role === "user" ? "bg-forest-800 text-white" : "bg-forest-50 dark:bg-white/5")}>
                  {m.role === "user" ? <p className="whitespace-pre-wrap text-sm">{m.content}</p> : <Markdown text={m.content} />}
                  {m.role === "assistant" && m.source && <div className="mt-1.5 text-[10px] uppercase tracking-wide opacity-50">{m.source === "knowledge_base" ? "AgriGuard knowledge base" : m.source}</div>}
                </div>
              </motion.div>
            ))}
            {typing && (
              <div className="flex gap-2"><div className="grid h-8 w-8 place-items-center rounded-full bg-forest-800 text-white"><Bot className="h-4 w-4" /></div>
                <div className="flex items-center gap-1 rounded-2xl bg-forest-50 px-4 py-3 dark:bg-white/5">{[0, 1, 2].map((i) => <motion.span key={i} className="h-2 w-2 rounded-full bg-forest-500" animate={{ y: [0, -4, 0] }} transition={{ repeat: Infinity, duration: 0.8, delay: i * 0.15 }} />)}</div></div>
            )}
            <div ref={end} />
          </div>
          {err && <div className="px-4"><ErrorBox message={err} /></div>}
          {msgs.length > 0 && <div className="flex gap-2 overflow-x-auto px-4 pt-2">{SUGGESTIONS.slice(0, 4).map((s) => <button key={s} onClick={() => send(s)} className="shrink-0 rounded-full border border-forest-900/15 px-3 py-1 text-xs hover:bg-forest-50 dark:border-white/10 dark:hover:bg-white/5">{s}</button>)}</div>}
          <form onSubmit={submit} className="flex gap-2 p-4">
            <input className="input" placeholder="Apna sawal likhiye… / Type your question…" value={text} onChange={(e) => setText(e.target.value)} maxLength={2000} />
            <button className="btn-primary" disabled={!text.trim() || typing} aria-label="Send"><Send className="h-4 w-4" /></button>
          </form>
        </Card>
      </div>
    </div>
  );
}
