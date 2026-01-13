import arabic_reshaper
from bidi.algorithm import get_display


def fix_arabic_for_terminal(text: str) -> str:
    try:
        reshaped = arabic_reshaper.reshape(text)
        return str(get_display(reshaped))
    except Exception as e:
        print(f"[warn] Arabic reshaping failed, using raw text. Error: {e}")
        return text
