import React, { useState, useRef, useEffect } from "react";

interface DataIngestionTabProps {
  onDiscover: (text: string, ruleText?: string) => Promise<void>;
  onDiscoverSocial?: (platform: string, domain: string, isViral: boolean, keywords?: string[], ruleText?: string) => Promise<void>;
  ruleText: string;
  onOpenRuleModal: () => void;
}

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
  onDiscoverSocial,
  ruleText,
  onOpenRuleModal,
}: DataIngestionTabProps) {
  const [logsText, setLogsText] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Social Explore tab states
  const [platform, setPlatform] = useState<string>("Facebook");
  const [showPlatformDropdown, setShowPlatformDropdown] = useState(false);
  const [customPlatform, setCustomPlatform] = useState("");

  // Domain Category Selector states
  const [selectedDomainId, setSelectedDomainId] = useState<string>("du-lich");
  const [isCustomDomain, setIsCustomDomain] = useState(false);
  const [customDomainLabel, setCustomDomainLabel] = useState("");
  const [showDomainDropdown, setShowDomainDropdown] = useState(false);

  // Active list of keywords/hashtags for search
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
      alert("Vui lòng tải tệp tin lên hoặc dán nội dung cuộc trò chuyện hỗ trợ khách hàng.");
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
    setSocialLoading(true);
    
    // Determine exact platform and domain to send to API
    const finalPlatform = platform === "Other" ? (customPlatform.trim() || "Mạng xã hội khác") : platform;
    const finalDomain = isCustomDomain ? (customDomainLabel.trim() || "Lĩnh vực Tùy chỉnh") : (PRESET_DOMAINS.find(d => d.id === selectedDomainId)?.label || "Du lịch");

    try {
      await onDiscoverSocial(finalPlatform, finalDomain, isViral, keywords, ruleText);
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
                  placeholder={`Dán các cuộc trò chuyện hỗ trợ khách hàng hoặc log dữ liệu thô tại đây... Ví dụ:
"Tôi gặp lỗi khi cố gắng đổi mật khẩu đăng nhập hệ thống."
"Làm cách nào để chuyển nhượng tài khoản đăng ký thanh toán này?"`}
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
                      onClick={() => {
                        setPlatform(p);
                        if (p !== "Other") {
                          setShowPlatformDropdown(false);
                        } else {
                          setShowPlatformDropdown(true);
                        }
                      }}
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
            <div className="pt-4 flex justify-start">
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
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
