import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = 3000;
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

// Capture raw body as Buffer for ALL content types (JSON, multipart, binary)
// so the proxy can forward uploads (multipart/form-data) untouched.
app.use(express.raw({ type: "*/*", limit: "50mb" }));

// Proxy all /api/* requests to the Python FastAPI backend
app.all("/api/*", async (req, res) => {
  try {
    const targetUrl = `${BACKEND_URL}${req.originalUrl}`;
    const headers: Record<string, string> = {};
    if (req.headers["content-type"]) {
      headers["Content-Type"] = req.headers["content-type"] as string;
    }
    if (req.headers.authorization) {
      headers.Authorization = req.headers.authorization as string;
    }

    const fetchOptions: RequestInit = { method: req.method, headers };

    const hasBody =
      req.method !== "GET" &&
      req.method !== "HEAD" &&
      Buffer.isBuffer(req.body) &&
      req.body.length > 0;
    if (hasBody) {
      fetchOptions.body = req.body;
    }

    const response = await fetch(targetUrl, fetchOptions);
    const contentType = response.headers.get("content-type") || "";
    res.status(response.status);

    if (contentType.includes("application/json")) {
      const data = await response.json();
      res.json(data);
    } else {
      const buffer = Buffer.from(await response.arrayBuffer());
      if (contentType) res.setHeader("Content-Type", contentType);
      res.send(buffer);
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    console.error(`Proxy error for ${req.method} ${req.originalUrl}:`, message);
    res.status(502).json({
      error: `Backend unreachable at ${BACKEND_URL}. Is the Python server running?`,
    });
  }
});

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
    app.get("*", (_req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Frontend server running on http://localhost:${PORT}`);
    console.log(`Proxying /api/* to ${BACKEND_URL}`);
  });
}

startServer();
