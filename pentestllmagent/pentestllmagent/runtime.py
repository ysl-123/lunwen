"""通用执行器：模型决策 → 工具/子智能体 → 结果反馈 → 再决策。"""

from dataclasses import dataclass
import json
from typing import Any, Callable, Protocol, Sequence


class Model(Protocol):
    """模型适配接口；返回一条 assistant 消息，不是完整的 API 响应。"""

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        ...


class BudgetExceeded(RuntimeError):
    """整个调用树的模型调用额度耗尽。"""


class RoundLimitExceeded(RuntimeError):
    """当前智能体未在限定轮次内完成任务。"""


@dataclass
class RunContext:
    """一次顶层任务的共享额度；不保存各智能体的私有对话。"""

    remaining_calls: int = 50

    def consume(self) -> None:
        if self.remaining_calls <= 0:
            raise BudgetExceeded("整个任务的模型调用额度已耗尽")
        self.remaining_calls -= 1


@dataclass(frozen=True)
class Tool:
    """普通工具与专家采用相同接口。handler(arguments, context) → 文本。"""

    name: str
    description: str
    parameters: dict
    handler: Callable[[dict[str, Any], RunContext], str]

    def definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class Agent:
    """规划者、调度者和专家复用同一个循环，差别在提示词与可用工具。"""

    def __init__(
        self,
        name: str,
        model: Model,
        system_prompt: str,
        tools: Sequence[Tool] = (),
        max_rounds: int = 10,
    ):
        if max_rounds < 1:
            raise ValueError("max_rounds 必须大于 0")
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tuple(tools)
        self.max_rounds = max_rounds
        self._registry = {tool.name: tool for tool in self.tools}
        if len(self._registry) != len(self.tools):
            raise ValueError("同一智能体内的工具名称不能重复")

    def run(self, task: str, context: RunContext | None = None) -> str:
        context = context if context is not None else RunContext()
        # 每次调用建立独立对话；父智能体只接收子智能体的最终文本。
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task},
        ]
        definitions = [tool.definition() for tool in self.tools]
        for _ in range(self.max_rounds):
            context.consume()
            response = self.model.complete(messages, definitions)
            messages.append(response)
            calls = response.get("tool_calls") or []
            if not calls:
                return response.get("content") or ""
            # 与原项目一致：同一轮中的多个工具按顺序执行。
            for call in calls:
                output = self._call(call["function"], context)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": output,
                })
        raise RoundLimitExceeded(f"{self.name} 超过 {self.max_rounds} 轮，任务尚未完成")

    def _call(self, function: dict, context: RunContext) -> str:
        try:
            name = function["name"]
            if name not in self._registry:
                raise ValueError(f"未注册工具: {name}")
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            if not isinstance(arguments, dict):
                raise ValueError("工具参数必须是 JSON 对象")
            return str(self._registry[name].handler(arguments, context))
        except BudgetExceeded:
            # 全局额度耗尽必须终止整个调用树，不能作为普通工具错误吞掉。
            raise
        except Exception as exc:
            # 错误也反馈给上层模型，由它决定换工具、修正参数或结束。
            return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False)

    def as_tool(self, description: str) -> Tool:
        """把智能体暴露为父智能体可调用的工具，也适用于中间调度层。"""
        return Tool(
            name=self.name,
            description=description,
            parameters={
                "type": "object",
                "properties": {"task": {"type": "string", "description": "子任务及必要上下文"}},
                "required": ["task"],
                "additionalProperties": False,
            },
            handler=lambda arguments, context: self.run(arguments["task"], context),
        )
