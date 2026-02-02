import pygetwindow as gw

def get_active_window():
    """
    Returns the title of the currently active window.
    This function is SAFE and read-only.
    """
    try:
        window = gw.getActiveWindow()
        if window and window.title:
            return window.title
    except Exception:
        pass

    return "Unknown"