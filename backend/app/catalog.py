ACTIVITIES = [
    {
        "id": "memory-match",
        "title": "Memory Match",
        "description": "Match two familiar objects.",
        "difficulty": 2,
    },
    {
        "id": "object-recall",
        "title": "Remember the Objects",
        "description": "Look, listen, then remember.",
        "difficulty": 2,
    },
    {
        "id": "pattern",
        "title": "Pattern Completion",
        "description": "Choose what comes next.",
        "difficulty": 2,
    },
]


LANGUAGE_CONFIG = [
    {
        "languageCode": "en-IN",
        "languageName": "English",
        "speechSupported": True,
        "ttsSupported": True,
        "ttsFallbackNote": None,
        "bhashinSupported": False,
        "bhashinNote": None,
    },
    {
        "languageCode": "as-IN",
        "languageName": "Assamese",
        "speechSupported": True,
        "ttsSupported": False,
        "ttsFallbackNote": "Voice guides will use English until an Assamese voice pack is installed.",
        "bhashinSupported": True,
        "bhashinNote": "Enhanced Assamese speech recognition is available via BHASHINI. Configure a BHASHINI API key to activate it.",
    },
    {
        "languageCode": "hi-IN",
        "languageName": "Hindi",
        "speechSupported": True,
        "ttsSupported": True,
        "ttsFallbackNote": None,
        "bhashinSupported": True,
        "bhashinNote": "Enhanced Hindi speech recognition is available via BHASHINI.",
    },
]
