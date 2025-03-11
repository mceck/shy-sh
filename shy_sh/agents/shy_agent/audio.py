import os
from shy_sh.settings import settings


def capture_prompt():
    import speech_recognition as sr

    r = sr.Recognizer()
    r.energy_threshold = 4000
    r.pause_threshold = 1.5
    r.phrase_threshold = 1.5
    with sr.Microphone() as source:
        audio = r.listen(source, timeout=5)

    try:
        os.environ["GROQ_API_KEY"] = (
            os.environ.get("GROQ_API_KEY") or settings.llm.api_key
        )
        return r.recognize_groq(audio)
    except Exception:
        return ""
