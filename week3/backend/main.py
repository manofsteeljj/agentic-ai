import uuid
import os
import traceback
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google import genai
from google.genai import types
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, QueryRequest
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from llama_index.embeddings.google import GeminiEmbedding

# ── Clients ───────────────────────────────────────────────────────────────────
gemini_client = genai.Client()
embed_model = GeminiEmbedding(
    model_name="models/gemini-embedding-1",
    api_key=os.environ.get("GEMINI_API_KEY")
)

qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))


# Local embedding model — runs offline, no API key needed
# all-MiniLM-L6-v2 is fast and lightweight (384 dims)
print("Loading embedding model...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
print("Embedding model loaded.")

COLLECTION_NAME = "rag_documents"
VECTOR_SIZE = 384          # all-MiniLM-L6-v2 output size
SCORE_THRESHOLD = 0.40

# ── Ensure Qdrant collection exists ──────────────────────────────────────────
if not qdrant_client.collection_exists(COLLECTION_NAME):
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="Simple RAG Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler → always return JSON ────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_embedding(text: str) -> list[float]:
    """Generate a local embedding with sentence-transformers."""
    return embed_model.encode(text, normalize_embeddings=True).tolist()


def simple_chunk(text: str, chunk_size: int = 200, overlap: int = 30) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


def search_context(query: str, limit: int = 5):
    """Return (context_str, best_score) from Qdrant."""
    vector = get_embedding(query)
    # Search without threshold first so we can log actual scores
    all_results = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=limit,
    ).points
    if not all_results:
        print(f"[RAG] No results at all for: '{query}'")
        return None, 0.0

    print(f"[RAG] Top scores for '{query}': {[round(r.score, 4) for r in all_results]}")

    best_score = all_results[0].score
    if best_score < SCORE_THRESHOLD:
        return None, best_score

    blocks = [hit.payload["text"] for hit in all_results if hit.score >= SCORE_THRESHOLD]
    return "\n\n".join(blocks), best_score


# ── Routes ────────────────────────────────────────────────────────────────────
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Ingest a plain-text file into Qdrant."""
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported.")

    raw_text = (await file.read()).decode("utf-8")

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="File is empty.")

    chunks = simple_chunk(raw_text)

    points = []
    for chunk in chunks:
        vector = get_embedding(chunk)
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={"text": chunk, "source": file.filename},
            )
        )

    if points:
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)

    return {"message": f"Indexed {len(points)} chunks from '{file.filename}'."}


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chat(request: ChatRequest):
    """Answer a question using the uploaded documents."""
    context, score = search_context(request.message)

    if context is None or score < SCORE_THRESHOLD:
        return {
            "answer": "I don't know. The question doesn't seem relevant to the uploaded data.",
            "score": round(score, 4),
            "relevant": False,
        }

    system_instruction = f"""
    You are a helpful assistant that answers questions strictly based on the provided context.
    If the answer is not found in the context, respond with "I don't know based on the provided data."  
    


[CONTEXT]
{context}
"""

    response = gemini_client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=request.message,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,
        ),
    )

    return {
        "answer": response.text,
        "score": round(score, 4),
        "relevant": True,
    }


@app.delete("/reset")
async def reset_collection():
    """Wipe all stored vectors."""
    qdrant_client.delete_collection(COLLECTION_NAME)
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    return {"message": "Collection reset successfully."}
