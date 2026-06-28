from kv_cache_profiler.schema import RequestRecord


def test_request_record_calculates_cache_metrics():
    record = RequestRecord.build(
        benchmark_run_id="bench",
        workflow_run_id="run",
        thread_id="thread",
        agent_id="planner",
        request_uuid="request",
        prompt_tokens=100,
        cached_tokens=35,
        output_tokens=6,
        timestamp_start_ns=1_000_000_000,
        first_token_ns=1_050_000_000,
        last_token_ns=1_150_000_000,
        timestamp_end_ns=1_200_000_000,
    )

    assert record.new_prefill_tokens == 65
    assert record.reported_cache_hit_ratio == 0.35
    assert record.ttft_ms == 50.0
    assert record.tpot_ms == 20.0
    assert record.e2e_ms == 200.0
    assert record.validate() == []
