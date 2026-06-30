import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";

type OpType = "ingest" | "discover" | "crawl" | "personas" | "testcases" | "rule";

const OP_CONFIG: Record<OpType, { label: string; color: string; dotColor: string; messages: string[] }> = {
  ingest: {
    label: "DATA INGEST",
    color: "text-sky-400",
    dotColor: "bg-sky-400",
    messages: [
      "Parsing uploaded files...",
      "Normalizing source data...",
      "Extracting PRD structure...",
      "Merging data sources...",
      "Building raw input index...",
    ],
  },
  discover: {
    label: "INTENT DISCOVERY",
    color: "text-[#ff6a30]",
    dotColor: "bg-[#ff6a30]",
    messages: [
      "Chunking raw input...",
      "Running intent mining agent...",
      "Deduplicating intent clusters...",
      "Cross-referencing PRD signals...",
      "Finalizing intent taxonomy...",
    ],
  },
  crawl: {
    label: "SOCIAL CRAWL",
    color: "text-emerald-400",
    dotColor: "bg-emerald-400",
    messages: [
      "Connecting to social platforms...",
      "Fetching trending posts...",
      "Filtering by engagement signals...",
      "Aggregating crawl results...",
      "Indexing social content...",
    ],
  },
  personas: {
    label: "PERSONA SYNTHESIS",
    color: "text-violet-400",
    dotColor: "bg-violet-400",
    messages: [
      "Loading selected intents...",
      "Generating persona archetypes...",
      "Simulating user journeys...",
      "Validating behavioral patterns...",
      "Finalizing persona profiles...",
    ],
  },
  testcases: {
    label: "TEST COMPILATION",
    color: "text-amber-400",
    dotColor: "bg-amber-400",
    messages: [
      "Mapping personas to intents...",
      "Synthesizing test prompts...",
      "Validating expected outcomes...",
      "Building test case matrix...",
      "Running quality checks...",
    ],
  },
  rule: {
    label: "DIRECTIVE REFINEMENT",
    color: "text-fuchsia-400",
    dotColor: "bg-fuchsia-400",
    messages: [
      "Analyzing existing directives...",
      "Refining with AI model...",
      "Validating rule consistency...",
    ],
  },
};

interface OperationConsoleProps {
  operation: string | null;
}

export default function OperationConsole({ operation }: OperationConsoleProps) {
  const [msgIdx, setMsgIdx] = useState(0);
  const [cursorOn, setCursorOn] = useState(true);

  const config = operation ? OP_CONFIG[operation as OpType] : null;

  useEffect(() => {
    setMsgIdx(0);
  }, [operation]);

  useEffect(() => {
    if (!config) return;
    const id = setInterval(() => {
      setMsgIdx((i) => (i + 1) % config.messages.length);
    }, 2500);
    return () => clearInterval(id);
  }, [config]);

  useEffect(() => {
    const id = setInterval(() => setCursorOn((v) => !v), 530);
    return () => clearInterval(id);
  }, []);

  return (
    <AnimatePresence>
      {config && (
        <motion.div
          key={operation}
          initial={{ x: 40, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 40, opacity: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          className="fixed top-20 right-6 z-50 w-80 bg-stone-900 border border-stone-700 rounded-xl shadow-2xl overflow-hidden select-none"
        >
          {/* Content area */}
          <div className="px-4 py-3">
            {/* Row 1: pulsing dot + label + step counter */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                {/* Pulsing dot */}
                <span className="relative flex h-2 w-2 shrink-0">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-60 ${config.dotColor}`} />
                  <span className={`relative inline-flex h-2 w-2 rounded-full ${config.dotColor}`} />
                </span>
                <span className={`text-[10px] font-mono font-bold uppercase tracking-widest ${config.color}`}>
                  {config.label}
                </span>
              </div>
              <span className="text-[9px] font-mono text-stone-500">
                step {msgIdx + 1} / {config.messages.length}
              </span>
            </div>

            {/* Row 2: cycling message + cursor */}
            <div className="flex items-center gap-1 min-h-[18px]">
              <AnimatePresence mode="wait">
                <motion.span
                  key={msgIdx}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.2 }}
                  className="text-[10.5px] font-mono text-stone-300 tracking-wide"
                >
                  {config.messages[msgIdx]}
                </motion.span>
              </AnimatePresence>
              <span
                className={`text-[12px] font-mono text-stone-400 transition-opacity duration-75 shrink-0 ${
                  cursorOn ? "opacity-100" : "opacity-0"
                }`}
              >
                ▌
              </span>
            </div>
          </div>

          {/* Progress bar — flush bottom, outside padding */}
          <div className="h-1.5 bg-stone-800">
            <div
              className="h-full bg-[#ff4d00] transition-all duration-700"
              style={{
                width: `${Math.min(((msgIdx + 1) / config.messages.length) * 100, 90)}%`,
              }}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
