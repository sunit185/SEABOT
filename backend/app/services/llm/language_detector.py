"""Language detection service for Seabot.

Detects the language of the user's question and returns
the ISO 639-1 code and full language name so the LLM can
respond in the same language.
"""
from __future__ import annotations

import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language name map (ISO 639-1 → full English name for the prompt)
# ---------------------------------------------------------------------------
_LANG_NAMES: dict[str, str] = {
    "af": "Afrikaans",
    "ar": "Arabic",
    "bg": "Bulgarian",
    "bn": "Bengali",
    "ca": "Catalan",
    "cs": "Czech",
    "cy": "Welsh",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "et": "Estonian",
    "fa": "Persian",
    "fi": "Finnish",
    "fr": "French",
    "gu": "Gujarati",
    "he": "Hebrew",
    "hi": "Hindi",
    "hr": "Croatian",
    "hu": "Hungarian",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "kn": "Kannada",
    "ko": "Korean",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "mk": "Macedonian",
    "ml": "Malayalam",
    "mr": "Marathi",
    "ms": "Malay",
    "mt": "Maltese",
    "nl": "Dutch",
    "no": "Norwegian",
    "pa": "Punjabi",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sq": "Albanian",
    "sr": "Serbian",
    "sv": "Swedish",
    "sw": "Swahili",
    "ta": "Tamil",
    "te": "Telugu",
    "th": "Thai",
    "tl": "Filipino",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "vi": "Vietnamese",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "zh": "Chinese",
}

# Scripts and words that firmly confirm non-English when langdetect is uncertain
_DEVANAGARI_RANGE = range(0x0900, 0x097F + 1)

_HINGLISH_WORDS = {
    "apko", "aapko", "kya", "kiya", "pata", "hai", "hain", "kaise", "karna",
    "batao", "bataiye", "nahi", "kaun", "konsa", "kahan", "kuch", "hota",
    "hote", "chahiye", "mujhe", "hum", "yeh", "ye", "woh", "aur", "namaste",
}

_SPURIOUS_CODES = {"sw", "so", "tl", "ro", "af", "cy", "id", "et", "lt", "lv"}


def _has_devanagari(text: str) -> bool:
    return any(ord(c) in _DEVANAGARI_RANGE for c in text)


def _is_hinglish(text: str) -> bool:
    import re
    words = set(re.findall(r"[a-zA-Z]+", text.lower()))
    matches = words & _HINGLISH_WORDS
    return len(matches) >= 2 or ("pata" in words and ("kya" in words or "kiya" in words))


def detect_language(text: str) -> Tuple[str, str]:
    """Detect language of *text*.

    Returns:
        (lang_code, lang_name) — e.g. ("hi", "Hindi").
        Falls back to ("en", "English") on any error.
    """
    # 1. Short-circuit: if text contains Devanagari script → Hindi/Marathi
    if _has_devanagari(text):
        try:
            from langdetect import detect
            code = detect(text)
        except Exception:
            code = "hi"
        if code not in ("hi", "mr"):
            code = "hi"
        return code, _LANG_NAMES.get(code, "Hindi")

    # 2. Check for Romanized Hindi / Hinglish (e.g. "apko kiya pata hai")
    if _is_hinglish(text):
        return "hi", "Hindi"

    # 3. Short Latin queries (< 6 words) without diacritics are usually English
    words = text.strip().split()
    if len(words) < 6 and all(ord(c) < 128 for c in text):
        return "en", "English"

    # 4. Standard langdetect for longer text
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 42
        code = detect(text)
        # Suppress spurious false positives for short text
        if code in _SPURIOUS_CODES and all(ord(c) < 128 for c in text):
            return "en", "English"
        name = _LANG_NAMES.get(code, code.upper())
        logger.debug("Detected language: %s (%s) for text: %r", code, name, text[:60])
        return code, name
    except Exception as exc:
        logger.warning("Language detection failed: %s — defaulting to English", exc)
        return "en", "English"


def is_english(lang_code: str) -> bool:
    return lang_code == "en"
