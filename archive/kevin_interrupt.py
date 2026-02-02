import asyncio
import os
import re
import json
import subprocess
import speech_recognition as sr
from groq import Groq, AsyncGroq
from dotenv import load_dotenv
import edge_tts
import pygame
from colorama import init, Fore, Style

# --- LIBRARY KHUSUS INTERUPSI ---
import pyaudio
import audioop

# --- 1. SETUP & CONFIGURATION ---
init()
load_dotenv()

client_whisper = Groq(api_key=os.getenv("GROQ_API_KEY"))
client_chat = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

pygame.mixer.init()
TEMP_INPUT_FILE = "temp_input.wav"
TEMP_OUTPUT_FILE = "temp_output.mp3"
WAKE_WORD = "kevin"

# --- CONFIG SENSITIVITAS MIC (PENTING DIATUR) ---
# Semakin KECIL angkanya = Semakin sensitif (dikit suara langsung stop)
# Semakin BESAR angkanya = Harus teriak baru stop
INTERRUPT_THRESHOLD = 2000 

# --- 2. SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are Kevin, a highly advanced AI interface modeled after J.A.R.V.I.S.
Your priority is efficiency, precision, and absolute loyalty to the User.

CORE PERSONALITY PROTOCOLS:
1. Address: Always address the user as "Boss".
2. Tone: Sophisticated, calm, ultra-professional, with a hint of dry wit.
3. Language: Process Indonesian/English input, BUT ALWAYS RESPOND IN ELEGANT ENGLISH.

SYSTEM CONTROL (JSON MANDATE):
If the user requests a system action, output STRICT JSON:
{
  "reply": "Short confirmation phrase",
  "action": "open/close/system",
  "target": "app_name_cleaned"
}

EXAMPLES:
User: "Buka Notepad."
Kevin: {"reply": "Initializing Notepad, Boss.", "action": "open", "target": "notepad"}
"""

conversation_history = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

# --- 3. EXECUTION LOGIC ---
def execute_command(action, target):
    print(f"{Fore.CYAN}[EXECUTING] Action: {action} | Target: {target}{Style.RESET_ALL}")
    try:
        if action == "open":
            if "notepad" in target.lower(): subprocess.Popen("notepad.exe")
            elif "calculator" in target.lower(): subprocess.Popen("calc.exe")
            elif "chrome" in target.lower(): os.system("start chrome")
            elif "spotify" in target.lower(): os.system("start spotify")
            else: os.system(f"start {target}")

        elif action == "close":
            os.system(f"taskkill /F /IM {target}.exe")

        elif action == "system":
            if "shutdown" in target.lower(): os.system("shutdown /s /t 10")
            elif "restart" in target.lower(): os.system("shutdown /r /t 10")
                
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Execution failed: {e}{Style.RESET_ALL}")

def clean_json_string(text):
    text = text.strip()
    if text.startswith("```json"): text = text.replace("```json", "").replace("```", "")
    elif text.startswith("```"): text = text.replace("```", "")
    return text.strip()

# --- 4. MAIN FUNCTIONS ---

def listen():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300 
    recognizer.dynamic_energy_threshold = True 
    recognizer.pause_threshold = 0.8

    with sr.Microphone() as source:
        print(f"\n{Fore.BLACK}{Style.BRIGHT}[STANDBY] Listening...{Style.RESET_ALL}")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
            
            with open(TEMP_INPUT_FILE, "wb") as f:
                f.write(audio.get_wav_data())

            KEYWORDS_PROMPT = "Kevin, Notepad, Chrome, Spotify, Calculator, Shutdown, Restart, Open, Close"

            with open(TEMP_INPUT_FILE, "rb") as file_obj:
                transcription = client_whisper.audio.transcriptions.create(
                    file=(TEMP_INPUT_FILE, file_obj.read()),
                    model="whisper-large-v3",
                    prompt=KEYWORDS_PROMPT, 
                    response_format="text",
                    task="translate" # Tetap translate ke English
                )
            
            text_result = transcription.strip()
            if text_result:
                print(f"{Fore.LIGHTBLACK_EX}[HEARD] '{text_result}'{Style.RESET_ALL}")
            return text_result

        except sr.WaitTimeoutError:
            return None 
        except Exception:
            return None

async def think(user_text):
    print(f"{Fore.MAGENTA}[THINKING] Processing...{Style.RESET_ALL}")
    conversation_history.append({"role": "user", "content": user_text})
    
    try:
        completion = await client_chat.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=conversation_history,
            temperature=0.3, 
            max_tokens=200,
        )
        response_text = completion.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": response_text})
        return response_text
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Brain Error: {e}{Style.RESET_ALL}")
        return "System error, Boss."

# --- UPDATE: FUNGSI SPEAK DENGAN INTERUPSI ---
async def speak(text):
    if not text: return
    print(f"{Fore.BLUE}[KEVIN] {text}{Style.RESET_ALL}")
    
    try:
        # 1. Generate Audio File
        communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural", rate="+10%", pitch="-5Hz")
        await communicate.save(TEMP_OUTPUT_FILE)
        
        # 2. Setup PyAudio buat 'Ngintip' Mic
        chunk = 1024
        p = pyaudio.PyAudio()
        stream = None
        
        try:
            # Buka mic stream
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=chunk)
        except Exception:
            print(f"{Fore.YELLOW}[WARN] Mic busy, interrupt feature disabled.{Style.RESET_ALL}")

        # 3. Play Audio Kevin
        pygame.mixer.music.load(TEMP_OUTPUT_FILE)
        pygame.mixer.music.play()
        
        print(f"{Fore.GREEN}>> Ngomong 'KEVIN!' untuk potong pembicaraan...{Style.RESET_ALL}")

        # 4. Loop: Putar suara sambil cek mic user
        while pygame.mixer.music.get_busy():
            if stream:
                try:
                    # Baca data suara dari mic
                    data = stream.read(chunk, exception_on_overflow=False)
                    # Hitung volume (RMS)
                    rms = audioop.rms(data, 2) 
                    
                    # LOGIC POTONG OMONGAN
                    if rms > INTERRUPT_THRESHOLD: 
                        print(f"\n{Fore.RED}[INTERRUPTED] User spoken! (RMS: {rms}){Style.RESET_ALL}")
                        pygame.mixer.music.stop() # Matikan suara Kevin
                        break # Keluar loop, langsung ke listen lagi
                except Exception:
                    pass
            
            await asyncio.sleep(0.05) # Cek tiap 0.05 detik biar enteng
            
        # Cleanup Resources
        if stream:
            stream.stop_stream()
            stream.close()
        p.terminate()
        pygame.mixer.music.unload()

    except Exception as e:
        print(f"Error speaking: {e}")

def process_wake_word(text):
    if not text: return None
    if WAKE_WORD in text.lower():
        print(f"{Fore.CYAN}[ACTIVATED] System Active.{Style.RESET_ALL}")
        clean = re.sub(r'\bkevin\b', '', text, flags=re.IGNORECASE)
        return clean.strip().lstrip(",.!").strip() or "Ready, Boss." 
    return None

# --- 5. MAIN LOOP ---
async def main():
    print(f"{Style.BRIGHT}{Fore.GREEN}=== KEVIN (INTERRUPT ENABLED) ONLINE ==={Style.RESET_ALL}")
    print(f"{Fore.YELLOW}NOTE: Gunakan Headset agar fitur interupsi berjalan optimal.{Style.RESET_ALL}")
    
    await speak("System initialized. I am ready, Boss.")

    try:
        while True:
            raw_input = listen()
            cleaned_input = process_wake_word(raw_input)

            if cleaned_input:
                response = await think(cleaned_input)

                if "{" in response and "}" in response:
                    try:
                        json_str = clean_json_string(response)
                        start_idx = json_str.find("{")
                        end_idx = json_str.rfind("}") + 1
                        valid_json_str = json_str[start_idx:end_idx]
                        
                        data = json.loads(valid_json_str)
                        await speak(data.get("reply", "Done."))
                        execute_command(data.get("action"), data.get("target"))

                    except json.JSONDecodeError:
                        await speak(response)
                else:
                    await speak(response)

            await asyncio.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[SYSTEM] Force Shutdown.")
        if os.path.exists(TEMP_INPUT_FILE): os.remove(TEMP_INPUT_FILE)
        if os.path.exists(TEMP_OUTPUT_FILE): os.remove(TEMP_OUTPUT_FILE)

if __name__ == "__main__":
    asyncio.run(main())