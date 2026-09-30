from collections.abc import Callable

from tokenizers import Tokenizer

from src.config import WHISPER_TOKENIZER


def load_token_counter() -> Callable[[str], int]:
    """Return a function that counts tokens the way Whisper does when it reads a prompt."""
    tokenizer = Tokenizer.from_pretrained(WHISPER_TOKENIZER)

    def count_tokens(text: str) -> int:
        return len(tokenizer.encode(text, add_special_tokens=False).ids)

    return count_tokens
