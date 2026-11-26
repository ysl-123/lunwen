"""扩展点二：在这里定义专家职责、执行方法和可用工具。"""

from typing import Sequence

from .runtime import Agent, Model, Tool


def build_expert(
    name: str,
    model: Model,
    instructions: str,
    tools: Sequence[Tool] = (),
) -> Agent:
    # 不预设领域或工作步骤；instructions 和 tools 由你自己的专家设计决定。
    return Agent(name=name, model=model, system_prompt=instructions, tools=tools)
