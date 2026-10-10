"""Unit and integration tests for Ollama integration and Gemma service."""
from __future__ import annotations

import json
import pytest
from pydantic import BaseModel

from backend import config
from backend.llm.client import call_json, _fixture
from backend.llm.gemma import GemmaService, clean_json_str, get_gemma_service
from backend.models import DraftRulesOut, ExplainOut, ParserOut


class SampleSchema(BaseModel):
    status: str
    code: int = 0


def test_clean_json_str():
    # Plain JSON
    assert clean_json_str('{"status": "ok"}') == '{"status": "ok"}'

    # Wrapped in markdown json block
    markdown_json = "```json\n{\"status\": \"ok\", \"code\": 200}\n```"
    assert clean_json_str(markdown_json) == '{"status": "ok", "code": 200}'

    # Wrapped in plain markdown block with surrounding text
    wrapped = "Here is the result:\n```\n{\"status\": \"ready\"}\n```\nHope this helps!"
    assert clean_json_str(wrapped) == '{"status": "ready"}'


def test_gemma_service_initialization():
    service = GemmaService(
        base_url="http://127.0.0.1:11434",
        intake_model="gemma:4b",
        reason_model="gemma:12b",
    )
    assert service.base_url == "http://127.0.0.1:11434"
    assert service.model_for_tier("intake") == "gemma:4b"
    assert service.model_for_tier("reason") == "gemma:12b"
    assert service.model_for_tier("4b") == "gemma:4b"
    assert service.model_for_tier("12b") == "gemma:12b"


def test_convert_openai_messages_to_ollama():
    service = get_gemma_service()

    # Plain text messages
    messages = [
        {"role": "system", "content": "You are an assistant"},
        {"role": "user", "content": "Extract rules"},
    ]
    converted = service._convert_openai_messages_to_ollama(messages)
    assert len(converted) == 2
    assert converted[0]["content"] == "You are an assistant"

    # Multimodal image message
    multimodal_messages = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg=="}},
                {"type": "text", "text": "Extract rules from photo"},
            ],
        }
    ]
    conv_multi = service._convert_openai_messages_to_ollama(multimodal_messages)
    assert len(conv_multi) == 1
    assert "Extract rules from photo" in conv_multi[0]["content"]
    assert conv_multi[0]["images"] == ["iVBORw0KGgoAAAANSUhEUg=="]


def test_gemma_check_health():
    service = get_gemma_service()
    health = service.check_health()
    # Ollama is running locally in this environment
    if health["connected"]:
        assert health["ok"] is True
        assert isinstance(health["installed_models"], list)
        assert len(health["installed_models"]) > 0


def test_mock_fixture_loading():
    # Verify mock fixtures load and match their target schemas
    audio_fixture = _fixture("extract_rules_audio")
    validated_audio = DraftRulesOut.model_validate(audio_fixture)
    assert len(validated_audio.rules) > 0

    text_fixture = _fixture("extract_rules_text")
    validated_text = DraftRulesOut.model_validate(text_fixture)
    assert len(validated_text.rules) > 0

    conflict_fixture = _fixture("explain_conflict")
    validated_conflict = ExplainOut.model_validate(conflict_fixture)
    assert len(validated_conflict.options) > 0

    parser_fixture = _fixture("gen_sheet_parser")
    validated_parser = ParserOut.model_validate(parser_fixture)
    assert "def parse" in validated_parser.code


def test_call_json_mock_mode(monkeypatch):
    monkeypatch.setattr(config, "MOCK_LLM", True)
    result = call_json("extract_rules_text", "intake", [], DraftRulesOut)
    assert isinstance(result, DraftRulesOut)
    assert len(result.rules) > 0


def test_live_requests_include_schema_and_requested_timeout(monkeypatch):
    captured = {}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self):
            return json.dumps({'message': {'content': '{"status":"ok","code":200}'}}).encode()
    def urlopen(request, timeout):
        captured.update(payload=json.loads(request.data), timeout=timeout)
        return Response()
    monkeypatch.setattr('urllib.request.urlopen', urlopen)
    result, _ = GemmaService().generate_json('intake', [{'role': 'user', 'content': 'Check'}], SampleSchema, timeout_s=120)
    assert result.code == 200
    assert captured['payload']['format'] == SampleSchema.model_json_schema()
    assert captured['timeout'] == 120


def test_health_does_not_match_a_partial_model_name(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return json.dumps({'models': [{'name': 'gemma:4'}]}).encode()
    monkeypatch.setattr('urllib.request.urlopen', lambda *a, **k: Response())
    health = GemmaService(intake_model='gemma:4b').check_health()
    assert not health['intake_ready']
