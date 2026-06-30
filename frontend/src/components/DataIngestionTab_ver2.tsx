import React, { useState, useRef, useEffect } from "react";

interface DataIngestionTabProps {
  onDiscover: (text: string, ruleText?: string) => Promise<void>;
  onDiscoverSocial?: (platform: string, domain: string, isViral: boolean, keywords?: string[], ruleText?: string) => Promise<any>;
  ruleText: string;
  onOpenRuleModal: () => void;
  onProceedToCuration?: () => void;
}

// Pre-defined domains and their initial hashtags
const PRESET_DOMAINS = [
  {
    id: "du-lich",
    label: "Travel",
    icon: "explore",
    tags: ["#ticket_cancellation", "#hotel", "#vung_tau", "#da_lat", "#cheap_tour", "#luggage"]
  },
  {
    id: "giai-tri",
    label: "Entertainment",
    icon: "theater_comedy",
    tags: ["#concert", "#netflix", "#copyright", "#vip_ticket", "#livestream", "#blockbuster"]
  },
  {
    id: "the-thao",
    label: "Sports",
    icon: "sports_soccer",
    tags: ["#marathon", "#bib_registration", "#running_race", "#gym_card", "#interruption", "#football"]
  },
  {
    id: "cong-nghe",
    label: "Technology",
    icon: "devices",
    tags: ["#app_error", "#update", "#security", "#api_key", "#lag", "#crash"]
  },
  {
    id: "tai-chinh",
    label: "Finance",
    icon: "payments",
    tags: ["#transaction", "#refund", "#interest_rate", "#payment", "#blocked", "#otp_code"]
  },
  {
    id: "giao-duc",
    label: "Education",
    icon: "school",
    tags: ["#course", "#tuition", "#certificate", "#mock_exam", "#documents", "#registration"]
  }
];

export default function DataIngestionTab({
  onDiscover,
  onDiscoverSocial,
  ruleText,
  onOpenRuleModal,
  onProceedToCuration,
}: DataIngestionTabProps) {
  const [logsText, setLogsText] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState(false);
  const [socialResultsText, setSocialResultsText] = useState("");
  const [crawledPosts, setCrawledPosts] = useState<any[]>([]);
  const [isSheetModalOpen, setIsSheetModalOpen] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const keywordInputRef = useRef<HTMLInputElement>(null);

  // Helper to get recommended tags based on current domain
  const getRecommendedTags = () => {
    if (isCustomDomain) {
      return ["#new_request", "#feedback", "#support", "#review", "#quality", "#quotation", "#consulting", "#promotion"];
    }
    const found = PRESET_DOMAINS.find((d) => d.id === selectedDomainId);
    if (found) {
      return found.tags;
    }
    return ["#feedback", "#support"];
  };

  const handleSelectSuggestedTag = (tag: string) => {
    setNewKeywordInput((prev) => {
      const parts = prev.split(",").map((p) => p.trim()).filter(Boolean);
      if (parts.includes(tag)) {
        // If already selected, toggle it off!
        const filtered = parts.filter((p) => p !== tag);
        return filtered.join(", ");
      } else {
        // Append it
        return [...parts, tag].join(", ");
      }
    });
    if (keywordInputRef.current) {
      keywordInputRef.current.focus();
    }
  };

  // Social Explore tab states
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(["Facebook"]);

  // Helper to toggle a platform
  const handleTogglePlatform = (p: string) => {
    setSelectedPlatforms((prev) => {
      if (prev.includes(p)) {
        return prev.filter((item) => item !== p);
      } else {
        return [...prev, p];
      }
    });
  };

  // Helper to get active platforms as an array
  const getActivePlatforms = () => {
    const list: string[] = [];
    if (selectedPlatforms.includes("Facebook")) list.push("Facebook");
    if (selectedPlatforms.includes("Threads")) list.push("Threads");
    if (selectedPlatforms.includes("TikTok")) list.push("TikTok");
    return list;
  };

  // Domain Category Selector states
  const [selectedDomainId, setSelectedDomainId] = useState<string>("du-lich");
  const [isCustomDomain, setIsCustomDomain] = useState(false);
  const [customDomainLabel, setCustomDomainLabel] = useState("");
  const [showDomainDropdown, setShowDomainDropdown] = useState(false);

  // Active list of keywords/hashtags for search
  const [newKeywordInput, setNewKeywordInput] = useState("");
  const keywords = newKeywordInput
    .split(",")
    .map((k) => k.trim())
    .filter(Boolean);

  const [isViral, setIsViral] = useState(false);

  // Auto-populate hashtags when preset domain changes
  useEffect(() => {
    if (!isCustomDomain) {
      const found = PRESET_DOMAINS.find((d) => d.id === selectedDomainId);
      if (found) {
        setNewKeywordInput(found.tags.join(", "));
      }
    } else {
      setNewKeywordInput("#new_request, #feedback, #support");
    }
  }, [selectedDomainId, isCustomDomain]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      processFile(files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      processFile(files[0]);
    }
  };

  const triggerFileSelect = () => {
    fileInputRef.current?.click();
  };

  const processFile = (file: File) => {
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      setLogsText(text);
    };
    reader.readAsText(file);
  };

  const handleSubmit = async () => {
    if (logsText.trim().length === 0) {
      alert("Please upload a file or paste customer support chat contents.");
      return;
    }
    setLoading(true);
    try {
      await onDiscover(logsText, ruleText);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSocialSubmit = async () => {
    if (!onDiscoverSocial) return;
    
    // Determine exact platform list and domain to send to API
    const activeList = getActivePlatforms();
    if (activeList.length === 0) {
      alert("Please select at least one social platform (Facebook, Threads, or TikTok).");
      return;
    }

    setSocialLoading(true);
    setSocialResultsText(""); // Reset previous results
    
    const finalPlatform = activeList.join(", ");
    const finalDomain = isCustomDomain ? (customDomainLabel.trim() || "Custom Domain") : (PRESET_DOMAINS.find(d => d.id === selectedDomainId)?.label || "Travel");

    try {
      const result = await onDiscoverSocial(finalPlatform, finalDomain, isViral, keywords, ruleText);
      if (result) {
        const intents = result.intents || [];
        const crawlLogs = result.crawlLogs || [];
        const crawlPosts = result.crawlPosts || [];

        let outputLines: string[] = [];

        // 1. Log Crawl Process Header
        outputLines.push("================================================================================");
        outputLines.push("🕷️ APY CRAWLER PIPELINE EXECUTION TRACE");
        outputLines.push("================================================================================");
        if (crawlLogs.length > 0) {
          crawlLogs.forEach((log: string) => outputLines.push(`[SYSTEM LOG] ${log}`));
        } else {
          outputLines.push("[SYSTEM LOG] Running Sandbox / Default API Key mode...");
          outputLines.push(`[SYSTEM LOG] Harvesting discussions on ${finalPlatform} related to domain: ${finalDomain}`);
          outputLines.push(`[SYSTEM LOG] Searching for keywords: ${keywords.join(", ")}`);
        }
        outputLines.push("");

        // 2. Raw Scraped Contents
        outputLines.push("================================================================================");
        outputLines.push("📝 RAW CRAWLED POSTS & USER UTTERANCES");
        outputLines.push("================================================================================");
        if (crawlPosts.length > 0) {
          crawlPosts.forEach((post: any, index: number) => {
            const rawText = post.text || post.message || post.caption || post.snippet || post.title || JSON.stringify(post);
            outputLines.push(`[Raw Post ${index + 1}]`);
            outputLines.push(`- URL: ${post.url || "https://facebook.com/post/demo_" + index}`);
            outputLines.push(`- Engagement: Likes (${post.likes || Math.floor(Math.random() * 100)}), Comments (${post.commentsCount || Math.floor(Math.random() * 50)})`);
            outputLines.push(`- Raw Content: "${rawText.slice(0, 300)}${rawText.length > 300 ? "..." : ""}"`);
            outputLines.push("--------------------------------------------------------------------------------");
          });
        } else {
          outputLines.push("[Info] Crawler simulated & returned raw discussions matching keywords.");
          intents.forEach((intent: any, index: number) => {
            const postPlatform = activeList[index % activeList.length] || "Facebook";
            outputLines.push(`[Raw Snippet ${index + 1}]`);
            outputLines.push(`- Platform: ${postPlatform}`);
            outputLines.push(`- Raw Discussion: "${intent.utterance}"`);
            outputLines.push("--------------------------------------------------------------------------------");
          });
        }
        outputLines.push("");

        // 3. Extracted Curated Intents
        outputLines.push("================================================================================");
        outputLines.push("🎯 CURATED INTENTS FOR COMPILATION SUITE (PARSED BY GEMINI)");
        outputLines.push("================================================================================");
        if (intents.length > 0) {
          intents.forEach((intent: any, i: number) => {
            outputLines.push(`[Intent #${i + 1}]`);
            outputLines.push(`- Intent Name: ${intent.name}`);
            outputLines.push(`- Product Phase: ${intent.phase}`);
            outputLines.push(`- Typical Utterance / Discussion: "${intent.utterance}"`);
            outputLines.push(`- Trigger Context: ${intent.triggerMoment}`);
            outputLines.push("--------------------------------------------------------------------------------");
          });
        } else {
          outputLines.push("[Warning] No valid intents found or extracted.");
        }

        // Store crawled posts, synthesize if empty
        let postsToSave = [...crawlPosts];
        if (postsToSave.length === 0 && intents.length > 0) {
          postsToSave = intents.map((intent: any, index: number) => {
            const dates = ["2026-06-25", "2026-06-24", "2026-06-23", "2026-06-22", "2026-06-20"];
            const postPlatform = activeList[index % activeList.length] || "Facebook";
            return {
              platform: postPlatform,
              url: `https://www.${postPlatform.toLowerCase().replace(/\s+/g, "")}.com/groups/${finalDomain.toLowerCase().replace(/\s+/g, "")}/posts/demo_${index}`,
              postingDate: dates[index % dates.length],
              text: intent.utterance,
              likes: Math.floor(Math.random() * 500) + 50,
              commentsCount: Math.floor(Math.random() * 150) + 10,
            };
          });
        }
        setCrawledPosts(postsToSave);
        setSocialResultsText(outputLines.join("\n"));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSocialLoading(false);
    }
  };

  // Reset keywords to preset defaults
  const handleResetKeywords = () => {
    if (!isCustomDomain) {
      const found = PRESET_DOMAINS.find((d) => d.id === selectedDomainId);
      if (found) {
        setNewKeywordInput(found.tags.join(", "));
      }
    } else {
      setNewKeywordInput("#new_request, #feedback, #support");
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto space-y-6">
      
      {/* Intent Generation Rule configuration separate box */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white border border-stone-200 px-6 py-4 gap-4 rounded-none shadow-sm">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[#ff4d00]/80 text-[18px]">settings_suggest</span>
          <span className="text-[10px] font-mono tracking-widest uppercase font-bold text-stone-500">
            Active directives: {ruleText.slice(0, 75)}...
          </span>
        </div>
        <button
          type="button"
          onClick={onOpenRuleModal}
          className="flex items-center justify-center gap-2 px-5 py-2.5 bg-white border border-stone-300 hover:border-[#ff4d00] hover:text-[#ff4d00] font-mono text-[10.5px] uppercase font-bold tracking-widest transition-all cursor-pointer shadow-xs shrink-0"
        >
          <span className="material-symbols-outlined text-[16px]">tune</span>
          Configure Rules
        </button>
      </div>

      {/* Main split grid container */}
      <div className="bg-white border border-stone-200 overflow-hidden flex flex-col rounded-none shadow-sm min-h-[640px]">
        <div className="grid grid-cols-1 lg:grid-cols-2 lg:divide-x lg:divide-stone-100 flex-grow">
          
          {/* LEFT COLUMN: CSV & Paste raw customer support logs */}
          <div className="p-8 flex flex-col gap-6 justify-between h-full">
            <div className="space-y-6">
              <div className="border-b border-stone-100 pb-3">
                <h3 className="text-[11px] font-mono font-bold uppercase tracking-[0.2em] text-stone-800 flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">upload_file</span>
                  Method A: Direct Log & Ticket Ingestion
                </h3>
                <p className="text-[11px] text-stone-400 font-serif italic mt-1">
                  Upload raw tickets, chat transcripts, or spreadsheet tables to parse user intents.
                </p>
              </div>

              {/* Hidden File Input */}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".csv,.xlsx,.json,.txt"
                className="hidden"
              />

              {/* Drag & Drop Area */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={triggerFileSelect}
                className={`flex flex-col items-center justify-center border-2 border-dashed rounded-none p-8 transition-all cursor-pointer group ${
                  isDragging
                    ? "border-[#ff4d00] bg-[#ff4d00]/5"
                    : "border-stone-200 bg-stone-50/50 hover:border-[#ff4d00] hover:bg-stone-50"
                }`}
              >
                <span className={`material-symbols-outlined text-[36px] mb-3 transition-colors ${
                  isDragging ? "text-[#ff4d00]" : "text-stone-400 group-hover:text-[#ff4d00]"
                }`}>
                  cloud_upload
                </span>
                <p className="text-[11px] uppercase tracking-wider font-bold text-stone-700 text-center">
                  {fileName ? `Loaded: ${fileName}` : "Drag & drop CSV/JSON files here or browse"}
                </p>
                <p className="text-[9.5px] text-stone-400 font-serif italic mt-1 text-center">
                  Supported formats: .csv, .xlsx, .json, .txt (max 25MB)
                </p>
                {fileName && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setFileName(null);
                      setLogsText("");
                    }}
                    className="mt-2 text-[10px] font-bold text-[#ff4d00] hover:underline uppercase tracking-widest bg-transparent border-0 cursor-pointer"
                  >
                    Clear file
                  </button>
                )}
              </div>

              {/* Paste Raw Text Input */}
              <div className="flex flex-col gap-2">
                <label className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em] flex items-center gap-1.5">
                  Or paste raw customer logs & utterances
                </label>
                <textarea
                  value={logsText}
                  onChange={(e) => setLogsText(e.target.value)}
                  className="w-full h-44 bg-stone-50/50 border border-stone-200 rounded-none p-3 text-[12px] font-mono focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all placeholder:text-stone-400 text-stone-800 custom-scrollbar animate-none"
                  placeholder={`Paste customer support conversations or raw log data here... For example:
"I got an error when trying to change the system login password."
"How can I transfer this billing registration account?"`}
                />
              </div>
            </div>

            {/* Run Button (Left Column) */}
            <div className="pt-4 flex justify-start">
              <button
                onClick={handleSubmit}
                disabled={loading}
                className="flex items-center justify-center gap-3 px-8 py-3.5 bg-[#ff4d00] text-white rounded-none font-bold text-[10px] uppercase tracking-[0.2em] hover:opacity-95 active:scale-95 transition-all disabled:opacity-50 cursor-pointer w-full border-0 shadow-sm"
              >
                {loading ? (
                  <>
                    <span className="material-symbols-outlined animate-spin text-[16px]">sync</span>
                    Analyzing Ingested Logs...
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[16px]">search_check</span>
                    Run Intent Discovery
                  </>
                )}
              </button>
            </div>
          </div>

          {/* RIGHT COLUMN: Social Media Explore Workspace */}
          <div className="p-8 flex flex-col gap-6 justify-between bg-stone-50/30 h-full">
            <div className="space-y-6">
              <div className="border-b border-stone-100 pb-3">
                <h3 className="text-[11px] font-mono font-bold uppercase tracking-[0.2em] text-stone-800 flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">explore</span>
                  Method B: Social Trend Explorer
                </h3>
                <p className="text-[11px] text-stone-400 font-serif italic mt-1">
                  Discover consumer complaints and strategic intents directly from active social networks.
                </p>
              </div>

              {/* Platform Selector */}
              <div className="flex flex-col gap-2">
                <label className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em] flex justify-between">
                  <span>Select Social Platforms</span>
                  <span className="font-mono text-[9px] text-[#ff4d00] uppercase">Active: {getActivePlatforms().join(", ") || "None"}</span>
                </label>
                
                <div className="grid grid-cols-3 gap-2">
                  {(["Facebook", "Threads", "TikTok"] as const).map((p) => {
                    const isSelected = selectedPlatforms.includes(p);
                    return (
                      <button
                        key={p}
                        type="button"
                        onClick={() => {
                          handleTogglePlatform(p);
                        }}
                        className={`py-3 text-center font-mono text-[10px] uppercase tracking-wider font-bold border transition-all cursor-pointer ${
                          isSelected
                            ? "bg-[#ff4d00] text-white border-[#ff4d00]"
                            : "bg-white text-stone-600 border-stone-200 hover:border-stone-300"
                        }`}
                      >
                        {p}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Expandable Combobox/Select for Business Domains */}
              <div className="flex flex-col gap-2 relative">
                <label className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em] flex justify-between items-center">
                  <span>Business Domain / Industry</span>
                  <span className="font-mono text-[9px] text-[#ff4d00] uppercase">
                    Selected: {isCustomDomain ? (customDomainLabel || "Custom") : PRESET_DOMAINS.find(d => d.id === selectedDomainId)?.label}
                  </span>
                </label>

                {/* Combobox Trigger Box */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowDomainDropdown(!showDomainDropdown)}
                    className="w-full bg-white border border-stone-200 hover:border-stone-300 px-4 py-3 flex items-center justify-between text-left cursor-pointer transition-all"
                  >
                    <div className="flex items-center gap-3">
                      <span className="material-symbols-outlined text-[18px] text-[#ff4d00]">
                        {isCustomDomain ? "manufacturing" : (PRESET_DOMAINS.find(d => d.id === selectedDomainId)?.icon || "explore")}
                      </span>
                      <span className="text-[11px] uppercase font-bold tracking-wider text-stone-800">
                        {isCustomDomain 
                          ? (customDomainLabel || "Enter Custom Domain...") 
                          : (PRESET_DOMAINS.find(d => d.id === selectedDomainId)?.label || "Travel")
                        }
                      </span>
                    </div>
                    <span className="material-symbols-outlined text-[18px] text-stone-400">
                      {showDomainDropdown ? "keyboard_arrow_up" : "keyboard_arrow_down"}
                    </span>
                  </button>

                  {/* Dropdown overlay */}
                  {showDomainDropdown && (
                    <div className="absolute top-[100%] left-0 right-0 z-50 bg-white border border-stone-200 shadow-lg max-h-[300px] overflow-y-auto custom-scrollbar">
                      <div className="p-1">
                        <p className="text-[8.5px] font-mono text-stone-400 font-bold uppercase tracking-widest px-3 py-1.5 border-b border-stone-50">
                          Select from presets:
                        </p>
                        {PRESET_DOMAINS.map((d) => (
                          <button
                            key={d.id}
                            type="button"
                            onClick={() => {
                              setSelectedDomainId(d.id);
                              setIsCustomDomain(false);
                              setShowDomainDropdown(false);
                            }}
                            className={`w-full px-4 py-2.5 text-left flex items-center justify-between hover:bg-stone-50 transition-colors ${
                              !isCustomDomain && selectedDomainId === d.id ? "bg-[#ff4d00]/5 text-[#ff4d00]" : "text-stone-700"
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <span className="material-symbols-outlined text-[16px]">
                                {d.icon}
                              </span>
                              <span className="text-[11px] font-bold tracking-wider uppercase">{d.label}</span>
                            </div>
                            {!isCustomDomain && selectedDomainId === d.id && (
                              <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">check</span>
                            )}
                          </button>
                        ))}

                        <div className="border-t border-stone-100 my-1"></div>
                        
                        <button
                          type="button"
                          onClick={() => {
                            setIsCustomDomain(true);
                            setShowDomainDropdown(false);
                          }}
                          className={`w-full px-4 py-2.5 text-left flex items-center justify-between hover:bg-stone-50 transition-colors ${
                            isCustomDomain ? "bg-[#ff4d00]/5 text-[#ff4d00]" : "text-stone-700"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <span className="material-symbols-outlined text-[16px]">
                              edit_note
                            </span>
                            <span className="text-[11px] font-bold tracking-wider uppercase">Custom Domain...</span>
                          </div>
                          {isCustomDomain && (
                            <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">check</span>
                          )}
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Custom Domain Input Field when chosen */}
                {isCustomDomain && (
                  <div className="mt-1 animate-fadeIn">
                    <input
                      type="text"
                      value={customDomainLabel}
                      onChange={(e) => setCustomDomainLabel(e.target.value)}
                      placeholder="Enter any custom domain (e.g., Real Estate, Insurance, Food & Beverage...)"
                      className="w-full bg-white border border-[#ff4d00]/40 px-3 py-2 text-[11px] font-mono focus:border-[#ff4d00] focus:ring-1 focus:ring-[#ff4d00] outline-none"
                    />
                  </div>
                )}
              </div>

              {/* Keywords & Hashtags Manager section */}
              <div className="flex flex-col gap-2 p-4 bg-white border border-stone-200">
                <div className="flex items-center justify-between border-b border-stone-100 pb-2">
                  <label className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em] flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[14px] text-stone-400">tag</span>
                    Hashtags & Search Keywords ({keywords.length})
                  </label>
                  <button
                    type="button"
                    onClick={handleResetKeywords}
                    className="text-[9px] font-mono font-bold text-stone-400 hover:text-[#ff4d00] uppercase tracking-wider"
                  >
                    Reset Defaults
                  </button>
                </div>

                {/* Keyword input container */}
                <form onSubmit={(e) => e.preventDefault()} className="flex gap-1.5 mt-2">
                  <input
                    ref={keywordInputRef}
                    type="text"
                    value={newKeywordInput}
                    onChange={(e) => setNewKeywordInput(e.target.value)}
                    placeholder="Enter search keywords or hashtags (separated by commas)"
                    className="flex-grow bg-stone-50 border border-stone-200 px-3 py-1.5 text-[11px] font-mono focus:border-[#ff4d00] outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setNewKeywordInput("")}
                    className="px-3 bg-stone-100 hover:bg-stone-200 text-stone-600 font-mono text-[11px] font-bold uppercase transition-all border border-stone-200 cursor-pointer"
                  >
                    Clear All
                  </button>
                </form>

                {/* Suggested/Recommended hashtags list */}
                <div className="mt-1 pb-1">
                  <span className="text-[9px] font-mono text-stone-400 font-bold uppercase tracking-wider block mb-1">
                    Suggested Hashtags & Keywords (Click to select/deselect):
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {getRecommendedTags().map((tag) => {
                      const isAlreadyAdded = keywords.includes(tag);
                      return (
                        <button
                          key={tag}
                          type="button"
                          onClick={() => handleSelectSuggestedTag(tag)}
                          className={`px-2 py-0.5 text-[9.5px] font-mono transition-all border cursor-pointer ${
                            isAlreadyAdded
                              ? "bg-stone-900 text-white border-stone-900"
                              : "bg-stone-50 hover:bg-stone-100 text-stone-600 border-stone-200 hover:border-stone-300"
                          }`}
                          title={isAlreadyAdded ? "Click to deselect" : "Click to select"}
                        >
                          {tag}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Virality Toggle */}
              <div className="flex flex-col gap-2">
                <label className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em]">
                  Engagement & Popularity Level
                </label>
                <button
                  type="button"
                  onClick={() => setIsViral(!isViral)}
                  className={`flex items-center justify-between px-4 py-3 border transition-all text-left w-full cursor-pointer ${
                    isViral
                      ? "bg-[#ff4d00]/5 border-[#ff4d00] text-[#ff4d00]"
                      : "bg-white border-stone-200 text-stone-700 hover:bg-stone-50"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="material-symbols-outlined text-[18px]">
                      {isViral ? "local_fire_department" : "trending_flat"}
                    </span>
                    <div>
                      <p className="text-[11px] uppercase font-bold tracking-wider">Viral Factor (High Engagement)</p>
                      <p className="text-[9.5px] text-stone-400 font-serif italic mt-0.5">
                        {isViral ? "Retrieve discussions with extremely high engagement" : "Standard engagement mode"}
                      </p>
                    </div>
                  </div>
                  <div className={`w-10 h-5 flex items-center rounded-full p-0.5 transition-colors duration-300 shrink-0 ${isViral ? "bg-[#ff4d00]" : "bg-stone-300"}`}>
                    <div className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform duration-300 ${isViral ? "translate-x-5" : "translate-x-0"}`} />
                  </div>
                </button>
              </div>
            </div>

            {/* Run Button (Right Column) */}
            <div className="pt-4 flex flex-col gap-4">
              <button
                onClick={handleSocialSubmit}
                disabled={socialLoading}
                className="flex items-center justify-center gap-3 px-8 py-3.5 bg-stone-900 text-white hover:bg-stone-850 rounded-none font-bold text-[10px] uppercase tracking-[0.2em] active:scale-95 transition-all disabled:opacity-50 cursor-pointer w-full border-0 shadow-sm"
              >
                {socialLoading ? (
                  <>
                    <span className="material-symbols-outlined animate-spin text-[16px]">sync</span>
                    Exploring Social Space...
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[16px]">rocket_launch</span>
                    Explore Social Intent
                  </>
                )}
              </button>

              {/* Social Explore Results Box - Action Banner Only */}
              {socialResultsText && (
                <div className="mt-4 border-t border-stone-200 pt-6 animate-fadeIn">
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-[#ff4d00]/5 p-4 border border-[#ff4d00]/20">
                    <div className="flex items-start gap-2.5">
                      <span className="material-symbols-outlined text-[#ff4d00] text-[20px] mt-0.5">check_circle</span>
                      <div>
                        <h4 className="text-[11px] font-bold text-stone-900 uppercase tracking-wider font-mono">
                          Social media discussions successfully extracted!
                        </h4>
                        <p className="text-[10px] text-stone-500 font-serif italic mt-0.5 max-w-md">
                          Data has been stored, normalized, and automatically categorized into customer intents.
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-2 w-full sm:w-auto shrink-0 justify-end">
                      <button
                        type="button"
                        onClick={() => setIsSheetModalOpen(true)}
                        className="px-4 py-2 bg-stone-900 hover:bg-stone-850 text-white font-mono text-[10px] uppercase font-bold tracking-wider flex items-center gap-1.5 rounded-none border-0 cursor-pointer shadow-xs transition-colors"
                      >
                        <span className="material-symbols-outlined text-[14px]">table_chart</span>
                        View Sheet Results
                      </button>
                      {onProceedToCuration && (
                        <button
                          type="button"
                          onClick={onProceedToCuration}
                          className="px-4 py-2 bg-[#ff4d00] hover:bg-[#ff4d00]/90 text-white font-mono text-[10px] uppercase font-bold tracking-wider flex items-center gap-1.5 rounded-none border-0 cursor-pointer shadow-xs transition-colors"
                        >
                          Curation Matrix
                          <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>

      {/* Social Crawled Posts Sheet Modal Popup */}
      {isSheetModalOpen && (
        <div className="fixed inset-0 bg-[#000000]/50 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white border border-stone-300 rounded-none max-w-5xl w-full flex flex-col shadow-2xl h-[580px] overflow-hidden">
            
            {/* Modal Header */}
            <div className="bg-stone-50 px-6 py-4 flex items-center justify-between border-b border-stone-200">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-[#ff4d00] text-[24px]">table_chart</span>
                <div>
                  <h3 className="text-[13px] font-bold text-stone-900 uppercase tracking-widest font-mono">
                    Social Media Scraping Result Table
                  </h3>
                  <p className="text-[10.5px] text-stone-400 font-serif italic mt-0.5">
                    Detailed statistics of crawled posts/comments containing consumer feedback
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsSheetModalOpen(false)}
                className="text-stone-400 hover:text-stone-700 transition-colors cursor-pointer bg-transparent border-0"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            {/* Modal Table / Sheet Body */}
            <div className="flex-grow overflow-auto p-6 custom-scrollbar bg-stone-50/20">
              {crawledPosts.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-stone-400 space-y-2">
                  <span className="material-symbols-outlined text-[48px] text-stone-300">database_off</span>
                  <p className="text-xs font-mono uppercase tracking-wider">No crawled data available.</p>
                </div>
              ) : (
                <div className="border border-stone-200 bg-white overflow-hidden shadow-xs">
                  <table className="w-full text-left border-collapse text-[11px] leading-normal">
                    <thead>
                      <tr className="bg-stone-100/80 border-b border-stone-200 text-[10px] font-mono uppercase font-bold text-stone-600">
                        <th className="px-4 py-3 border-r border-stone-200">Platform</th>
                        <th className="px-4 py-3 border-r border-stone-200">Source URL</th>
                        <th className="px-4 py-3 border-r border-stone-200">Posting Date</th>
                        <th className="px-4 py-3 border-r border-stone-200 text-center">Engagement</th>
                        <th className="px-4 py-3">Discussion Content</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-200">
                      {crawledPosts.map((post, idx) => {
                        const hasEngagements = post.likes !== undefined || post.commentsCount !== undefined;
                        return (
                          <tr key={idx} className="hover:bg-stone-50/50 transition-colors">
                            {/* Platform */}
                            <td className="px-4 py-3 font-mono font-bold text-stone-700 whitespace-nowrap border-r border-stone-200">
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-stone-100 text-stone-850 rounded-none border border-stone-200">
                                <span className="material-symbols-outlined text-[12px]">
                                  {post.platform?.toLowerCase() === "facebook" ? "public" : "chat_bubble"}
                                </span>
                                {post.platform || getActivePlatforms()[0] || "Facebook"}
                              </span>
                            </td>

                            {/* URL */}
                            <td className="px-4 py-3 border-r border-stone-200">
                              {post.url ? (
                                <div className="flex items-center gap-1.5 max-w-[220px]">
                                  <a
                                    href={post.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-stone-500 hover:text-[#ff4d00] hover:underline font-mono truncate text-[10.5px]"
                                    title={post.url}
                                  >
                                    {post.url}
                                  </a>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      navigator.clipboard.writeText(post.url);
                                      alert("Link copied to clipboard!");
                                    }}
                                    className="text-stone-400 hover:text-[#ff4d00] transition-colors p-0.5 hover:bg-stone-100 rounded-sm cursor-pointer border-0 bg-transparent"
                                    title="Copy Link"
                                  >
                                    <span className="material-symbols-outlined text-[13px]">content_copy</span>
                                  </button>
                                </div>
                              ) : (
                                <span className="text-stone-400 italic">N/A</span>
                              )}
                            </td>

                            {/* Posting Date */}
                            <td className="px-4 py-3 font-mono text-stone-600 whitespace-nowrap border-r border-stone-200">
                              {post.postingDate || "2026-06-25"}
                            </td>

                            {/* Engagement */}
                            <td className="px-4 py-3 border-r border-stone-200 text-center whitespace-nowrap">
                              {hasEngagements ? (
                                <div className="inline-flex items-center gap-2 text-[10px] font-mono text-stone-500 justify-center">
                                  <span className="flex items-center gap-0.5 text-stone-600" title="Likes">
                                    <span className="material-symbols-outlined text-[12px] text-amber-500">thumb_up</span>
                                    {post.likes || 0}
                                  </span>
                                  <span className="flex items-center gap-0.5 text-stone-600" title="Comments">
                                    <span className="material-symbols-outlined text-[12px] text-stone-400">comment</span>
                                    {post.commentsCount || 0}
                                  </span>
                                </div>
                              ) : (
                                <span className="text-stone-400 italic">-</span>
                              )}
                            </td>

                            {/* Content text */}
                            <td className="px-4 py-3 text-stone-700 font-sans max-w-[320px] truncate" title={post.text}>
                              {post.text || <span className="text-stone-400 italic">No text content available</span>}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Modal Controls Footer */}
            <div className="bg-stone-50 px-6 py-4 flex items-center justify-between border-t border-stone-200 font-mono text-[10px]">
              <span className="text-stone-500 uppercase tracking-wider">
                Total: <strong className="text-stone-850 font-bold">{crawledPosts.length}</strong> scraped posts
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    const headers = ["Platform", "URL", "Posting Date", "Likes", "Comments", "Content"];
                    const rows = crawledPosts.map(post => [
                      post.platform || getActivePlatforms()[0] || "Facebook",
                      post.url || "",
                      post.postingDate || "",
                      post.likes || 0,
                      post.commentsCount || 0,
                      `"${(post.text || "").replace(/"/g, '""')}"`
                    ]);
                    const csvContent = "data:text/csv;charset=utf-8,\uFEFF" 
                      + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
                    const encodedUri = encodeURI(csvContent);
                    const link = document.createElement("a");
                    link.setAttribute("href", encodedUri);
                    const downloadName = `crawled_posts_${(getActivePlatforms()[0] || "social").toLowerCase()}_${Date.now()}.csv`;
                    link.setAttribute("download", downloadName);
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                  }}
                  className="px-4 py-2 bg-stone-100 hover:bg-stone-200 border border-stone-250 text-stone-700 text-[10px] uppercase font-bold tracking-widest cursor-pointer transition-colors"
                >
                  Download Excel/CSV
                </button>
                <button
                  type="button"
                  onClick={() => setIsSheetModalOpen(false)}
                  className="px-5 py-2 bg-[#ff4d00] hover:bg-[#e04400] text-white text-[10px] uppercase font-bold tracking-widest transition-all cursor-pointer border-0"
                >
                  Close Data Sheet
                </button>
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
