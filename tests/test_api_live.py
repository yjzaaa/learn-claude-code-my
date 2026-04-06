"""
测试本地运行的 main.py API
"""
import json

import requests

BASE = "http://127.0.0.1:8001"

# 1. 创建对话
r = requests.post(f"{BASE}/api/dialogs", json={"title": "Live Test"})
print("Create dialog:", r.status_code, r.text)
d = r.json()
dialog_id = d["data"]["id"]

# 2. 发送消息 (stream)
print("\nSend message stream:")
r = requests.post(
    f"{BASE}/api/dialogs/{dialog_id}/messages",
    json={"content": "hello", "stream": True},
    stream=True,
)
for line in r.iter_lines():
    if line:
        text = line.decode("utf-8")
        if text.startswith("data: "):
            try:
                data = json.loads(text[6:])
                print("SSE:", json.dumps(data, ensure_ascii=False)[:300])
            except Exception:
                print("Raw:", text[:200])
