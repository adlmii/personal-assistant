import pyautogui
import time
from colorama import Fore, Style

class PCControlManager:
    def __init__(self):
        # Safety Fail-safe: Geser mouse ke pojok kiri atas untuk membatalkan script jika error
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        
        # --- DEFINISI PERILAKU APLIKASI (SMART TYPING) ---
        # Format: "kata_kunci_judul_window": ["tombol_1", "tombol_2"]
        # Ini adalah tombol yang ditekan SEBELUM mengetik text agar kursor pindah ke search bar.
        self.APP_BEHAVIORS = {
            "spotify": ["ctrl", "l"],       # Spotify: Ctrl+L masuk ke search bar
            "chrome": ["ctrl", "l"],        # Browser: Ctrl+L masuk ke address bar
            "edge": ["ctrl", "l"],          # Edge: Sama
            "firefox": ["ctrl", "l"],       # Firefox: Sama
            "discord": ["ctrl", "k"],       # Discord: Ctrl+K untuk Quick Switcher
            "youtube": ["/"],               # YouTube (di browser): tombol "/" untuk search
            "whatsapp": ["ctrl", "f"],      # WA Desktop: Ctrl+F cari chat
            "telegram": ["ctrl", "f"],      # Telegram: Ctrl+F cari
            "code": ["ctrl", "f"],          # VS Code: Ctrl+F Find
            "notion": ["ctrl", "p"],        # Notion: Search
        }
        
        print(f"{Fore.YELLOW}[SYSTEM] PC Control (Smart Typing) Module Loaded.{Style.RESET_ALL}")

    def execute_action(self, action_type: str, data: dict, active_window_title: str = ""):
        """
        Main Router untuk kontrol PC.
        Menerima parameter tambahan: active_window_title untuk konteks aplikasi.
        """
        try:
            if not isinstance(data, dict):
                return False

            # --- ACTION: MEDIA ---
            if action_type == "media":
                command = data.get("command")
                if command:
                    return self._handle_media(command)

            # --- ACTION: TYPE (SMART TYPING) ---
            elif action_type == "type":
                content = data.get("content", "").strip()
                if content:
                    print(f"{Fore.CYAN}[PC] Preparing to type in: '{active_window_title}'{Style.RESET_ALL}")
                    
                    # 1. Cek Pre-Typing Shortcut (Smart Context)
                    self._trigger_app_shortcut(active_window_title)
                    
                    # 2. Typing Process
                    print(f"{Fore.CYAN}[PC] Typing: '{content}'{Style.RESET_ALL}")
                    # Sedikit delay biar shortcut tereksekusi dulu
                    time.sleep(0.3) 
                    pyautogui.write(content, interval=0.05)
                    
                    # Opsional: Uncomment jika ingin otomatis Enter setelah ngetik
                    # pyautogui.press('enter') 

            # --- ACTION: PRESS ---
            elif action_type == "press":
                keys = data.get("keys", [])
                if isinstance(keys, list) and keys:
                    print(f"{Fore.CYAN}[PC] Pressing: {keys}{Style.RESET_ALL}")
                    pyautogui.hotkey(*keys)

            # --- ACTION: SCROLL ---
            elif action_type == "scroll":
                amount = int(data.get("amount", 0))
                pyautogui.scroll(amount)

            return True

        except pyautogui.FailSafeException:
            print(f"{Fore.RED}[EMERGENCY] PyAutoGUI Failsafe Triggered!{Style.RESET_ALL}")
            return False

        except Exception as e:
            print(f"{Fore.RED}[ERROR] PC Control: {e}{Style.RESET_ALL}")
            return False

    def _trigger_app_shortcut(self, window_title):
        """
        Mengecek apakah window aktif butuh tombol khusus sebelum mengetik.
        """
        if not window_title: return

        window_title_lower = window_title.lower()
        
        for app_keyword, keys in self.APP_BEHAVIORS.items():
            if app_keyword in window_title_lower:
                print(f"{Fore.MAGENTA}[SMART-CTX] Detected {app_keyword}. Pressing shortcut: {keys}{Style.RESET_ALL}")
                if len(keys) == 1:
                    pyautogui.press(keys[0])
                else:
                    pyautogui.hotkey(*keys)
                return

    def _handle_media(self, command: str):
        """
        Mapping perintah suara ke tombol keyboard media.
        """
        print(f"{Fore.GREEN}[MEDIA] Executing: {command}{Style.RESET_ALL}")
        
        mapping = {
            "play_pause": "playpause",
            "next": "nexttrack",
            "prev": "prevtrack",
            "volume_up": "volumeup",
            "volume_down": "volumedown",
            "mute": "volumemute"
        }
        
        key = mapping.get(command)
        if key:
            pyautogui.press(key)
            # Kadang volume butuh ditekan beberapa kali agar terasa,
            # tapi untuk sekarang kita set 1 kali saja.
            
        return True