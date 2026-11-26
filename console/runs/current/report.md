送评前预检，非正式密评

未授权系统不在范围内，最终以专业人员测评为准。以下为自测参考，不是正式密评结论。

## 不符合项

### 通信机密性
参考结论：不符合
事实编号：F-002、F-003
条款出处：条款卡 NET-CONF（GB/T 39786）
原文摘录：应采用密码技术保证通信过程中重要数据的机密性。
对象：浏览器到网站的信道
理由：事实 F-002 记录协议为 HTTP；事实 F-003 记录口令以明文出现。通信过程中的重要数据没有机密性保护。
修改建议：为信道加上机密性保护后再复测。本阶段只做丙档预检，不切换配置。

### 存储机密性
参考结论：不符合
事实编号：F-004、F-005
条款出处：条款卡 APP-STORE-CONF（GB/T 39786）
原文摘录：应采用密码技术保证重要数据在存储过程中的机密性。
对象：登录口令字段、资料页手机号字段
理由：事实 F-004 显示口令为明文、事实 F-005 显示手机号为明文。重要数据（口令、手机号）在库中原样存放。
修改建议：口令和手机号不要以明文入库。本阶段只记录建议，不改数据库。

## 采集事实

- F-001（current_profile）：{"grade": "丙", "entry": "http://127.0.0.1:8000"}
- F-002（channel_facts）：{"protocol": "HTTP", "suite": "无", "cert_signature_algorithm": null}
- F-003（login_observation）：{"observed": true, "password_in_clear": true, "protocol": "HTTP", "suite": "无"}
- F-004（field_storage）：{"field": "口令", "storage": "plaintext"}
- F-005（field_storage）：{"field": "手机号", "storage": "plaintext"}
