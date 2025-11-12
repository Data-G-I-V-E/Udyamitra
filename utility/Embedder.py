import os
import httpx
import asyncio

EMBEDDING_API_URL = os.getenv(
    "EMBEDDING_API_URL",
    "https://adityapeopleplus-embedding-generator.hf.space/embed"
)

async def get_embedding(text: str):
    """Send text to the HF Space embedding API and return the vector."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(EMBEDDING_API_URL, json={"text": text})
        resp.raise_for_status()
        data = resp.json()
        return data.get("embedding") or data


def run_async(coro):
    """Safely run async functions in sync contexts."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        result = new_loop.run_until_complete(coro)
        new_loop.close()
        return result
    else:
        return asyncio.run(coro)


class HFAPIEmbeddings:
    """Wrapper for Hugging Face embedding API."""

    async def embed_documents(self, texts):
        embeddings = []
        for text in texts:
            vec = await get_embedding(text)
            embeddings.append(vec)
        return embeddings

    def embed_documents_sync(self, texts):
        """Sync wrapper for embedding multiple texts."""
        return run_async(self.embed_documents(texts))

    def embed_query(self, text):
        """Sync single-text embedding for AstraDBVectorStore."""
        return run_async(get_embedding(text))
