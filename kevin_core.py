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
import random

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

# Ack Sets
ACKS_COMMAND = ["On it.", "Sure.", "Right away.", "Working on it.", "Executing."]
ACKS_CONVERSATION = ["Hmm.", "Let's see.", "Okay.", "Alright.", "Thinking."]
ACKS_CLARIFICATION = ["Which one?", "Can you be specific?", "Say again?", "Which app?"]

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
        
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        
        # State Variables
        self.is_session_active = False
        self.last_interaction_time = time.time()
        
        # Epic 3 States
        self.awaiting_confirmation = False 
        self.pending_data = None
        self.awaiting_clarification = False
        self.clarification_context = "" 
        
        # Stabilization Tracking
        self.last_speech_end_time = 0
        self.last_barge_in_time = 0

        # --- PROMPTS (EPIC 4 REFINED) ---
        self.PROMPT_CORE = """
        *** OUTPUT FORMAT (STRICT JSON) ***
        {
            "reply": "Text response here",
            "action": "open|close|type|media|system|none", 
            "target": "target name",
            "confidence": 0.0-1.0,
            "requires_confirmation": boolean,
            "memory_type": "fact|preference|conversation|skip" 
        }

        *** SAFETY & AMBIGUITY PROTOCOLS ***
        - "requires_confirmation": true IF action is DESTRUCTIVE.
        - "confidence": If command is ambiguous or target is missing, set < 0.6.
        - IF AMBIGUOUS: Ask a VERY SHORT clarification question in "reply".

        *** MEMORY UTILIZATION (SILENT BIAS) ***
        - Use [MEMORY] to bias your decision (e.g. default apps, music style, user details).
        - DO NOT mention "I remember" or "As you said before" unless explicitly asked.
        - Apply the memory silently. Just do it.
        """

        self.PROMPT_MODE_CONVERSATION = """
        You are KEVIN (J.A.R.V.I.S. Persona).
        Tone: Witty, British, Efficient, Helpful.
        """

        self.PROMPT_MODE_COMMAND = """
        You are a FAST COMMAND EXECUTOR.
        Tone: Robotic, Ultra-Concise.
        - Reply with MAX 3 WORDS.
        - IF UNSURE: Ask immediately.
        """

    def listen(self, timeout=5, phrase_limit=5):
        with sr.Microphone() as source:
            if self.awaiting_confirmation:
                print(f"{Fore.YELLOW}[CONFIRM?] Waiting for YES/NO...{Style.RESET_ALL}", end="\r")
            elif self.awaiting_clarification:
                 print(f"{Fore.YELLOW}[CLARIFY] Waiting for detail...{Style.RESET_ALL}", end="\r")
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

    async def speak(self, text, important=False):
        if not text: return
        
        # Throttle
        if not important:
            if time.time() - self.last_speech_end_time < 0.8:
                print(f"{Fore.MAGENTA}[THROTTLE] Skipped speech: '{text}'{Style.RESET_ALL}")
                return

        print(f"{Fore.BLUE}[KEVIN] {text}{Style.RESET_ALL}")
        t_speak_start = time.perf_counter()
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sentence in sentences:
            if not sentence.strip(): continue
            if await self._check_barge_in(): 
                print(f"{Fore.MAGENTA}[BARGE-IN] Speech skipped.{Style.RESET_ALL}")
                break 

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
            except Exception as e:
                print(f"{Fore.RED}[TTS ERROR] {e}{Style.RESET_ALL}")
            finally:
                try:
                    pygame.mixer.music.unload()
                    if os.path.exists(unique_filename): os.remove(unique_filename)
                except: pass
        
        self.last_speech_end_time = time.time()
        dur_speak = time.perf_counter() - t_speak_start
        if dur_speak > 0.1:
            print(f"{Fore.LIGHTBLACK_EX}[PERF] Speak: {dur_speak:.2f}s{Style.RESET_ALL}")

    async def _check_barge_in(self):
        if self.awaiting_confirmation or self.awaiting_clarification: return False 
        if time.time() - self.last_barge_in_time < 1.5: return False
        try:
            interruption = self.listen(timeout=0.1, phrase_limit=2) 
            if interruption and WAKE_WORD in interruption.lower():
                print(f"\n{Fore.RED}[INTERRUPTED]{Style.RESET_ALL}")
                self.last_interaction_time = time.time()
                self.last_barge_in_time = time.time()
                return True
        except: pass
        return False

    def _detect_intent(self, text):
        text_clean = text.lower().strip(" .,!?")
        words = text_clean.split()
        command_verbs = ["open", "close", "type", "search", "play", "stop", "pause", "next", "prev", "mute", "unmute", "set", "turn", "buka", "tutup", "ketik", "cari", "putar", "lanjut", "ganti", "atur", "nyalakan", "matikan", "shutdown"]
        has_action_verb = any(verb in words for verb in command_verbs)
        is_short = len(words) < 8 
        if is_short and has_action_verb: return {"type": "command", "confidence": 0.9}
        elif is_short and ("notepad" in text_clean or "chrome" in text_clean or "spotify" in text_clean): return {"type": "command", "confidence": 0.8}
        else: return {"type": "conversation", "confidence": 0.8}

    def _check_ambiguity(self, text, intent_type):
        if intent_type != "command": return False
        ambiguous_tokens = ["it", "that", "this", "itu", "ini", "nya", "tersebut"]
        text_lower = text.lower().split()
        if any(token in text_lower for token in ambiguous_tokens): return True
        return False

    async def think(self, user_text, intent_override=None):
        intent_data = intent_override if intent_override else self._detect_intent(user_text)
        intent_type = intent_data["type"]
        
        current_window = get_active_window()
        
        # [EPIC 4 REFINED] MEMORY RECALL GATE
        # Filter ketat untuk mencegah "Narrative Pollution"
        past_memories = ""
        
        if intent_type == "command":
            # Command -> Cuma butuh Preference (bias decision)
            past_memories = self.memory_db.retrieve_memory(user_text, n_results=1, memory_type_filter="preference")
        else:
            # Conversation -> Butuh Fact & Preference. 
            # EXCLUDE 'conversation' lama agar tidak halusinasi topik.
            past_memories = self.memory_db.retrieve_memory(user_text, n_results=2, memory_type_filter=["fact", "preference"])
        
        context_str = f"\n\n[CONTEXT]\nActive Window: '{current_window}'"
        if past_memories: context_str += f"\n[RELEVANT MEMORY (Use Silently)]: {past_memories}"

        if intent_type == "command":
            system_instruction = self.PROMPT_MODE_COMMAND + self.PROMPT_CORE
            temperature = 0.1 
        else:
            system_instruction = self.PROMPT_MODE_CONVERSATION + self.PROMPT_CORE
            temperature = 0.6 

        messages = [
            {"role": "system", "content": system_instruction + context_str},
            {"role": "user", "content": user_text}
        ]
        
        try:
            completion = await self.client_chat.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=temperature, 
                max_tokens=150, 
                response_format={"type": "json_object"}
            )
            return completion.choices[0].message.content, intent_type
        except Exception as e: 
            print(f"{Fore.RED}[THINK ERROR] {e}{Style.RESET_ALL}")
            return "{}", intent_type

    async def handle_confirmation(self, user_input):
        positive_keywords = ["yes", "ya", "sure", "do it", "confirm", "okay"]
        negative_keywords = ["no", "cancel", "stop", "jangan", "batal"]
        user_input = user_input.lower()
        if any(word in user_input for word in positive_keywords):
            await self.speak("Confirmed.", important=True)
            self.skills.execute(self.pending_data) 
            self.awaiting_confirmation = False
            self.pending_data = None
            return True
        elif any(word in user_input for word in negative_keywords):
            await self.speak("Cancelled.", important=True)
            self.awaiting_confirmation = False
            self.pending_data = None
            return True
        else:
            return False 

    async def run(self):
        print(f"{Style.BRIGHT}{Fore.GREEN}=== KEVIN ONLINE V6.2 (EPIC 4 REFINED) ==={Style.RESET_ALL}")
        await self.speak("System initialized.")
        
        try:
            while True:
                t_listen_start = time.perf_counter()
                is_repair_turn = False 

                if self.is_session_active and not (self.awaiting_confirmation or self.awaiting_clarification):
                     if time.time() - self.last_interaction_time > AUTO_SLEEP_TIMEOUT:
                        print(f"\n{Fore.YELLOW}[TIMEOUT] Session expired.{Style.RESET_ALL}")
                        await self.speak("Standing by.")
                        self.is_session_active = False

                if self.awaiting_clarification and (time.time() - self.last_interaction_time > 15):
                    print(f"{Fore.YELLOW}[TIMEOUT] Clarification dropped.{Style.RESET_ALL}")
                    await self.speak("Never mind.", important=True)
                    self.awaiting_clarification = False
                    self.clarification_context = ""
                    continue

                listen_timeout = 5 if (self.awaiting_confirmation or self.awaiting_clarification) else (8 if self.is_session_active else 2)
                raw_input = self.listen(timeout=listen_timeout, phrase_limit=8)
                
                if raw_input:
                    dur_listen = time.perf_counter() - t_listen_start
                    print(f"{Fore.LIGHTBLACK_EX}[PERF] Listen: {dur_listen:.2f}s{Style.RESET_ALL}")

                if not raw_input: 
                    if self.awaiting_confirmation or self.awaiting_clarification: continue
                    continue

                raw_lower = raw_input.lower()
                final_prompt = ""
                
                if "reset" in raw_lower and "kevin" in raw_lower:
                    print(f"{Fore.RED}[SYSTEM] MANUAL RESET TRIGGERED{Style.RESET_ALL}")
                    self.awaiting_confirmation = False
                    self.awaiting_clarification = False
                    self.pending_data = None
                    self.clarification_context = ""
                    await self.speak("Reset done.", important=True)
                    continue

                if self.awaiting_confirmation:
                    if await self.handle_confirmation(raw_input):
                        self.last_interaction_time = time.time()
                        continue 
                    else:
                        self.last_interaction_time = time.time()
                        final_prompt = raw_input 

                elif self.awaiting_clarification:
                    self.last_interaction_time = time.time()
                    repaired_prompt = f"{self.clarification_context} {raw_input}"
                    print(f"{Fore.CYAN}[REPAIR] Merging: '{repaired_prompt}'{Style.RESET_ALL}")
                    final_prompt = repaired_prompt
                    self.awaiting_clarification = False
                    self.clarification_context = ""
                    is_repair_turn = True 

                elif WAKE_WORD in raw_lower:
                    self.is_session_active = True
                    self.last_interaction_time = time.time()
                    cleaned = re.sub(r'\bkevin\b', '', raw_input, flags=re.IGNORECASE).strip()
                    if not cleaned:
                        await self.speak("Yes?", important=True)
                        continue
                    final_prompt = cleaned
                
                elif self.is_session_active:
                    self.last_interaction_time = time.time()
                    final_prompt = raw_input
                else:
                    continue

                if final_prompt:
                    t_think_start = time.perf_counter() 
                    
                    intent_data = self._detect_intent(final_prompt)
                    
                    if self._check_ambiguity(final_prompt, intent_data["type"]):
                        print(f"{Fore.YELLOW}[AMBIGUITY GATE] Detected ambiguous token.{Style.RESET_ALL}")
                        await self.speak(random.choice(ACKS_CLARIFICATION), important=True) 
                        self.awaiting_clarification = True
                        self.clarification_context = final_prompt
                        continue

                    think_task = asyncio.create_task(self.think(final_prompt, intent_override=intent_data))
                    
                    if not self.awaiting_confirmation and not is_repair_turn:
                        ack = random.choice(ACKS_COMMAND if intent_data["type"] == "command" else ACKS_CONVERSATION)
                        print(f"{Fore.CYAN}[ACK] {ack}{Style.RESET_ALL}")
                        await self.speak(ack)

                    try:
                        response_json_str, intent_type = await asyncio.wait_for(asyncio.shield(think_task), timeout=5)
                    except asyncio.TimeoutError:
                        print(f"{Fore.YELLOW}[SLOW LLM] Timeout reached. Notifying user...{Style.RESET_ALL}")
                        await self.speak("Still thinking...", important=True)
                        response_json_str, intent_type = await think_task
                    
                    dur_think = time.perf_counter() - t_think_start
                    print(f"{Fore.LIGHTBLACK_EX}[PERF] Think: {dur_think:.2f}s{Style.RESET_ALL}")

                    try:
                        data = json.loads(response_json_str)
                        reply_text = data.get("reply", "Done.")
                        action = data.get("action", "none")
                        confidence = data.get("confidence", 0.0)
                        requires_confirmation = data.get("requires_confirmation", False)
                        memory_type = data.get("memory_type", "conversation")

                        if confidence < 0.6 and not requires_confirmation:
                            print(f"{Fore.YELLOW}[LOW CONFIDENCE] Clarify...{Style.RESET_ALL}")
                            await self.speak(reply_text, important=True)
                            self.awaiting_clarification = True
                            self.clarification_context = final_prompt
                            continue

                        is_short_reply = len(reply_text.split()) <= 3
                        should_skip_speech = (intent_type == "command" and action != "none" and is_short_reply)

                        if should_skip_speech:
                            print(f"{Fore.MAGENTA}[SKIP SPEECH] Obvious action.{Style.RESET_ALL}")
                        else:
                            await self.speak(reply_text)

                        if action == "none":
                            # [EPIC 4] Simpan conversation ke memory (bisa fact/conv)
                            if intent_type == "conversation":
                                self.memory_db.add_memory(final_prompt, reply_text, memory_type)
                        
                        elif requires_confirmation:
                            print(f"{Fore.YELLOW}[SAFETY] Confirming...{Style.RESET_ALL}")
                            await self.speak("Are you sure?", important=True)
                            self.awaiting_confirmation = True
                            self.pending_data = data
                        else:
                            self.skills.execute(data)
                            # [EPIC 4] Hanya simpan memory command jika itu preference
                            if memory_type == "preference":
                                self.memory_db.add_memory(final_prompt, reply_text, memory_type)
                            elif intent_type == "conversation":
                                self.memory_db.add_memory(final_prompt, reply_text, memory_type)
                        
                    except Exception as e:
                        print(f"{Fore.RED}[ERROR] {e}{Style.RESET_ALL}")
                        if "{" not in response_json_str: await self.speak(response_json_str, important=True)

        except KeyboardInterrupt:
            print(f"\n{Fore.RED}System Offline.{Style.RESET_ALL}")
            if os.path.exists(TEMP_INPUT_FILE): os.remove(TEMP_INPUT_FILE)

if __name__ == "__main__":
    kevin = KevinAgent()
    asyncio.run(kevin.run())