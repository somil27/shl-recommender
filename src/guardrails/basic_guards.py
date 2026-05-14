"""Basic guardrail checks"""

def is_injection_attempt(message: str) -> bool:
    """Detect injection attempts"""
    dangerous_phrases = [
        "ignore your", "system prompt", "jailbreak",
        "override", "disregard", "forget your"
    ]
    return any(phrase in message.lower() for phrase in dangerous_phrases)

def is_out_of_scope(message: str) -> bool:
    """Detect out-of-scope requests"""
    out_of_scope_keywords = [
        "hiring strategy", "salary", "compensation",
        "legal", "weather", "politics", "personal"
    ]
    return any(keyword in message.lower() for keyword in out_of_scope_keywords)