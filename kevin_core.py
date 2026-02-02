import asyncio
import os
import re
import json
import speech_recognition as sr
from groq import Groq, AsyncGroq
from dotenv import load_dotenv
import edge_tts
import pygame
from colorama import init, Fore, Style
import time
import uuid

# --- CUSTOM MODULES ---
from memory_core import MemoryManager 
from pc_control import PCControlManager
from context_manager import get_active_window
from skills_registry import SkillDispatcher 

# --- SETUP ---
init()
load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    print(f"{Fore.RED}[ERROR] GROQ_API_KEY tidak ditemukan!{Style.RESET_ALL}")
    exit()

WAKE_WORD = "kevin"
AUTO_SLEEP_TIMEOUT = 60
TEMP_INPUT_FILE = "temp_input.wav"

class KevinAgent:
    def __init__(self):
        # Clients
        self.client_whisper = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.client_chat = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        
        # Managers
        self.memory_db = MemoryManager()
        self.pc_controller = PCControlManager()
        self.skills = SkillDispatcher(self.pc_controller)
        
        # Audio Init
        pygame.mixer.init()
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        
        print(f"{Fore.YELLOW}[SYSTEM] Calibrating Microphone...{Style.RESET_ALL}")
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print(f"{Fore.GREEN}[SYSTEM] Calibration Complete.{Style.RESET_ALL}")
        
        # State Variables
        self.is_session_active = False
        self.last_interaction_time = time.time()
        self.awaiting_confirmation = False 
        self.pending_data = None           
        
        # --- [UPDATED] SYSTEM PROMPT V5 ---
        self.BASE_SYSTEM_PROMPT = """
        You are KEVIN (J.A.R.V.I.S. Persona).
        Tone: Witty, British, Efficient.

        *** 1. CONTEXT AWARENESS ***
        - Use [REAL-TIME CONTEXT] below to resolve "this", "here", or "it".

        *** 2. MEMORY PROTOCOLS (CLASSIFICATION) ***
        Classify the interaction into "memory_type":
        - "fact": User teaches you something (e.g., "My name is Budi", "I live in Jakarta").
        - "preference": User likes/dislikes (e.g., "I hate jazz", "Set volume to 50%").
        - "conversation": Meaningful discussion.
        - "skip": Short commands ("Open Chrome"), greetings ("Hi"), or confirmations ("Yes"). -> DO NOT SAVE.

        *** 3. RISK & SAFETY PROTOCOLS ***
        - "requires_confirmation": true IF action is DESTRUCTIVE (Shutdown, Close App, Delete).
        - "requires_confirmation": false IF action is SAFE (Open, Type, Play Music).
        - "confidence": 0.0 to 1.0. If < 0.5, I will ask for clarification.

        *** JSON OUTPUT FORMAT (STRICT) ***
        {
            "reply": "Response text",
            "action": "open|close|type|media|system|none", 
            "target": "target name",
            "confidence": 0.95,
            "requires_confirmation": false,
            "memory_type": "conversation" 
        }
        """

    def listen(self, timeout=5, phrase_limit=5):
        with sr.Microphone() as source:
            if self.awaiting_confirmation:
                print(f"{Fore.YELLOW}[CONFIRM?] Waiting for YES/NO...{Style.RESET_ALL}", end="\r")
            elif self.is_session_active:
                print(f"{Fore.GREEN}[LISTENING]...{Style.RESET_ALL}", end="\r")
            else:
                print(f"{Fore.BLACK}{Style.BRIGHT}[IDLE] Waiting...   {Style.RESET_ALL}", end="\r")
            
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
                with open(TEMP_INPUT_FILE, "wb") as f: f.write(audio.get_wav_data())
                with open(TEMP_INPUT_FILE, "rb") as file_obj:
                    transcription = self.client_whisper.audio.transcriptions.create(
                        file=(TEMP_INPUT_FILE, file_obj.read()),
                        model="whisper-large-v3",
                        response_format="text", language="id" 
                    )
                text = transcription.strip()
                if text: print(f"{Fore.LIGHTBLACK_EX}> Input: {text}{Style.RESET_ALL}")
                return text
            except Exception: return None

    async def speak(self, text):
        if not text: return
        print(f"{Fore.BLUE}[KEVIN] {text}{Style.RESET_ALL}")
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sentence in sentences:
            if not sentence.strip(): continue
            if await self._check_barge_in(): break
            unique_filename = f"tts_{uuid.uuid4().hex}.mp3"
            try:
                communicate = edge_tts.Communicate(sentence, "en-US-ChristopherNeural", rate="+10%")
                await communicate.save(unique_filename)
                pygame.mixer.music.load(unique_filename)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    if await self._check_barge_in(): 
                        pygame.mixer.music.stop()
                        return 
                    await asyncio.sleep(0.1)
                await asyncio.sleep(0.2) 
            except Exception: pass
            finally:
                try:
                    pygame.mixer.music.unload()
                    if os.path.exists(unique_filename): os.remove(unique_filename)
                except: pass

    async def _check_barge_in(self):
        if self.awaiting_confirmation: return False 
        interruption = self.listen(timeout=0.5, phrase_limit=2) 
        if interruption and WAKE_WORD in interruption.lower():
            print(f"\n{Fore.RED}[INTERRUPTED]{Style.RESET_ALL}")
            self.last_interaction_time = time.time()
            return True
        return False

    async def think(self, user_text):
        current_window = get_active_window()
        past_memories = self.memory_db.retrieve_memory(user_text, n_results=2)
        
        context_str = f"\n\n[REAL-TIME CONTEXT]\nUser Active Window: '{current_window}'"
        if past_memories: context_str += f"\nMemory: {past_memories}"

        messages = [
            {"role": "system", "content": self.BASE_SYSTEM_PROMPT + context_str},
            {"role": "user", "content": user_text}
        ]
        
        try:
            completion = await self.client_chat.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.1, max_tokens=250,
                response_format={"type": "json_object"}
            )
            return completion.choices[0].message.content
        except Exception: return "{}"

    async def handle_confirmation(self, user_input):
        positive_keywords = ["yes", "ya", "sure", "do it", "confirm", "okay"]
        negative_keywords = ["no", "cancel", "stop", "jangan", "batal"]
        user_input = user_input.lower()
        if any(word in user_input for word in positive_keywords):
            await self.speak("Confirmed. Executing.")
            self.skills.execute(self.pending_data) 
            self.awaiting_confirmation = False
            self.pending_data = None
            return True
        elif any(word in user_input for word in negative_keywords):
            await self.speak("Cancelled.")
            self.awaiting_confirmation = False
            self.pending_data = None
            return True
        else:
            return False 

    async def run(self):
        print(f"{Style.BRIGHT}{Fore.GREEN}=== KEVIN ONLINE V5 (SAFE & STRUCTURED) ==={Style.RESET_ALL}")
        await self.speak("Systems initialized. Safety protocols active.")
        
        try:
            while True:
                if self.is_session_active and not self.awaiting_confirmation and (time.time() - self.last_interaction_time > AUTO_SLEEP_TIMEOUT):
                    print(f"\n{Fore.YELLOW}[TIMEOUT] Session expired.{Style.RESET_ALL}")
                    await self.speak("Standing by.")
                    self.is_session_active = False

                listen_timeout = 5 if self.awaiting_confirmation else (8 if self.is_session_active else 2)
                raw_input = self.listen(timeout=listen_timeout, phrase_limit=8)

                if not raw_input: 
                    if self.awaiting_confirmation:
                        print(f"{Fore.RED}[TIMEOUT] Confirmation ignored.{Style.RESET_ALL}")
                        self.awaiting_confirmation = False
                        self.pending_data = None
                    continue

                raw_lower = raw_input.lower()
                final_prompt = ""

                if self.awaiting_confirmation:
                    if await self.handle_confirmation(raw_input):
                        self.last_interaction_time = time.time()
                        continue 
                    else:
                        self.last_interaction_time = time.time()
                        final_prompt = raw_input 

                elif WAKE_WORD in raw_lower:
                    self.is_session_active = True
                    self.last_interaction_time = time.time()
                    cleaned = re.sub(r'\bkevin\b', '', raw_input, flags=re.IGNORECASE).strip()
                    if not cleaned:
                        await self.speak("Yes, Sir?")
                        continue
                    final_prompt = cleaned
                
                elif self.is_session_active:
                    self.last_interaction_time = time.time()
                    final_prompt = raw_input
                else:
                    continue

                if final_prompt:
                    response_json_str = await self.think(final_prompt)
                    try:
                        data = json.loads(response_json_str)
                        reply_text = data.get("reply", "Done.")
                        action = data.get("action", "none")
                        confidence = data.get("confidence", 0.0)
                        requires_confirmation = data.get("requires_confirmation", False)
                        
                        # [FEATURE 13] Extract Memory Type
                        memory_type = data.get("memory_type", "conversation")

                        # 1. Low Confidence Check
                        if confidence < 0.5:
                            print(f"{Fore.RED}[LOW CONFIDENCE] {confidence}{Style.RESET_ALL}")
                            await self.speak("I'm unsure about that command, Sir.")
                            continue

                        await self.speak(reply_text)

                        if action == "none":
                            # Walaupun action none, tetap simpan memory jika itu fakta/chat
                            self.memory_db.add_memory(final_prompt, reply_text, memory_type)
                            continue

                        # 2. [FEATURE 11] Risk-Based Safety
                        if requires_confirmation:
                            print(f"{Fore.YELLOW}[SAFETY PROTOCOL] Confirmation required for: {action}{Style.RESET_ALL}")
                            await self.speak("This action requires confirmation. Proceed?")
                            self.awaiting_confirmation = True
                            self.pending_data = data
                        else:
                            self.skills.execute(data)
                            self.memory_db.add_memory(final_prompt, reply_text, memory_type)

                    except Exception as e:
                        print(f"{Fore.RED}[ERROR] {e}{Style.RESET_ALL}")
                        if "{" not in response_json_str: await self.speak(response_json_str)

        except KeyboardInterrupt:
            print(f"\n{Fore.RED}System Offline.{Style.RESET_ALL}")
            if os.path.exists(TEMP_INPUT_FILE): os.remove(TEMP_INPUT_FILE)

if __name__ == "__main__":
    kevin = KevinAgent()
    asyncio.run(kevin.run())