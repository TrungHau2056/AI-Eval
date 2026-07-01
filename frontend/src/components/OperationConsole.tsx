import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";

type OpType = "ingest" | "discover" | "crawl" | "personas" | "testcases" | "rule";

const OP_CONFIG: Record<OpType, { label: string; color: string; dotColor: string; messages: string[] }> = {
  ingest: {
    label: "DATA INGEST",
    color: "text-sky-600",
    dotColor: "bg-sky-500",
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
    color: "text-[#ff4d00]",
    dotColor: "bg-[#ff4d00]",
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
    color: "text-emerald-600",
    dotColor: "bg-emerald-500",
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
    color: "text-violet-600",
    dotColor: "bg-violet-500",
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
    color: "text-amber-600",
    dotColor: "bg-amber-500",
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
    color: "text-fuchsia-600",
    dotColor: "bg-fuchsia-500",
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
          className="fixed top-20 right-6 z-50 w-80 bg-white border border-stone-200 rounded-none shadow-2xl overflow-hidden select-none"
        >
          {/* Content area */}
          <div className="px-4 py-3">
            {/* Row 1: pulsing dot + label */}
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
                  className="text-[10.5px] font-mono text-stone-500 tracking-wide"
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

          {/* Indeterminate progress bar — flush bottom, outside padding. Duration of the
              underlying async op is unknown, so this slides continuously rather than filling
              to a % and resetting (which read as "finishes then restarts"). */}
          <div className="h-1 bg-stone-100 overflow-hidden">
            <div className="h-full w-1/3 bg-[#ff4d00] progress-indeterminate" />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
