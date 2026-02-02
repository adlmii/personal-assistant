import chromadb
import uuid
import time
from colorama import Fore, Style

class MemoryManager:
    def __init__(self):
        # Pastikan path ini sesuai / konsisten
        self.client = chromadb.PersistentClient(path="kevin_memory_db")
        self.collection = self.client.get_or_create_collection(name="user_interactions")

    def add_memory(self, user_input, assistant_reply, memory_type):
        """
        [EPIC 4] Noise Filter & Taxonomy Lock
        """
        # Rule 1: Taxonomy Lock - Skip is Skip.
        if memory_type == "skip":
            return

        # Rule 2: Noise Filter (Panjang kata)
        # Jangan simpan input pendek kecuali itu explicit preference
        if len(user_input.split()) < 3 and memory_type != "preference":
            print(f"{Fore.LIGHTBLACK_EX}[MEMORY] Skipped (Too short/noise){Style.RESET_ALL}")
            return

        # Rule 3: Format Storage
        text_to_store = f"User: {user_input} | Kevin: {assistant_reply}"
        
        self.collection.add(
            documents=[text_to_store],
            metadatas=[{
                "type": memory_type,
                "timestamp": time.time(), 
                "raw_input": user_input
            }],
            ids=[str(uuid.uuid4())]
        )
        print(f"{Fore.MAGENTA}[MEMORY] Stored ({memory_type}): {user_input[:30]}...{Style.RESET_ALL}")

    def retrieve_memory(self, query, n_results=2, memory_type_filter=None):
        """
        [EPIC 4] Recall Gate Support (Updated for List Filter)
        """
        try:
            where_clause = None
            if memory_type_filter:
                # Support list: ["fact", "preference"]
                if isinstance(memory_type_filter, list):
                    where_clause = {"type": {"$in": memory_type_filter}}
                else:
                    where_clause = {"type": memory_type_filter}

            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause 
            )
            
            if results and results['documents']:
                memories = [doc for doc in results['documents'][0]]
                return "\n".join(memories)
            return ""
        except Exception as e:
            print(f"{Fore.RED}[MEMORY ERROR] {e}{Style.RESET_ALL}")
            return ""