"""离线连线示例：固定脚本模拟模型响应，只演示架构，不实现智能决策。"""

import json

from .expert import build_expert
from .planner import build_planner
from .runtime import RunContext, Tool


class DemoModel:
    """真实模型适配器只需实现同名 complete 方法。"""

    def __init__(self, tool_name: str, arguments: dict):
        self.tool_name = tool_name
        self.arguments = arguments

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        if messages[-1]["role"] == "tool":
            return {"role": "assistant", "content": messages[-1]["content"]}
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "demo_call",
                "type": "function",
                "function": {
                    "name": self.tool_name,
                    "arguments": json.dumps(self.arguments, ensure_ascii=False),
                },
            }],
        }


def main() -> None:
    # 1. 注册普通工具。将 handler 换成你自己的业务函数即可。
    tool = Tool(
        name="example_tool",
        description="返回示例数据，用于验证调用链",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        handler=lambda arguments, context: f"工具执行结果：{arguments['text']}",
    )
    # 2. 专家拥有自己的模型、提示词和工具。
    expert = build_expert(
        name="example_expert",
        model=DemoModel("example_tool", {"text": "架构调用链已打通"}),
        instructions="TODO: 填写专家职责及执行方法。",
        tools=[tool],
    )
    # 3. 规划者通过工具接口调用专家，随后接收结果继续决策。
    planner = build_planner(
        model=DemoModel("example_expert", {"task": "执行一个示例子任务"}),
        experts=[expert],
        descriptions=["负责示例子任务；请替换为真实专家的能力说明"],
    )
    context = RunContext(remaining_calls=20)
    print("调用链：规划智能体 → 专家智能体 → 普通工具 → 专家 → 规划智能体")
    print(planner.run("演示主从智能体协作", context))
    print(f"模型调用次数：{20 - context.remaining_calls}")


if __name__ == "__main__":
    main()
