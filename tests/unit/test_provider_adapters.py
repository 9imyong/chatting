import pytest
import httpx

from app.adapters.outbound.gptsovits_http_client import GPTSoVITSHTTPClient
from app.adapters.outbound.vllm_http_client import VLLMHTTPClient
from app.domain.entities.message import ChatMessage
from app.domain.exceptions.errors import LLMBadResponseError, LLMTimeoutError, TTSBadResponseError


@pytest.mark.asyncio
async def test_vllm_timeout_maps_to_llm_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = VLLMHTTPClient(
        base_url="http://vllm",
        model="m",
        temperature=0.7,
        max_tokens=32,
        connect_timeout_sec=1.0,
        read_timeout_sec=1.0,
        retry_count=0,
        retry_base_delay_sec=0.01,
        retry_max_delay_sec=0.01,
        retry_jitter_enabled=False,
        retry_jitter_ratio=0.0,
        retry_total_timeout_sec=1.0,
        http_client=client,
    )

    with pytest.raises(LLMTimeoutError):
        await adapter.generate([ChatMessage(role="user", content="hello")])

    await adapter.close()
    await client.aclose()


@pytest.mark.asyncio
async def test_tts_invalid_body_maps_to_tts_bad_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = GPTSoVITSHTTPClient(
        base_url="http://tts",
        connect_timeout_sec=1.0,
        read_timeout_sec=1.0,
        retry_count=0,
        retry_base_delay_sec=0.01,
        retry_max_delay_sec=0.01,
        retry_jitter_enabled=False,
        retry_jitter_ratio=0.0,
        retry_total_timeout_sec=1.0,
        synthesis_idempotent=False,
        http_client=client,
    )

    with pytest.raises(TTSBadResponseError):
        await adapter.synthesize("hello")

    await adapter.close()
    await client.aclose()


@pytest.mark.asyncio
async def test_vllm_retries_on_429_then_succeeds() -> None:
    calls = {"count": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = VLLMHTTPClient(
        base_url="http://vllm",
        model="m",
        temperature=0.7,
        max_tokens=32,
        connect_timeout_sec=1.0,
        read_timeout_sec=1.0,
        retry_count=1,
        retry_base_delay_sec=0.0,
        retry_max_delay_sec=0.0,
        retry_jitter_enabled=False,
        retry_jitter_ratio=0.0,
        retry_total_timeout_sec=5.0,
        http_client=client,
    )

    text = await adapter.generate([ChatMessage(role="user", content="hello")])

    assert text == "ok"
    assert calls["count"] == 2
    await adapter.close()
    await client.aclose()


@pytest.mark.asyncio
async def test_vllm_invalid_body_is_non_retryable() -> None:
    calls = {"count": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        calls["count"] += 1
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = VLLMHTTPClient(
        base_url="http://vllm",
        model="m",
        temperature=0.7,
        max_tokens=32,
        connect_timeout_sec=1.0,
        read_timeout_sec=1.0,
        retry_count=2,
        retry_base_delay_sec=0.0,
        retry_max_delay_sec=0.0,
        retry_jitter_enabled=False,
        retry_jitter_ratio=0.0,
        retry_total_timeout_sec=5.0,
        http_client=client,
    )

    with pytest.raises(LLMBadResponseError):
        await adapter.generate([ChatMessage(role="user", content="hello")])

    assert calls["count"] == 1
    await adapter.close()
    await client.aclose()


@pytest.mark.asyncio
async def test_tts_does_not_retry_5xx_when_non_idempotent() -> None:
    calls = {"count": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        calls["count"] += 1
        return httpx.Response(503, json={"error": "unavailable"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = GPTSoVITSHTTPClient(
        base_url="http://tts",
        connect_timeout_sec=1.0,
        read_timeout_sec=1.0,
        retry_count=2,
        retry_base_delay_sec=0.0,
        retry_max_delay_sec=0.0,
        retry_jitter_enabled=False,
        retry_jitter_ratio=0.0,
        retry_total_timeout_sec=5.0,
        synthesis_idempotent=False,
        http_client=client,
    )

    with pytest.raises(TTSBadResponseError):
        await adapter.synthesize("hello")

    assert calls["count"] == 1
    await adapter.close()
    await client.aclose()


@pytest.mark.asyncio
async def test_tts_retries_connect_timeout_even_when_non_idempotent() -> None:
    calls = {"count": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        calls["count"] += 1
        if calls["count"] == 1:
            raise httpx.ConnectTimeout("connect timeout")
        return httpx.Response(200, json={"audio_url": "https://audio.local/file.wav"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = GPTSoVITSHTTPClient(
        base_url="http://tts",
        connect_timeout_sec=1.0,
        read_timeout_sec=1.0,
        retry_count=2,
        retry_base_delay_sec=0.0,
        retry_max_delay_sec=0.0,
        retry_jitter_enabled=False,
        retry_jitter_ratio=0.0,
        retry_total_timeout_sec=5.0,
        synthesis_idempotent=False,
        http_client=client,
    )

    audio = await adapter.synthesize("hello")

    assert audio.endswith("file.wav")
    assert calls["count"] == 2
    await adapter.close()
    await client.aclose()
