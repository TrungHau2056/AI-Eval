import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI, Type } from "@google/genai";
import dotenv from "dotenv";
import { Intent, Persona, TestCase } from "./src/types";

dotenv.config();

const app = express();
const PORT = 3000;

app.use(express.json());

interface AppState {
  apiKey: string;
  domain: string;
  aiModel: string;
  intents: Intent[];
  personas: Persona[];
  testCases: TestCase[];
}

// In-memory state store mimicking the screenshots' data
let appState: AppState = {
  apiKey: "••••••••••••••••",
  domain: "qa-env-01.local",
  aiModel: "GPT-4o Enterprise",
  intents: [
    {
      id: "int-1",
      name: "Check Billing History",
      phase: "RETENTION" as const,
      utterance: "I want to see how much I paid last June.",
      triggerMoment: "Post-Login Dashboard",
      selected: false,
    },
    {
      id: "int-2",
      name: "Update Profile Address",
      phase: "ACCOUNT MGMT" as const,
      utterance: "Change my shipping address to 123 Maple St.",
      triggerMoment: "Settings View",
      selected: true,
    },
    {
      id: "int-3",
      name: "Password Reset Flow",
      phase: "SECURITY" as const,
      utterance: "I forgot my password, send me a code.",
      triggerMoment: "Login Fail State",
      selected: false,
    },
    {
      id: "int-4",
      name: "Cancel Subscription",
      phase: "CHURN" as const,
      utterance: "Stop my monthly billing immediately.",
      triggerMoment: "Subscription Panel",
      selected: false,
    },
    {
      id: "int-5",
      name: "Bulk Data Export",
      phase: "USAGE" as const,
      utterance: "Download all records from last quarter as CSV.",
      triggerMoment: "Reporting Module",
      selected: true,
    },
    {
      id: "int-6",
      name: "Live Support Chat",
      phase: "SUPPORT" as const,
      utterance: "I need to talk to a human agent.",
      triggerMoment: "Help Widget",
      selected: false,
    },
  ],
  personas: [
    {
      id: "p-1",
      type: "happy" as const,
      name: "Standard User",
      trigger: "Login Successful",
      utterance: "I want to view my recent billing history and download the PDF for June.",
      frequency: 85,
      pain: "Slow PDF rendering",
      reject: "Incorrect credentials",
      intentId: "int-1",
    },
    {
      id: "p-2",
      type: "edge" as const,
      name: "Session Leaker",
      trigger: "Expired Token",
      utterance: "Attempting to refresh the dashboard after being inactive for 24 hours while on a VPN.",
      frequency: 12,
      pain: "Redundant re-logins",
      reject: "401 Unauthorized",
      intentId: "int-1",
    },
    {
      id: "p-int-2-happy",
      type: "happy" as const,
      name: "Residential Relocator",
      trigger: "Address fields filled",
      utterance: "Change my shipping address to 123 Maple St and set it to default.",
      frequency: 90,
      pain: "Slow address completion suggestion",
      reject: "Invalid zip code format",
      intentId: "int-2",
    },
    {
      id: "p-int-2-edge",
      type: "edge" as const,
      name: "Overseas Expat",
      trigger: "Special characters in address field",
      utterance: "Attempting to enter an international APO/FPO military address with custom state codes.",
      frequency: 15,
      pain: "Address length limitations",
      reject: "Incorrect state province validation",
      intentId: "int-2",
    },
    {
      id: "p-int-5-happy",
      type: "happy" as const,
      name: "Financial Auditor",
      trigger: "Export options selected",
      utterance: "Download all records from last quarter as CSV for compliance filing.",
      frequency: 80,
      pain: "Filename auto-truncation issues",
      reject: "Insufficient permissions for company export",
      intentId: "int-5",
    },
    {
      id: "p-int-5-edge",
      type: "edge" as const,
      name: "Automated Data Scraper",
      trigger: "Recursive payload download trigger",
      utterance: "Requesting a 10 Gigabyte compressed schema database dump repeatedly over a high-concurrency connection.",
      frequency: 8,
      pain: "Export timeout errors",
      reject: "Rate limit threshold breached",
      intentId: "int-5",
    },
  ],
  testCases: [
    {
      id: "TC-XEDIEN-1.1",
      intentName: "Update Profile Address",
      personaName: "Persona A (Standard User)",
      simulatedPrompt: "Change my shipping address to 123 Main St",
      expectedOutcome: "Success message & database updated",
      selected: true,
      status: "pending" as const,
      goal: "Validate profile address modification logic.",
    },
    {
      id: "TC-XEDIEN-1.2",
      intentName: "Password Reset Flow",
      personaName: "Persona B (Session Leaker)",
      simulatedPrompt: "I forgot my password, send me a reset link",
      expectedOutcome: "Security email dispatched to user",
      selected: true,
      status: "pending" as const,
      goal: "Assert user-initiated password authentication reset rules.",
    },
    {
      id: "TC-XEDIEN-1.3",
      intentName: "Bulk Data Export",
      personaName: "Persona A (Standard User)",
      simulatedPrompt: "Download all records from last month in JSON",
      expectedOutcome: "File generation starts & progress bar",
      selected: true,
      status: "pending" as const,
      goal: "Verify secure records bulk download capability.",
    },
  ],
};

// Help-method to get Gemini AI Client
function getGeminiClient(): GoogleGenAI | null {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey || apiKey === "MY_GEMINI_API_KEY") {
    console.log("No valid GEMINI_API_KEY environment variable found. Falling back to local/static responses.");
    return null;
  }
  return new GoogleGenAI({
    apiKey: apiKey,
    httpOptions: {
      headers: {
        "User-Agent": "aistudio-build",
      },
    },
  });
}

// 1. Get Application State
app.get("/api/state", (req, res) => {
  res.json(appState);
});

// 2. Put / Update Part of Application State
app.post("/api/state", (req, res) => {
  appState = { ...appState, ...req.body };
  res.json({ success: true, state: appState });
});

// 2.5. Compile rule using user's natural prompt or uploaded MD context
app.post("/api/compile-rule", async (req, res) => {
  const { userPrompt, currentRule } = req.body;
  if (!userPrompt || userPrompt.trim().length === 0) {
    return res.status(400).json({ error: "Please provide a prompt to adjust the rules." });
  }

  const ai = getGeminiClient();
  if (!ai) {
    // Elegant fallback simulation compiling prompt into custom rule
    const formattedPrompt = userPrompt.trim();
    const mockCompiled = `Custom Rule V2: Optimized directive parameters focusing on ${formattedPrompt}. This overrides default classification priority, keeping standard categories. Extracted in real-time.`;
    return res.json({ success: true, rule: mockCompiled, fallback: true });
  }

  try {
    const prompt = `Convert the following user request or directive into an explicit, modular system directive that specifies how metadata and user intents should be extracted from customer logs.

User adjustment request: "${userPrompt}"
Current active rule: "${currentRule || "None (Default)"}"

Generate a concise, highly professional 1-2 sentence instruction. Output ONLY the resulting instruction text. No quotes around it, no wrapper.`;
    
    const response = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents: prompt,
    });
    
    const ruleResult = response.text?.trim() || currentRule;
    res.json({ success: true, rule: ruleResult, fallback: false });
  } catch (err: any) {
    console.error("Failed to compile user rule prompt with Gemini:", err);
    res.status(500).json({ error: "Gemini failed to compile. Reverting." });
  }
});

// 3. Reset application state to default
app.post("/api/state/reset", (req, res) => {
  appState.intents = [
    {
      id: "int-1",
      name: "Check Billing History",
      phase: "RETENTION",
      utterance: "I want to see how much I paid last June.",
      triggerMoment: "Post-Login Dashboard",
      selected: false,
    },
    {
      id: "int-2",
      name: "Update Profile Address",
      phase: "ACCOUNT MGMT",
      utterance: "Change my shipping address to 123 Maple St.",
      triggerMoment: "Settings View",
      selected: true,
    },
    {
      id: "int-3",
      name: "Password Reset Flow",
      phase: "SECURITY",
      utterance: "I forgot my password, send me a code.",
      triggerMoment: "Login Fail State",
      selected: false,
    },
    {
      id: "int-4",
      name: "Cancel Subscription",
      phase: "CHURN",
      utterance: "Stop my monthly billing immediately.",
      triggerMoment: "Subscription Panel",
      selected: false,
    },
    {
      id: "int-5",
      name: "Bulk Data Export",
      phase: "USAGE",
      utterance: "Download all records from last quarter as CSV.",
      triggerMoment: "Reporting Module",
      selected: true,
    },
    {
      id: "int-6",
      name: "Live Support Chat",
      phase: "SUPPORT",
      utterance: "I need to talk to a human agent.",
      triggerMoment: "Help Widget",
      selected: false,
    },
  ];
  appState.personas = [
    {
      id: "p-1",
      type: "happy",
      name: "Standard User",
      trigger: "Login Successful",
      utterance: "I want to view my recent billing history and download the PDF for June.",
      frequency: 85,
      pain: "Slow PDF rendering",
      reject: "Incorrect credentials",
      intentId: "int-1",
    },
    {
      id: "p-2",
      type: "edge",
      name: "Session Leaker",
      trigger: "Expired Token",
      utterance: "Attempting to refresh the dashboard after being inactive for 24 hours while on a VPN.",
      frequency: 12,
      pain: "Redundant re-logins",
      reject: "401 Unauthorized",
      intentId: "int-1",
    },
    {
      id: "p-int-2-happy",
      type: "happy",
      name: "Residential Relocator",
      trigger: "Address fields filled",
      utterance: "Change my shipping address to 123 Maple St and set it to default.",
      frequency: 90,
      pain: "Slow address completion suggestion",
      reject: "Invalid zip code format",
      intentId: "int-2",
    },
    {
      id: "p-int-2-edge",
      type: "edge",
      name: "Overseas Expat",
      trigger: "Special characters in address field",
      utterance: "Attempting to enter an international APO/FPO military address with custom state codes.",
      frequency: 15,
      pain: "Address length limitations",
      reject: "Incorrect state province validation",
      intentId: "int-2",
    },
    {
      id: "p-[#int-5]-happy",
      type: "happy",
      name: "Financial Auditor",
      trigger: "Export options selected",
      utterance: "Download all records from last quarter as CSV for compliance filing.",
      frequency: 80,
      pain: "Filename auto-truncation issues",
      reject: "Insufficient permissions for company export",
      intentId: "int-5",
    },
    {
      id: "p-[#int-5]-edge",
      type: "edge",
      name: "Automated Data Scraper",
      trigger: "Recursive payload download trigger",
      utterance: "Requesting a 10 Gigabyte compressed schema database dump repeatedly over a high-concurrency connection.",
      frequency: 8,
      pain: "Export timeout errors",
      reject: "Rate limit threshold breached",
      intentId: "int-5",
    },
  ];
  appState.testCases = [
    {
      id: "TC-XEDIEN-1.1",
      intentName: "Update Profile Address",
      personaName: "Persona A (Standard User)",
      simulatedPrompt: "Change my shipping address to 123 Main St",
      expectedOutcome: "Success message & database updated",
      selected: true,
      status: "pending",
    },
    {
      id: "TC-XEDIEN-1.2",
      intentName: "Password Reset Flow",
      personaName: "Persona B (Session Leaker)",
      simulatedPrompt: "I forgot my password, send me a reset link",
      expectedOutcome: "Security email dispatched to user",
      selected: true,
      status: "pending",
    },
    {
      id: "TC-XEDIEN-1.3",
      intentName: "Bulk Data Export",
      personaName: "Persona A (Standard User)",
      simulatedPrompt: "Download all records from last month in JSON",
      expectedOutcome: "File generation starts & progress bar",
      selected: true,
      status: "pending",
    },
  ];
  res.json({ success: true, state: appState });
});

// 4. Discover Intents from pasted text Logs (Gemini API with schemas)
app.post("/api/discover", async (req, res) => {
  const { logsText, ruleText } = req.body;
  if (!logsText || logsText.trim().length === 0) {
    return res.status(400).json({ error: "Please enter some logs text or upload a file first." });
  }

  const ai = getGeminiClient();
  if (!ai) {
    // Return high quality dummy intents if offline / no API key configured
    // Let's customize dummy intents based on search keywords or just yield excellent responsive ones
    const textLower = logsText.toLowerCase();
    let computedIntents = [];

    if (textLower.includes("payment") || textLower.includes("card") || textLower.includes("bill")) {
      computedIntents = [
        {
          id: "disc-1",
          name: "Verify Credit Card Payment",
          phase: "USAGE" as const,
          utterance: "Why did my credit card payment fail yesterday?",
          triggerMoment: "Checkout Page",
          selected: true,
        },
        {
          id: "disc-2",
          name: "Download Invoice Copy",
          phase: "RETENTION" as const,
          utterance: "I need to get a copy of invoice #3492 for tax filings.",
          triggerMoment: "Billing Panel",
          selected: true,
        },
      ];
    } else {
      computedIntents = [
        {
          id: "disc-1",
          name: "Add Collaboration Member",
          phase: "ACCOUNT MGMT" as const,
          utterance: "Can you send a project workspace invite to my colleague?",
          triggerMoment: "Team Workspace Page",
          selected: true,
        },
        {
          id: "disc-2",
          name: "Change Authentication Token",
          phase: "SECURITY" as const,
          utterance: "Generate a new access token for API webhook calls.",
          triggerMoment: "Developer Options Panel",
          selected: true,
        },
        {
          id: "disc-3",
          name: "Optimize Cloud Resource",
          phase: "USAGE" as const,
          utterance: "Review recommendations to reduce container memory leaks.",
          triggerMoment: "Cluster Setup Console",
          selected: true,
        },
      ];
    }

    // append to our current list
    appState.intents = [...computedIntents, ...appState.intents];
    return res.json({ intents: computedIntents, fallback: true });
  }

  try {
    const prompt = `Analyze the following customer support inquiries, chat transcripts, or log entries. Discover and extract distinct test case intents that represent target product actions.
Extract 2 to 4 high-quality unique intents.

Logs to analyze:
"${logsText}"`;

    const response = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents: prompt,
      config: {
        systemInstruction: `You are an enterprise AI quality assurance (QA) platform parser. Classify each intent with one of these exact phases: RETENTION, ACCOUNT MGMT, SECURITY, CHURN, USAGE, or SUPPORT. UTTERANCE must represent a typical user's statement for this intent. TRIGGER MOMENT is the exact location or visual state in the system.${ruleText ? `\n\nAdhere strictly to these extra user-specific generation rules:\n${ruleText}` : ""}`,
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              name: {
                type: Type.STRING,
                description: "Clean, action-oriented intent name, e.g. 'Reset Expired Token'",
              },
              phase: {
                type: Type.STRING,
                description: "Must be exactly RETENTION, ACCOUNT MGMT, SECURITY, CHURN, USAGE, or SUPPORT",
              },
              utterance: {
                type: Type.STRING,
                description: "A natural user quotation expressing this intent.",
              },
              triggerMoment: {
                type: Type.STRING,
                description: "The dashboard view, widget, page, or context where this executes.",
              },
            },
            required: ["name", "phase", "utterance", "triggerMoment"],
          },
        },
      },
    });

    const resultText = response.text || "[]";
    const parsedIntents = JSON.parse(resultText);

    const mappedIntents = parsedIntents.map((item: any, index: number) => ({
      id: `discovered-${Date.now()}-${index}`,
      name: item.name || "Custom Discovered Intent",
      phase: ["RETENTION", "ACCOUNT MGMT", "SECURITY", "CHURN", "USAGE", "SUPPORT"].includes(item.phase)
        ? item.phase
        : "SUPPORT",
      utterance: item.utterance || "Perform system action.",
      triggerMoment: item.triggerMoment || "General View",
      selected: true,
    }));

    appState.intents = [...mappedIntents, ...appState.intents];
    res.json({ intents: mappedIntents, fallback: false });
  } catch (error: any) {
    console.error("Gemini Intent Discovery failed:", error);
    res.status(500).json({ error: "Gemini API failed to parse contents. Falling back to local pattern." });
  }
});

// 4.5 Discover Intents from Social Media (Facebook/Threads/Custom) with specialized Domains, Virality, and custom Keywords
app.post("/api/discover-social", async (req, res) => {
  const { platform, domain, isViral, ruleText, keywords } = req.body;
  
  const selectedPlatform = platform || "Facebook";
  const selectedDomain = domain || "Du lịch";
  const isViralFlag = !!isViral;
  const kwList = Array.isArray(keywords) ? keywords : [];

  const ai = getGeminiClient();
  if (!ai) {
    // Generate fallback mock intents based on inputs
    let computedIntents: any[] = [];
    const seed = Date.now();
    const kwString = kwList.length > 0 ? ` (${kwList.join(", ")})` : "";

    if (selectedDomain.toLowerCase().includes("du lịch")) {
      computedIntents = [
        {
          id: `social-disc-${seed}-1`,
          name: `${selectedPlatform}: Phản hồi bồi thường hủy chuyến bay`,
          phase: "SUPPORT",
          utterance: `Hãng hàng không vừa hủy chuyến bay đi Đà Lạt sát giờ bay mà không hề có hỗ trợ thỏa đáng gì cả! Làm sao để đòi bồi thường đây mọi người ơi? #${selectedDomain} #${isViralFlag ? "viral_trend" : "feedback"}${kwList.length > 0 ? ` # ${kwList[0]}` : ""}`,
          triggerMoment: `${selectedPlatform} Feed / Post`,
          selected: true,
        },
        {
          id: `social-disc-${seed}-2`,
          name: `${selectedPlatform}: Săn voucher phòng khách sạn 5 sao`,
          phase: "RETENTION",
          utterance: `Mọi người ơi, xin review khách sạn 5 sao ở Phú Quốc có deal hời cho hè này không? Cho mình xin link đặt phòng trực tiếp nha. ${kwList.length > 1 ? `Cần dịch vụ liên quan tới ${kwList[1]}` : ""}`,
          triggerMoment: `${selectedPlatform} Group Discussion`,
          selected: true,
        },
        {
          id: `social-disc-${seed}-3`,
          name: `${selectedPlatform}: Khiếu nại hành lý ký gửi thất lạc`,
          phase: "CHURN",
          utterance: `Hành lý ký gửi của mình bị thất lạc 3 ngày rồi vẫn chưa thấy hãng bay tìm ra. Dịch vụ hỗ trợ trực tuyến quá chậm trễ! ${kwList.length > 2 ? `Gặp sự cố với ${kwList[2]}` : ""}`,
          triggerMoment: `${selectedPlatform} Direct Message`,
          selected: true,
        }
      ];
    } else if (selectedDomain.toLowerCase().includes("giải trí")) {
      computedIntents = [
        {
          id: `social-disc-${seed}-1`,
          name: `${selectedPlatform}: Lỗi thanh toán trực tuyến vé concert`,
          phase: "SUPPORT",
          utterance: `Đang săn vé concert trực tuyến mà hệ thống báo lỗi, tài khoản ngân hàng trừ tiền rồi nhưng không xuất vé! Cứu với! #${selectedDomain} #${isViralFlag ? "HOT_TRENDING" : "bug"}${kwList.length > 0 ? ` # ${kwList[0]}` : ""}`,
          triggerMoment: `${selectedPlatform} Checkout Error Pop-up`,
          selected: true,
        },
        {
          id: `social-disc-${seed}-2`,
          name: `${selectedPlatform}: Đăng ký nâng cấp tài khoản VIP`,
          phase: "USAGE",
          utterance: `Gói VIP xem phim trực tuyến của mình vừa hết hạn, bên hệ thống có chương trình khuyến mãi gia hạn 1 năm giảm 50% không nhỉ? ${kwList.length > 1 ? `Yêu cầu liên quan đến ${kwList[1]}` : ""}`,
          triggerMoment: `${selectedPlatform} Premium Feed`,
          selected: true,
        },
        {
          id: `social-disc-${seed}-3`,
          name: `${selectedPlatform}: Khiếu nại đánh gậy bản quyền vô lý`,
          phase: "SECURITY",
          utterance: `Video sáng tạo của mình bị đánh bản quyền nhạc vô lý quá mặc dù đã mua license đầy đủ. Có cách nào liên hệ kháng nghị khẩn cấp không? ${kwList.length > 2 ? `Cần kiểm tra ${kwList[2]}` : ""}`,
          triggerMoment: `${selectedPlatform} Creator Dashboard`,
          selected: true,
        }
      ];
    } else { // "Thể thao" hoặc Custom
      computedIntents = [
        {
          id: `social-disc-${seed}-1`,
          name: `${selectedPlatform}: Chuyển nhượng đổi thông tin BIB chạy`,
          phase: "ACCOUNT MGMT",
          utterance: `Mình muốn chuyển nhượng thông tin đăng ký giải chạy hoặc nâng cấp cự ly thi đấu sắp tới thì gửi yêu cầu ở đâu? #${selectedDomain} #${isViralFlag ? "trend_chaybo" : "support"}${kwList.length > 0 ? ` # ${kwList[0]}` : ""}`,
          triggerMoment: `${selectedPlatform} Registration Page`,
          selected: true,
        },
        {
          id: `social-disc-${seed}-2`,
          name: `${selectedPlatform}: Đóng góp phản ánh gián đoạn truyền hình trực tiếp`,
          phase: "SUPPORT",
          utterance: `Kênh truyền hình trực tiếp trận đấu bị xoay vòng tròn tải liên tục, chất lượng giật lag mờ căm cực kỳ khó chịu! ${kwList.length > 1 ? `Ảnh hưởng trải nghiệm ${kwList[1]}` : ""}`,
          triggerMoment: `${selectedPlatform} Live Stream player`,
          selected: true,
        },
        {
          id: `social-disc-${seed}-3`,
          name: `${selectedPlatform}: Phản ánh bảo mật thông tin hội viên`,
          phase: "SECURITY",
          utterance: `Có ai bị lộ thông tin cá nhân hoặc nhận cuộc gọi tư vấn rác liên tục sau khi đăng ký dịch vụ này không? #${selectedDomain} ${kwList.length > 2 ? `Gửi yêu cầu tới ${kwList[2]}` : ""}`,
          triggerMoment: `${selectedPlatform} Security Post`,
          selected: true,
        }
      ];
    }

    if (isViralFlag) {
      computedIntents.forEach(intent => {
        intent.utterance = `🔥 [ĐANG XU HƯỚNG VIRAL] ${intent.utterance} (Bài viết nhận được >15k lượt tương tác, 2k bình luận và hàng trăm chia sẻ!)`;
      });
    }

    appState.intents = [...computedIntents, ...appState.intents];
    return res.json({ intents: computedIntents, fallback: true });
  }

  try {
    const viralPrompt = isViralFlag ? "The content has high public engagement, emotional complaints, and is extremely VIRAL / trending with many comments and shares." : "The content is a standard social user discussion.";
    const keywordsPrompt = kwList.length > 0 ? `The generated social media posts/comments MUST strongly relate to or include these user-configured keywords/hashtags: ${kwList.map((k: string) => `"${k}"`).join(", ")}.` : "";
    const prompt = `Analyze social media trends and customer intentions for the platform: "${selectedPlatform}" in the domain category: "${selectedDomain}".
    ${viralPrompt}
    ${keywordsPrompt}
    
    Generate exactly 3 distinct, highly realistic user-expressed intents, posts, or complaints that customers would post on ${selectedPlatform} regarding ${selectedDomain} products/services.
    
    The user chosen platform "${selectedPlatform}" and domain "${selectedDomain}" are targeted at Vietnamese social media users. You MUST generate the results in natural Vietnamese. Keep the tone organic, realistic, emotional, and highly reflective of how Vietnamese users actually speak/write on social media (e.g. using 'mọi người ơi', 'cứu với', 'thất vọng', 'hãng bay', 'săn vé', và các hashtag liên quan).
    
    Provide 3 unique intents.`;

    const response = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents: prompt,
      config: {
        systemInstruction: `You are an enterprise AI QA platform parser. Classify each intent with one of these exact phases: RETENTION, ACCOUNT MGMT, SECURITY, CHURN, USAGE, or SUPPORT. UTTERANCE must represent a typical user's post or comment in Vietnamese. TRIGGER MOMENT should be where the issue originates, e.g., 'Trang chủ ${selectedPlatform}', 'Group du lịch', 'Messenger Inbox', 'Trình phát video'.${ruleText ? `\n\nAdhere strictly to these extra user-specific rules:\n${ruleText}` : ""}`,
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              name: {
                type: Type.STRING,
                description: "Clean, action-oriented intent name in Vietnamese, e.g., 'Nâng cấp tài khoản VIP', 'Khiếu nại bồi thường vé máy bay'",
              },
              phase: {
                type: Type.STRING,
                description: "Must be exactly RETENTION, ACCOUNT MGMT, SECURITY, CHURN, USAGE, or SUPPORT",
              },
              utterance: {
                type: Type.STRING,
                description: "A natural social media post, comment, or question in Vietnamese expressing this intent.",
              },
              triggerMoment: {
                type: Type.STRING,
                description: "The visual context or platform location, e.g. 'Facebook Group', 'Threads Feed', 'Messenger Inbox'",
              },
            },
            required: ["name", "phase", "utterance", "triggerMoment"],
          },
        },
      },
    });

    const resultText = response.text || "[]";
    const parsedIntents = JSON.parse(resultText);

    const mappedIntents = parsedIntents.map((item: any, index: number) => ({
      id: `social-${Date.now()}-${index}`,
      name: item.name || `${selectedPlatform}: Custom Social Intent`,
      phase: ["RETENTION", "ACCOUNT MGMT", "SECURITY", "CHURN", "USAGE", "SUPPORT"].includes(item.phase)
        ? item.phase
        : "SUPPORT",
      utterance: item.utterance || "Thực hiện hành động hệ thống.",
      triggerMoment: item.triggerMoment || `${selectedPlatform} Feed`,
      selected: true,
    }));

    appState.intents = [...mappedIntents, ...appState.intents];
    res.json({ intents: mappedIntents, fallback: false });
  } catch (error: any) {
    console.error("Gemini Social Intent Discovery failed:", error);
    res.status(500).json({ error: "Gemini API failed to parse contents. Falling back to local pattern." });
  }
});

// 5. Generate Personas from Selected Intents (Gemini API with schemas)
app.post("/api/generate-personas", async (req, res) => {
  const { intents, ruleText } = req.body;
  if (!intents || intents.length === 0) {
    return res.status(400).json({ error: "No intents selected. Please select at least one intent to build personas." });
  }

  const ai = getGeminiClient();
  if (!ai) {
    // Generate happy and edge personas for every selected intent
    const generatedPersonas = intents.flatMap((intent: any, idx: number) => {
      // Choose descriptive names and helper content based on the intent characteristics
      const happyName = intent.name.replace(/Verify|Check|Update|Cancel|Download|Optimize|Add/i, "").trim() + " Operator";
      const edgeName = "Aggressive " + intent.name.replace(/Verify|Check|Update|Cancel|Download|Optimize|Add/i, "").trim() + " Tester";
      return [
        {
          id: `p-${Date.now()}-${idx}-happy`,
          type: "happy" as const,
          name: happyName || "Standard User",
          trigger: intent.triggerMoment || "General Page View",
          utterance: intent.utterance || "Retrieve the normal resources.",
          frequency: 85,
          pain: "High service load or slightly delayed response.",
          reject: "Standard validation failure status codes",
          expectedAIBehavior: "Acknowledge request helper parameters and guide user on standard golden paths.",
          intentId: intent.id,
        },
        {
          id: `p-${Date.now()}-${idx}-edge`,
          type: "edge" as const,
          name: edgeName || "Boundary Analyst",
          trigger: "Corrupted network socket or invalid browser state",
          utterance: `Simulate extreme high availability failure while trying: "${intent.utterance}" with empty headers.`,
          frequency: 15,
          pain: "Session expiration on VPN drop.",
          reject: "503 Back-End Service Not Available",
          expectedAIBehavior: "Assert guardrail compliance and block incorrect token requests.",
          intentId: intent.id,
        }
      ];
    });

    appState.personas = generatedPersonas;
    return res.json({ personas: generatedPersonas, fallback: true });
  }

  try {
    const intentsDescription = intents
      .map((i: any) => `- ID: "${i.id}" | Intent: "${i.name}" (${i.phase}) | Sample utterance: "${i.utterance}"`)
      .join("\n");

    const prompt = `Synthesize target QA test personas for the following selected user intents. For EACH intent listed, generate EXACTLY one standard happy-path persona (type: 'happy') AND EXACTLY one aggressive boundary-critical edge-case persona (type: 'edge'). You MUST return the corresponding intent ID for each persona so they can be mapped back accurately.

Selected Intents:
${intentsDescription}`;

    const response = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents: prompt,
      config: {
        systemInstruction: `You are an AI QA simulator. Create high-fidelity personas correlating directly with target intents. For each intent, output one happy-path and one edge case. You must specify the matching intentId in the output.${ruleText ? `\n\nAdhere strictly to these extra user-specific generation rules:\n${ruleText}` : ""}`,
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              intentId: {
                type: Type.STRING,
                description: "The unique ID matching the associated Intent.",
              },
              type: {
                type: Type.STRING,
                description: "Must be exactly 'happy' or 'edge'",
              },
              name: {
                type: Type.STRING,
                description: "Fictional persona archetype name, e.g. 'Standard User' or 'Token Dropper'",
              },
              trigger: {
                type: Type.STRING,
                description: "The action or user state, e.g. 'Login Success', 'Connection Lost'",
              },
              utterance: {
                type: Type.STRING,
                description: "Typical dialogue or workflow command string.",
              },
              frequency: {
                type: Type.INTEGER,
                description: "Occurence rate (0 - 100), e.g. 80 for happy-path, 10 for edge cases",
              },
              pain: {
                type: Type.STRING,
                description: "Core frustration or system failure experienced.",
              },
              reject: {
                type: Type.STRING,
                description: "Safety reject status code or message response code.",
              },
              expectedAIBehavior: {
                type: Type.STRING,
                description: "The correct, expected target behavior, guardrail prompt response or system reaction from the AI assistant for this specific user scenario.",
              },
            },
            required: ["intentId", "type", "name", "trigger", "utterance", "frequency", "pain", "reject", "expectedAIBehavior"],
          },
        },
      },
    });

    const resultText = response.text || "[]";
    const parsedPersonas = JSON.parse(resultText);

    const generated = parsedPersonas.map((p: any, idx: number) => ({
      id: `p-${Date.now()}-${idx}`,
      type: p.type === "edge" ? "edge" : "happy",
      name: p.name || (p.type === "edge" ? "Session Leaker" : "Standard User"),
      trigger: p.trigger || "System Event",
      utterance: p.utterance || "I want to perform the operations.",
      frequency: p.frequency || (p.type === "edge" ? 15 : 85),
      pain: p.pain || "System lag",
      reject: p.reject || "Operation denied",
      expectedAIBehavior: p.expectedAIBehavior || (p.type === "edge" ? "Reject query with standard corporate guardrail message." : "Helpfully answer the query and process the action."),
      intentId: p.intentId || intents[0]?.id,
    }));

    appState.personas = generated;
    res.json({ personas: generated, fallback: false });
  } catch (error: any) {
    console.error("Gemini Persona generation failed:", error);
    res.status(500).json({ error: "Gemini API failed to generate personas." });
  }
});

// 6. Generate Test Cases from intents and personas
app.post("/api/generate-testcases", async (req, res) => {
  const { intents, personas, ruleText } = req.body;
  if (!intents || !personas) {
    return res.status(400).json({ error: "Missing selected intents or generated personas to build test cases." });
  }

  const ai = getGeminiClient();
  if (!ai) {
    // Offline/Fallback test cases compiler
    const mockCases = intents.map((intent: any, index: number) => {
      const isEven = index % 2 === 0;
      const persona = isEven ? personas[0] : (personas[1] || personas[0]);
      return {
        id: `TC-XEDIEN-1.${index + 1}`,
        intentName: intent.name,
        personaName: `${persona.type === "happy" ? "Persona A" : "Persona B"} (${persona.name})`,
        simulatedPrompt: `As ${persona.name}, trigger "${intent.utterance}"`,
        expectedOutcome: persona.expectedAIBehavior || (persona.type === "happy" ? "Success code 200 with updated status" : `Reject path with: ${persona.reject}`),
        selected: true,
        status: "pending" as const,
      };
    });

    appState.testCases = mockCases;
    return res.json({ testCases: mockCases, fallback: true });
  }

  try {
    const intentsText = intents.map((i: any) => `- Intent: "${i.name}" (utters: "${i.utterance}")`).join("\n");
    const personasText = personas
      .map((p: any) => `- Persona: "${p.name}" (${p.type === "happy" ? "Happy Path" : "Edge Case"}) - Triggers: "${p.trigger}" - Expected AI behavior: "${p.expectedAIBehavior || 'Not specified'}"`)
      .join("\n");

    const prompt = `Synthesize optimized AI software test cases that map selected User Intents directly to simulated User Personas.

Selected Intents:
${intentsText}

Personas Available:
${personasText}

Create 3 distinct diagnostic test case items. Ensure Simulated User Prompts are written in quotes and represent actual input. Expected Outcome should represent specific technical success strings or rejection asserts.`;

    const response = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents: prompt,
      config: {
        systemInstruction: `You are an enterprise diagnostics compiler. Format the test suite securely in strict JSON schema format, assigning either Persona A or Persona B appropriately based on severity.${ruleText ? `\n\nAdhere strictly to these extra user-specific generation rules:\n${ruleText}` : ""}`,
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              intentName: {
                type: Type.STRING,
                description: "Name of the matching Intent.",
              },
              personaName: {
                type: Type.STRING,
                description: "Archetype name, e.g. 'Persona A (Standard User)'",
              },
              simulatedPrompt: {
                type: Type.STRING,
                description: "Simulated client quote or prompt to test.",
              },
              expectedOutcome: {
                type: Type.STRING,
                description: "The assertion output string expected.",
              },
              goal: {
                type: Type.STRING,
                description: "The targeted validation goal or purpose of this test scenario.",
              },
            },
            required: ["intentName", "personaName", "simulatedPrompt", "expectedOutcome", "goal"],
          },
        },
      },
    });

    const resultText = response.text || "[]";
    const parsedTestCases = JSON.parse(resultText);

    const finalCases = parsedTestCases.map((tc: any, index: number) => ({
      id: `TC-XEDIEN-1.${index + 1}`,
      intentName: tc.intentName || intents[0]?.name || "System Operation",
      personaName: tc.personaName || "Persona A (Standard User)",
      simulatedPrompt: tc.simulatedPrompt || "Run simulation prompt.",
      expectedOutcome: tc.expectedOutcome || "Verification passing.",
      goal: tc.goal || "Verify intent execution behavior.",
      selected: true,
      status: "pending" as const,
    }));

    appState.testCases = finalCases;
    res.json({ testCases: finalCases, fallback: false });
  } catch (error: any) {
    console.error("Gemini test case compiling failed:", error);
    res.status(500).json({ error: "Gemini API failed to compile custom test suite." });
  }
});

// 7. Simulated Diagnostic Test Run
app.post("/api/testcases/run", (req, res) => {
  const { testCaseIds } = req.body;
  if (!testCaseIds || testCaseIds.length === 0) {
    return res.status(400).json({ error: "Please select at least one test case to run." });
  }

  // Update status in server memory and build logs
  const results = appState.testCases.map((item) => {
    if (testCaseIds.includes(item.id)) {
      const isFailedSample = item.intentName.toLowerCase().includes("fail") || item.personaName.toLowerCase().includes("leak");
      const finalStatus = isFailedSample ? ("failed" as const) : ("passed" as const);
      
      const scenarioLogs = [
        `[INFO] Initializing sandbox environment for: ${item.id}`,
        `[INFO] Loading domain routing: ${appState.domain} via model: ${appState.aiModel}`,
        `[MOCK] Persona injected: ${item.personaName} with preset browser triggers.`,
        `[SEND] Simulated Prompt: ${item.simulatedPrompt}`,
        finalStatus === "failed" 
          ? `[WARN] Assert rejection check triggered: ${appState.personas[1]?.reject || "Reject verification fail"}`
          : `[PASS] Correct outcome assertion verified: ${item.expectedOutcome}`,
        `[INFO] Test case completed with status: ${finalStatus.toUpperCase()}`
      ];

      return {
        ...item,
        status: finalStatus,
        logs: scenarioLogs
      };
    }
    return item;
  });

  appState.testCases = results;
  res.json({ success: true, testCases: results });
});

// Configure Vite integration or asset serving
async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`AI Test Case Gen full-stack server running on http://localhost:${PORT}`);
  });
}

startServer();
