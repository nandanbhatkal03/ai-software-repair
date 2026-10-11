# NOTE: deliberately not named logging.py (would shadow the stdlib module when run from this dir).
import logging

def get_logger(name: str) -> logging.Logger:
    root = logging.getLogger("aisr")
    if not root.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(h)
        root.setLevel(logging.INFO)
    return logging.getLogger(f"aisr.{name}")
