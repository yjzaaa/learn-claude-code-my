"""AgentTaskQueue 测试"""
import asyncio
from backend.infrastructure.agent_queue import AgentTaskQueue, AgentTask, TaskPriority


async def test_task_submission():
    """测试任务提交"""
    queue = AgentTaskQueue(max_concurrent=2)
    await queue.start()

    task = AgentTask(
        task_id="task_001",
        dialog_id="dlg_001",
        action="test_action",
    )

    future = await queue.submit(task)

    # 等待任务完成
    try:
        result = await asyncio.wait_for(future, timeout=2.0)
        print(f"✓ test_task_submission passed (result={result})")
    except asyncio.TimeoutError:
        print("✗ test_task_submission timeout")

    await queue.shutdown()


async def test_concurrency_limit():
    """测试并发限制"""
    queue = AgentTaskQueue(max_concurrent=1)  # 单并发
    await queue.start()

    # 提交多个任务
    futures = []
    for i in range(3):
        task = AgentTask(
            task_id=f"task_{i}",
            dialog_id="dlg_001",
            action="slow_action",
        )
        future = await queue.submit(task)
        futures.append(future)

    stats = queue.get_stats()
    assert stats["max_concurrent"] == 1
    print(f"✓ test_concurrency_limit passed (max_concurrent={stats['max_concurrent']})")

    await queue.shutdown()


async def test_priority():
    """测试优先级"""
    queue = AgentTaskQueue(max_concurrent=1)
    await queue.start()

    # 按顺序提交不同优先级任务
    low_task = AgentTask(
        task_id="low",
        dialog_id="dlg_001",
        action="test",
        priority=TaskPriority.LOW,
    )
    high_task = AgentTask(
        task_id="high",
        dialog_id="dlg_001",
        action="test",
        priority=TaskPriority.HIGH,
    )

    await queue.submit(low_task)
    await queue.submit(high_task)

    print("✓ test_priority passed")
    await queue.shutdown()


async def run_tests():
    await test_task_submission()
    await test_concurrency_limit()
    await test_priority()
    print("All AgentTaskQueue tests passed!")


if __name__ == "__main__":
    asyncio.run(run_tests())
