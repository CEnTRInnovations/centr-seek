
import os
import re
import json
import hashlib
import tempfile
import shutil
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from urllib.parse import urlparse

from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import trafilatura
import fitz
import torch
from transformers import pipeline
from sentence_transformers import SentenceTransformer, util

from dotenv import load_dotenv
from openai import OpenAI

# --- FastAPI app ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuration ---
DIMENSIONS = [
    "Partnership and Power",
    "Community Voice",
    "Process and Methods",
    "Outcomes and Impact",
    "Sustainability",
]

HYPOTHESIS_TEMPLATE_DIM = {
    "Partnership and Power": "Shared decision-making, equitable practices, and trust-building between university and community partners.",
    "Community Voice": "Community members co-designed, informed, or interpreted the research using their knowledge and perspectives.",
    "Process and Methods": "Participatory and culturally responsive methods were used, with community members actively collaborating in the research process.",
    "Outcomes and Impact": "The project benefits the community, builds capacity, and co-creates knowledge or systemic change.",
    "Sustainability": "The collaboration is ongoing, supported institutionally, and builds long-term community capacity"
}

WEIGHTS = {
    "Partnership and Power": 0.25,
    "Community Voice": 0.20,
    "Process and Methods": 0.20,
    "Outcomes and Impact": 0.20,
    "Sustainability": 0.15,
}

ZSC_WEIGHT = 0.1
SIM_WEIGHT = 0.9
FINAL_THRESHOLD = 0.65
CANDIDATE_LABELS = list(HYPOTHESIS_TEMPLATE_DIM.values())

# --- Load env & OpenAI client ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set in .env")
client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Models ---
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=-1)
embedder = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
with torch.inference_mode():
    QUERY_EMBEDS = {
        dim: embedder.encode(HYPOTHESIS_TEMPLATE_DIM[dim], convert_to_tensor=True, normalize_embeddings=True)
        for dim in DIMENSIONS
    }

# --- Utilities ---
def is_url(s: str) -> bool:
    try:
        p = urlparse(s)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False

def md5_12(s: str) -> str:
    return hashlib.md5(s.encode("utf-8", errors="ignore")).hexdigest()[:12]

def clean_text(txt: str) -> str:
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()

#reads pdf and extracts text
def extract_pdf(path: str) -> str:
    doc = fitz.open(path)
    pages = [page.get_text() for page in doc]
    return clean_text("\n\n".join(pages))

def extract_txt(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return clean_text(f.read())
    except UnicodeDecodeError:
        with open(path, "r", encoding="ISO-8859-1") as f:
            return clean_text(f.read())

def extract_url(u: str) -> str:
    raw = trafilatura.fetch_url(u)
    if not raw:
        return ""
    txt = trafilatura.extract(raw, favor_recall=True, include_comments=False, include_tables=False)
    return clean_text(txt or "")

def load_document(source: str) -> str:
    if is_url(source):
        return extract_url(source)
    lower = source.lower()
    if lower.endswith(".pdf"):
        return extract_pdf(source)
    elif lower.endswith(".txt"):
        return extract_txt(source)
    else:
        try:
            return extract_txt(source)
        except Exception:
            return ""

def sentence_chunks(text: str, max_sents: int = 4) -> List[str]:
    sents = re.split(r"(?<=[.!?])\s+", text)
    chunks = [" ".join(sents[i:i+max_sents]) for i in range(0, len(sents), max_sents)]
    return [c.strip() for c in chunks if len(c.strip()) > 30 and any(ch.isalpha() for ch in c)][:2000]

@dataclass
class DocRecord:
    doc_id: str
    source_type: str
    path_or_url: str
    known_label: int | None
    text: str

def zero_shot_scores(doc_text: str) -> Dict[str, float]:
    res = classifier(doc_text, candidate_labels=CANDIDATE_LABELS, multi_label=True)
    return {dim: float(res["scores"][res["labels"].index(HYPOTHESIS_TEMPLATE_DIM[dim])]) for dim in DIMENSIONS}

def best_chunk_per_dimension(chunks: List[str]) -> Dict[str, Dict[str, Any]]:
    if not chunks:
        return {dim: {"top_chunk": "", "similarity": 0.0} for dim in DIMENSIONS}
    with torch.inference_mode():
        chunk_emb = embedder.encode(chunks[:100], convert_to_tensor=True, normalize_embeddings=True)
        out = {}
        for dim in DIMENSIONS:
            sims = util.cos_sim(QUERY_EMBEDS[dim], chunk_emb)[0]
            top_idx = int(torch.topk(sims, k=1).indices[0])
            out[dim] = {"top_chunk": chunks[top_idx], "similarity": float(sims[top_idx].item())}
        return out

def score_document(text: str) -> Dict[str, Any]:
    label_scores = zero_shot_scores(text)
    chunks = sentence_chunks(text)
    explanations = best_chunk_per_dimension(chunks)
    details = {}
    final_scores = []
    for dim in DIMENSIONS:
        zsc = label_scores[dim]
        sim = explanations[dim]["similarity"]
        top_chunk = explanations[dim]["top_chunk"]
        chunk_res = classifier(top_chunk, candidate_labels=[HYPOTHESIS_TEMPLATE_DIM[dim]], multi_label=True)
        chunk_zsc = float(chunk_res["scores"][0])
        final = (ZSC_WEIGHT * zsc) + (SIM_WEIGHT * chunk_zsc)
        details[dim] = {"score": round(zsc,4), "top_chunk": top_chunk, "similarity": round(sim,4), "chunk_zsc": round(chunk_zsc,4), "final_score": round(final,4)}
        final_scores.append(final)
    avg_final = sum(final_scores)/len(final_scores)
    return {"average_final_score": round(avg_final,4), "is_community_engaged": avg_final >= FINAL_THRESHOLD, "details": details}

# --- GPT ToT prompt generator ---
# def generate_tot_prompt(doc_text: str) -> str:
#     MAX_LEN = 10000
#     doc_text = doc_text[:MAX_LEN] + "\n[... Document truncated ...]" if len(doc_text) > MAX_LEN else doc_text
#     return f"""
# You are leading a team to categorize documents based on a framework of community engaged research.
# Run THREE independent rounds (Thought A, B, C) producing scores 0-1 for these 5 factors: {DIMENSIONS}.
# Output tables in markdown format: Factor | Thought A Score | Thought B Score | Thought C Score | Mean Score | Weighted Score
# Compute final average after 3 rounds and write a short 2-4 sentence justification.
# Document:
# --------------------------
# {doc_text}
# --------------------------
# """

def generate_tot_prompt(doc_text: str) -> str:
    MAX_LEN = 10000
    doc_text = doc_text[:MAX_LEN] + "\n[... Document truncated ...]" if len(doc_text) > MAX_LEN else doc_text

    return f"""
You are performing a **Tree-of-Thought (ToT)** evaluation to determine whether this document
demonstrates **community-engaged research (CER)**.

You MUST follow this exact structure.

=====================================================
### 🌳 TREE OF THOUGHT REASONING (3 independent branches)
For each branch (Thought A, Thought B, Thought C):

1. **Extract evidence** from the document for each factor.
2. **Reason step-by-step** about what is present, missing, weak, or strong.
3. Assign a **score from 0 to 1** based ONLY on evidence.
4. Penalize missing elements:
   - No explicit shared decision-making → score MUST be <0.25
   - No community co-design → score MUST be <0.40
   - Purely university-driven activities → Partnership score <0.30
   - No sustainability plan → score <0.40
   - If outcomes are strong, score 0.70–0.90
5. Avoid optimism bias. Missing information = LOW SCORES.

=====================================================
### 📊 SCORING FRAMEWORK (5 Factors)
Use these EXACT weights:

1. Partnership and Power — **0.25**
2. Community Voice — **0.20**
3. Process and Methods — **0.20**
4. Outcomes and Impact — **0.20**
5. Sustainability — **0.15**

=====================================================
### 📋 OUTPUT FORMAT (STRICT)
You MUST output ONLY the following table:

| Factor | Thought A Score | Thought B Score | Thought C Score | Mean Score | Weighted Score |
|-------|------------------|------------------|------------------|------------|-----------------|

After the table, output:

### Final Weighted Average Score
<value>

### Justification (3–5 sentences)
=====================================================

### DOCUMENT TO ANALYZE
--------------------------
{doc_text}
--------------------------
"""


def call_gpt_tot(doc_text: str) -> str:
    prompt = generate_tot_prompt(doc_text)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return resp.choices[0].message.content

# --- Parse functions (use your earlier TOT parser) ---
# (reuse _safe_float, parse_round_table_rows, parse_tot_and_compute_scores)
# For brevity, assume these are copied from your previous code.

# --- Process text source ---
def _safe_float(x):
    try:
        return float(x)
    except:
        return None

def parse_round_table_rows(text: str):
    """
    Extracts markdown table rows of the form:
    Factor | A | B | C | Mean | Weighted
    Returns dict: {factor: {...}}
    """
    rows = {}
    lines = text.splitlines()

    for line in lines:
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|") if p.strip()]

        # Expect 6 columns
        if len(parts) != 6:
            continue

        factor, A, B, C, mean, weighted = parts

        if factor not in DIMENSIONS:
            continue

        rows[factor] = {
            "round_A": _safe_float(A),
            "round_B": _safe_float(B),
            "round_C": _safe_float(C),
            "mean": _safe_float(mean),
            "weighted": _safe_float(weighted),
        }

    return rows

def parse_tot_and_compute_scores(tot_text: str):
    rows = parse_round_table_rows(tot_text)
    weighted_values = [
        rows.get(dim, {}).get("weighted")
        for dim in DIMENSIONS
        if rows.get(dim, {}).get("weighted") is not None
    ]

    final_score = (
        sum(weighted_values) / len(weighted_values)
        if weighted_values else None
    )

    return {
        "parsed_dimensions": rows,
        "final_mean_score": final_score
    }

def process_text_source(source_name: str, text: str) -> Dict[str, Any]:
    try:
        res = score_document(text)
        if res.get("is_community_engaged"):
            tot_text = call_gpt_tot(text)
            res["tree_of_thought"] = {"tot_reasoning": tot_text}
            res["tree_of_thought_parsed"] = parse_tot_and_compute_scores(tot_text)
        return {"source": source_name, "result": res}
    except Exception as e:
        return {"source": source_name, "error": str(e)}

# --- FastAPI endpoints ---
@app.get("/ping")
async def ping():
    return {"ok": True}

@app.post("/api/score")
async def score_endpoint(urls: str = Form("[]"), file: UploadFile | None = File(None)):
    try:
        urls_list = json.loads(urls)
        urls_list = [u.strip() for u in urls_list if isinstance(u, str) and u.strip()]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"urls must be a JSON array string: {e}")

    results: List[Dict[str, Any]] = []

    if file:
        suffix = ".pdf" if file.filename.lower().endswith(".pdf") else ".txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        text = load_document(tmp_path)
        os.remove(tmp_path)
        if not text:
            results.append({"source": file.filename, "error": "failed to extract text"})
        else:
            results.append(process_text_source(file.filename, text))

    for u in urls_list:
        text = load_document(u)
        if not text:
            results.append({"source": u, "error": "failed to fetch/extract"})
        else:
            results.append(process_text_source(u, text))

    return {"records": results}

@app.post("/api/download-json")
async def download_json(payload: Dict[str, Any]):
    return JSONResponse(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=community_engagement.json"}
    )