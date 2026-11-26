"""只测试架构协作契约，不绑定任何业务或真实模型。"""

from copy import deepcopy
import json
import unittest

from pentestllmagent import Agent, BudgetExceeded, RoundLimitExceeded, RunContext, Tool, build_planner


def tool_call(name, arguments, call_id="call_1"):
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": call_id,
            "type": "function",
            "function": {"name": name, "arguments": arguments},
        }],
    }


class ScriptModel:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.inputs = []

    def complete(self, messages, tools):
        self.inputs.append(deepcopy((messages, tools)))
        response = next(self.responses)
        return response(messages) if callable(response) else response


def return_tool_result(messages):
    return {"role": "assistant", "content": messages[-1]["content"]}


class ArchitectureTests(unittest.TestCase):
    def test_nested_delegation_feedback_and_private_histories(self):
        observed = []
        tool = Tool("lookup", "示例工具", {}, lambda args, ctx: observed.append(args) or "真实工具结果")
        expert_model = ScriptModel(tool_call("lookup", '{"query": "输入"}', "expert_call"), return_tool_result)
        expert = Agent("expert", expert_model, "专家私有提示词", [tool])
        group_model = ScriptModel(tool_call("expert", {"task": "专家子任务"}), return_tool_result)
        group = build_planner(group_model, [expert], ["专家职责"], name="group")
        main_model = ScriptModel(tool_call("group", {"task": "调度子任务"}), return_tool_result)
        planner = build_planner(main_model, [group], ["调度职责"])
        context = RunContext(6)

        self.assertEqual(planner.run("顶层目标", context), "真实工具结果")
        self.assertEqual(context.remaining_calls, 0)
        self.assertEqual(observed, [{"query": "输入"}])
        # 每层仅看到自己的任务、工具和结果，不能看见下层内部对话。
        self.assertEqual(expert_model.inputs[0][0][1]["content"], "专家子任务")
        self.assertEqual(group_model.inputs[0][0][1]["content"], "调度子任务")
        self.assertNotIn("专家私有提示词", str(main_model.inputs))
        self.assertNotIn("lookup", str(main_model.inputs))
        expert_feedback = expert_model.inputs[1][0][-1]
        self.assertEqual(expert_feedback["tool_call_id"], "expert_call")

    def test_planner_can_use_result_to_select_a_second_expert(self):
        first = Agent("first", ScriptModel({"role": "assistant", "content": "证据A"}), "")
        second_model = ScriptModel(lambda messages: {"role": "assistant", "content": messages[1]["content"]})
        second = Agent("second", second_model, "")

        def choose_next(messages):
            self.assertEqual(messages[-1]["content"], "证据A")
            return tool_call("second", {"task": "结合" + messages[-1]["content"]}, "call_2")

        model = ScriptModel(tool_call("first", {"task": "先取证据"}), choose_next, return_tool_result)
        planner = build_planner(model, [first, second], ["取证", "复核"])
        self.assertEqual(planner.run("目标"), "结合证据A")

    def test_reusing_agent_starts_a_fresh_conversation(self):
        model = ScriptModel({"role": "assistant", "content": "一"}, {"role": "assistant", "content": "二"})
        agent = Agent("expert", model, "私有提示词")
        agent.run("第一次")
        agent.run("第二次")
        self.assertEqual(model.inputs[1][0], [
            {"role": "system", "content": "私有提示词"},
            {"role": "user", "content": "第二次"},
        ])

    def test_tool_errors_are_returned_to_model(self):
        def fail(args, context):
            raise RuntimeError("工具失败")

        cases = [("missing", {}), ("fail", "{broken"), ("fail", "[]"), ("fail", {})]
        for name, arguments in cases:
            with self.subTest(name=name, arguments=arguments):
                model = ScriptModel(tool_call(name, arguments), return_tool_result)
                agent = Agent("expert", model, "", [Tool("fail", "", {}, fail)])
                output = json.loads(agent.run("任务"))
                self.assertEqual(output["status"], "error")
                self.assertTrue(output["error"])

    def test_global_budget_propagates_through_nested_agents(self):
        expert = Agent("expert", ScriptModel({"role": "assistant", "content": "不应调用"}), "")
        model = ScriptModel(tool_call("expert", {"task": "子任务"}), return_tool_result)
        planner = build_planner(model, [expert], ["专家"])
        with self.assertRaises(BudgetExceeded):
            planner.run("任务", RunContext(1))
        self.assertEqual(expert.model.inputs, [])

    def test_round_limit_is_not_a_success(self):
        tool = Tool("repeat", "", {}, lambda args, ctx: "继续")
        model = ScriptModel(tool_call("repeat", {}))
        with self.assertRaises(RoundLimitExceeded):
            Agent("expert", model, "", [tool], max_rounds=1).run("任务")

    def test_multiple_tool_calls_keep_order_and_ids(self):
        response = tool_call("echo", {"value": "A"}, "a")
        response["tool_calls"] += tool_call("echo", {"value": "B"}, "b")["tool_calls"]
        model = ScriptModel(response, return_tool_result)
        agent = Agent("expert", model, "", [Tool("echo", "", {}, lambda args, ctx: args["value"])])
        self.assertEqual(agent.run("任务"), "B")
        outputs = model.inputs[1][0][-2:]
        self.assertEqual([(msg["tool_call_id"], msg["content"]) for msg in outputs], [("a", "A"), ("b", "B")])


if __name__ == "__main__":
    unittest.main()
