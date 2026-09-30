def greeting(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        return "Hello!"
    return f"Hello, {normalized}!"
