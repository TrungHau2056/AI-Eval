import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import StepIndicator from "./components/StepIndicator";
import DataIngestionTab from "./components/DataIngestionTab";
import IntentCurationTab from "./components/IntentCurationTab";
import PersonaPlaygroundTab from "./components/PersonaPlaygroundTab";
import ExportTab from "./components/ExportTab";
import RunningTestsModal from "./components/RunningTestsModal";
import { Intent, Persona, TestCase, IngestStats } from "./types";

export default function App() {
  const [currentStep, setCurrentStep] = useState(1);
  const [activeSidebarTab, setActiveSidebarTab] = useState("dashboard");

  // App core state
  const [apiKey, setApiKey] = useState("••••••••••••••••");
  const [domain, setDomain] = useState("qa-env-01.local");
  const [aiModel, setAiModel] = useState("Gemini 1.5 Pro");
  const [intents, setIntents] = useState<Intent[]>([]);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [testCases, setTestCases] = useState<TestCase[]>([]);

  // Synchronized generation rules
  const [intentRule, setIntentRule] = useState(() => {
    return localStorage.getItem("system_intent_rule") || "System Default V1.0: Analyze customer support interactions and utterances to discover distinct user intents. Categorize into strategic core customer stages like RETENTION, USAGE, SECURITY, ACCOUNT MGMT, CHURN, and SUPPORT.";
  });

  const [personaRule, setPersonaRule] = useState(() => {
    return localStorage.getItem("system_persona_rule") || "System Default V2.0: Craft high-fidelity user personas reflecting realistic behavioral paradigms. For each intent, synthesize a Happy-path persona (Persona A) and an aggressive, complex Edge-case persona (Persona B) to fully evaluate system guardrails.";
  });

  const [testCaseRule, setTestCaseRule] = useState(() => {
    return localStorage.getItem("system_testcase_rule") || "System Default V3.1: Generate robust, comprehensive, and exhaustive test cases based on defined intent fields and simulated user persona criteria. Each test case should include highly detailed pre-conditions, structured test steps, expected functional outcomes, and safety evaluation parameters.";
  });

  // Modal active state
  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false);
  const [activeRuleType, setActiveRuleType] = useState<"intent" | "persona" | "testcase">("intent");

  // Rule refinement states
  const [promptText, setPromptText] = useState("");
  const [compilingRule, setCompilingRule] = useState(false);
  const [mdFileName, setMdFileName] = useState<string | null>(null);
  const [mdFileDragging, setMdFileDragging] = useState(false);
  const fileInputRefRules = useRef<HTMLInputElement>(null);

  // Modals & alerts
  const [isTestModalOpen, setIsTestModalOpen] = useState(false);
  const [logsOnlyMode, setLogsOnlyMode] = useState(false);
  const [viewingTestCase, setViewingTestCase] = useState<TestCase | null>(null);
  const [alertInfo, setAlertInfo] = useState<{ message: string; type: "success" | "info" | "error" } | null>(null);

  // Reset pipeline state once per browser tab load (F5). Skip on Vite HMR remounts so
  // crawled social data in memory is not wiped mid-session.
  useEffect(() => {
    const w = window as Window & { __pipelineSessionInit?: boolean };
    if (w.__pipelineSessionInit) return;
    w.__pipelineSessionInit = true;

    fetch("/api/state/reset", { method: "POST" })
      .then((res) => res.json())
      .then((data) => {
        if (data?.state) {
          setApiKey(data.state.apiKey || "");
          setDomain(data.state.domain || "");
          setAiModel(data.state.aiModel || "Gemini 1.5 Pro");
          setIntents(data.state.intents || []);
          setPersonas(data.state.personas || []);
          setTestCases(data.state.testCases || []);
        }
      })
      .catch((err) => {
        console.error("Failed to reset session state:", err);
        showToast("Error initializing fresh session.", "error");
      });
  }, []);

  const showToast = (message: string, type: "success" | "info" | "error" = "info") => {
    setAlertInfo({ message, type });
    setTimeout(() => {
      setAlertInfo(null);
    }, 4000);
  };

  // Sync state helpers
  const saveStateToServer = (updatedFields: any) => {
    fetch("/api/state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updatedFields),
    })
      .then((res) => res.json())
      .then((data) => {
        if (!data.success) {
          console.error("Server declined state sync.");
        }
      })
      .catch((err) => console.error("Error syncing state with backend:", err));
  };

  // Handles: Settings Updates
  const handleApiKeyChange = (val: string) => {
    setApiKey(val);
    saveStateToServer({ apiKey: val });
  };

  const handleDomainChange = (val: string) => {
    setDomain(val);
    saveStateToServer({ domain: val });
  };

  const handleAiModelChange = (val: string) => {
    setAiModel(val);
    saveStateToServer({ aiModel: val });
    showToast(`Diagnostic model hot-swapped to: ${val}`, "info");
  };

  // Step 1a: Ingest multi-source files (server-side FormData → /api/ingest)
  const handleIngest = async (
    files: { file: File; sourceType: string }[],
    prdFile: File | null,
  ): Promise<IngestStats> => {
    const fd = new FormData();
    files.forEach(({ file, sourceType }) => {
      fd.append("files", file);
      fd.append("types", sourceType);
    });
    if (prdFile) fd.append("prd_file", prdFile);

    const response = await fetch("/api/ingest", { method: "POST", body: fd });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Ingest failed.");
    }
    const stats: IngestStats = await response.json();
    if (stats.warnings?.length) {
      showToast(stats.warnings[0], "info");
    }
    return stats;
  };

  // Step 1: Discover Intents
  const handleDiscover = async (text: string, ruleText?: string) => {
    try {
      const response = await fetch("/api/discover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ logsText: text, ruleText }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to discover intents.");
      }

      const result = await response.json();
      
      // refresh local state from full-stack state endpoint
      const statsRes = await fetch("/api/state");
      const freshState = await statsRes.json();
      setIntents(freshState.intents || []);

      if (result.fallback) {
        showToast("Demo Mode: Extracted typical intents from transcript parameters.", "info");
      } else if ((result.intents?.length ?? 0) === 0) {
        showToast(
          "Discovery finished but found 0 intents. Check that crawl data or uploaded text is not empty, and verify your LLM API key.",
          "error",
        );
      } else {
        showToast(`Successfully extracted ${result.intents.length} unique curated intents!`, "success");
      }

      setCurrentStep(2); // Jump to curation screen automatically
    } catch (err: any) {
      console.error(err);
      showToast(err.message || "Intent parsing failed. Check API configuration.", "error");
    }
  };

  // Step 1b: Crawl one social platform; backend prepends results to JSON store + returns full sheet.
  const platformToSlug = (platform: string): string => {
    const p = platform.toLowerCase();
    if (p.includes("threads")) return "threads";
    if (p.includes("tiktok")) return "tiktok";
    return "facebook";
  };

  const handleCrawlSocial = async (
    platform: string,
    domain: string,
    keywords?: string[],
    postsPerKeyword?: number,
  ): Promise<{ crawlPosts: any[]; newCrawlPosts: any[]; crawlLogs: string[] }> => {
    const slug = platformToSlug(platform);

    try {
      const response = await fetch(`/api/crawl/${slug}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform,
          domain,
          keywords: keywords || [],
          search_limit: postsPerKeyword,
          posts_limit: postsPerKeyword,
          extract_intents: false,
          model: aiModel,
          api_key: apiKey && apiKey !== "••••••••••••••••" ? apiKey : undefined,
        }),
      });

      const result = await response.json();
      if (!response.ok || result.error) {
        throw new Error(result.detail || result.error || "Social crawl failed.");
      }

      const newCrawlPosts: any[] = result.new_crawl_posts || [];
      const crawlPosts: any[] = result.crawl_posts || [];
      if (newCrawlPosts.length > 0) {
        showToast(`Crawled ${platform} → ${newCrawlPosts.length} new posts (${crawlPosts.length} total in sheet).`, "success");
      } else {
        showToast(`Crawl finished for ${platform} but no new posts were returned.`, "info");
      }

      return {
        crawlPosts,
        newCrawlPosts,
        crawlLogs: result.crawl_logs ?? [],
      };
    } catch (err: any) {
      console.error(err);
      showToast(err.message || "Social crawl failed.", "error");
      return { crawlPosts: [], newCrawlPosts: [], crawlLogs: [String(err.message || err)] };
    }
  };

  // Step 2: Curation Matrix edits
  const handleUpdateIntent = (id: string, updated: Partial<Intent>) => {
    const updatedList = intents.map((item) => (item.id === id ? { ...item, ...updated } : item));
    setIntents(updatedList);
    saveStateToServer({ intents: updatedList });
  };

  const handleToggleSelectAllIntents = (checked: boolean) => {
    const updatedList = intents.map((item) => ({ ...item, selected: checked }));
    setIntents(updatedList);
    saveStateToServer({ intents: updatedList });
  };

  const handleAddIntent = () => {
    const newIntent: Intent = {
      id: `custom-int-${Date.now()}`,
      name: "New Custom Intent",
      phase: "SUPPORT",
      utterance: "Where can I configure webhook web subscriptions?",
      triggerMoment: "Admin Console View",
      selected: true,
    };
    const updatedList = [newIntent, ...intents];
    setIntents(updatedList);
    saveStateToServer({ intents: updatedList });
    showToast("Added new customer intent to curation grid.", "success");
  };

  const handleProcessIntents = () => {
    const selectedIntents = intents.filter((i) => i.selected);
    if (selectedIntents.length === 0) {
      showToast("Please selection at least one intent from curation table.", "error");
      return;
    }

    showToast("Compiling intent dataset for persona simulation...", "info");

    fetch("/api/generate-personas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intents: selectedIntents, ruleText: personaRule }),
    })
      .then((res) => {
        if (!res.ok) throw new Error("Persona generation failed");
        return res.json();
      })
      .then((data) => {
        setPersonas(data.personas || []);
        if (data.fallback) {
          showToast("Generated model test personas for active QA suite.", "info");
        } else {
          showToast("AI synthesized optimal test personas successfully!", "success");
        }
        setCurrentStep(3); // Jump to step 3!
      })
      .catch((err) => {
        console.error(err);
        showToast("Failed to compile user personas from intents dataset.", "error");
      });
  };

  // Step 3: Persona Playground edits
  const handleUpdatePersona = (id: string, updated: Partial<Persona>) => {
    const updatedList = personas.map((item) => (item.id === id ? { ...item, ...updated } : item));
    setPersonas(updatedList);
    saveStateToServer({ personas: updatedList });
  };

  const handleRegeneratePersona = async (id: string, feedback?: string) => {
    const selectedIntents = intents.filter((i) => i.selected);
    const target = personas.find((p) => p.id === id);
    try {
      const body: Record<string, unknown> = { intents: selectedIntents, ruleText: personaRule };
      if (feedback) body.feedback = feedback;
      const response = await fetch("/api/generate-personas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error();
      const data = await response.json();
      // Find the regenerated persona matching the same type
      const matchType = target?.type || "happy";
      const updatedPersona = data.personas.find((p: Persona) => p.type === matchType) || data.personas[0];

      if (updatedPersona) {
        handleUpdatePersona(id, {
          name: updatedPersona.name,
          trigger: updatedPersona.trigger,
          utterance: updatedPersona.utterance,
          frequency: updatedPersona.frequency,
          pain: updatedPersona.pain,
          reject: updatedPersona.reject,
          expectedAIBehavior: updatedPersona.expectedAIBehavior,
        });
        showToast("Refreshed persona archetype variables successfully.", "success");
      }
    } catch (e) {
      // Offline fallback
      showToast("Offline fallback: generated fresh mockup persona parameters.", "info");
      if (target) {
        handleUpdatePersona(id, {
          name: target.type === "happy" ? "Standard Corporate Persona" : "Security Inspector",
          trigger: target.type === "happy" ? "Dashboard Load Success" : "Strict Header Validation",
          utterance: target.type === "happy" ? "I want to retrieve my account reports for audit purposes." : "Attempts unauthorized bearer token insertions.",
          expectedAIBehavior: target.type === "happy" ? "Generate complete report dynamically." : "Reject query with security warning code.",
        });
      }
    }
  };

  const handleConfirmPersonas = () => {
    const selectedIntents = intents.filter((i) => i.selected);
    showToast("Generating optimal software tests for active compilation suite...", "info");

    fetch("/api/generate-testcases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intents: selectedIntents, personas: personas, ruleText: testCaseRule }),
    })
      .then((res) => {
        if (!res.ok) throw new Error("Test compiles failed");
        return res.json();
      })
      .then((data) => {
        setTestCases(data.testCases || []);
        if (data.fallback) {
          showToast("Synthetic Test Suite compiled successfully.", "info");
        } else {
          showToast("AI compiled optimized diagnostics test scenarios!", "success");
        }
        setCurrentStep(4); // navigate to finale
      })
      .catch((err) => {
        console.error(err);
        showToast("Compile failed. Verify model limits.", "error");
      });
  };

  // Direct rule compilers & MD files importers
  const handleCompileRule = async () => {
    if (!promptText.trim()) return;
    setCompilingRule(true);
    let currentRuleText = "";
    if (activeRuleType === "intent") currentRuleText = intentRule;
    else if (activeRuleType === "persona") currentRuleText = personaRule;
    else if (activeRuleType === "testcase") currentRuleText = testCaseRule;

    try {
      const response = await fetch("/api/compile-rule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          activeDirective: currentRuleText,
          promptInstruction: promptText,
        }),
      });

      if (!response.ok) throw new Error();
      const data = await response.json();
      if (data.compiledDirective) {
        if (activeRuleType === "intent") {
          setIntentRule(data.compiledDirective);
          localStorage.setItem("system_intent_rule", data.compiledDirective);
        } else if (activeRuleType === "persona") {
          setPersonaRule(data.compiledDirective);
          localStorage.setItem("system_persona_rule", data.compiledDirective);
        } else if (activeRuleType === "testcase") {
          setTestCaseRule(data.compiledDirective);
          localStorage.setItem("system_testcase_rule", data.compiledDirective);
        }
        showToast("Gemini model refined the parsing directive successfully!", "success");
        setPromptText("");
      }
    } catch (err) {
      showToast("Could not refine directive. Check Gemini connection status.", "error");
    } finally {
      setCompilingRule(false);
    }
  };

  const handleMdFileChangeRules = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      processMdFile(files[0]);
    }
  };

  const handleDragOverRules = (e: React.DragEvent) => {
    e.preventDefault();
    setMdFileDragging(true);
  };

  const handleDragLeaveRules = () => {
    setMdFileDragging(false);
  };

  const handleDropRules = (e: React.DragEvent) => {
    e.preventDefault();
    setMdFileDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      processMdFile(files[0]);
    }
  };

  const processMdFile = (file: File) => {
    if (!file.name.endsWith(".md")) {
      showToast("Only markdown (.md) rule configurations can be imported here.", "error");
      return;
    }
    setMdFileName(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      if (activeRuleType === "intent") {
        setIntentRule(text);
        localStorage.setItem("system_intent_rule", text);
      } else if (activeRuleType === "persona") {
        setPersonaRule(text);
        localStorage.setItem("system_persona_rule", text);
      } else if (activeRuleType === "testcase") {
        setTestCaseRule(text);
        localStorage.setItem("system_testcase_rule", text);
      }
      showToast(`Imported rule template from markdown file!`, "success");
    };
    reader.readAsText(file);
  };

  const handleResetRuleToDefault = () => {
    if (activeRuleType === "intent") {
      const def = "System Default V1.0: Analyze customer support interactions and utterances to discover distinct user intents. Categorize into strategic core customer stages like RETENTION, USAGE, SECURITY, ACCOUNT MGMT, CHURN, and SUPPORT.";
      setIntentRule(def);
      localStorage.setItem("system_intent_rule", def);
    } else if (activeRuleType === "persona") {
      const def = "System Default V2.0: Craft high-fidelity user personas reflecting realistic behavioral paradigms. For each intent, synthesize a Happy-path persona (Persona A) and an aggressive, complex Edge-case persona (Persona B) to fully evaluate system guardrails.";
      setPersonaRule(def);
      localStorage.setItem("system_persona_rule", def);
    } else if (activeRuleType === "testcase") {
      const def = "System Default V3.1: Generate robust, comprehensive, and exhaustive test cases based on defined intent fields and simulated user persona criteria. Each test case should include highly detailed pre-conditions, structured test steps, expected functional outcomes, and safety evaluation parameters.";
      setTestCaseRule(def);
      localStorage.setItem("system_testcase_rule", def);
    }
    showToast("Reset current directive back to standard system preset.", "info");
  };

  // Step 4: Finalize & Run Test
  const handleUpdateTestCase = (id: string, updated: Partial<TestCase>) => {
    const updatedList = testCases.map((tc) => (tc.id === id ? { ...tc, ...updated } : tc));
    setTestCases(updatedList);
    saveStateToServer({ testCases: updatedList });
  };

  const handleResetWorkspace = () => {
    if (confirm("Reset the QA compilation workspace back to default seed data?")) {
      fetch("/api/state/reset", { method: "POST" })
        .then((res) => res.json())
        .then((data) => {
          if (data.success) {
            setIntents(data.state.intents || []);
            setPersonas(data.state.personas || []);
            setTestCases(data.state.testCases || []);
            setCurrentStep(1);
            showToast("Workspace was reset successfully.", "success");
          }
        });
    }
  };

  // Starts active sandbox execution run of the compiled cases
  const triggerPipelineRun = () => {
    showToast("Support and documentation is coming soon.", "info");
  };

  const handleOpenStaticLogs = (tc: TestCase) => {
    setLogsOnlyMode(true);
    setViewingTestCase(tc);
    setIsTestModalOpen(true);
  };

  // Finished the test run, patch backend statuses
  const handleRunComplete = (updatedCasesFromRunner: TestCase[]) => {
    // Map status outputs
    const activeMapping = testCases.map((tc) => {
      const runResult = updatedCasesFromRunner.find((rc) => rc.id === tc.id);
      return runResult ? { ...tc, status: runResult.status, logs: runResult.logs } : tc;
    });

    setTestCases(activeMapping);
    saveStateToServer({ testCases: activeMapping });
    showToast("Completed enterprise testing run! Checks saved to logs.", "success");
  };

  return (
    <div className="min-h-screen bg-[#f8f9fa] text-[#1a1a1a] flex font-sans select-none">
      
      {/* 256px wide fixed left sidebar */}
      <Sidebar
        apiKey={apiKey}
        domain={domain}
        aiModel={aiModel}
        onApiKeyChange={handleApiKeyChange}
        onDomainChange={handleDomainChange}
        onAiModelChange={handleAiModelChange}
        activeSidebarTab={activeSidebarTab}
        setActiveSidebarTab={setActiveSidebarTab}
        onComingSoonClick={() => showToast("Support and documentation is coming soon.", "info")}
      />

      {/* Main Content Area */}
      <div className="flex-1 pl-64 flex flex-col min-h-screen">
        
        {/* Top Header */}
        <Header
          currentStep={currentStep}
          onRunTest={triggerPipelineRun}
        />

        {/* Workspace Alert Indicator */}
        {alertInfo && (
          <div className="fixed top-24 right-8 z-50">
            <div
              className={`px-5 py-3 rounded-none shadow-xl flex items-center gap-2.5 text-[10px] font-mono uppercase tracking-widest border ${
                alertInfo.type === "success"
                  ? "bg-[#ff4d00] text-white border-[#ff4d00]"
                  : alertInfo.type === "error"
                  ? "bg-rose-100 text-rose-800 border-rose-300"
                  : "bg-stone-100 text-stone-800 border-stone-300"
              }`}
            >
              <span className="material-symbols-outlined text-[16px]">
                {alertInfo.type === "success" ? "check_circle" : alertInfo.type === "error" ? "error" : "info"}
              </span>
              <span>{alertInfo.message}</span>
            </div>
          </div>
        )}

        <div className="flex-1 p-8">
          
          {/* Stepper progress indicator */}
          <StepIndicator currentStep={currentStep} onStepChange={setCurrentStep} />

          {/* Active Tab View Frame */}
          <main className="mt-2">
            {currentStep === 1 && (
              <DataIngestionTab
                onDiscover={handleDiscover}
                onIngest={handleIngest}
                onCrawlSocial={handleCrawlSocial}
                onProceedToCuration={() => setCurrentStep(2)}
                ruleText={intentRule}
                onOpenRuleModal={() => {
                  setActiveRuleType("intent");
                  setPromptText("");
                  setMdFileName(null);
                  setIsRuleModalOpen(true);
                }}
              />
            )}

            {currentStep === 2 && (
              <IntentCurationTab
                intents={intents}
                onUpdateIntent={handleUpdateIntent}
                onToggleSelectAll={handleToggleSelectAllIntents}
                onAddIntent={handleAddIntent}
                onProcessIntents={handleProcessIntents}
                ruleText={personaRule}
                onOpenRuleModal={() => {
                  setActiveRuleType("persona");
                  setPromptText("");
                  setMdFileName(null);
                  setIsRuleModalOpen(true);
                }}
              />
            )}

            {currentStep === 3 && (
              <PersonaPlaygroundTab
                intents={intents}
                personas={personas}
                onUpdatePersona={handleUpdatePersona}
                onRegeneratePersona={handleRegeneratePersona}
                onConfirmPersonas={handleConfirmPersonas}
                ruleText={testCaseRule}
                onOpenRuleModal={() => {
                  setActiveRuleType("testcase");
                  setPromptText("");
                  setMdFileName(null);
                  setIsRuleModalOpen(true);
                }}
              />
            )}

            {currentStep === 4 && (
              <ExportTab
                testCases={testCases}
                onUpdateTestCase={handleUpdateTestCase}
                onRunTest={triggerPipelineRun}
                onOpenLogs={handleOpenStaticLogs}
                onOpenRuleModal={() => {
                  setActiveRuleType("testcase");
                  setPromptText("");
                  setMdFileName(null);
                  setIsRuleModalOpen(true);
                }}
              />
            )}
          </main>

          {/* Extra utility row */}
          <div className="max-w-6xl mx-auto mt-8 flex justify-between items-center select-none opacity-60 hover:opacity-100 transition-opacity">
            <p className="text-[10px] text-stone-500 uppercase tracking-widest font-mono">
              Enterprise Suite Database synced with sandbox. Local changes update in real-time.
            </p>
            <button
              onClick={handleResetWorkspace}
              className="text-[10px] font-bold text-[#ff4d00] hover:underline uppercase tracking-widest font-mono flex items-center gap-1 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[13px]">restart_alt</span>
              Reset workspace seed data
            </button>
          </div>

        </div>
      </div>

      {/* Pipeline execution / logs modal */}
      <RunningTestsModal
        isOpen={isTestModalOpen}
        onClose={() => setIsTestModalOpen(false)}
        selectedTestCases={testCases.filter((tc) => tc.selected)}
        onComplete={handleRunComplete}
        logsOnly={logsOnlyMode}
        singleTestCase={viewingTestCase}
      />

      {/* Unified Rules Configuration Modal */}
      <AnimatePresence>
        {isRuleModalOpen && (
          <div className="fixed inset-0 z-50 overflow-y-auto flex items-center justify-center p-4">
            {/* Overlay */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsRuleModalOpen(false)}
              className="fixed inset-0 bg-stone-900/40 backdrop-blur-xs"
            />
            
            {/* Modal Box */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 15 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              className="bg-white border border-stone-200 shadow-2xl max-w-2xl w-full p-8 relative flex flex-col gap-6 rounded-none z-10 custom-scrollbar max-h-[90vh] overflow-y-auto"
            >
              {/* Header */}
              <div className="flex items-start justify-between border-b border-stone-100 pb-4">
                <div>
                  <h3 className="text-[13px] font-bold text-stone-950 uppercase tracking-widest flex items-center gap-2 font-mono">
                    <span className="material-symbols-outlined text-[#ff4d00]/90 text-[20px]">tune</span>
                    QA Generation directives
                  </h3>
                  <p className="text-[11px] text-stone-500 font-serif italic mt-1 leading-normal">
                    Synchronize pipeline compilation rules across all tabs via custom prompts or direct edits.
                  </p>
                </div>
                <button
                  onClick={() => setIsRuleModalOpen(false)}
                  className="text-stone-400 hover:text-stone-800 transition-colors cursor-pointer bg-transparent border-0"
                >
                  <span className="material-symbols-outlined text-[20px]">close</span>
                </button>
              </div>

              {/* Sub-tabs inside Modal */}
              <div className="flex border-b border-stone-100 gap-1">
                <button
                  type="button"
                  onClick={() => {
                    setActiveRuleType("intent");
                    setPromptText("");
                    setMdFileName(null);
                  }}
                  className={`px-4 py-2 text-[10px] uppercase font-mono tracking-wider font-bold border-b-2 transition-all bg-transparent border-0 cursor-pointer ${
                    activeRuleType === "intent"
                      ? "border-[#ff4d00] text-[#ff4d00]"
                      : "border-transparent text-stone-400 hover:text-stone-700"
                  }`}
                >
                  1. Intent Discovery
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setActiveRuleType("persona");
                    setPromptText("");
                    setMdFileName(null);
                  }}
                  className={`px-4 py-2 text-[10px] uppercase font-mono tracking-wider font-bold border-b-2 transition-all bg-transparent border-0 cursor-pointer ${
                    activeRuleType === "persona"
                      ? "border-[#ff4d00] text-[#ff4d00]"
                      : "border-transparent text-stone-400 hover:text-stone-700"
                  }`}
                >
                  2. Persona Synthesis
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setActiveRuleType("testcase");
                    setPromptText("");
                    setMdFileName(null);
                  }}
                  className={`px-4 py-2 text-[10px] uppercase font-mono tracking-wider font-bold border-b-2 transition-all bg-transparent border-0 cursor-pointer ${
                    activeRuleType === "testcase"
                      ? "border-[#ff4d00] text-[#ff4d00]"
                      : "border-transparent text-stone-400 hover:text-stone-700"
                  }`}
                >
                  3. Testcase Compiling
                </button>
              </div>

              {/* Input Area 1: Insert Rule by Prompt Directly */}
              <div className="flex flex-col gap-2.5">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[#ff4d00] text-[16px]">psychology</span>
                  <label className="text-[10px] font-bold text-stone-700 uppercase tracking-widest">
                    Adjust Rules via AI Prompt
                  </label>
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={promptText}
                    onChange={(e) => setPromptText(e.target.value)}
                    placeholder="e.g. Focus on aggressive payment limits and retry failures, discarding UI layout checks."
                    className="flex-1 bg-stone-50 text-stone-900 border border-stone-300 rounded-none px-4 py-2.5 text-xs focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all placeholder:text-stone-400 font-mono"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleCompileRule();
                      }
                    }}
                  />
                  <button
                    type="button"
                    disabled={compilingRule}
                    onClick={handleCompileRule}
                    className="px-5 py-2.5 bg-stone-950 text-white rounded-none hover:bg-stone-850 disabled:opacity-50 text-[10px] font-bold uppercase tracking-wider font-mono cursor-pointer shrink-0 border-0"
                  >
                    {compilingRule ? "Refining..." : "Refine Directives"}
                  </button>
                </div>
                <p className="text-[10px] text-stone-400 font-mono leading-normal">
                  Type instructions & click 'Refine Directives' to instantly update the active directive below using Gemini model compiler.
                </p>
              </div>

              {/* Input Area 2: Upload MD Rules */}
              <div className="flex flex-col gap-2.5">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[#ff4d00] text-[16px]">upload_file</span>
                  <label className="text-[10px] font-bold text-stone-700 uppercase tracking-widest">
                    Or Upload Markdown Rules (.md)
                  </label>
                </div>
                <div
                  onDragOver={handleDragOverRules}
                  onDragLeave={handleDragLeaveRules}
                  onDrop={handleDropRules}
                  onClick={() => fileInputRefRules.current?.click()}
                  className={`border border-dashed p-4 flex flex-col items-center justify-center cursor-pointer transition-all ${
                    mdFileDragging ? "border-[#ff4d00] bg-[#ff4d00]/5" : "border-stone-300 hover:border-[#ff4d00] bg-stone-50/30"
                  }`}
                >
                  <span className="material-symbols-outlined text-stone-450 text-[18px] mb-1">download_for_offline</span>
                  <p className="text-[10.5px] font-mono uppercase tracking-wider text-stone-600">
                    {mdFileName ? `Attached: ${mdFileName}` : "Drag and drop markdown rule file here, or click to browse"}
                  </p>
                  <input
                    type="file"
                    ref={fileInputRefRules}
                    onChange={handleMdFileChangeRules}
                    accept=".md"
                    className="hidden"
                  />
                </div>
              </div>

              {/* Direct Text Editor */}
              <div className="flex flex-col gap-2.5">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[#ff4d00] text-[16px]">edit_document</span>
                    <label className="text-[10px] font-bold text-stone-700 uppercase tracking-widest">
                      Active Directive Text (Direct Edit)
                    </label>
                  </div>
                  <button
                    type="button"
                    onClick={handleResetRuleToDefault}
                    className="text-[10px] text-stone-400 hover:text-[#ff4d00] uppercase font-bold tracking-widest hover:underline bg-transparent border-0 cursor-pointer"
                  >
                    Reset to Default
                  </button>
                </div>
                <textarea
                  value={activeRuleType === "intent" ? intentRule : activeRuleType === "persona" ? personaRule : testCaseRule}
                  onChange={(e) => {
                    const txt = e.target.value;
                    if (activeRuleType === "intent") {
                      setIntentRule(txt);
                      localStorage.setItem("system_intent_rule", txt);
                    } else if (activeRuleType === "persona") {
                      setPersonaRule(txt);
                      localStorage.setItem("system_persona_rule", txt);
                    } else if (activeRuleType === "testcase") {
                      setTestCaseRule(txt);
                      localStorage.setItem("system_testcase_rule", txt);
                    }
                  }}
                  className="w-full h-32 bg-stone-50 border border-stone-200 p-3 text-[11.5px] text-[#1a1a1a] font-mono focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none resize-y"
                  placeholder="Insert strict directive rules..."
                />
              </div>

              {/* Footer */}
              <div className="flex justify-end gap-3 border-t border-stone-100 pt-5">
                <button
                  type="button"
                  onClick={() => setIsRuleModalOpen(false)}
                  className="px-6 py-2.5 bg-stone-100 hover:bg-stone-200 text-stone-800 font-bold text-[10px] uppercase tracking-wider font-mono cursor-pointer border-0"
                >
                  Close & Save Directives
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
}
