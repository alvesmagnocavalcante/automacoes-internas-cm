"""Normalização textual compartilhada pela leitura e pelas regras de negócio."""

from __future__ import annotations

import unicodedata


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return (
        "".join(character for character in text if not unicodedata.combining(character))
        .casefold()
        .strip()
    )
