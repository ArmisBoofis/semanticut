from app.ingestion import phases


def test_progress_at_phase_start_monotonic():
    assert phases.progress_at_phase_start(phases.PHASE_EXTRACTING_AUDIO) == 0
    assert phases.progress_at_phase_start(phases.PHASE_TRANSCRIBING) == 20
    assert phases.progress_at_phase_start(phases.PHASE_CHUNKING) == 40
    assert phases.progress_at_phase_start(phases.PHASE_EMBEDDING) == 60
    assert phases.progress_at_phase_start(phases.PHASE_INDEXING) == 80


def test_progress_unknown_phase_defaults_to_zero():
    assert phases.progress_at_phase_start("unknown") == 0
