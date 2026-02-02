import chromadb
from sentence_transformers import SentenceTransformer
import uuid
import datetime
import os
import logging
from colorama import Fore, Style

# Silence ChromaDB logs
logging.getLogger("chromadb").setLevel(logging.ERROR)

# Tipe Memori yang Valid
MEMORY_TYPES = {"conversation", "fact", "preference", "skip"}

class MemoryManager:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "kevin_memory_db")

        print(f"{Fore.YELLOW}[MEMORY] Typed Memory System Online.{Style.RESET_ALL}")

        self.client = chromadb.PersistentClient(path=db_path)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

        self.collection = self.client.get_or_create_collection(
            name="kevin_memory"
        )

    # ADD MEMORY WITH TYPE
    def add_memory(
        self,
        user_text: str,
        ai_text: str,
        mem_type: str = "conversation"
    ):
        """
        Store a memory with type.
        Default type = conversation
        """
        if mem_type == "skip":
            return 

        if mem_type not in MEMORY_TYPES:
            mem_type = "conversation"

        timestamp = datetime.datetime.now().isoformat()
        memory_id = f"{mem_type}_{timestamp}_{uuid.uuid4().hex[:6]}"

        document = f"[{mem_type.upper()}] User: {user_text}\nKevin: {ai_text}"
        embedding = self.embedder.encode(document).tolist()

        print(f"{Fore.MAGENTA}[MEMORY SAVED] Type: {mem_type}{Style.RESET_ALL}")

        self.collection.add(
            documents=[document],
            embeddings=[embedding],
            metadatas=[{
                "type": mem_type,
                "user_text": user_text,
                "ai_text": ai_text,
                "timestamp": timestamp
            }],
            ids=[memory_id]
        )

    # RETRIEVE MEMORY (Prioritize Facts/Prefs)
    def retrieve_memory(
        self,
        query: str,
        n_results: int = 3
    ):
        try:
            query_embedding = self.embedder.encode(query).tolist()

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )

            if results and results.get("documents") and results["documents"][0]:
                return results["documents"][0]

            return []

        except Exception:
            return []