import React, { useEffect, useState, useRef } from "react";
import { TestCase } from "../types";

interface RunningTestsModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedTestCases: TestCase[];
  onComplete: (updatedCases: TestCase[]) => void;
  logsOnly?: boolean;  // If true, just view static log list of selected item
  singleTestCase?: TestCase | null; // Selected item to view static logs
}

export default function RunningTestsModal({
  isOpen,
  onClose,
  selectedTestCases,
  onComplete,
  logsOnly = false,
  singleTestCase = null
}: RunningTestsModalProps) {
  if (!isOpen) return null;

  const [simulatedLogs, setSimulatedLogs] = useState<string[]>([]);
  const [percentComplete, setPercentComplete] = useState(0);
  const [runningIdx, setRunningIdx] = useState(0);
  const [done, setDone] = useState(false);
  const terminalBottomRef = useRef<HTMLDivElement>(null);

  // If logsOnly is active, represent the statically saved logs from that test case
  useEffect(() => {
    if (logsOnly) {
      if (singleTestCase && singleTestCase.logs) {
        setSimulatedLogs(singleTestCase.logs);
        setPercentComplete(100);
        setDone(true);
      } else {
        setSimulatedLogs([
          `[INFO] Examining logs for: ${singleTestCase?.id || "Unspecified Case"}`,
          `[WARN] No live execution log data exists yet. Click 'Run Test' to generate metrics.`
        ]);
        setPercentComplete(0);
        setDone(true);
      }
      return;
    }

    // Otherwise, simulate a live active pipeline run!
    setDone(false);
    setPercentComplete(0);
    setRunningIdx(0);
    setSimulatedLogs(["[START] Booting diagnostic test cluster test-runner-01.local...", "[INFO] Access Token validated successfully."]);

    let logLines: string[] = [];
    let currentPercentage = 0;
    let tickCount = 0;

    const interval = setInterval(() => {
      tickCount++;

      if (tickCount === 2) {
        setSimulatedLogs((prev) => [...prev, "[OK] Found DNS records.", "[INFO] Launching prompt scenarios..."]);
        setPercentComplete(15);
      } else if (tickCount === 5) {
        const item = selectedTestCases[0];
        if (item) {
          setSimulatedLogs((prev) => [
            ...prev,
            `[RUN] Executing Scenario: ${item.id} | Intent: ${item.intentName}`,
            `[PROMPT] "${item.simulatedPrompt}"`,
            `[ASSERT] Expecting: "${item.expectedOutcome}"`,
            `[OK] Assertion passed successfully.`
          ]);
        }
        setPercentComplete(40);
      } else if (tickCount === 9) {
        const item = selectedTestCases[1];
        if (item) {
          setSimulatedLogs((prev) => [
            ...prev,
            `[RUN] Executing Scenario: ${item.id} | Intent: ${item.intentName}`,
            `[PROMPT] "${item.simulatedPrompt}"`,
            `[ASSERT] Expecting: "${item.expectedOutcome}"`,
            item.personaName.toLowerCase().includes("leak") || item.intentName.toLowerCase().includes("fail")
              ? `[REJECT] Rejection token assert passed code check correctly.`
              : `[OK] Suite assertion checked out.`
          ]);
        }
        setPercentComplete(75);
      } else if (tickCount === 12) {
        const item = selectedTestCases[2];
        if (item) {
          setSimulatedLogs((prev) => [
            ...prev,
            `[RUN] Executing Scenario: ${item.id} | Intent: ${item.intentName}`,
            `[PROMPT] "${item.simulatedPrompt}"`,
            `[ASSERT] Expecting: "${item.expectedOutcome}"`,
            `[OK] File payload bytes generated.`
          ]);
        }
        setPercentComplete(95);
      } else if (tickCount >= 14) {
        setSimulatedLogs((prev) => [...prev, "[FINISH] Compilation Suite finished.", "[INFO] All scenarios fully finalized."]);
        setPercentComplete(100);
        setDone(true);
        clearInterval(interval);

        // Notify parent state of matching output statuses
        const updated = selectedTestCases.map((item) => {
          const isFailedSample = item.intentName.toLowerCase().includes("fail") || item.personaName.toLowerCase().includes("leak");
          const finalStatus = isFailedSample ? ("failed" as const) : ("passed" as const);
          return {
            ...item,
            status: finalStatus,
            logs: [
              `[INFO] Run record for: ${item.id}`,
              `[MOCK] Simulated Prompt check: "${item.simulatedPrompt}"`,
              `[ASSERT] Expected Check: "${item.expectedOutcome}"`,
              finalStatus === "failed" ? `[WARN] Assert rejection exception verified.` : `[PASS] Verified matching successful state.`
            ]
          };
        });
        onComplete(updated);
      }
    }, 500);

    return () => clearInterval(interval);
  }, [isOpen, logsOnly, singleTestCase, selectedTestCases]);

  // Scroll terminal to view newest line automatically
  useEffect(() => {
    terminalBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [simulatedLogs]);

  return (
    <div className="fixed inset-0 bg-[#000000]/40 flex items-center justify-center z-50 p-4 select-none">
      <div className="bg-white border border-stone-300 rounded-none max-w-3xl w-full flex flex-col shadow-2xl h-[560px] overflow-hidden">
        
        {/* Terminal Header */}
        <div className="bg-stone-50 px-6 py-4 flex items-center justify-between border-b border-stone-200">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-none bg-[#ff4d00]"></span>
              <span className="w-2 h-2 rounded-none bg-stone-300"></span>
              <span className="w-2 h-2 rounded-none bg-stone-400"></span>
            </div>
            <span className="text-[10px] font-mono text-stone-500 uppercase tracking-widest ml-1">
              {logsOnly ? `logsViewer_instance::${singleTestCase?.id}` : "testCaseGen_runner_cluster.sh"}
            </span>
          </div>

          <button
            onClick={onClose}
            className="text-stone-400 hover:text-stone-700 transition-colors cursor-pointer"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        {/* Dynamic Progress Indicator */}
        <div className="bg-stone-50/55 px-6 py-3 border-b border-stone-200 flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-3 flex-grow max-w-sm">
            <span className="text-stone-500 text-[10px] uppercase tracking-widest">Runner progress:</span>
            <div className="flex-grow bg-stone-200 h-1 rounded-none overflow-hidden">
              <div
                className="bg-[#ff4d00] h-full transition-all duration-300 rounded-none"
                style={{ width: `${percentComplete}%` }}
              ></div>
            </div>
            <span className="text-[#ff4d00] text-[10px] font-bold font-mono">{percentComplete}%</span>
          </div>
          <span className="text-[10px] text-[#ff4d00] font-bold uppercase tracking-widest flex items-center gap-1.5">
            {done ? (
              <>
                <span className="w-1.5 h-1.5 rounded-none bg-[#ff4d00]"></span>
                Done
              </>
            ) : (
              <>
                <span className="w-1.5 h-1.5 rounded-none bg-stone-400 animate-pulse"></span>
                Running...
              </>
            )}
          </span>
        </div>

        {/* Terminal Stream Logs */}
        <div className="flex-grow p-6 overflow-y-auto font-mono text-[11px] leading-relaxed text-stone-700 space-y-1.5 bg-[#fcfcfc]">
          {simulatedLogs.map((log, index) => {
            const isError = log.includes("[WARN]") || log.includes("[REJECT]");
            const isOk = log.includes("[OK]") || log.includes("[PASS]") || log.includes("[START]") || log.includes("[FINISH]");
            const isPrompt = log.includes("[PROMPT]");

            let logColor = "text-stone-600";
            if (isError) logColor = "text-rose-600 font-bold";
            else if (isOk) logColor = "text-[#ff4d00] font-bold";
            else if (isPrompt) logColor = "text-stone-500 font-serif italic";

            return (
              <div key={index} className={logColor}>
                {log}
              </div>
            );
          })}
          <div ref={terminalBottomRef} />
        </div>

        {/* Terminal Controls Bar */}
        <div className="bg-stone-50 px-6 py-4 flex items-center justify-between border-t border-stone-200">
          <span className="text-[10px] text-stone-450 font-mono uppercase tracking-widest">
            Enterprise QA sandbox v1.2.4
          </span>
          <button
            onClick={onClose}
            disabled={!done && !logsOnly}
            className="px-6 py-2 bg-[#ff4d00] hover:bg-[#e04400] disabled:opacity-25 disabled:cursor-not-allowed text-white text-[11px] font-bold font-mono uppercase tracking-widest rounded-none transition-all cursor-pointer"
          >
            {logsOnly ? "Close Viewer" : done ? "Close Log Stream" : "Awaiting runner..."}
          </button>
        </div>

      </div>
    </div>
  );
}
