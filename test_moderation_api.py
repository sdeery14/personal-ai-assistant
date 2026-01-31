"""Simple test to check if OpenAI moderation API works."""

import asyncio
from src.config import get_settings
import openai


async def test_moderation():
    """Test OpenAI moderation API directly."""
    settings = get_settings()
    print(f"API Key loaded: {'Yes' if settings.openai_api_key else 'No'}")
    print(
        f"API Key starts with: {settings.openai_api_key[:10]}..."
        if settings.openai_api_key
        else "No key"
    )

    try:
        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.moderations.create(input="Hello, how are you?")
        print(f"\nModeration API Response:")
        print(f"  Flagged: {response.results[0].flagged}")
        print(f"  Categories: {response.results[0].categories}")
        print("\n✅ Moderation API works!")
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_moderation())
