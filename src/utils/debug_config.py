"""
Debug configuration utility module.
Provides global access to debug mode settings.
"""

# Global debug flag
DEBUG_MODE = False

def set_debug_mode(enabled: bool):
    """Set the global debug mode flag."""
    global DEBUG_MODE
    DEBUG_MODE = enabled

def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return DEBUG_MODE

def debug_log(message: str, logger, level=1):
    """Log a message only if debug mode is enabled."""
    if DEBUG_MODE:
        logger.log(message, level=level) 