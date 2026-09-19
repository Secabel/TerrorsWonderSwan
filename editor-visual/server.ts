import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import dotenv from "dotenv";

dotenv.config({ path: '.env' });
dotenv.config({ path: '.env.example' }); // Fallback for the injected key

import { GoogleGenAI } from "@google/genai";

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // API route to proxy Gemini requests
  app.post("/api/gemini", async (req, res) => {
    try {
      // Prioritize platform environment variable, fallback to client input
      const apiKey = process.env.GEMINI_API_KEY || req.body.apiKey;
      
      if (!apiKey) {
         return res.status(401).json({ error: "Falta la API Key. Configúrala en los Secrets (si estás en AI Studio) o pégala en la app." });
      }

      const ai = new GoogleGenAI({
        apiKey,
        httpOptions: {
          headers: {
            'User-Agent': 'aistudio-build',
          }
        }
      });

      const response = await ai.models.generateContent({
        model: "gemini-3.5-flash",
        contents: req.body.payload?.contents || [],
        config: req.body.payload?.generationConfig
      });
      
      // Simulate REST payload format expected by the frontend
      res.json({
        candidates: [
          {
            content: {
              parts: [{ text: response.text }]
            }
          }
        ]
      });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    // Production static serving
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
