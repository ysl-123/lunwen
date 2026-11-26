"""扩展点一：在这里定义规划者如何拆任务、选专家和判断完成。"""

from typing import Sequence

from .runtime import Agent, Model, Tool


PLANNER_PROMPT = """你是规划智能体。
根据目标和已有结果，选择合适的专家工具并提供明确的子任务及必要上下文。
收到专家结果后决定下一步，完成目标时输出汇总；失败时如实说明。
TODO: 在这里填写你自己的规划策略、专家选择规则和完成条件。
"""


def build_planner(
    model: Model,
    experts: Sequence[Agent],
    descriptions: Sequence[str],
    tools: Sequence[Tool] = (),
    name: str = "planner",
) -> Agent:
    """专家描述用于模型选人；tools 保留主智能体直接使用普通工具的能力。"""
    if len(experts) != len(descriptions):
        raise ValueError("每个专家必须有一条职责描述")
    expert_tools = [expert.as_tool(description) for expert, description in zip(experts, descriptions)]
    return Agent(name, model, PLANNER_PROMPT, [*expert_tools, *tools])
