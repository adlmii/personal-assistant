import time
from colorama import Fore, Style
from AppOpener import open as open_app
from AppOpener import close as close_app
from context_manager import get_active_window

# Dictionary global untuk menyimpan mapping "nama_action" -> "fungsi"
ACTIONS = {}

def register_skill(action_name):
    """
    Decorator ajaib. Cukup tempel @register_skill('nama') di atas fungsi,
    maka fungsi itu otomatis masuk ke daftar kemampuan Kevin.
    """
    def decorator(func):
        ACTIONS[action_name] = func
        return func
    return decorator

class SkillDispatcher:
    def __init__(self, pc_controller):
        # Kita butuh akses ke PC Controller untuk aksi media/ngetik
        self.pc_controller = pc_controller

    def execute(self, data):
        """
        Mencari fungsi yang cocok di registry dan menjalankannya.
        """
        action = data.get("action")
        
        if action in ACTIONS:
            print(f"{Fore.CYAN}[SKILL] Executing skill: {action}{Style.RESET_ALL}")
            # Panggil fungsi yang terdaftar
            # Kita kirim 'self' (dispatcher) agar fungsi bisa akses pc_controller
            return ACTIONS[action](self, data)
        else:
            print(f"{Fore.RED}[ERROR] Skill '{action}' not found in registry.{Style.RESET_ALL}")

# --- DEFINISI SKILLS (MODULAR) ---

@register_skill("open")
def handle_open(dispatcher, data):
    target = data.get("target")
    # match_closest=True biar kalau typo dikit tetap kebuka
    open_app(target, match_closest=True, output=False)
    time.sleep(1) # Beri waktu app loading

@register_skill("close")
def handle_close(dispatcher, data):
    target = data.get("target")
    close_app(target, match_closest=True, output=False)

@register_skill("system")
def handle_system(dispatcher, data):
    target = str(data.get("target")).lower()
    if "shutdown" in target:
        print(f"{Fore.RED}[SYSTEM] Shutdown sequence initiated...{Style.RESET_ALL}")
        # os.system("shutdown /s /t 10") # Uncomment untuk real shutdown

@register_skill("media")
def handle_media(dispatcher, data):
    # Delegate ke module PC Control yang sudah kita buat sebelumnya
    dispatcher.pc_controller.execute_action("media", data)

@register_skill("type")
def handle_type(dispatcher, data):
    # Ambil context window saat ini untuk smart typing
    current_window = get_active_window()
    dispatcher.pc_controller.execute_action("type", data, current_window)

@register_skill("scroll")
def handle_scroll(dispatcher, data):
    dispatcher.pc_controller.execute_action("scroll", data)

@register_skill("press")
def handle_press(dispatcher, data):
    dispatcher.pc_controller.execute_action("press", data)