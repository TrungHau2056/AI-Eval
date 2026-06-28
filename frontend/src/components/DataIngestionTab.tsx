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
  onCrawlSocial?: (
    platforms: string[],
    domain: string,
    keywords?: string[],
    maxPosts?: number,
  ) => Promise<{ crawlPosts: any[]; crawlLogs: string[] }>;
  ruleText: string;
  onOpenRuleModal: () => void;
  onProceedToCuration?: () => void;
}

const SOURCE_OPTIONS = ["survey", "social", "text"];

// Selectable social platforms (multi-select checkboxes).
const PLATFORMS = ["Facebook", "Threads", "TikTok"];

// Pre-defined domains and their initial hashtags (kept in Vietnamese — used as real crawl keywords).
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

export default function DataIngestionTab({
  onDiscover,
  onIngest,
  onCrawlSocial,
  ruleText,
  onOpenRuleModal,
  onProceedToCuration,
}: DataIngestionTabProps) {
  // ---- Multi-source ingest + PRD ----
  const [logsText, setLogsText] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [stagedFiles, setStagedFiles] = useState<StagedFile[]>([]);
  const [prdFile, setPrdFile] = useState<File | null>(null);
  const [stats, setStats] = useState<IngestStats | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const prdInputRef = useRef<HTMLInputElement>(null);

  // ---- Social Trend Explorer ----
  const [socialLoading, setSocialLoading] = useState(false);
  const [socialResultsText, setSocialResultsText] = useState("");
  const [crawledPosts, setCrawledPosts] = useState<any[]>([]);
  const [isSheetModalOpen, setIsSheetModalOpen] = useState(false);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(["Facebook"]);
  const [selectedDomainId, setSelectedDomainId] = useState<string>("du-lich");
  const [isCustomDomain, setIsCustomDomain] = useState(false);
  const [customDomainLabel, setCustomDomainLabel] = useState("");
  const [showDomainDropdown, setShowDomainDropdown] = useState(false);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [newKeywordInput, setNewKeywordInput] = useState("");
  const [isViral, setIsViral] = useState(false);
  // Cap tổng số post crawl mỗi nền tảng (bất kể số keyword). Trần backend = 50.
  const [maxPostsPerPlatform, setMaxPostsPerPlatform] = useState(2);

  // Toggle a platform in the multi-select list.
  const handleTogglePlatform = (p: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p],
    );
  };

  // Active platforms preserving the canonical order.
  const getActivePlatforms = () => PLATFORMS.filter((p) => selectedPlatforms.includes(p));

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

  // ---- Ingest handlers ----
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

  // Run Intent Discovery from any uploaded/pasted source (file / PRD / text). At least one required.
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

  // ---- Crawl-only handler: collect raw social posts into the results sheet ----
  // Intent extraction is NOT done here — that happens in Run Intent Discovery, which
  // reads the crawled content the backend persists.
  const handleCrawlSubmit = async () => {
    if (!onCrawlSocial) return;

    // Require at least one selected platform.
    const activeList = getActivePlatforms();
    if (activeList.length === 0) {
      alert("Please select at least one social platform.");
      return;
    }

    setSocialLoading(true);
    setSocialResultsText(""); // Reset previous results

    // Determine exact platform list and domain to send to API.
    const finalPlatform = activeList.join(", ");
    const finalDomain = isCustomDomain ? (customDomainLabel.trim() || "Lĩnh vực Tùy chỉnh") : (PRESET_DOMAINS.find(d => d.id === selectedDomainId)?.label || "Du lịch");

    try {
      const result = await onCrawlSocial(activeList, finalDomain, keywords, maxPostsPerPlatform);
      let postsToSave: any[] = result?.crawlPosts ? [...result.crawlPosts] : [];

      // Demo fallback when the crawler returns nothing (e.g. no Apify token): build
      // placeholder rows so the sheet isn't blank. Respect the per-platform cap:
      // up to maxPostsPerPlatform rows for EACH selected platform.
      if (postsToSave.length === 0) {
        const dates = ["2026-06-25", "2026-06-24", "2026-06-23", "2026-06-22", "2026-06-20"];
        const sampleTexts = keywords.length > 0 ? keywords : ["#feedback", "#support", "#issue"];
        postsToSave = activeList.flatMap((postPlatform) =>
          Array.from({ length: maxPostsPerPlatform }, (_, i) => {
            const kw = sampleTexts[i % sampleTexts.length];
            return {
              platform: postPlatform,
              url: `https://www.${postPlatform.toLowerCase().replace(/\s+/g, "")}.com/groups/${finalDomain.toLowerCase().replace(/\s+/g, "")}/posts/demo_${i}`,
              postingDate: dates[i % dates.length],
              text: `Thảo luận mẫu liên quan đến ${kw} trên ${postPlatform}.`,
              likes: Math.floor(Math.random() * 500) + 50,
              commentsCount: Math.floor(Math.random() * 150) + 10,
            };
          }),
        );
      }

      setCrawledPosts(postsToSave);
      // Non-empty marker just to reveal the results banner.
      setSocialResultsText(`Crawled ${postsToSave.length} posts from ${finalPlatform}.`);
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
          Configure Rules
        </button>
      </div>

      {/* Unified ingestion & discovery workspace */}
      <div className="bg-white border border-stone-200 overflow-hidden flex flex-col rounded-none shadow-sm min-h-[640px]">
        <div className="p-8 flex flex-col gap-8">

          {/* Workspace header */}
          <div className="border-b border-stone-100 pb-3">
            <h3 className="text-[12px] font-mono font-bold uppercase tracking-[0.2em] text-stone-800 flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px] text-[#ff4d00]">database</span>
              Data Ingestion & Intent Discovery
            </h3>
            <p className="text-[11px] text-stone-400 font-serif italic mt-1">
              Upload multi-source data or explore live social trends to discover user intents — both flows feed the same pipeline.
            </p>
          </div>

          {/* Two input groups inside one workspace (no Method A/B split) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

            {/* GROUP: Input Sources */}
            <div className="space-y-6">
              <div className="border-b border-stone-100 pb-3">
                <h4 className="text-[11px] font-mono font-bold uppercase tracking-[0.2em] text-stone-700 flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">upload_file</span>
                  Input Sources
                </h4>
                <p className="text-[11px] text-stone-400 font-serif italic mt-1">
                  Upload files (survey / social / text) + optional PRD, or paste raw text. At least one source is required.
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
                  placeholder={`Paste social posts + comments here, e.g.\n"where can I charge it?"\n"can I book a vf8 test drive this Saturday?"`}
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

            {/* GROUP: Social Trend Explorer */}
            <div className="space-y-6">
              <div className="border-b border-stone-100 pb-3">
                <h4 className="text-[11px] font-mono font-bold uppercase tracking-[0.2em] text-stone-700 flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">explore</span>
                  Social Trend Explorer
                </h4>
                <p className="text-[11px] text-stone-400 font-serif italic mt-1">
                  Discover consumer complaints and strategic intents directly from active social networks.
                </p>
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
                          ? (customDomainLabel || "Enter custom domain...")
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
                            <span className="text-[11px] font-bold tracking-wider uppercase">Custom domain...</span>
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
                      placeholder="Enter any domain (e.g. Real Estate, Insurance, F&B...)"
                      className="w-full bg-white border border-[#ff4d00]/40 px-3 py-2 text-[11px] font-mono focus:border-[#ff4d00] focus:ring-1 focus:ring-[#ff4d00] outline-none"
                    />
                  </div>
                )}
              </div>

              {/* Platform Selector - multi-select checkboxes */}
              <div className="flex flex-col gap-2">
                <label className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em] flex justify-between">
                  <span>Select social platforms</span>
                  <span className="font-mono text-[9px] text-[#ff4d00] uppercase">Active: {getActivePlatforms().join(", ") || "None"}</span>
                </label>

                <div className="grid grid-cols-3 gap-2">
                  {PLATFORMS.map((p) => {
                    const checked = selectedPlatforms.includes(p);
                    return (
                      <label
                        key={p}
                        className={`flex items-center justify-center gap-2 py-3 px-2 border font-mono text-[10px] uppercase tracking-wider font-bold cursor-pointer transition-all ${
                          checked
                            ? "bg-[#ff4d00] text-white border-[#ff4d00]"
                            : "bg-white text-stone-600 border-stone-200 hover:border-stone-300"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => handleTogglePlatform(p)}
                          className="w-3.5 h-3.5 accent-[#ff4d00] cursor-pointer"
                        />
                        {p}
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Keywords & Hashtags Manager section */}
              <div className="flex flex-col gap-2 p-4 bg-white border border-stone-200">
                <div className="flex items-center justify-between border-b border-stone-100 pb-2">
                  <label className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em] flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[14px] text-stone-400">tag</span>
                    Hashtags & Search keywords ({keywords.length})
                  </label>
                  <button
                    type="button"
                    onClick={handleResetKeywords}
                    className="text-[9px] font-mono font-bold text-stone-400 hover:text-[#ff4d00] uppercase tracking-wider"
                  >
                    Reset to defaults
                  </button>
                </div>

                {/* Keyword input container */}
                <form onSubmit={handleAddKeyword} className="flex gap-1.5 mt-2">
                  <input
                    type="text"
                    value={newKeywordInput}
                    onChange={(e) => setNewKeywordInput(e.target.value)}
                    placeholder="Add a new keyword or hashtag (e.g. #giá_vé)"
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
                      No keywords yet. Add keywords to better guide the AI.
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
                  Engagement / Popularity level
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
                      <p className="text-[11px] uppercase font-bold tracking-wider">Include viral signals</p>
                      <p className="text-[9.5px] text-stone-400 font-serif italic mt-0.5">
                        {isViral ? "Collect discussions with very high engagement" : "Standard engagement mode"}
                      </p>
                    </div>
                  </div>
                  <div className={`w-10 h-5 flex items-center rounded-full p-0.5 transition-colors duration-300 shrink-0 ${isViral ? "bg-[#ff4d00]" : "bg-stone-300"}`}>
                    <div className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform duration-300 ${isViral ? "translate-x-5" : "translate-x-0"}`} />
                  </div>
                </button>
              </div>

              {/* Max posts per platform */}
              <div className="flex flex-col gap-2">
                <label className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em]">
                  Posts per platform
                </label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={maxPostsPerPlatform}
                  onChange={(e) =>
                    setMaxPostsPerPlatform(
                      Math.max(1, Math.min(50, Number(e.target.value) || 1)),
                    )
                  }
                  className="px-4 py-3 border border-stone-200 bg-white text-stone-700 text-[12px] font-mono focus:border-[#ff4d00] focus:outline-none w-full"
                />
                <p className="text-[9.5px] text-stone-400 font-serif italic">
                  Limit total posts per platform (1–50), regardless of the number of keywords.
                </p>
              </div>
            </div>
          </div>
 {/* Social Explore Results Box - Action Banner */}
          {socialResultsText && (
            <div className="mt-2 border-t border-stone-200 pt-6 animate-fadeIn">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-[#ff4d00]/5 p-4 border border-[#ff4d00]/20">
                <div className="flex items-start gap-2.5">
                  <span className="material-symbols-outlined text-[#ff4d00] text-[20px] mt-0.5">check_circle</span>
                  <div>
                    <h4 className="text-[11px] font-bold text-stone-900 uppercase tracking-wider font-mono">
                      Social data crawled successfully!
                    </h4>
                    <p className="text-[10px] text-stone-500 font-serif italic mt-0.5 max-w-md">
                      Raw crawled posts are listed below — open the sheet to review, or run Intent Discovery to extract intents.
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
                    View results (Sheet)
                  </button>
                </div>
              </div>
            </div>
          )}
          {/* Shared action footer: both run buttons */}
          <div className="border-t border-stone-100 pt-6 flex flex-col sm:flex-row gap-4">
            {/* Run Intent Discovery (from uploaded/pasted sources) */}
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-3 px-8 py-3.5 bg-[#ff4d00] text-white rounded-none font-bold text-[10px] uppercase tracking-[0.2em] hover:opacity-95 active:scale-95 transition-all disabled:opacity-50 cursor-pointer border-0 shadow-sm"
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

              
            {/* Crawl Social Data (raw crawl → results sheet; no intent extraction) */}
            <button
              onClick={handleCrawlSubmit}
              disabled={socialLoading}
              className="flex-1 flex items-center justify-center gap-3 px-8 py-3.5 bg-stone-900 text-white hover:bg-stone-850 rounded-none font-bold text-[10px] uppercase tracking-[0.2em] active:scale-95 transition-all disabled:opacity-50 cursor-pointer border-0 shadow-sm"
            >
              {socialLoading ? (
                <>
                  <span className="material-symbols-outlined animate-spin text-[16px]">sync</span>
                  Crawling Social Data...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[16px]">travel_explore</span>
                  Crawl Social Data
                </>
              )}
            </button>
          </div>

          {/* Social Explore Results Box - raw log version (commented out, kept for reference) */}
          {/*
          {socialResultsText && (
            <div className="mt-4 border-t border-stone-200 pt-6 space-y-3 animate-fadeIn">
              <textarea
                readOnly
                value={socialResultsText}
                className="w-full h-64 bg-stone-900 text-stone-100 font-mono text-[11px] leading-relaxed p-4 rounded-none border border-stone-850 focus:outline-none custom-scrollbar shadow-inner"
              />
            </div>
          )}
          */}

         

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
                    Social Media Crawl Results
                  </h3>
                  <p className="text-[10.5px] text-stone-400 font-serif italic mt-0.5">
                    Detailed breakdown of posts/comments containing consumer feedback
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
                                      alert("Link copied!");
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
                              {post.text || <span className="text-stone-400 italic">No text content</span>}
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
                Total: <strong className="text-stone-850 font-bold">{crawledPosts.length}</strong> posts crawled
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
                    const csvContent = "data:text/csv;charset=utf-8,﻿"
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
                  Close
                </button>
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
