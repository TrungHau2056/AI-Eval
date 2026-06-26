from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent


@lru_cache(maxsize=None)
def _load(name: str) -> str:
    path = _PROMPTS_DIR / f"{name}.txt"
    text = path.read_text(encoding="utf-8")
    logger.debug("Loaded prompt template: %s (%d chars)", name, len(text))
    return text


def reload_prompts() -> None:
    """Clear the prompt cache so edited .txt files are picked up without restart."""
    _load.cache_clear()
    logger.info("Prompt cache cleared")


INTENT_SYSTEM = _load("intent_system")
INTENT_USER = _load("intent_user")

PERSONA_GENERATOR_SYSTEM = _load("persona_generator_system")
PERSONA_GENERATOR_USER = _load("persona_generator_user")
PERSONA_GENERATOR_REFINE_USER = _load("persona_generator_refine_user")

PERSONA_EVALUATOR_SYSTEM = _load("persona_evaluator_system")
PERSONA_EVALUATOR_USER = _load("persona_evaluator_user")

TESTCASE_SYSTEM = _load("testcase_system")
TESTCASE_USER = _load("testcase_user")
