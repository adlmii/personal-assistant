import asyncio
import os
import speech_recognition as sr
from groq import Groq
from dotenv import load_dotenv
import edge_tts
import pygame
from colorama import init, Fore, Style

# --- SETUP AWAL ---
init() # Colorama
load_dotenv() # Load API Key

# Setup Client Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Setup Pygame mixer
pygame.mixer.init()

# File path sementara
TEMP_INPUT_FILE = "temp_input.wav"
TEMP_OUTPUT_FILE = "temp_output.mp3"

def listen():
    """
    Mendengarkan suara user dan transkrip pakai Groq Whisper-Large-V3
    """
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300 
    recognizer.dynamic_energy_threshold = True

    with sr.Microphone() as source:
        print(f"\n{Fore.CYAN}[LISTENING] Silakan bicara...{Style.RESET_ALL}")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        try:
            # Rekam suara
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            print(f"{Fore.YELLOW}[PROCESS] Mengirim audio ke Groq Whisper...{Style.RESET_ALL}")
            
            # Simpan file sementara
            with open(TEMP_INPUT_FILE, "wb") as f:
                f.write(audio.get_wav_data())

            # --- BAGIAN YG DIUPDATE: Pake model whisper-large-v3 ---
            with open(TEMP_INPUT_FILE, "rb") as file_obj:
                transcription = client.audio.transcriptions.create(
                    file=(TEMP_INPUT_FILE, file_obj.read()),
                    model="whisper-large-v3",  # <-- Model baru yang stabil
                    response_format="text",
                    language="en" # Opsional: paksa inggris biar lebih akurat
                )
            # -------------------------------------------------------
            
            text_result = transcription.strip()
            print(f"{Fore.GREEN}[USER] {text_result}{Style.RESET_ALL}")
            return text_result

        except sr.WaitTimeoutError:
            print(f"{Fore.RED}[TIMEOUT] Tidak ada suara.{Style.RESET_ALL}")
            return None
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Masalah Mic/API: {e}{Style.RESET_ALL}")
            return None

async def speak(text):
    """
    Text-to-Speech pakai Edge-TTS
    """
    if not text:
        return

    print(f"{Fore.BLUE}[KEVIN] {text}{Style.RESET_ALL}")
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
        print(f"{Fore.RED}[ERROR] Gagal memutar suara: {e}{Style.RESET_ALL}")

async def main():
    print(f"{Style.BRIGHT}--- ECHO TEST STARTED (Ctrl+C untuk stop) ---{Style.RESET_ALL}")
    
    await speak("System updated. Connection to Whisper V3 established.")

    try:
        while True:
            user_text = listen()
            
            if user_text:
                # Echo: Ulangi apa yang user katakan
                await speak(f"You said: {user_text}")
                
            await asyncio.sleep(0.5)

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Program dihentikan.{Style.RESET_ALL}")
        # Bersihkan file sampah
        if os.path.exists(TEMP_INPUT_FILE): os.remove(TEMP_INPUT_FILE)
        if os.path.exists(TEMP_OUTPUT_FILE): os.remove(TEMP_OUTPUT_FILE)

if __name__ == "__main__":
    asyncio.run(main())