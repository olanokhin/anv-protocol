"""Unit tests for demo runner helpers."""

from __future__ import annotations

from demo import CaseResult, CaseSpec, evaluate_case, print_summary, summarize_body


def test_evaluate_case_success() -> None:
    spec = CaseSpec(
        key="A",
        title="SIGNED_AI + warn",
        request_url="http://127.0.0.1:8003/run",
        expected_status=200,
        expectation="HTTP 200, result=294, anv_status=SIGNED_AI",
        request_body={"task": "Calculate 42 * 7"},
        exact_fields=(("result", 294), ("anv_status", "SIGNED_AI")),
    )

    result = evaluate_case(spec, 200, {"result": 294, "anv_status": "SIGNED_AI"})
    assert result.ok is True
    assert result.details == ()


def test_evaluate_case_reports_field_mismatch() -> None:
    spec = CaseSpec(
        key="D",
        title="UNSIGNED + require",
        request_url="http://127.0.0.1:8004/run",
        expected_status=403,
        expectation="HTTP 403, anv_attestation_required, received=UNSIGNED",
        request_body={"task": "Calculate 42 * 7"},
        exact_fields=(("error", "anv_attestation_required"), ("received", "UNSIGNED")),
        list_contains=(("required", "SIGNED_AI"),),
    )

    result = evaluate_case(spec, 403, {"error": "wrong", "required": []})
    assert result.ok is False
    assert "expected error='anv_attestation_required', got 'wrong'" in result.details
    assert "expected received='UNSIGNED', got None" in result.details
    assert "expected required to contain 'SIGNED_AI'" in result.details


def test_summarize_body_uses_compact_fields() -> None:
    summary = summarize_body(
        {
            "result": 294,
            "anv_status": "UNSIGNED",
            "anv_warning": "No ANV attestation present.",
            "required": ["SIGNED_AI", "SIGNED_HUMAN"],
        }
    )
    assert "result=294" in summary
    assert "anv_status=UNSIGNED" in summary
    assert "anv_warning=present" in summary
    assert "required=SIGNED_AI,SIGNED_HUMAN" in summary


def test_summarize_body_record_mode_hides_provider() -> None:
    summary = summarize_body(
        {
            "result": 294,
            "anv_status": "SIGNED_AI",
            "anv_provider": "example-ai-provider.com",
        },
        record_mode=True,
    )
    assert "result=294" in summary
    assert "anv_status=SIGNED_AI" in summary
    assert "anv_provider" not in summary


def test_print_summary_record_mode_omits_readiness_line(capsys) -> None:
    result = CaseResult(
        spec=CaseSpec(
            key="A",
            title="SIGNED_AI + warn",
            request_url="http://127.0.0.1:8003/run",
            expected_status=200,
            expectation="HTTP 200, result=294, anv_status=SIGNED_AI",
            request_body={"task": "Calculate 42 * 7"},
        ),
        ok=True,
        status_code=200,
        body={"result": 294, "anv_status": "SIGNED_AI"},
        details=(),
    )
    print_summary([result], record_mode=True)
    captured = capsys.readouterr()
    assert "Summary" in captured.out
    assert "A PASS" in captured.out
    assert "PoC ready for demo" not in captured.out
