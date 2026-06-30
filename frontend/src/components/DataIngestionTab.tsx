import React, { useState, useRef, useEffect } from "react";
import { IngestStats } from "../types";

interface StagedFile {
  file: File;
  sourceType: string;
}

interface DataIngestionTabProps {
  onDiscover: (
    text: string,
    ruleText?: string,
    scope?: "data" | "prd" | "both",
  ) => Promise<void>;
  onIngest: (
    files: { file: File; sourceType: string }[],
    prdFile: File | null,
  ) => Promise<IngestStats>;
  onCrawlSocial?: (
    platform: string,
    domain: string,
    keywords?: string[],
    postsPerKeyword?: number,
  ) => Promise<{ crawlPosts: any[]; newCrawlPosts: any[]; crawlLogs: string[] }>;
  ruleText: string;
  onOpenRuleModal: () => void;
  onProceedToCuration?: () => void;
  onToast?: (message: string, type: "success" | "info" | "error") => void;
  prdLoaded?: boolean;
}

const SOURCE_OPTIONS = ["survey", "social", "text"];

// Selectable social platforms (multi-select checkboxes).
const PLATFORMS = ["Facebook", "Threads", "TikTok"];

const normalizeKeyword = (raw: string): string =>
  raw.replace(/#/g, "").replace(/_/g, " ").replace(/\s+/g, " ").trim();

const normalizeKeywords = (items: string[]): string[] => {
  const seen = new Set<string>();
  const normalized: string[] = [];
  for (const item of items) {
    const clean = normalizeKeyword(item);
    if (clean && !seen.has(clean)) {
      seen.add(clean);
      normalized.push(clean);
    }
  }
  return normalized;
};

// Pre-defined domains and their default search keywords (plain text, used as real crawl queries).
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
  onToast,
  prdLoaded,
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
  const [isPrdDragging, setIsPrdDragging] = useState(false);

  // Discovery scope: which flow(s) the single Run button acts on.
  const [discoveryScope, setDiscoveryScope] = useState<"data" | "prd" | "both">("data");
  // PRD is available if one was just uploaded locally, ingested, or already in backend state.
  const prdAvailable = !!prdFile || !!stats?.prd_loaded || !!prdLoaded;

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
  const [newKeywordInput, setNewKeywordInput] = useState("");
  const keywordInputRef = useRef<HTMLInputElement>(null);
  const keywords = newKeywordInput.split(",").map((k) => k.trim()).filter(Boolean);
  const [isViral, setIsViral] = useState(true);
  const [showCrawlSettings, setShowCrawlSettings] = useState(false);
  // Posts to crawl per keyword (shared across all platforms). No default — user must enter.
  const [postsPerKeyword, setPostsPerKeyword] = useState<string>("");

  // Toggle a platform in the multi-select list.
  const handleTogglePlatform = (p: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p],
    );
  };

  // Active platforms preserving the canonical order.
  const getActivePlatforms = () => PLATFORMS.filter((p) => selectedPlatforms.includes(p));

  // Load persisted crawl sheet from backend JSON store on mount.
  useEffect(() => {
    fetch("/api/crawl/posts")
      .then((res) => res.json())
      .then((data) => {
        const posts = data?.posts || [];
        if (posts.length > 0) {
          setCrawledPosts(posts);
          setSocialResultsText(`${posts.length} posts loaded from saved crawl data.`);
        }
      })
      .catch((err) => console.error("Failed to load saved crawl posts:", err));
  }, []);

  // If PRD becomes unavailable while a PRD-requiring scope is selected, fall back to Data.
  useEffect(() => {
    if (!prdAvailable && discoveryScope !== "data") {
      setDiscoveryScope("data");
    }
  }, [prdAvailable, discoveryScope]);

  // Auto-populate keywords when preset domain changes
  useEffect(() => {
    if (!isCustomDomain) {
      const found = PRESET_DOMAINS.find((d) => d.id === selectedDomainId);
      if (found) {
        setNewKeywordInput(found.tags.join(", "));
      }
    } else {
      setNewKeywordInput("#yêu_cầu_mới, #góp_ý, #hỗ_trợ");
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
      // Uploading a PRD implies wanting it analyzed → nudge scope to include gap analysis.
      setDiscoveryScope("both");
    }
    e.target.value = "";
  };

  const handlePrdDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsPrdDragging(true);
  };
  const handlePrdDragLeave = () => setIsPrdDragging(false);
  const handlePrdDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsPrdDragging(false);
    if (e.dataTransfer.files.length > 0) {
      setPrdFile(e.dataTransfer.files[0]);
      setStats(null);
      setDiscoveryScope("both");
    }
  };

  // Run Intent Discovery from uploaded/pasted sources and/or persisted social crawl data.
  const handleSubmit = async () => {
    const hasFiles = stagedFiles.length > 0 || prdFile;
    const hasCrawledData = crawledPosts.length > 0;
    const hasDataSource = stagedFiles.length > 0 || logsText.trim().length > 0 || hasCrawledData;

    // Validate against the chosen scope.
    if (discoveryScope === "data" && !hasDataSource) {
      onToast?.("Scope 'Data' cần crawl data, paste text, hoặc upload file trước.", "error");
      return;
    }
    if (discoveryScope === "prd" && !prdAvailable) {
      onToast?.("Scope 'PRD' cần upload PRD trước.", "error");
      return;
    }
    if (discoveryScope === "both" && !hasDataSource && !prdAvailable) {
      onToast?.("Add a file/PRD, paste raw text, or crawl social data first.", "error");
      return;
    }

    setLoading(true);
    try {
      // Server-side ingest (FormData) for files + PRD; paste-text goes straight to discover.
      if (hasFiles) {
        const ingestStats = await onIngest(stagedFiles, prdFile);
        setStats(ingestStats);
        // logsText (paste) takes precedence; else "" → backend uses ingested state.
        await onDiscover(logsText.trim(), ruleText, discoveryScope);
      } else {
        await onDiscover(logsText, ruleText, discoveryScope);
      }
    } catch (e: any) {
      console.error(e);
      onToast?.(e.message || "Ingest/discovery failed.", "error");
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
      onToast?.("Please select at least one social platform.", "error");
      return;
    }

    // Require an explicit posts-per-keyword count (no default).
    const perKeyword = parseInt(postsPerKeyword, 10);
    if (!perKeyword || perKeyword < 1) {
      onToast?.("Nhập số posts muốn crawl mỗi keyword (>= 1).", "error");
      return;
    }

    setSocialLoading(true);

    const finalDomain = isCustomDomain ? (customDomainLabel.trim() || "Lĩnh vực Tùy chỉnh") : (PRESET_DOMAINS.find(d => d.id === selectedDomainId)?.label || "Du lịch");
    const normalizedKeywords = normalizeKeywords(keywords);
    const crawlLogs: string[] = [];
    let mergedPosts: any[] = [...crawledPosts];
    let totalNew = 0;

    try {
      for (const platform of activeList) {
        const result = await onCrawlSocial(platform, finalDomain, normalizedKeywords, perKeyword);
        if (result?.crawlPosts?.length) {
          mergedPosts = result.crawlPosts;
        }
        totalNew += result?.newCrawlPosts?.length || 0;
        crawlLogs.push(...(result?.crawlLogs ?? []));
      }

      setCrawledPosts(mergedPosts);
      if (totalNew > 0) {
        setSocialResultsText(`Crawled ${totalNew} new posts (${mergedPosts.length} total in sheet).`);
        setIsSheetModalOpen(true);
      } else {
        setSocialResultsText(mergedPosts.length > 0 ? `${mergedPosts.length} posts in sheet (no new posts this run).` : "");
        const detail = crawlLogs.length > 0 ? crawlLogs.join(" ") : "No posts matched the selected keywords.";
        onToast?.(`Crawl finished but returned 0 new posts. ${detail}`, "info");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSocialLoading(false);
    }
  };

  // Suggested hashtags based on current domain
  const getRecommendedTags = () => {
    if (isCustomDomain) {
      return ["#yêu_cầu_mới", "#góp_ý", "#hỗ_trợ", "#đánh_giá", "#chất_lượng", "#báo_giá", "#tư_vấn", "#khuyến_mãi"];
    }
    const found = PRESET_DOMAINS.find((d) => d.id === selectedDomainId);
    return found ? found.tags : ["#phản_hồi", "#hỗ_trợ"];
  };

  // Toggle a suggested hashtag in/out of the keyword input string
  const handleSelectSuggestedTag = (tag: string) => {
    setNewKeywordInput((prev) => {
      const parts = prev.split(",").map((p) => p.trim()).filter(Boolean);
      if (parts.includes(tag)) {
        return parts.filter((p) => p !== tag).join(", ");
      } else {
        return [...parts, tag].join(", ");
      }
    });
    keywordInputRef.current?.focus();
  };

  // Delete a single crawled post (by sheet index) from backend store + local sheet.
  const handleDeletePost = async (idx: number) => {
    try {
      const res = await fetch("/api/crawl/posts/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ indices: [idx] }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.detail || data.error || "Delete failed.");
      }
      const posts: any[] = data.posts || [];
      setCrawledPosts(posts);
      setSocialResultsText(posts.length > 0 ? `${posts.length} posts in sheet.` : "");
    } catch (err) {
      console.error("Failed to delete crawled post:", err);
      onToast?.("Không xóa được dòng này. Vui lòng thử lại.", "error");
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
      setNewKeywordInput("#yêu_cầu_mới, #góp_ý, #hỗ_trợ");
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
              Two source families feed the same pipeline: a PRD spec (baseline for gap analysis) and Data (documents, raw text, and live social crawl).
            </p>
          </div>

          {/* Hidden file inputs (shared) */}
          <input type="file" ref={fileInputRef} onChange={handleFileChange} accept=".csv,.xlsx,.json,.jsonl,.md,.txt" multiple className="hidden" />
          <input type="file" ref={prdInputRef} onChange={handlePrdChange} accept=".md,.txt" className="hidden" />

          {/* TOP TIER — PRD | Social Crawl, equal weight, the two primary intent sources */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-0">

            {/* GROUP: PRD */}
            <div className="flex flex-col gap-6 pb-6 border-b border-stone-200 lg:pb-0 lg:border-b-0 lg:border-r lg:border-stone-200 lg:pr-8">
              <div className="border-b border-stone-100 pb-3 flex items-start gap-2.5">
                <span className="material-symbols-outlined text-[#ff4d00] text-[20px] mt-0.5">description</span>
                <div>
                  <h4 className="text-[11px] font-mono font-bold uppercase tracking-[0.2em] text-stone-800">
                    PRD · Product Specification
                  </h4>
                  <p className="text-[11px] text-stone-500 font-serif italic mt-0.5">
                    Trích xuất intent tường minh + tự khai phá gap/inferred intents từ spec — baseline cho gap analysis.
                  </p>
                </div>
              </div>

              {/* PRD drag-and-drop zone */}
              <div
                onDragOver={handlePrdDragOver}
                onDragLeave={handlePrdDragLeave}
                onDrop={handlePrdDrop}
                onClick={() => prdInputRef.current?.click()}
                className={`flex flex-col items-center justify-center border-2 border-dashed rounded-none p-8 transition-all cursor-pointer group ${
                  isPrdDragging ? "border-[#ff4d00] bg-[#ff4d00]/10" : "border-[#ff4d00]/30 bg-white hover:border-[#ff4d00] hover:bg-[#ff4d00]/5"
                }`}
              >
                <span className={`material-symbols-outlined text-[40px] mb-2 transition-colors ${isPrdDragging ? "text-[#ff4d00]" : "text-stone-400 group-hover:text-[#ff4d00]"}`}>upload_file</span>
                <p className="text-[13px] uppercase tracking-wider font-bold text-stone-700 text-center">Drag & drop PRD here</p>
                <p className="text-[11px] text-stone-400 font-serif italic mt-1 text-center">or click to upload · .md, .txt</p>
              </div>

              {/* PRD status */}
              <div>
                {prdFile ? (
                  <span className="text-[11px] font-mono text-stone-600 flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[14px] text-emerald-500">check_circle</span>
                    {prdFile.name}
                    <button onClick={() => setPrdFile(null)} className="ml-1 text-[#ff4d00] hover:underline bg-transparent border-0 cursor-pointer uppercase text-[10px] font-bold">clear</button>
                  </span>
                ) : prdAvailable ? (
                  <span className="text-[11px] font-mono text-emerald-600 flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[14px]">check_circle</span>
                    PRD loaded
                  </span>
                ) : (
                  <span className="text-[11px] font-mono text-stone-400 italic">No PRD loaded</span>
                )}
              </div>

              {/* Documents & Raw Text — supplementary, nested below PRD, least important */}
              <div className="border-t border-stone-100 pt-5 flex flex-col gap-3">
                <div>
                  <h5 className="text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-stone-500 flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[14px] text-stone-400">article</span>
                    Documents & Raw Text
                  </h5>
                  <p className="text-[10.5px] text-stone-400 font-serif italic mt-0.5">Tài liệu bổ sung (survey, transcript...) — không bắt buộc</p>
                </div>

                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`flex items-center justify-center gap-2 border-2 border-dashed rounded-none px-4 py-4 transition-all cursor-pointer group ${
                    isDragging ? "border-[#ff4d00] bg-[#ff4d00]/5" : "border-stone-200 bg-white hover:border-[#ff4d00] hover:bg-stone-50"
                  }`}
                >
                  <span className={`material-symbols-outlined text-[20px] transition-colors ${isDragging ? "text-[#ff4d00]" : "text-stone-400 group-hover:text-[#ff4d00]"}`}>cloud_upload</span>
                  <p className="text-[11px] uppercase tracking-wider font-bold text-stone-600">+ Add files (.csv, .xlsx, .json, .md, .txt)</p>
                </div>

                {stagedFiles.length > 0 && (
                  <div className="border border-stone-200">
                    {stagedFiles.map((sf, idx) => (
                      <div key={idx} className="flex items-center justify-between px-3 py-1.5 border-b border-stone-100 last:border-b-0">
                        <span className="text-[11px] font-mono text-stone-700 truncate flex-1">{sf.file.name}</span>
                        <div className="flex items-center gap-2 shrink-0">
                          <select
                            value={sf.sourceType}
                            onChange={(e) => setRowType(idx, e.target.value)}
                            className="text-[10px] font-mono uppercase tracking-wider border border-stone-300 bg-white px-1.5 py-0.5 outline-none focus:border-[#ff4d00] cursor-pointer"
                          >
                            {SOURCE_OPTIONS.map((opt) => (
                              <option key={opt} value={opt}>{opt}</option>
                            ))}
                          </select>
                          <button onClick={() => removeRow(idx)} className="text-stone-400 hover:text-[#ff4d00] bg-transparent border-0 cursor-pointer" title="Remove">
                            <span className="material-symbols-outlined text-[16px]">close</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {stats && (
                  <div className="border border-stone-200 bg-white px-3 py-2">
                    <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10.5px] font-mono text-stone-700">
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

                <div className="flex flex-col gap-2">
                  <label className="text-[10px] font-bold text-stone-400 uppercase tracking-[0.2em]">Or paste raw social text (post + comment)</label>
                  <textarea
                    value={logsText}
                    onChange={(e) => setLogsText(e.target.value)}
                    className="w-full h-24 bg-white border border-stone-200 rounded-none p-3 text-[12px] font-mono focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all placeholder:text-stone-400 text-stone-800"
                    placeholder={`Paste social posts + comments here...`}
                  />
                </div>
              </div>
            </div>

            {/* GROUP: Social Crawl */}
            <div className="flex flex-col gap-6 pt-6 lg:pt-0 lg:pl-8">
              <div className="border-b border-stone-100 pb-3">
                <h4 className="text-[11px] font-mono font-bold uppercase tracking-[0.2em] text-stone-700 flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">explore</span>
                  Social Crawl
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

              {/* Crawl Settings — collapsible: posts/keyword, hashtags & search keywords, engagement toggle */}
              <div className="flex flex-col gap-2">
                <button
                  type="button"
                  onClick={() => setShowCrawlSettings(!showCrawlSettings)}
                  className="w-full bg-white border border-stone-200 hover:border-stone-300 px-4 py-3 flex items-center justify-between text-left cursor-pointer transition-all"
                >
                  <div className="flex items-center gap-3">
                    <span className="material-symbols-outlined text-[18px] text-[#ff4d00]">tune</span>
                    <div>
                      <span className="text-[11px] uppercase font-bold tracking-wider text-stone-800">Crawl Settings</span>
                      <p className="text-[9.5px] text-stone-400 font-serif italic mt-0.5">
                        {postsPerKeyword || "?"} posts/keyword · {keywords.length} keywords · viral {isViral ? "on" : "off"}
                      </p>
                    </div>
                  </div>
                  <span className="material-symbols-outlined text-[18px] text-stone-400">
                    {showCrawlSettings ? "keyboard_arrow_up" : "keyboard_arrow_down"}
                  </span>
                </button>

                {showCrawlSettings && (
                  <div className="flex flex-col gap-6 mt-2 animate-fadeIn">
                    {/* Posts per keyword (shared across all platforms) */}
                    <div className="flex flex-col gap-2">
                      <label className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em] flex justify-between items-center">
                        <span>Posts mỗi keyword (mọi nền tảng)</span>
                        <span className="font-mono text-[9px] text-stone-400 normal-case tracking-normal">áp dụng cho từng keyword</span>
                      </label>
                      <input
                        type="number"
                        min={1}
                        max={50}
                        value={postsPerKeyword}
                        onChange={(e) => setPostsPerKeyword(e.target.value)}
                        placeholder="Nhập số posts muốn crawl mỗi keyword (vd. 2)"
                        className="w-full bg-white border border-stone-200 px-4 py-3 text-[11px] font-mono focus:border-[#ff4d00] focus:ring-1 focus:ring-[#ff4d00] outline-none"
                      />
                    </div>

                    {/* Keywords manager */}
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
                          Reset to defaults
                        </button>
                      </div>

                      {/* Keyword input — comma-separated free text */}
                      <form onSubmit={(e: React.FormEvent) => e.preventDefault()} className="flex gap-1.5 mt-2">
                        <input
                          ref={keywordInputRef}
                          type="text"
                          value={newKeywordInput}
                          onChange={(e) => setNewKeywordInput(e.target.value)}
                          placeholder="Nhập keywords hoặc #hashtags, cách nhau bằng dấu phẩy"
                          className="flex-grow bg-stone-50 border border-stone-200 px-3 py-1.5 text-[11px] font-mono focus:border-[#ff4d00] outline-none"
                        />
                        <button
                          type="button"
                          onClick={() => setNewKeywordInput("")}
                          className="px-3 bg-stone-100 hover:bg-stone-200 text-stone-600 font-mono text-[11px] font-bold uppercase transition-all border border-stone-200 cursor-pointer"
                        >
                          Clear
                        </button>
                      </form>

                      {/* Suggested hashtags — click to select/deselect */}
                      <div className="mt-1 pb-0.5">
                        <span className="text-[9px] font-mono text-stone-400 font-bold uppercase tracking-wider block mb-1.5">
                          Suggested (click to select/deselect):
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {getRecommendedTags().map((tag) => {
                            const isSelected = keywords.includes(tag);
                            return (
                              <button
                                key={tag}
                                type="button"
                                onClick={() => handleSelectSuggestedTag(tag)}
                                className={`px-2 py-0.5 text-[9.5px] font-mono transition-all border cursor-pointer ${
                                  isSelected
                                    ? "bg-stone-900 text-white border-stone-900"
                                    : "bg-stone-50 hover:bg-stone-100 text-stone-600 border-stone-200 hover:border-stone-300"
                                }`}
                                title={isSelected ? "Click to deselect" : "Click to select"}
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
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Shared action footer: both run buttons */}
          <div className="border-t border-stone-100 pt-6 flex flex-col sm:flex-row gap-4">
            {/* Discovery group: scope toggle + Run button (single button, scope-aware) */}
            <div className="flex-1 flex flex-col gap-2">
              {/* Scope toggle — picks which flow(s) discovery acts on */}
              <div className="flex items-center gap-2">
                <span className="text-[9px] font-bold text-stone-400 uppercase tracking-[0.2em] shrink-0">Scope</span>
                <div className="flex border border-stone-200 rounded-none overflow-hidden">
                  {([
                    { id: "data", label: "Data", enabled: true },
                    { id: "prd", label: "PRD", enabled: prdAvailable },
                    { id: "both", label: "Data + PRD", enabled: prdAvailable },
                  ] as const).map((opt) => {
                    const active = discoveryScope === opt.id;
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        disabled={!opt.enabled}
                        onClick={() => setDiscoveryScope(opt.id)}
                        title={!opt.enabled ? "Upload a PRD to enable this scope" : `Discover from ${opt.label}`}
                        className={`px-3 py-1.5 text-[9px] font-mono font-bold uppercase tracking-wider border-r border-stone-200 last:border-r-0 transition-colors ${
                          active
                            ? "bg-[#ff4d00] text-white"
                            : opt.enabled
                              ? "bg-white text-stone-600 hover:bg-stone-50 cursor-pointer"
                              : "bg-stone-50 text-stone-300 cursor-not-allowed"
                        }`}
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Run Intent Discovery (scope-aware) */}
              <button
                onClick={handleSubmit}
                disabled={loading}
                className="w-full flex items-center justify-center gap-3 px-8 py-3.5 bg-[#ff4d00] text-white rounded-none font-bold text-[10px] uppercase tracking-[0.2em] hover:opacity-95 active:scale-95 transition-all disabled:opacity-50 cursor-pointer border-0 shadow-sm"
              >
                {loading ? (
                  <>
                    <span className="material-symbols-outlined animate-spin text-[16px]">sync</span>
                    Ingesting & Discovering Intents...
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[16px]">search_check</span>
                    Run Intent Discovery · {discoveryScope === "data" ? "Data" : discoveryScope === "prd" ? "PRD" : "Data + PRD"}
                  </>
                )}
              </button>
            </div>

            {/* Crawl group: [Crawl Social Data] [View Results] on same row + success message below */}
            <div className="flex-1 flex flex-col gap-2">
              <div className="flex gap-2">
                <button
                  onClick={handleCrawlSubmit}
                  disabled={socialLoading}
                  className="flex-1 flex items-center justify-center gap-3 px-8 py-3.5 bg-stone-900 text-white hover:bg-stone-850 rounded-none font-bold text-[10px] uppercase tracking-[0.2em] active:scale-95 transition-all disabled:opacity-50 cursor-pointer border-0 shadow-sm"
                >
                  {socialLoading ? (
                    <>
                      <span className="material-symbols-outlined animate-spin text-[16px]">sync</span>
                      Crawling...
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-[16px]">travel_explore</span>
                      Crawl Social Data
                    </>
                  )}
                </button>

                {crawledPosts.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setIsSheetModalOpen(true)}
                    className="flex items-center gap-1.5 px-4 py-3.5 bg-stone-100 hover:bg-stone-200 text-stone-700 font-mono text-[10px] uppercase font-bold tracking-wider rounded-none border border-stone-200 cursor-pointer transition-colors shrink-0"
                  >
                    <span className="material-symbols-outlined text-[14px]">table_chart</span>
                    View Results
                  </button>
                )}
              </div>

              {socialResultsText && (
                <p className="flex items-center gap-1.5 text-[10px] font-mono text-stone-500 animate-fadeIn">
                  <span className="material-symbols-outlined text-[13px] text-emerald-500">check_circle</span>
                  {socialResultsText}
                </p>
              )}
            </div>
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
                <div className="border border-stone-200 bg-white overflow-x-auto shadow-xs">
                  <table className="w-full text-left border-collapse text-[11px] leading-normal">
                    <thead>
                      <tr className="bg-stone-100/80 border-b border-stone-200 text-[10px] font-mono uppercase font-bold text-stone-600">
                        <th className="px-4 py-3 border-r border-stone-200">Platform</th>
                        <th className="px-4 py-3 border-r border-stone-200">Source URL</th>
                        <th className="px-4 py-3 border-r border-stone-200">Posting Date</th>
                        <th className="px-4 py-3 border-r border-stone-200 text-center">Engagement</th>
                        <th className="px-4 py-3 border-r border-stone-200">Discussion Content</th>
                        <th className="px-4 py-3 text-center sticky right-0 bg-stone-100 z-20 border-l border-stone-200">Action</th>
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
                                      onToast?.("Link copied!", "success");
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
                            <td className="px-4 py-3 text-stone-700 font-sans max-w-[320px] truncate border-r border-stone-200" title={post.text}>
                              {post.text || <span className="text-stone-400 italic">No text content</span>}
                            </td>

                            {/* Delete action */}
                            <td className="px-4 py-3 text-center whitespace-nowrap sticky right-0 bg-white z-10 border-l border-stone-200">
                              <button
                                type="button"
                                onClick={() => {
                                  if (window.confirm("Xóa kết quả này khỏi sheet?")) handleDeletePost(idx);
                                }}
                                className="text-stone-400 hover:text-rose-600 hover:bg-rose-50 p-1 rounded-sm transition-colors cursor-pointer border-0 bg-transparent"
                                title="Xóa dòng này"
                              >
                                <span className="material-symbols-outlined text-[16px]">close</span>
                              </button>
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
                  onClick={async () => {
                    try {
                      const res = await fetch("/api/crawl/posts");
                      const data = await res.json();
                      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
                      const url = URL.createObjectURL(blob);
                      const link = document.createElement("a");
                      link.href = url;
                      link.download = `crawl_posts_${Date.now()}.json`;
                      document.body.appendChild(link);
                      link.click();
                      document.body.removeChild(link);
                      URL.revokeObjectURL(url);
                    } catch (err) {
                      console.error("Download failed:", err);
                      onToast?.("Failed to download crawl data.", "error");
                    }
                  }}
                  className="px-4 py-2 bg-stone-100 hover:bg-stone-200 border border-stone-250 text-stone-700 text-[10px] uppercase font-bold tracking-widest cursor-pointer transition-colors"
                >
                  Download JSON
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
