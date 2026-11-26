"""阶段 1：用规则比对采集事实。不读答案本，不调用模型。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUSES_PATH = ROOT / "clauses.json"
REPORT_FIRST_LINE = "送评前预检，非正式密评"


def load_clauses() -> list[dict]:
    payload = json.loads(CLAUSES_PATH.read_text(encoding="utf-8"))
    return list(payload["clauses"])


CHECKLIST_LAYERS = {"物理和环境", "管理制度", "人员管理", "建设运行", "应急处置"}


def checklist_units() -> list[dict]:
    return [unit for unit in build_plan() if unit["layer"] in CHECKLIST_LAYERS]


JUDGED = {
    "NET-CONF": {
        "object": "浏览器到网站的信道",
        "collectors": ["channel_facts", "login_observation"],
        "pass_when": "协议不是 HTTP，且登录口令没有以明文出现",
        "fail_when": "协议为 HTTP，或登录口令以明文出现",
    },
    "DEV-AUTH": {
        "object": "设备登录",
        "collectors": ["current_profile"],
        "pass_when": "配置导出写明设备登录使用了密码技术",
        "fail_when": "导出里没有设备登录措施时写证据不足",
    },
    "DEV-REMOTE": {
        "object": "远程管理入口",
        "collectors": ["current_profile"],
        "pass_when": "管理入口使用受保护通道",
        "fail_when": "导出里没有管理入口时写证据不足",
    },
    "DEV-ACL": {
        "object": "系统资源访问控制信息",
        "collectors": ["current_profile"],
        "pass_when": "导出中有完整性措施",
        "fail_when": "没有完整性字段时写证据不足",
    },
    "DEV-LABEL": {
        "object": "重要信息资源安全标记",
        "collectors": ["current_profile"],
        "pass_when": "导出中有安全标记完整性措施",
        "fail_when": "没有该项导出时写证据不足",
    },
    "DEV-LOG": {
        "object": "日志记录",
        "collectors": ["current_profile"],
        "pass_when": "导出中有日志完整性措施",
        "fail_when": "没有日志完整性字段时写证据不足",
    },
    "DEV-BIN": {
        "object": "重要可执行程序",
        "collectors": ["current_profile"],
        "pass_when": "导出中有程序完整性措施",
        "fail_when": "没有程序完整性记录时写证据不足",
    },
    "APP-AUTH": {
        "object": "应用登录口令",
        "collectors": ["current_profile"],
        "pass_when": "口令用杂凑或密码算法校验",
        "fail_when": "口令按明文比对",
    },
    "APP-ACL": {
        "object": "应用访问控制信息",
        "collectors": ["current_profile"],
        "pass_when": "导出中有完整性措施",
        "fail_when": "没有完整性字段时写证据不足",
    },
    "APP-TRANS-CONF": {
        "object": "重要数据传输",
        "collectors": ["channel_facts", "login_observation"],
        "pass_when": "协议不是 HTTP，且登录口令没有以明文出现",
        "fail_when": "协议为 HTTP，或登录口令以明文出现",
    },
    "APP-STORE-CONF": {
        "object": "登录口令字段、资料页手机号字段",
        "collectors": ["field_storage"],
        "pass_when": "口令和手机号都是杂凑或密文",
        "fail_when": "口令或手机号为明文",
    },
    "APP-TRANS-INT": {
        "object": "重要数据传输",
        "collectors": ["current_profile"],
        "pass_when": "传输有完整性措施",
        "fail_when": "没有完整性措施时写证据不足",
    },
    "APP-STORE-INT": {
        "object": "用户表",
        "collectors": ["current_profile"],
        "pass_when": "表内有完整性字段",
        "fail_when": "没有完整性字段时写证据不足",
    },
    "APP-NR": {
        "object": "业务操作",
        "collectors": ["current_profile"],
        "pass_when": "导出中有原发或接收证据",
        "fail_when": "没有不可否认措施时写证据不足",
    },
}


def clause_by_id(clause_id: str) -> dict:
    for item in load_clauses():
        if item["id"] == clause_id:
            return item
    raise KeyError(clause_id)


def build_plan() -> list[dict]:
    raw = CLAUSES_PATH.read_text(encoding="utf-8")
    units = []
    for index, clause in enumerate(load_clauses(), start=1):
        excerpt = clause["excerpt"]
        if excerpt not in raw:
            raise RuntimeError(f"{clause['id']} 的摘录不在条款卡原文中")
        extra = JUDGED.get(clause["id"])
        if extra is None and clause["layer"] in CHECKLIST_LAYERS:
            extra = {
                "object": "材料文件",
                "collectors": ["current_profile"],
                "pass_when": "本次提交里有该条制度文件，且正文含有该条原文",
                "fail_when": "没有真实文件则未提供；读不到或对不上原文则证据不足",
            }
        units.append(
            {
                "unit_id": f"U{index:02d}",
                "name": clause["name"],
                "clause_id": clause["id"],
                "clause_title": clause["title"],
                "excerpt": excerpt,
                "standard": clause["standard"],
                "layer": clause["layer"],
                "strength": clause["strength"],
                "high_risk": bool(clause["high_risk"]),
                "object": extra["object"] if extra else "未提供对象",
                "expert": clause["layer"],
                "collectors": extra["collectors"] if extra else [],
                "pass_when": extra["pass_when"] if extra else "本阶段不判定",
                "fail_when": extra["fail_when"] if extra else "未提供对象，不进入判定",
                "judged": extra is not None,
            }
        )
    return units


def _index(facts: list[dict]) -> dict[str, dict]:
    return {item["id"]: item for item in facts}


def judge(facts: list[dict]) -> list[dict]:
    by_tool: dict[str, list[dict]] = {}
    for item in facts:
        by_tool.setdefault(item["tool"], []).append(item)
    by_id = {unit["clause_id"]: unit for unit in build_plan()}
    by_fact = {item["id"]: item for item in facts}
    results = [
        _judge_channel(by_id["NET-CONF"], by_tool),
        _judge_channel(by_id["APP-TRANS-CONF"], by_tool),
        _judge_storage(by_id["APP-STORE-CONF"], by_tool),
        _judge_app_login(by_id["APP-AUTH"], by_fact),
        _gap(by_id["DEV-AUTH"], by_fact, "F-014", "配置导出没有设备登录鉴别措施。"),
        _gap(by_id["DEV-REMOTE"], by_fact, "F-008", "配置导出的路由里没有远程管理入口。"),
        _gap(by_id["DEV-ACL"], by_fact, "F-013", "配置导出没有系统资源访问控制信息的完整性措施。"),
        _gap(by_id["DEV-LABEL"], by_fact, "F-009", "配置导出没有安全标记完整性措施。"),
        _gap(by_id["DEV-LOG"], by_fact, "F-010", "配置导出没有日志完整性措施。"),
        _gap(by_id["DEV-BIN"], by_fact, "F-011", "配置导出没有重要可执行程序完整性措施。"),
        _gap(by_id["APP-ACL"], by_fact, "F-013", "配置导出没有应用访问控制信息的完整性措施。"),
        _gap(by_id["APP-TRANS-INT"], by_fact, "F-015", "配置导出没有传输完整性措施。"),
        _gap(by_id["APP-STORE-INT"], by_fact, "F-007", "用户表导出里没有完整性字段。"),
        _gap(by_id["APP-NR"], by_fact, "F-012", "配置导出没有不可否认证据。"),
    ]
    results.extend(_judge_checklist(unit, by_fact) for unit in build_plan() if unit["layer"] in CHECKLIST_LAYERS)
    results.append(_judge_algorithm(by_tool))
    for item in results:
        if item["result"] == "不符合" and not item["fact_ids"]:
            raise RuntimeError(f"{item['name']} 的不符合缺少事实编号")
    return results


def _judge_channel(unit: dict, by_tool: dict[str, list[dict]]) -> dict:
    channel = by_tool.get("channel_facts", [None])[0]
    login = by_tool.get("login_observation", [None])[0]
    if channel is None:
        return _row(unit, "证据不足", [], "没有信道采集事实")
    protocol = channel["data"].get("protocol")
    fact_ids: list[str] = []
    reasons: list[str] = []
    if protocol == "HTTP":
        fact_ids.append(channel["id"])
        reasons.append(f"事实 {channel['id']} 记录协议为 HTTP")
    if login and login["data"].get("password_in_clear") is True:
        fact_ids.append(login["id"])
        reasons.append(f"事实 {login['id']} 记录口令以明文出现")
    if fact_ids:
        return _row(
            unit,
            "不符合",
            fact_ids,
            "；".join(reasons) + "。通信过程中的重要数据没有机密性保护。",
            "为信道加上机密性保护后再复测。本阶段只做丙档预检，不切换配置。",
        )
    if (
        protocol
        and protocol != "HTTP"
        and login
        and login["data"].get("observed")
        and login["data"].get("password_in_clear") is False
    ):
        return _row(unit, "符合", [channel["id"]], "信道不是明文，登录摘要里口令未以明文出现。")
    return _row(unit, "证据不足", [], "信道事实不足以判断通信机密性。")


def _judge_storage(unit: dict, by_tool: dict[str, list[dict]]) -> dict:
    fields = by_tool.get("field_storage", [])
    if len(fields) < 2:
        return _row(unit, "证据不足", [], "缺少口令或手机号的存储事实")
    plain = [item for item in fields if item["data"].get("storage") == "plaintext"]
    unknown = [item for item in fields if item["data"].get("storage") == "unknown"]
    if plain:
        names = "、".join(item["data"]["field"] for item in plain)
        ids = [item["id"] for item in plain]
        detail = "、".join(
            f"事实 {item['id']} 显示{item['data']['field']}为明文" for item in plain
        )
        return _row(
            unit,
            "不符合",
            ids,
            detail + f"。重要数据（{names}）在库中原样存放。",
            "口令和手机号不要以明文入库。本阶段只记录建议，不改数据库。",
        )
    if unknown:
        return _row(unit, "证据不足", [], "有重要字段看不出存储形态。")
    ids = [item["id"] for item in fields]
    return _row(unit, "符合", ids, "口令和手机号都不是明文。")


def _judge_checklist(unit: dict, by_fact: dict[str, dict]) -> dict:
    from console.checklist_text import matching_quote, read_material, resolve_material

    fact_id = f"F-CL-{unit['clause_id']}"
    fact = by_fact.get(fact_id)
    filename = str((fact or {}).get("data", {}).get("filename") or "").strip()
    path = resolve_material(filename)
    if path is None:
        return _row(unit, "未提供", [], "本次提交里没有该条制度文件，本项保持未提供。")
    text = read_material(path)
    if text is None:
        return _row(unit, "证据不足", [fact_id], f"文件 {path.name} 读不到，不能对照条款原文。")
    quote = matching_quote(text, unit["excerpt"])
    if not quote or quote not in text:
        return _row(unit, "证据不足", [fact_id], f"文件 {path.name} 的正文里没有该条原文，不能写成符合。")
    return _row(
        unit,
        "符合",
        [fact_id],
        f"文件 {path.name} 中原样出现该条原文，并已在正文中核对。",
        material_quote=quote,
    )


def _gap(unit: dict, by_fact: dict[str, dict], fact_id: str, reason: str) -> dict:
    fact = by_fact.get(fact_id)
    if fact is None:
        return _row(unit, "证据不足", [], "配置导出里没有对应事实。")
    data = fact["data"]
    if data.get("present") is True or data.get("integrity_columns") or data.get("remote_admin") is True:
        return _row(unit, "符合", [fact_id], f"事实 {fact_id} 显示该项措施已出现在配置导出中。")
    return _row(unit, "证据不足", [fact_id], f"事实 {fact_id}：{reason}看不出来的项不写成不符合。")


def _judge_app_login(unit: dict, by_fact: dict[str, dict]) -> dict:
    fact = by_fact.get("F-006")
    if fact is None:
        return _row(unit, "证据不足", [], "没有应用登录方式的配置导出。")
    method = fact["data"].get("method")
    if method == "plaintext":
        return _row(
            unit,
            "不符合",
            ["F-006"],
            "事实 F-006 显示应用登录按明文比对口令。",
            "口令不要按原样比对。本阶段只记录建议，不改登录逻辑。",
        )
    if method in ("sha256", "sm3"):
        return _row(unit, "符合", ["F-006"], f"事实 F-006 显示应用登录使用{method}校验口令。")
    return _row(unit, "证据不足", ["F-006"], "事实 F-006 看不出登录口令的校验方式。")


def _channel_family(channel: dict) -> str:
    blob = " ".join(
        str(channel["data"].get(key) or "")
        for key in ("protocol", "suite", "cert_signature_algorithm")
    )
    if channel["data"].get("protocol") == "HTTP":
        return "无"
    has_sm = any(token in blob for token in ("SM2", "SM3", "SM4"))
    upper = blob.upper()
    has_intl = any(token in upper for token in ("AES", "RSA", "ECDSA", "SHA256", "SHA-256", "CHACHA"))
    if has_sm and has_intl:
        return "混合"
    if has_sm:
        return "SM"
    if has_intl:
        return "国际"
    return "未知"


def _judge_algorithm(by_tool: dict[str, list[dict]]) -> dict:
    channel = by_tool.get("channel_facts", [None])[0]
    fields = by_tool.get("field_storage", [])
    unit = {
        "unit_id": "ALG",
        "name": "算法合规性",
        "clause_id": "通用检查",
        "clause_title": "算法合规性",
        "excerpt": "国际算法出现在重要数据保护上时，预检标成需要处理。",
        "standard": "通用检查，不单独打分",
        "object": "信道、口令、手机号",
    }
    if channel is None or len(fields) < 2:
        return _row(unit, "证据不足", [], "缺少信道或字段事实，不能判断算法。")
    family = _channel_family(channel)
    if family == "未知" or "待探测" in str(channel["data"].get("suite")):
        return _row(unit, "证据不足", [channel["id"]], "信道套件还没有探测到。")
    used = [channel["id"]]
    detail = [f"事实 {channel['id']} 的信道算法族为{family}"]
    families = {family}
    for item in fields:
        algorithm = item["data"].get("algorithm")
        used.append(item["id"])
        if algorithm in ("SM2", "SM3", "SM4"):
            families.add("SM")
            detail.append(f"事实 {item['id']} 的{item['data']['field']}算法为{algorithm}")
        elif algorithm in ("SHA-256", "AES"):
            families.add("国际")
            detail.append(f"事实 {item['id']} 的{item['data']['field']}算法为{algorithm}")
        else:
            families.add("无")
            detail.append(f"事实 {item['id']} 的{item['data']['field']}没有密码算法")
    if families == {"SM"}:
        return _row(unit, "符合", used, "；".join(detail) + "。保护重要数据的算法是 SM2、SM3、SM4。")
    return _row(
        unit,
        "不符合",
        used,
        "；".join(detail) + "。重要数据保护没有全部使用 SM2、SM3、SM4。",
        "已加密不等于算法合规。国际算法或明文都要单独标出。",
    )


def _row(
    unit: dict,
    result: str,
    fact_ids: list[str],
    reason: str,
    suggestion: str = "",
    material_quote: str = "",
) -> dict:
    row = {
        "unit_id": unit["unit_id"],
        "name": unit["name"],
        "clause_id": unit["clause_id"],
        "clause_title": unit["title"] if "title" in unit else unit["clause_title"],
        "excerpt": unit["excerpt"],
        "standard": unit["standard"],
        "object": unit["object"],
        "result": result,
        "fact_ids": fact_ids,
        "source": f"条款卡 {unit['clause_id']}（{unit['standard']}）",
        "reason": reason,
        "suggestion": suggestion,
        "high_risk": bool(unit.get("high_risk")),
        "strength": unit.get("strength", ""),
    }
    if material_quote:
        row["material_quote"] = material_quote
    return row


def build_report(judgments: list[dict], facts: list[dict]) -> str:
    lines = [
        REPORT_FIRST_LINE,
        "",
        "未授权系统不在范围内，最终以专业人员测评为准。以下为自测参考，不是正式密评结论。",
        "",
        "## 不符合项",
        "",
    ]
    noncompliant = [item for item in judgments if item["result"] == "不符合"]
    noncompliant.sort(key=lambda item: (0 if item.get("high_risk") else 1, {"应": 0, "宜": 1, "可": 2}.get(item.get("strength"), 3), item["name"]))
    for item in noncompliant:
        ids = "、".join(item["fact_ids"])
        lines.extend(
            [
                f"### {item['name']}",
                f"参考结论：{item['result']}",
                f"事实编号：{ids}",
                f"条款出处：{item['source']}",
                f"原文摘录：{item['excerpt']}",
                f"对象：{item['object']}",
                f"理由：{item['reason']}",
                f"修改建议：{item['suggestion']}",
                "",
            ]
        )
    lines.extend(["## 未提供", ""])
    for item in judgments:
        if item["result"] != "未提供":
            continue
        lines.extend(
            [
                f"### {item['name']}",
                f"参考结论：{item['result']}",
                f"条款出处：{item['source']}",
                f"理由：{item['reason']}",
                "",
            ]
        )
    lines.extend(["## 证据不足", ""])
    for item in judgments:
        if item["result"] != "证据不足":
            continue
        ids = "、".join(item["fact_ids"]) or "无"
        lines.extend(
            [
                f"### {item['name']}",
                f"参考结论：{item['result']}",
                f"事实编号：{ids}",
                f"条款出处：{item['source']}",
                f"理由：{item['reason']}",
                "",
            ]
        )
    lines.extend(["## 其余参考结论", ""])
    for item in judgments:
        if item["result"] != "符合":
            continue
        ids = "、".join(item["fact_ids"]) or "无"
        lines.extend(
            [
                f"### {item['name']}",
                f"参考结论：{item['result']}",
                f"事实编号：{ids}",
                f"条款出处：{item['source']}",
                f"理由：{item['reason']}",
            ]
        )
        if item.get("material_quote"):
            lines.append(f"材料摘录：{item['material_quote']}")
        lines.append("")
    lines.extend(["## 采集事实", ""])
    for fact in facts:
        lines.append(f"- {fact['id']}（{fact['tool']}）：{json.dumps(fact['data'], ensure_ascii=False)}")
    lines.append("")
    text = "\n".join(lines)
    if not text.startswith(REPORT_FIRST_LINE):
        raise RuntimeError("报告声明丢失")
    return text
