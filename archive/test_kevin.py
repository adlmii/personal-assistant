import asyncio
import os
import sys
from dotenv import load_dotenv
from groq import AsyncGroq, APIConnectionError, AuthenticationError, APIStatusError
from colorama import init, Fore, Style

# Inisialisasi colorama
init()

# Load environment variables
load_dotenv()

async def test_groq_connection():
    print(f"{Fore.CYAN}[INFO] Memulai test koneksi ke 'Kevin' (Groq API)...{Style.RESET_ALL}")

    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print(f"{Fore.RED}[ERROR] API Key tidak ditemukan.{Style.RESET_ALL}")
        return

    client = AsyncGroq(api_key=api_key)

    try:
        print(f"{Fore.YELLOW}[PROCESS] Mengirim pesan percobaan ke Llama 3.3...{Style.RESET_ALL}")
        
        chat_completion = await client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Kamu adalah Kevin, asisten AI yang ramah dan membantu."
                },
                {
                    "role": "user",
                    "content": "Halo Kevin! Cek suara, apakah kamu bisa mendengarku?"
                }
            ],
            # --- BAGIAN INI YANG DIUPDATE ---
            model="llama-3.3-70b-versatile", 
            # --------------------------------
            temperature=0.7,
            max_tokens=150,
        )

        response = chat_completion.choices[0].message.content
        
        print(f"\n{Fore.GREEN}[SUCCESS] Koneksi Berhasil!{Style.RESET_ALL}")
        print(f"{Fore.BLUE}Kevin menjawab:{Style.RESET_ALL}")
        print(f"{Style.BRIGHT}{response}{Style.RESET_ALL}\n")

    except Exception as e:
        print(f"{Fore.RED}[ERROR] Terjadi kesalahan: {e}{Style.RESET_ALL}")
    finally:
        await client.close()

if __name__ == "__main__":
    try:
        asyncio.run(test_groq_connection())
    except KeyboardInterrupt:
        pass