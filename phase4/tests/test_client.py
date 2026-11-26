import json
import os
import urllib.error

import pytest

from phase4.groq_client import GROQ_URL, DEFAULT_MODEL, GroqClient, GroqError, load_local_env


def test_missing_key_does_not_open_the_network(monkeypatch):
    def fail_open(*args, **kwargs):
        raise AssertionError("network")

    monkeypatch.setattr("phase4.groq_client.urllib.request.urlopen", fail_open)
    client = GroqClient(api_key="")
    with pytest.raises(GroqError, match="missing api key"):
        client.complete([{"role": "user", "content": "hi"}])


def test_complete_posts_chat_completions(monkeypatch):
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    captured: dict[str, object] = {}

    class Response:
        def read(self) -> bytes:
            return json.dumps(
                {"choices": [{"message": {"content": "{\"recommendations\": []}"}}]}
            ).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> bool:
            return False

    def fake_urlopen(request, timeout=0):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["auth"] = request.get_header("Authorization")
        captured["agent"] = request.get_header("User-agent")
        captured["body"] = json.loads(request.data.decode())
        return Response()

    monkeypatch.setattr("phase4.groq_client.urllib.request.urlopen", fake_urlopen)
    client = GroqClient(api_key="test-key", timeout=3)
    text = client.complete([{"role": "user", "content": "rank"}])
    assert text == '{"recommendations": []}'
    assert captured["url"] == GROQ_URL
    assert captured["timeout"] == 3
    assert captured["auth"] == "Bearer test-key"
    assert captured["agent"] == "zomato-recommendations/0.1"
    assert client.model == DEFAULT_MODEL
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == DEFAULT_MODEL
    assert body["response_format"] == {"type": "json_object"}


def test_rate_limit_and_timeout_raise(monkeypatch):
    def rate_limited(request, timeout=0):
        raise urllib.error.HTTPError(GROQ_URL, 429, "Too Many Requests", None, None)

    monkeypatch.setattr("phase4.groq_client.urllib.request.urlopen", rate_limited)
    with pytest.raises(GroqError, match="rate limit"):
        GroqClient(api_key="test-key").complete([{"role": "user", "content": "rank"}])

    def timed_out(request, timeout=0):
        raise TimeoutError("timed out")

    monkeypatch.setattr("phase4.groq_client.urllib.request.urlopen", timed_out)
    with pytest.raises(GroqError, match="timeout"):
        GroqClient(api_key="test-key").complete([{"role": "user", "content": "rank"}])


def test_content_parts_are_joined(monkeypatch):
    class Response:
        def read(self) -> bytes:
            return json.dumps(
                {"choices": [{"message": {"content": [{"text": "{"}, {"text": "}"}]}}]}
            ).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> bool:
            return False

    monkeypatch.setattr(
        "phase4.groq_client.urllib.request.urlopen",
        lambda request, timeout=0: Response(),
    )
    assert GroqClient(api_key="test-key").complete([{"role": "user", "content": "rank"}]) == "{}"


def test_dotenv_fills_missing_keys_only(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        'GROQ_API_KEY="from-file"\nexport GROQ_MODEL=custom-model\n# ignored\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("GROQ_API_KEY", "already")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    load_local_env(env_file)
    assert os.environ["GROQ_API_KEY"] == "already"
    assert os.environ["GROQ_MODEL"] == "custom-model"
