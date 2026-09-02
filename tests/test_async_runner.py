from py_crow_tool.services.async_runner import AsyncLoopRunner


async def _add(a, b):
    return a + b


def test_submit_runs_coroutine_and_resolves_future():
    runner = AsyncLoopRunner()
    try:
        future = runner.submit(_add(2, 3))
        assert future.result(timeout=2) == 5
    finally:
        runner.stop()


def test_run_sync_blocks_until_the_coroutine_completes():
    runner = AsyncLoopRunner()
    try:
        assert runner.run_sync(_add(4, 5), timeout=2) == 9
    finally:
        runner.stop()


def test_many_coroutines_share_the_same_background_loop():
    runner = AsyncLoopRunner()
    try:
        results = [runner.submit(_add(i, 1)).result(timeout=2) for i in range(10)]
        assert results == list(range(1, 11))
    finally:
        runner.stop()


def test_stop_is_safe_to_call_when_idle():
    runner = AsyncLoopRunner()
    runner.stop()  # must not raise or hang
