# from fastapi import FastAPI
# from pydantic import BaseModel
# import os, re, hashlib
# from typing import List, Dict, Any
# from dataclasses import dataclass
# from urllib.parse import urlparse

# import fitz
# import trafilatura
# import pandas as pd
# import torch
# from tqdm import tqdm
# from transformers import pipeline
# from sentence_transformers import SentenceTransformer, util
# import orjson
# app = FastAPI()

# class DocRequest(BaseModel):
#     text: str

# @app.post("/score")
# async def score_document(req: DocRequest):
#     # Call your ML pipeline here

#     DIMENSIONS = [
#         "Community Voice",
#         "Power Sharing",
#         "Participatory Methods",
#         "Community Impact",
#         "Sustainability"
#     ]

#     # Dimension-specific prompts
#     HYPOTHESIS_TEMPLATE_DIM = {
#         "Community Voice": "This text shows that community members’ perspectives are actively considered and included.",
#         "Power Sharing": "This text shows that decision-making is shared with community members.",
#         "Participatory Methods": "This text shows that research methods involve community members in design or execution.",
#         "Community Impact": "This text shows that research outcomes benefit the community directly.",
#         "Sustainability": "This text shows that community engagement is maintained over time."
#     }

#     # Scoring thresholds
#     ZSC_WEIGHT = 0.7
#     SIM_WEIGHT = 0.3
#     FINAL_THRESHOLD = 0.72

#     # -----------------------
#     # INITIALIZE MODELS
#     # -----------------------

#     classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device_map="auto")
#     embedder = SentenceTransformer("all-MiniLM-L6-v2")

#     # -----------------------
#     # UTILITY FUNCTIONS
#     # -----------------------

#     def is_url(s: str) -> bool:
#         try:
#             p = urlparse(s)
#             return p.scheme in ("http", "https") and bool(p.netloc)
#         except Exception:
#             return False

#     def md5_12(s: str) -> str:
#         return hashlib.md5(s.encode("utf-8", errors="ignore")).hexdigest()[:12]

#     def clean_text(txt: str) -> str:
#         txt = re.sub(r"[ \t]+", " ", txt)
#         txt = re.sub(r"\n{3,}", "\n\n", txt)
#         return txt.strip()

#     def extract_pdf(path: str) -> str:
#         doc = fitz.open(path)
#         pages = [page.get_text() for page in doc]
#         return clean_text("\n\n".join(pages))
#     def extract_txt(path: str) -> str:
#         try:
#             with open(path, "r", encoding="utf-8") as f:
#                 return clean_text(f.read())
#         except UnicodeDecodeError:
#             with open(path, "r", encoding="ISO-8859-1") as f:
#                 return clean_text(f.read())

#     def extract_url(u: str) -> str:
#         raw = trafilatura.fetch_url(u)
#         if not raw:
#             return ""
#         txt = trafilatura.extract(raw, favor_recall=True, include_comments=False, include_tables=False)
#         return clean_text(txt or "")

#     def load_document(source: str) -> str:
#         if is_url(source):
#             return extract_url(source)
#         lower = source.lower()
#         if lower.endswith(".pdf"):
#             return extract_pdf(source)
#         elif lower.endswith(".txt"):
#             return extract_txt(source)
#         else:
#             try:
#                 return extract_txt(source)
#             except Exception:
#                 return ""
        
#     def sentence_chunks(text: str, max_sents: int = 4) -> List[str]:
#         sents = re.split(r"(?<=[.!?])\s+", text)
#         chunks = [" ".join(sents[i:i + max_sents]) for i in range(0, len(sents), max_sents)]
#         chunks = [c.strip() for c in chunks if len(c.strip()) > 30 and any(ch.isalpha() for ch in c)]
#         return chunks[:2000]


#     @dataclass
#     class DocRecord:
#         doc_id: str
#         source_type: str
#         path_or_url: str
#         known_label: int | None
#         text: str

# # -----------------------
# # SCORING FUNCTIONS
# # -----------------------

#     def zero_shot_scores(doc_text: str) -> Dict[str, float]:
#         candidate_labels = list(HYPOTHESIS_TEMPLATE_DIM.values())
#         res = classifier(doc_text, candidate_labels=candidate_labels, multi_label=True)
#         # Map dimension name -> score
#         return {dim: float(res["scores"][res["labels"].index(HYPOTHESIS_TEMPLATE_DIM[dim])]) for dim in DIMENSIONS}

#     def best_chunk_per_dimension(chunks: List[str]) -> Dict[str, Dict[str, Any]]:
#         if not chunks:
#             return {dim: {"top_chunk": "", "similarity": 0.0} for dim in DIMENSIONS}

#         with torch.inference_mode():
#             chunk_emb = embedder.encode(chunks, convert_to_tensor=True, normalize_embeddings=True)
#             out: Dict[str, Dict[str, Any]] = {}
#             for dim in DIMENSIONS:
#                 q_emb = embedder.encode(HYPOTHESIS_TEMPLATE_DIM[dim], convert_to_tensor=True, normalize_embeddings=True)
#                 sims = util.cos_sim(q_emb, chunk_emb)[0]
#                 top_idx = int(torch.topk(sims, k=1).indices[0])
#                 out[dim] = {
#                     "top_chunk": chunks[top_idx],
#                     "similarity": float(sims[top_idx].item()),
#                 }
#             return out

#     def score_document(text: str) -> Dict[str, Any]:
#         label_scores = zero_shot_scores(text)
#         chunks = sentence_chunks(text)
#         explanations = best_chunk_per_dimension(chunks)

#         dim_scores = {}
#         final_scores = []
#         for dim in DIMENSIONS:
#             zsc = label_scores[dim]
#             sim = explanations[dim]["similarity"]
#             final = ZSC_WEIGHT * zsc + SIM_WEIGHT * sim
#             dim_scores[dim] = round(zsc, 4)
#             final_scores.append(final)

#         avg_final = sum(final_scores) / len(final_scores)
#         is_engaged = avg_final >= FINAL_THRESHOLD

#         details = {}
#         for i, dim in enumerate(DIMENSIONS):
#             details[dim] = {
#                 "score": dim_scores[dim],
#                 "top_chunk": explanations[dim]["top_chunk"],
#                 "similarity": round(explanations[dim]["similarity"], 4),
#                 "final_score": round(final_scores[i], 4)
#             }

#         return {
#             "dimension_scores": dim_scores,
#             "average_final_score": avg_final,
#             "is_community_engaged": is_engaged,
#             "details": details
#         }

#     # -----------------------
#     # MAIN PIPELINE
#     # -----------------------

#     def main():
#         records: List[DocRecord] = []

#         # Load files
#         for p in tqdm(FILE_PATHS, desc="Loading files"):
#             txt = load_document(p)
#             if not txt:
#                 print(f"[WARN] Empty/failed file: {p}")
#                 continue
#             records.append(DocRecord(md5_12(p), "file", p, None, txt))

#         # Load URLs
#         for u, label in tqdm(URLS, desc="Loading URLs"):
#             txt = load_document(u)
#             if not txt:
#                 print(f"[WARN] Empty/failed URL: {u}")
#                 continue
#             records.append(DocRecord(md5_12(u), "url", u, label, txt))

#         # Save combined corpus
#         os.makedirs("outputs", exist_ok=True)
#         with open("outputs/combined_docs.jsonl", "wb") as f:
#             for r in records:
#                 f.write(orjson.dumps({
#                     "doc_id": r.doc_id,
#                     "source_type": r.source_type,
#                     "path_or_url": r.path_or_url,
#                     "known_label": r.known_label,
#                     "text": r.text,
#                 }) + b"\n")

#         pd.DataFrame([{
#             "doc_id": r.doc_id,
#             "source_type": r.source_type,
#             "path_or_url": r.path_or_url,
#             "known_label": r.known_label,
#             "chars": len(r.text)
#         } for r in records]).to_csv("outputs/combined_docs.csv", index=False)

#         # Score documents
#         rows_wide = []
#         with open("outputs/zsc_scores.jsonl", "wb") as fjson:
#             for r in tqdm(records, desc="Scoring"):
#                 s = score_document(r.text)
#                 fjson.write(orjson.dumps({
#                     "doc_id": r.doc_id,
#                     "source_type": r.source_type,
#                     "path_or_url": r.path_or_url,
#                     "known_label": r.known_label,
#                     "average_final_score": round(s["average_final_score"], 4),
#                     "is_community_engaged": s["is_community_engaged"],
#                     "details": s["details"],
#                 }) + b"\n")

#                 # Wide row for CSV
#                 row = {
#                     "doc_id": r.doc_id,
#                     "source_type": r.source_type,
#                     "path_or_url": r.path_or_url,
#                     "known_label": r.known_label,
#                     "average_final_score": round(s["average_final_score"], 4),
#                     "is_community_engaged": s["is_community_engaged"],
#                 }
#                 for dim in DIMENSIONS:
#                     row[f"{dim}_score"] = s["details"][dim]["score"]
#                     row[f"{dim}_sim"] = s["details"][dim]["similarity"]
#                     row[f"{dim}_final"] = s["details"][dim]["final_score"]
#                 rows_wide.append(row)

#         pd.DataFrame(rows_wide).to_csv("outputs/zsc_scores_wide.csv", index=False)
#         print("[INFO] Wrote outputs/zsc_scores.jsonl and outputs/zsc_scores_wide.csv")

#     # -----------------------
#     # if __name__ == "__main__":
#     #     main()



#     return {"average_final_score": 0.82, "is_community_engaged": True}
