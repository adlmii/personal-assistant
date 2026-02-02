import asyncio
import os
import re
import speech_recognition as sr
from groq import Groq, AsyncGroq
from dotenv import load_dotenv
import edge_tts
import pygame
from colorama import init, Fore, Style

# --- SETUP AWAL ---
init()
load_dotenv()

# Client Init
client_whisper = Groq(api_key=os.getenv("GROQ_API_KEY"))
client_chat = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

# Audio Setup
pygame.mixer.init()
TEMP_INPUT_FILE = "temp_input.wav"
TEMP_OUTPUT_FILE = "temp_output.mp3"
WAKE_WORD = "kevin"  # <-- Kata kunci pemicu

# System Prompt
SYSTEM_PROMPT = """
Kamu adalah Kevin, AI Coding Partner & Tech Bro.
Personality: Chill, helpful, to-the-point, panggil user 'Bro' atau 'Boss'.
Skill: Jago Python, Tech, dan memberikan solusi singkat padat.
"""

conversation_history = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

def listen():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300 
    recognizer.dynamic_energy_threshold = True

    with sr.Microphone() as source:
        print(f"\n{Fore.BLACK}{Style.BRIGHT}[STANDBY] Menunggu panggilan...{Style.RESET_ALL}")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        try:
            # Timeout diperpanjang dikit biar gak gampang putus
            audio = recognizer.listen(source, timeout=None, phrase_time_limit=8)
            
            # Simpan file audio
            with open(TEMP_INPUT_FILE, "wb") as f:
                f.write(audio.get_wav_data())

            # Transkrip Whisper
            with open(TEMP_INPUT_FILE, "rb") as file_obj:
                transcription = client_whisper.audio.transcriptions.create(
                    file=(TEMP_INPUT_FILE, file_obj.read()),
                    model="whisper-large-v3",
                    response_format="text",
                    language="en"
                )
            
            text_result = transcription.strip()
            # Tampilkan apa yang didengar (warna abu-abu dulu karena belum tentu diproses)
            print(f"{Fore.LIGHTBLACK_EX}[HEARD] '{text_result}'{Style.RESET_ALL}")
            return text_result

        except sr.WaitTimeoutError:
            return None
        except Exception:
            # Error silent aja biar gak nyepam terminal kalau hening
            return None

async def think(user_text):
    print(f"{Fore.MAGENTA}[THINKING] Processing: '{user_text}'...{Style.RESET_ALL}")
    
    conversation_history.append({"role": "user", "content": user_text})
    
    try:
        completion = await client_chat.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=conversation_history,
            temperature=0.7,
            max_tokens=200,
        )
        
        response_text = completion.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": response_text})
        return response_text
    
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Brain error: {e}{Style.RESET_ALL}")
        return "My brain is lagging, Bro. Coba lagi."

async def speak(text):
    if not text: return
    print(f"{Fore.BLUE}[KEVIN] {text}{Style.RESET_ALL}")
    
    try:
        communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
        await communicate.save(TEMP_OUTPUT_FILE)

        pygame.mixer.music.load(TEMP_OUTPUT_FILE)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
            
        pygame.mixer.music.unload()
    except Exception as e:
        print(f"{Fore.RED}[ERROR] TTS error: {e}{Style.RESET_ALL}")

def process_wake_word(text):
    """
    Fungsi untuk cek ada kata 'Kevin' gak.
    Kalau ada, balikin teks bersihnya. Kalau gak, balikin None.
    """
    text_lower = text.lower()
    
    if WAKE_WORD in text_lower:
        print(f"{Fore.CYAN}[ACTIVATED] Wake word detected!{Style.RESET_ALL}")
        
        # 1. Hapus kata "kevin" (pakai regex biar case insensitive & rapi)
        # \b artinya batas kata, jadi "kevin" kena, tapi "kevinspace" nggak.
        clean_text = re.sub(r'\bkevin\b', '', text, flags=re.IGNORECASE)
        
        # 2. Bersihkan tanda baca sisa di awal/akhir kalimat
        # Contoh: "Kevin, what time?" -> ", what time?" -> "what time?"
        clean_text = clean_text.strip().lstrip(",").lstrip(".").lstrip("!").strip()
        
        # 3. Kalau user cuma panggil "Kevin" doang tanpa perintah
        if not clean_text:
            return "Hello, I am here." 
            
        return clean_text
        
    return None

async def main():
    print(f"{Style.BRIGHT}--- KEVIN AI (WAKE WORD: 'KEVIN') ONLINE ---{Style.RESET_ALL}")
    await speak("System ready. Just say my name, Boss.")

    try:
        while True:
            # 1. Dengar Semua Suara
            raw_input = listen()
            
            if raw_input:
                # 2. Cek Exit Command (Prioritas)
                if "stop program" in raw_input.lower():
                    await speak("Shutting down. See ya.")
                    break

                # 3. Filter Wake Word
                cleaned_input = process_wake_word(raw_input)

                if cleaned_input:
                    # 4. Kalau Lolos Filter -> Mikir & Jawab
                    response = await think(cleaned_input)
                    await speak(response)
                else:
                    # Log Ignore
                    pass # Diem aja, gak usah print apa-apa biar bersih

            await asyncio.sleep(0.1)

    except KeyboardInterrupt:
        print("\nForce Shutdown.")
        if os.path.exists(TEMP_INPUT_FILE): os.remove(TEMP_INPUT_FILE)
        if os.path.exists(TEMP_OUTPUT_FILE): os.remove(TEMP_OUTPUT_FILE)

if __name__ == "__main__":
    asyncio.run(main())