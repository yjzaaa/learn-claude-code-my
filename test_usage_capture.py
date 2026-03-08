"""
测试 Usage 捕获逻辑 - 使用模拟数据验证
"""

import json
from unittest.mock import MagicMock


def test_usage_capture():
    """测试 usage 捕获逻辑"""

    # 模拟 API 返回的 usage 对象
    class MockUsage:
        def __init__(self, prompt, completion, total):
            self.prompt_tokens = prompt
            self.completion_tokens = completion
            self.total_tokens = total

    # 模拟 API 响应
    class MockResponse:
        def __init__(self, round_num, usage_data):
            self.choices = [MagicMock()]
            self.choices[0].message = MagicMock()
            self.choices[0].message.content = f"Response {round_num}"
            self.choices[0].message.tool_calls = None
            self.choices[0].finish_reason = "stop"
            self.usage = usage_data

    # 测试用法
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    usage_history = []

    # 模拟三轮调用
    rounds_data = [
        MockUsage(100, 50, 150),
        MockUsage(200, 100, 300),
        MockUsage(300, 150, 450),
    ]

    for i, usage in enumerate(rounds_data, 1):
        response = MockResponse(i, usage)

        # 捕获 usage 逻辑（来自 BaseAgentLoop.run）
        usage_obj = getattr(response, 'usage', None)
        if usage_obj:
            usage_dict = {
                "prompt_tokens": getattr(usage_obj, 'prompt_tokens', 0),
                "completion_tokens": getattr(usage_obj, 'completion_tokens', 0),
                "total_tokens": getattr(usage_obj, 'total_tokens', 0),
            }
            usage_history.append({"round": i, "usage": usage_dict})
            for key in total_usage:
                total_usage[key] += usage_dict.get(key, 0)

    result = {
        "total": total_usage,
        "history": usage_history,
        "rounds": len(rounds_data),
    }

    print("=" * 60)
    print("Usage Capture Test Result")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    print()

    # 验证结果
    assert result["total"]["prompt_tokens"] == 600, "Total prompt should be 600"
    assert result["total"]["completion_tokens"] == 300, "Total completion should be 300"
    assert result["total"]["total_tokens"] == 900, "Total tokens should be 900"
    assert len(result["history"]) == 3, "Should have 3 history entries"

    print("[PASS] All assertions passed!")


if __name__ == "__main__":
    test_usage_capture()
