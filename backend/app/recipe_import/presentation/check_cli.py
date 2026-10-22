"""
Checks that the keys of the recipe import really work, without printing them:

    python -m app.recipe_import.presentation.check_cli                   # the model that reads the text
    python -m app.recipe_import.presentation.check_cli --url <video>     # and Supadata too (spends 2 credits)

Reads the same settings as the API (backend/.env). For Gemini it first lists the models the key can see
(free, no tokens) and says whether the configured model is among them, then makes one small real
extraction on a made-up caption. Provider errors are logged with their status code, never with the key.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import time

import httpx2

from app.recipe_import.domain.services.ports import ExtractionCatalog
from app.recipe_import.domain.source_url import parse_source_url
from app.recipe_import.domain.video_text import ImportUnavailableError, VideoText, VideoUnavailableError
from app.recipe_import.infrastructure.claude_recipe_extractor import ClaudeRecipeExtractor
from app.recipe_import.infrastructure.gemini_recipe_extractor import GeminiRecipeExtractor
from app.recipe_import.infrastructure.supadata_video_text_source import SupadataVideoTextSource
from app.shared.config.settings import get_settings

SAMPLE = VideoText(
    title="Brownies fudgy",
    description="Brownies de chocolate: 200 g de chocolate, 100 g de manteca, 3 huevos y 150 g de azúcar. "
    "Derrite el chocolate con la manteca, bate a mano con los huevos y el azúcar y hornea 25 minutos a 180 grados.",
    transcript=None,
    author="@check",
)
SAMPLE_CATALOG = ExtractionCatalog(
    ingredients=["Chocolate, chips", "Mantequilla / Manteca", "Huevo", "Azúcar blanca"],
    units=["g", "cup", "u"],
    equipment=["Batidor de globo", "Batidora de mano", "Horno", "Molde para tarta"],
    categories=["Tortas", "Brownies y barras", "Galletas"],
)


async def list_gemini_models(api_key: str) -> list[str] | None:
    async with httpx2.AsyncClient(timeout=20) as client:
        response = await client.get(
            "https://generativelanguage.googleapis.com/v1beta/models", params={"pageSize": 200}, headers={"x-goog-api-key": api_key}
        )
    if response.status_code != 200:
        print(f"  models list: HTTP {response.status_code}  {response.text[:200]}")
        return None
    return [model["name"].removeprefix("models/") for model in response.json().get("models", [])]


async def check_extractor() -> bool:
    settings = get_settings()
    print(f"Extractor: {settings.import_extractor}")
    if settings.import_extractor == "claude":
        if not settings.anthropic_api_key:
            print("  ANTHROPIC_API_KEY is not set in backend/.env")
            return False
        print(f"  key: set ({len(settings.anthropic_api_key)} characters), model: {settings.anthropic_model}")
        extractor = ClaudeRecipeExtractor(settings.anthropic_api_key, settings.anthropic_model)
    else:
        if not settings.gemini_api_key:
            print("  GEMINI_API_KEY is not set in backend/.env")
            return False
        print(f"  key: set ({len(settings.gemini_api_key)} characters), model: {settings.gemini_model}")
        models = await list_gemini_models(settings.gemini_api_key)
        if models is None:
            print("  The key cannot list models: it is wrong, restricted to another API, or its project is denied.")
            return False
        found = settings.gemini_model in models
        print(f"  the key sees {len(models)} models; configured model available: {'yes' if found else 'NO'}")
        if not found:
            print("  flash models it does see: " + ", ".join(sorted(name for name in models if "flash" in name)[:12]))
            print("  -> set GEMINI_MODEL to one of those.")
        extractor = GeminiRecipeExtractor(settings.gemini_api_key, settings.gemini_model)

    started = time.monotonic()
    try:
        recipe = await extractor.extract(SAMPLE, SAMPLE_CATALOG)
    except ImportUnavailableError:
        print("  extraction: FAILED (the line above or in the log has the status code)")
        return False
    print(f"  extraction: ok in {time.monotonic() - started:.1f}s — recipe={recipe.is_recipe}, {len(recipe.ingredients)} ingredients, {len(recipe.steps)} steps")
    for line in recipe.ingredients:
        print(f"    - {line.quantity or '?'} {line.unit or ''} {line.name}  (catalog: {line.catalog_name or '—'})")
    print(f"    category: {recipe.category or '—'}   equipment: {', '.join(recipe.equipment) or '—'}  (hand-beating should give the whisk and the oven)")
    return recipe.is_recipe and len(recipe.ingredients) >= 3


async def check_supadata(url: str) -> bool:
    settings = get_settings()
    print("Supadata")
    if not settings.supadata_api_key:
        print("  SUPADATA_API_KEY is not set in backend/.env")
        return False
    print(f"  key: set ({len(settings.supadata_api_key)} characters)")
    try:
        text = await SupadataVideoTextSource(settings.supadata_api_key, min_interval=settings.supadata_min_interval_seconds).fetch(parse_source_url(url))
    except VideoUnavailableError:
        print("  the video is private, removed or unreachable")
        return False
    except ImportUnavailableError:
        print("  FAILED (see the log line above for the status code)")
        return False
    print(f"  read: title {len(text.title or '')} chars, description {len(text.description or '')} chars, captions {len(text.transcript or '')} chars, author {text.author or '—'}")
    return text.is_enough


def main() -> None:
    parser = argparse.ArgumentParser(description="Check the recipe import keys without printing them.")
    parser.add_argument("--url", help="a TikTok / Reel link: also checks Supadata (spends 2 credits)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.ERROR, format="  log: %(message)s")

    async def run() -> bool:
        results = [await check_extractor()]
        if args.url:
            results.append(await check_supadata(args.url))
        return all(results)

    ok = asyncio.run(run())
    print("\nAll good." if ok else "\nSomething needs attention (see above).")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
