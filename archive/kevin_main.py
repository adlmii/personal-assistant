import asyncio
import os
import speech_recognition as sr
from groq import Groq, AsyncGroq # Kita pakai dua jenis client
from dotenv import load_dotenv
import edge_tts
import pygame
from colorama import init, Fore, Style

# --- SETUP AWAL ---
init()
load_dotenv()

# 1. Client Sync untuk Whisper (Audio Processing)
client_whisper = Groq(api_key=os.getenv("GROQ_API_KEY"))

# 2. Client Async untuk Chat/Otak (Llama 3.3)
client_chat = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

# Setup Audio
pygame.mixer.init()
TEMP_INPUT_FILE = "temp_input.wav"
TEMP_OUTPUT_FILE = "temp_output.mp3"

# --- PERSONA KEVIN (MODE JARVIS) ---
SYSTEM_PROMPT = """
Kamu adalah Kevin, sebuah asisten AI yang sangat cerdas, efisien, dan setia (mirip J.A.R.V.I.S).
Kepribadian:
- Gaya bicara: Formal, sopan, elegan, dan sedikit 'witty' (cerdas/humoris tipis).
- Panggil user dengan sebutan "Sir" (Tuan) atau "Boss".
- Jangan gunakan bahasa gaul/slang. Gunakan Bahasa Indonesia yang baku namun natural (tidak kaku seperti robot).
- Fokus utama: Melayani user dengan kecepatan tinggi dan akurasi maksimal.
- Jika user bertanya, jawab dengan ringkas (maksimal 2-3 kalimat) kecuali diminta penjelasan detail.
- Jika diminta melakukan coding, berikan solusi terbaik dengan sikap profesional.

Contoh Respon:
- "Sistem siap, Sir. Apa yang perlu kita kerjakan hari ini?"
- "Sedang memproses data tersebut. Mohon tunggu sebentar."
- "Tampaknya ada kesalahan pada syntax di baris 10, Sir. Saya sarankan perbaikan berikut."
"""

# Memori Percakapan (Context Window)
conversation_history = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

def listen():
    """
    Mendengarkan suara user -> Kirim ke Whisper
    """
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300 
    recognizer.dynamic_energy_threshold = True

    with sr.Microphone() as source:
        print(f"\n{Fore.CYAN}[LISTENING] Mic on...{Style.RESET_ALL}")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            print(f"{Fore.YELLOW}[WHISPER] Processing audio...{Style.RESET_ALL}")
            
            with open(TEMP_INPUT_FILE, "wb") as f:
                f.write(audio.get_wav_data())

            with open(TEMP_INPUT_FILE, "rb") as file_obj:
                transcription = client_whisper.audio.transcriptions.create(
                    file=(TEMP_INPUT_FILE, file_obj.read()),
                    model="whisper-large-v3",
                    response_format="text",
                    language="en"
                )
            
            text_result = transcription.strip()
            print(f"{Fore.GREEN}[YOU] {text_result}{Style.RESET_ALL}")
            return text_result

        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Mic issue: {e}{Style.RESET_ALL}")
            return None

async def think(user_text):
    """
    Mengirim teks user ke Llama 3.3 (Brain)
    """
    print(f"{Fore.MAGENTA}[THINKING] Kevin is typing...{Style.RESET_ALL}")
    
    # Masukkan input user ke memori
    conversation_history.append({"role": "user", "content": user_text})
    
    try:
        completion = await client_chat.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=conversation_history,
            temperature=0.7, # Kreatif tapi terkontrol
            max_tokens=200,  # Batasi biar gak ngoceh kepanjangan
        )
        
        response_text = completion.choices[0].message.content
        
        # Masukkan jawaban Kevin ke memori
        conversation_history.append({"role": "assistant", "content": response_text})
        
        return response_text
    
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Brain freeze: {e}{Style.RESET_ALL}")
        return "Sorry Bro, otak gw lagi disconnect nih. Cek koneksi lo."

async def speak(text):
    """
    Output Suara Kevin
    """
    if not text: return

    print(f"{Fore.BLUE}[KEVIN] {text}{Style.RESET_ALL}")
    
    # Suara Cowok Casual
    VOICE = "en-US-ChristopherNeural" 
    
    try:
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(TEMP_OUTPUT_FILE)

        pygame.mixer.music.load(TEMP_OUTPUT_FILE)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
            
        pygame.mixer.music.unload()

    except Exception as e:
        print(f"{Fore.RED}[ERROR] TTS Fail: {e}{Style.RESET_ALL}")

async def main():
    print(f"{Style.BRIGHT}--- KEVIN AI IS ONLINE (Ctrl+C to Exit) ---{Style.RESET_ALL}")
    
    # Sapaan pembuka
    opening = "Yo Boss, Kevin is online. System normal. What are we building today?"
    await speak(opening)

    try:
        while True:
            # 1. Listen (Dengar)
            user_input = listen()
            
            # 2. Think (Mikir) & 3. Speak (Jawab)
            if user_input:
                # Cek command buat exit
                if "stop" in user_input.lower() or "exit" in user_input.lower():
                    await speak("Alright, shutting down. Catch you later, Bro.")
                    break
                
                response = await think(user_input)
                await speak(response)
            
            # Istirahat dikit biar CPU gak panas
            await asyncio.sleep(0.2)

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Force shutdown initiated.{Style.RESET_ALL}")
        if os.path.exists(TEMP_INPUT_FILE): os.remove(TEMP_INPUT_FILE)
        if os.path.exists(TEMP_OUTPUT_FILE): os.remove(TEMP_OUTPUT_FILE)

if __name__ == "__main__":
    asyncio.run(main())