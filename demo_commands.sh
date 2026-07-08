#!/usr/bin/env bash
# Provenance Guard — on-camera demo commands.
# Run these ONE AT A TIME while recording.
# Server must be running:  uv run flask run

API=http://127.0.0.1:5000

# ── 1) Human submission ──────────────────────────────────────────────
curl -s -X POST $API/submit -H "Content-Type: application/json" -d '{
  "text": "ok so i finally tried that new ramen place downtown and honestly? underwhelming. the broth was fine but they put WAY too much sodium in it and i was thirsty for like three hours after.",
  "creator_id": "creator-jess"
}' | python3 -m json.tool

# ── 2) AI submission ─────────────────────────────────────────────────
curl -s -X POST $API/submit -H "Content-Type: application/json" -d '{
  "text": "It is important to note that artificial intelligence represents a significant advancement in modern technology. Furthermore, machine learning algorithms enable systems to process data efficiently. Additionally, neural networks have demonstrated remarkable capabilities across various domains. Moreover, organizations must consider implementing these technologies strategically. In conclusion, the integration of AI tools will continue to optimize outcomes and enhance productivity across industries.",
  "creator_id": "creator-alice"
}' | python3 -m json.tool

# ── 3) Uncertain submission ──────────────────────────────────────────
curl -s -X POST $API/submit -H "Content-Type: application/json" -d '{
  "text": "The relationship between creativity and technology has always been complex. I think what gets lost in these conversations is that tools don'\''t write — people do. That said, it is important to consider how AI systems are increasingly capable of producing coherent, structured prose. Organizations must evaluate these developments carefully and consider the implications for creative work and attribution.",
  "creator_id": "creator-uncertain"
}' | python3 -m json.tool

# ── 4) Appeal the uncertain submission ──────────────────────────────
# Paste the content_id from step 3 here before recording
CID="PASTE_UNCERTAIN_CONTENT_ID_HERE"
curl -s -X POST $API/appeal -H "Content-Type: application/json" -d "{
  \"content_id\": \"$CID\",
  \"creator_reasoning\": \"I wrote this myself for a philosophy class. It reads formally because it is an academic essay, not because it is AI-generated.\"
}" | python3 -m json.tool

# ── 5) Show the full audit log ───────────────────────────────────────
curl -s $API/log | python3 -m json.tool