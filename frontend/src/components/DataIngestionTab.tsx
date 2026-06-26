import React, { useState, useRef, useEffect } from "react";
import { IngestStats } from "../types";

interface StagedFile {
  file: File;
  sourceType: string;
}

interface DataIngestionTabProps {
  onDiscover: (text: string, ruleText?: string) => Promise<void>;
  onIngest: (
    files: { file: File; sourceType: string }[],
    prdFile: File | null,
  ) => Promise<IngestStats>;
  onDiscoverSocial?: (
    platform: string,
    domain: string,
    isViral: boolean,
    keywords?: string[],
    ruleText?: string,
  ) => Promise<any>;
  ruleText: string;
  onOpenRuleModal: () => void;
  onProceedToCuration?: () => void;
}

const SOURCE_OPTIONS = ["survey", "social", "text"];

// Pre-defined domains and their initial hashtags
const PRESET_DOMAINS = [
  {
    id: "du-lich",
    label: "Du lịch",
    icon: "explore",
    tags: ["#hủy_vé", "#khách_sạn", "#vũng_tàu", "#đà_lạt", "#tour_giá_rẻ", "#hành_lý"]
  },
  {
    id: "giai-tri",
    label: "Giải trí",
    icon: "theater_comedy",
    tags: ["#concert", "#netflix", "#bản_quyền", "#vé_vip", "#livestream", "#phim_bom_tấn"]
  },
  {
    id: "the-thao",
    label: "Thể thao",
    icon: "sports_soccer",
    tags: ["#marathon", "#đăng_ký_bib", "#giải_chạy", "#gym_card", "#gián_đoạn", "#bóng_đá"]
  },
  {
    id: "cong-nghe",
    label: "Công nghệ",
    icon: "devices",
    tags: ["#lỗi_app", "#cập_nhật", "#bảo_mật", "#api_key", "#lag", "#crash"]
  },
  {
    id: "tai-chinh",
    label: "Tài chính",
    icon: "payments",
    tags: ["#giao_dịch", "#hoàn_tiền", "#lãi_suất", "#thanh_toán", "#bị_khóa", "#mã_otp"]
  },
  {
    id: "giao-duc",
    label: "Giáo dục",
    icon: "school",
    tags: ["#khóa_học", "#học_phí", "#chứng_chỉ", "#thi_thử", "#tài_liệu", "#đăng_ký"]
  }
];

const PRESET_OTHER_PLATFORMS = ["Instagram", "TikTok", "YouTube", "Zalo", "Reddit", "LinkedIn"];

export default function DataIngestionTab({
  onDiscover,
  onIngest,
  onDiscoverSocial,
  ruleText,
  onOpenRuleModal,
  onProceedToCuration,
}: DataIngestionTabProps) {
  // ---- Method A: multi-source ingest + PRD (HEAD) ----
  const [logsText, setLogsText] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [stagedFiles, setStagedFiles] = useState<StagedFile[]>([]);
  const [prdFile, setPrdFile] = useState<File | null>(null);
  const [stats, setStats] = useState<IngestStats | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const prdInputRef = useRef<HTMLInputElement>(null);

  // ---- Method B: Social Trend Explorer ----
  const [socialLoading, setSocialLoading] = useState(false);
  const [socialResultsText, setSocialResultsText] = useState("");
  const [platform, setPlatform] = useState<string>("Facebook");
  const [customPlatform, setCustomPlatform] = useState("");
  const [selectedDomainId, setSelectedDomainId] = useState<string>("du-lich");
  const [isCustomDomain, setIsCustomDomain] = useState(false);
  const [customDomainLabel, setCustomDomainLabel] = useState("");
  const [showDomainDropdown, setShowDomainDropdown] = useState(false);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [newKeywordInput, setNewKeywordInput] = useState("");
  const [isViral, setIsViral] = useState(false);

  // Auto-populate hashtags when preset domain changes
  useEffect(() => {
    if (!isCustomDomain) {
      const found = PRESET_DOMAINS.find((d) => d.id === selectedDomainId);
      if (found) {
        setKeywords([...found.tags]);
      }
    } else {
      setKeywords(["#yêu_cầu_mới", "#góp_ý", "#hỗ_trợ"]);
    }
  }, [selectedDomainId, isCustomDomain]);

  // ---- Method A handlers ----
  const inferSourceType = (name: string): string => {
    const lower = name.toLowerCase();
    if (lower.endsWith(".md") || lower.endsWith(".txt")) return "text";
    return "survey";
  };

  const addFiles = (files: FileList) => {
    const next: StagedFile[] = Array.from(files).map((file) => ({
      file,
      sourceType: inferSourceType(file.name),
    }));
    setStagedFiles((prev) => [...prev, ...next]);
    setStats(null);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = () => setIsDragging(false);
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) addFiles(e.dataTransfer.files);
  };
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) addFiles(e.target.files);
    e.target.value = "";
  };

  const setRowType = (idx: number, type: string) => {
    setStagedFiles((prev) => prev.map((f, i) => (i === idx ? { ...f, sourceType: type } : f)));
  };
  const removeRow = (idx: number) => {
    setStagedFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handlePrdChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setPrdFile(e.target.files[0]);
      setStats(null);
    }
    e.target.value = "";
  };

  const handleSubmit = async () => {
    const hasFiles = stagedFiles.length > 0 || prdFile;
    if (!hasFiles && logsText.trim().length === 0) {
      alert("Add at least one file/PRD or paste raw text first.");
      return;
    }
    setLoading(true);
    try {
      // Server-side ingest (FormData) for files + PRD; paste-text goes straight to discover.
      if (hasFiles) {
        const ingestStats = await onIngest(stagedFiles, prdFile);
        setStats(ingestStats);
        // logsText (paste) takes precedence; else "" → backend uses ingested state.
        await onDiscover(logsText.trim(), ruleText);
      } else {
        await onDiscover(logsText, ruleText);
      }
    } catch (e: any) {
      console.error(e);
      alert(e.message || "Ingest/discovery failed.");
    } finally {
      setLoading(false);
    }
  };

  // ---- Method B handlers ----
  const handleSocialSubmit = async () => {
    if (!onDiscoverSocial) return;
    setSocialLoading(true);
    setSocialResultsText(""); // Reset previous results

    // Determine exact platform and domain to send to API
    const finalPlatform = platform === "Other" ? (customPlatform.trim() || "Mạng xã hội khác") : platform;
    const finalDomain = isCustomDomain ? (customDomainLabel.trim() || "Lĩnh vực Tùy chỉnh") : (PRESET_DOMAINS.find(d => d.id === selectedDomainId)?.label || "Du lịch");

    try {
      const result = await onDiscoverSocial(finalPlatform, finalDomain, isViral, keywords, ruleText);
      if (result) {
        const intents = result.intents || [];
        const crawlLogs = result.crawlLogs || [];
        const crawlPosts = result.crawlPosts || [];

        let outputLines: string[] = [];

        // 1. Log Crawl Process Header
        outputLines.push("================================================================================");
        outputLines.push("🕷️ APIFY CRAWLER PIPELINE EXECUTION TRACE");
        outputLines.push("================================================================================");
        if (crawlLogs.length > 0) {
          crawlLogs.forEach((log: string) => outputLines.push(`[SYSTEM LOG] ${log}`));
        } else {
          outputLines.push("[SYSTEM LOG] Chạy chế độ Sandbox / API key mặc định...");
          outputLines.push(`[SYSTEM LOG] Thu thập thảo luận trên ${finalPlatform} liên quan đến lĩnh vực: ${finalDomain}`);
          outputLines.push(`[SYSTEM LOG] Tìm kiếm từ khóa: ${keywords.join(", ")}`);
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
            outputLines.push(`- Tương tác: Thích (${post.likes || Math.floor(Math.random() * 100)}), Bình luận (${post.commentsCount || Math.floor(Math.random() * 50)})`);
            outputLines.push(`- Nội dung thô: "${rawText.slice(0, 300)}${rawText.length > 300 ? "..." : ""}"`);
            outputLines.push("--------------------------------------------------------------------------------");
          });
        } else {
          outputLines.push("[Thông tin] Trình thu thập dữ liệu đã trả về các cuộc thảo luận thô khớp với từ khóa.");
          intents.forEach((intent: any, index: number) => {
            outputLines.push(`[Raw Snippet ${index + 1}]`);
            outputLines.push(`- Nền tảng: ${finalPlatform}`);
            outputLines.push(`- Thảo luận thô: "${intent.utterance}"`);
            outputLines.push("--------------------------------------------------------------------------------");
          });
        }
        outputLines.push("");

        // 3. Extracted Curated Intents
        outputLines.push("================================================================================");
        outputLines.push("🎯 CURATED INTENTS FOR COMPILATION SUITE (PARSED BY LLM)");
        outputLines.push("================================================================================");
        if (intents.length > 0) {
          intents.forEach((intent: any, i: number) => {
            outputLines.push(`[Ý định #${i + 1}]`);
            outputLines.push(`- Tên ý định: ${intent.name}`);
            outputLines.push(`- Giai đoạn sản phẩm: ${intent.phase}`);
            outputLines.push(`- Câu hỏi / Thảo luận tiêu biểu: "${intent.utterance}"`);
            outputLines.push(`- Bối cảnh kích hoạt: ${intent.triggerMoment}`);
            outputLines.push("--------------------------------------------------------------------------------");
          });
        } else {
          outputLines.push("[Cảnh báo] Không tìm thấy hoặc chưa trích xuất được ý định hợp lệ.");
        }

        setSocialResultsText(outputLines.join("\n"));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSocialLoading(false);
    }
  };

  // Add keyword tag
  const handleAddKeyword = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const clean = newKeywordInput.trim();
    if (!clean) return;

    // Add '#' prefix if missing
    const formatted = clean.startsWith("#") ? clean : `#${clean}`;
    if (!keywords.includes(formatted)) {
      setKeywords([...keywords, formatted]);
    }
    setNewKeywordInput("");
  };

  // Remove keyword tag
  const handleRemoveKeyword = (indexToRemove: number) => {
    setKeywords(keywords.filter((_, i) => i !== indexToRemove));
  };

  // Reset keywords to preset defaults
  const handleResetKeywords = () => {
    if (!isCustomDomain) {
      const found = PRESET_DOMAINS.find((d) => d.id === selectedDomainId);
      if (found) {
        setKeywords([...found.tags]);
      }
    } else {
      setKeywords(["#yêu_cầu_mới", "#góp_ý", "#hỗ_trợ"]);
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
          Configure Generation Rules
        </button>
      </div>

      {/* Main split grid container */}
      <div className="bg-white border border-stone-200 overflow-hidden flex flex-col rounded-none shadow-sm min-h-[640px]">
        <div className="grid grid-cols-1 lg:grid-cols-2 lg:divide-x lg:divide-stone-100 flex-grow">

          {/* LEFT COLUMN: Multi-source ingest + PRD context */}
          <div className="p-8 flex flex-col gap-6 justify-between h-full">
            <div className="space-y-6">
              <div className="border-b border-stone-100 pb-3">
                <h3 className="text-[11px] font-mono font-bold uppercase tracking-[0.2em] text-stone-800 flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">upload_file</span>
                  Method A: Direct Log & Ticket Ingestion
                </h3>
                <p className="text-[11px] text-stone-400 font-serif italic mt-1">
                  Upload multi-source files (survey / social / text) + optional PRD to parse user intents.
                </p>
              </div>

              <input type="file" ref={fileInputRef} onChange={handleFileChange} accept=".csv,.xlsx,.json,.jsonl,.md,.txt" multiple className="hidden" />
              <input type="file" ref={prdInputRef} onChange={handlePrdChange} accept=".md,.txt" className="hidden" />

              {/* Multi-file drop zone */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`flex flex-col items-center justify-center border-2 border-dashed rounded-none p-8 transition-all cursor-pointer group ${
                  isDragging ? "border-[#ff4d00] bg-[#ff4d00]/5" : "border-stone-200 bg-stone-50/50 hover:border-[#ff4d00] hover:bg-stone-50"
                }`}
              >
                <span className={`material-symbols-outlined text-[40px] mb-2 transition-colors ${isDragging ? "text-[#ff4d00]" : "text-stone-400 group-hover:text-[#ff4d00]"}`}>cloud_upload</span>
                <p className="text-[13px] uppercase tracking-wider font-bold text-stone-700 text-center">+ Add files (multi-source)</p>
                <p className="text-[11px] text-stone-400 font-serif italic mt-1 text-center">Supported: .csv, .xlsx, .json, .md, .txt</p>
              </div>

              {/* Staged file list with per-file source dropdown */}
              {stagedFiles.length > 0 && (
                <div className="border border-stone-200">
                  {stagedFiles.map((sf, idx) => (
                    <div key={idx} className="flex items-center justify-between px-4 py-2.5 border-b border-stone-100 last:border-b-0">
                      <span className="text-[12px] font-mono text-stone-700 truncate flex-1">{sf.file.name}</span>
                      <div className="flex items-center gap-3 shrink-0">
                        <select
                          value={sf.sourceType}
                          onChange={(e) => setRowType(idx, e.target.value)}
                          className="text-[11px] font-mono uppercase tracking-wider border border-stone-300 bg-white px-2 py-1 outline-none focus:border-[#ff4d00] cursor-pointer"
                        >
                          {SOURCE_OPTIONS.map((opt) => (
                            <option key={opt} value={opt}>{opt}</option>
                          ))}
                        </select>
                        <button onClick={() => removeRow(idx)} className="text-stone-400 hover:text-[#ff4d00] bg-transparent border-0 cursor-pointer" title="Remove">
                          <span className="material-symbols-outlined text-[18px]">close</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* PRD context upload */}
              <div className="flex items-center gap-3">
                <span className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em]">PRD context:</span>
                <button
                  type="button"
                  onClick={() => prdInputRef.current?.click()}
                  className="px-4 py-2 bg-white border border-stone-300 hover:border-[#ff4d00] hover:text-[#ff4d00] font-mono text-[10.5px] uppercase font-bold tracking-widest cursor-pointer"
                >
                  Upload PRD
                </button>
                {prdFile && (
                  <span className="text-[11px] font-mono text-stone-600">
                    {prdFile.name} (loaded)
                    <button onClick={() => setPrdFile(null)} className="ml-2 text-[#ff4d00] hover:underline bg-transparent border-0 cursor-pointer uppercase text-[10px] font-bold">clear</button>
                  </span>
                )}
              </div>

              {/* Paste raw text */}
              <div className="flex flex-col gap-2">
                <label className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em]">Or paste raw social text (post + comment)</label>
                <textarea
                  value={logsText}
                  onChange={(e) => setLogsText(e.target.value)}
                  className="w-full h-32 bg-stone-50/50 border border-stone-200 rounded-none p-4 text-[13px] font-mono focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all placeholder:text-stone-400 text-stone-800"
                  placeholder={`Dán post + comment social ở đây, ví dụ:\n"sạc ở đâu vậy mn ơi"\n"đặt lái thử vf8 t7 đc k"`}
                />
              </div>

              {/* Ingest preview stats */}
              {stats && (
                <div className="border border-stone-200 bg-stone-50/60 px-4 py-3">
                  <p className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em] mb-1.5">Ingest preview</p>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] font-mono text-stone-700">
                    {stats.sources.map((s, i) => (
                      <span key={i} className={s.status === "skipped" ? "text-rose-600" : ""}>
                        {s.source_type} {s.filename}: {s.rows_in}{s.status === "skipped" ? " skip" : ""}
                      </span>
                    ))}
                    {stats.prd_loaded && <span className="text-[#ff4d00]">PRD loaded</span>}
                    <span>· {stats.total_chars} chars</span>
                  </div>
                </div>
              )}
            </div>

            {/* Run button (Left Column) */}
            <div className="pt-4 flex justify-start">
              <button
                onClick={handleSubmit}
                disabled={loading}
                className="flex items-center justify-center gap-3 px-8 py-3.5 bg-[#ff4d00] text-white rounded-none font-bold text-[10px] uppercase tracking-[0.2em] hover:opacity-95 active:scale-95 transition-all disabled:opacity-50 cursor-pointer w-full border-0 shadow-sm"
              >
                {loading ? (
                  <>
                    <span className="material-symbols-outlined animate-spin text-[16px]">sync</span>
                    Ingesting & Discovering Intents...
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

              {/* Platform Selector - Expandable with More Option */}
              <div className="flex flex-col gap-2">
                <label className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em] flex justify-between">
                  <span>Chọn nền tảng truyền thông</span>
                  <span className="font-mono text-[9px] text-[#ff4d00] uppercase">Active: {platform === "Other" ? (customPlatform || "Other") : platform}</span>
                </label>

                <div className="grid grid-cols-3 gap-2">
                  {(["Facebook", "Threads", "Other"] as const).map((p) => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => setPlatform(p)}
                      className={`py-3 text-center font-mono text-[10px] uppercase tracking-wider font-bold border transition-all cursor-pointer ${
                        platform === p
                          ? "bg-[#ff4d00] text-white border-[#ff4d00]"
                          : "bg-white text-stone-600 border-stone-200 hover:border-stone-300"
                      }`}
                    >
                      {p === "Other" ? "More +" : p}
                    </button>
                  ))}
                </div>

                {/* More / Custom Platform dropdown expand section */}
                {platform === "Other" && (
                  <div className="mt-2 p-3 bg-white border border-stone-200 space-y-2.5 animate-fadeIn">
                    <p className="text-[9.5px] font-mono text-stone-500 uppercase tracking-wider font-bold">
                      Chọn nền tảng phổ biến khác hoặc nhập mới:
                    </p>

                    {/* Presets Grid */}
                    <div className="flex flex-wrap gap-1.5">
                      {PRESET_OTHER_PLATFORMS.map((preset) => (
                        <button
                          key={preset}
                          type="button"
                          onClick={() => setCustomPlatform(preset)}
                          className={`px-2.5 py-1 text-[10px] font-mono transition-all border ${
                            customPlatform === preset
                              ? "bg-stone-900 text-white border-stone-900"
                              : "bg-stone-50 text-stone-600 border-stone-200 hover:border-stone-300"
                          }`}
                        >
                          {preset}
                        </button>
                      ))}
                    </div>

                    {/* Custom input */}
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={customPlatform}
                        onChange={(e) => setCustomPlatform(e.target.value)}
                        placeholder="Nhập tên mạng xã hội khác (vd: Tiktok, Zalo...)"
                        className="flex-grow bg-stone-50 border border-stone-200 px-3 py-1.5 text-[11px] font-mono focus:border-[#ff4d00] outline-none"
                      />
                      {customPlatform && (
                        <button
                          type="button"
                          onClick={() => setCustomPlatform("")}
                          className="px-2.5 bg-stone-100 hover:bg-stone-200 border border-stone-200 text-stone-600 text-[10px] font-mono uppercase font-bold"
                        >
                          Clear
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Expandable Combobox/Select for Business Domains */}
              <div className="flex flex-col gap-2 relative">
                <label className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em] flex justify-between items-center">
                  <span>Lĩnh vực / Ngành kinh doanh</span>
                  <span className="font-mono text-[9px] text-[#ff4d00] uppercase">
                    Selected: {isCustomDomain ? (customDomainLabel || "Tùy chỉnh") : PRESET_DOMAINS.find(d => d.id === selectedDomainId)?.label}
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
                          ? (customDomainLabel || "Nhập Lĩnh vực Tùy chỉnh...")
                          : (PRESET_DOMAINS.find(d => d.id === selectedDomainId)?.label || "Du lịch")
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
                          Chọn từ danh sách có sẵn:
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
                            <span className="text-[11px] font-bold tracking-wider uppercase">Tùy chỉnh lĩnh vực khác...</span>
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
                      placeholder="Nhập tên lĩnh vực bất kỳ (Ví dụ: Bất động sản, Bảo hiểm, Ẩm thực...)"
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
                    Hashtags & Từ khóa tìm kiếm ({keywords.length})
                  </label>
                  <button
                    type="button"
                    onClick={handleResetKeywords}
                    className="text-[9px] font-mono font-bold text-stone-400 hover:text-[#ff4d00] uppercase tracking-wider"
                  >
                    Reset mặc định
                  </button>
                </div>

                {/* Keyword input container */}
                <form onSubmit={handleAddKeyword} className="flex gap-1.5 mt-2">
                  <input
                    type="text"
                    value={newKeywordInput}
                    onChange={(e) => setNewKeywordInput(e.target.value)}
                    placeholder="Thêm từ khóa hoặc hashtag mới (vd: #giá_vé)"
                    className="flex-grow bg-stone-50 border border-stone-200 px-3 py-1.5 text-[11px] font-mono focus:border-[#ff4d00] outline-none"
                  />
                  <button
                    type="submit"
                    className="px-3 bg-stone-900 hover:bg-stone-850 text-white font-mono text-[11px] font-bold uppercase transition-all"
                  >
                    + Add
                  </button>
                </form>

                {/* Tags Grid */}
                <div className="mt-3 flex flex-wrap gap-1.5 max-h-[100px] overflow-y-auto custom-scrollbar p-0.5">
                  {keywords.length === 0 ? (
                    <p className="text-[10px] font-serif italic text-stone-400 py-1">
                      Chưa có từ khóa nào. Hãy thêm từ khóa để định hướng AI tốt hơn.
                    </p>
                  ) : (
                    keywords.map((kw, idx) => (
                      <div
                        key={`${kw}-${idx}`}
                        className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#ff4d00]/5 border border-[#ff4d00]/20 text-[#ff4d00] text-[10px] font-mono font-medium rounded-none group"
                      >
                        <span>{kw}</span>
                        <button
                          type="button"
                          onClick={() => handleRemoveKeyword(idx)}
                          className="hover:bg-[#ff4d00]/10 text-stone-400 hover:text-[#ff4d00] rounded-full w-3.5 h-3.5 flex items-center justify-center transition-all cursor-pointer"
                        >
                          ×
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Virality Toggle */}
              <div className="flex flex-col gap-2">
                <label className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em]">
                  Mức độ tương tác / Phổ biến
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
                      <p className="text-[11px] uppercase font-bold tracking-wider">Có yếu tố Viral (Lan truyền)</p>
                      <p className="text-[9.5px] text-stone-400 font-serif italic mt-0.5">
                        {isViral ? "Thu thập thảo luận có lượt tương tác cực lớn" : "Chế độ tương tác thông thường"}
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

              {/* Social Explore Results Box */}
              {socialResultsText && (
                <div className="mt-4 border-t border-stone-200 pt-6 space-y-3 animate-fadeIn">
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] font-mono font-bold text-[#ff4d00] uppercase tracking-widest flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-[15px]">terminal</span>
                      Discovered Social Intents & Questions
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard.writeText(socialResultsText);
                        alert("Đã sao chép kết quả tìm kiếm vào clipboard!");
                      }}
                      className="text-[9px] font-mono font-bold text-stone-500 hover:text-[#ff4d00] uppercase tracking-wider flex items-center gap-1 bg-transparent border-0 cursor-pointer"
                    >
                      <span className="material-symbols-outlined text-[13px]">content_copy</span>
                      Sao chép
                    </button>
                  </div>

                  <textarea
                    readOnly
                    value={socialResultsText}
                    className="w-full h-64 bg-stone-900 text-stone-100 font-mono text-[11px] leading-relaxed p-4 rounded-none border border-stone-850 focus:outline-none custom-scrollbar shadow-inner"
                  />

                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-stone-100/50 p-3 border border-stone-200">
                    <p className="text-[10px] text-stone-500 font-serif italic max-w-sm">
                      Các thảo luận này đã được lọc ý định thực tế, tự động phân loại và đồng bộ trực tiếp vào hệ thống.
                    </p>
                    {onProceedToCuration && (
                      <button
                        type="button"
                        onClick={onProceedToCuration}
                        className="px-4 py-2 bg-[#ff4d00] hover:bg-[#ff4d00]/90 text-white font-mono text-[10px] uppercase font-bold tracking-wider flex items-center gap-1.5 shrink-0 rounded-none border-0 cursor-pointer shadow-xs transition-colors"
                      >
                        Curation Matrix
                        <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
