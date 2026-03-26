from app.services.ingestion_service import (
    FragmentPlanItem,
    build_fragment_plan,
    merge_fragment_chunks_with_global_timestamps,
)


def test_build_fragment_plan_boundaries():
    assert build_fragment_plan(duration_seconds=1799, max_fragment_seconds=1800) == [
        FragmentPlanItem(index=0, start_offset_sec=0.0, duration_sec=1799.0)
    ]
    assert build_fragment_plan(duration_seconds=1800, max_fragment_seconds=1800) == [
        FragmentPlanItem(index=0, start_offset_sec=0.0, duration_sec=1800.0)
    ]
    assert build_fragment_plan(duration_seconds=1801, max_fragment_seconds=1800) == [
        FragmentPlanItem(index=0, start_offset_sec=0.0, duration_sec=1800.0),
        FragmentPlanItem(index=1, start_offset_sec=1800.0, duration_sec=1.0),
    ]


def test_build_fragment_plan_multiple_fragments_with_remainder():
    plan = build_fragment_plan(duration_seconds=3650, max_fragment_seconds=1800)
    assert plan == [
        FragmentPlanItem(index=0, start_offset_sec=0.0, duration_sec=1800.0),
        FragmentPlanItem(index=1, start_offset_sec=1800.0, duration_sec=1800.0),
        FragmentPlanItem(index=2, start_offset_sec=3600.0, duration_sec=50.0),
    ]


def test_merge_fragment_chunks_reconstructs_global_timeline():
    plan = [
        FragmentPlanItem(index=0, start_offset_sec=0.0, duration_sec=1800.0),
        FragmentPlanItem(index=1, start_offset_sec=1800.0, duration_sec=1800.0),
    ]
    merged = merge_fragment_chunks_with_global_timestamps(
        fragment_plan=plan,
        fragment_chunks=[
            [(10.0, 20.0, "a"), (1700.0, 1750.0, "b")],
            [(5.0, 12.0, "c"), (100.0, 140.0, "d")],
        ],
    )
    assert merged == [
        (10.0, 20.0, "a"),
        (1700.0, 1750.0, "b"),
        (1805.0, 1812.0, "c"),
        (1900.0, 1940.0, "d"),
    ]


def test_merge_fragment_chunks_raises_on_non_monotonic_timestamps():
    plan = [
        FragmentPlanItem(index=0, start_offset_sec=0.0, duration_sec=1800.0),
        FragmentPlanItem(index=1, start_offset_sec=1800.0, duration_sec=1800.0),
    ]
    try:
        merge_fragment_chunks_with_global_timestamps(
            fragment_plan=plan,
            fragment_chunks=[
                [(1795.0, 1799.0, "a")],
                [(-10.0, 1.0, "b")],
            ],
        )
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "non-monotonic" in str(exc)
