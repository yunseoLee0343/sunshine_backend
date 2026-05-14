"""TICKET-055 — boundary tests: no ONNX, no local model loading, no vLLM in-process."""

from __future__ import annotations


def _src(module_name: str) -> str:
    import importlib

    mod = importlib.import_module(module_name)
    return open(mod.__file__, encoding="utf-8").read()


def test_no_onnx_runtime_in_qwen_client() -> None:
    src = _src("app.llm.qwen_client")
    assert "onnxruntime" not in src
    assert "ONNXRuntime" not in src


def test_no_local_model_loading_in_qwen_client() -> None:
    src = _src("app.llm.qwen_client")
    for forbidden in ("transformers", "AutoModelFor", "from_pretrained", "torch.load"):
        assert forbidden not in src


def test_no_vllm_process_in_qwen_client() -> None:
    src = _src("app.llm.qwen_client")
    # _API_VERSION = "vllm" is fine; we forbid starting a vLLM process
    for forbidden in ("import vllm", "from vllm", "LLMEngine", "AsyncLLMEngine"):
        assert forbidden not in src


def test_no_onnx_runtime_in_endpoint_registry() -> None:
    src = _src("app.llm.endpoint_registry")
    assert "onnxruntime" not in src


def test_no_model_files_loaded_in_endpoint_registry() -> None:
    src = _src("app.llm.endpoint_registry")
    for forbidden in ("transformers", "from_pretrained", "torch"):
        assert forbidden not in src


def test_no_prompt_builder_changes_in_qwen_client() -> None:
    src = _src("app.llm.qwen_client")
    for forbidden in ("PromptBuilder", "EvidenceBuilder", "RAG", "retrieval"):
        assert forbidden not in src


def test_no_embedding_changes_in_endpoint_registry() -> None:
    src = _src("app.llm.endpoint_registry")
    for forbidden in ("embedding", "EMBEDDING", "vector"):
        assert forbidden not in src


def test_endpoint_registry_makes_no_network_call_at_import() -> None:
    """Importing EndpointRegistry must not trigger any HTTP connections."""
    from unittest.mock import patch

    with patch("httpx.AsyncClient") as mock_http:
        import importlib

        importlib.import_module("app.llm.endpoint_registry")

    mock_http.assert_not_called()


def test_client_factory_makes_no_network_call_at_import() -> None:
    from unittest.mock import patch

    with patch("httpx.AsyncClient") as mock_http:
        import importlib

        importlib.import_module("app.llm.client_factory")

    mock_http.assert_not_called()
