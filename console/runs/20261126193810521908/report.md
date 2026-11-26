送评前预检，非正式密评

未授权系统不在范围内，最终以专业人员测评为准。以下为自测参考，不是正式密评结论。

## 不符合项

### 存储机密性
参考结论：不符合
事实编号：F-004、F-005
条款出处：条款卡 APP-STORE-CONF（GB/T 39786）
原文摘录：应采用密码技术保证重要数据在存储过程中的机密性。
对象：登录口令字段、资料页手机号字段
理由：事实 F-004 显示口令为明文、事实 F-005 显示手机号为明文。重要数据（口令、手机号）在库中原样存放。
修改建议：口令和手机号不要以明文入库。本阶段只记录建议，不改数据库。

### 应用身份鉴别
参考结论：不符合
事实编号：F-006
条款出处：条款卡 APP-AUTH（GB/T 39786）
原文摘录：应采用密码技术对登录用户进行身份鉴别，保证应用系统用户身份的真实性。
对象：应用登录口令
理由：事实 F-006 显示应用登录按明文比对口令。
修改建议：口令不要按原样比对。本阶段只记录建议，不改登录逻辑。

### 通信机密性
参考结论：不符合
事实编号：F-002、F-003
条款出处：条款卡 NET-CONF（GB/T 39786）
原文摘录：应采用密码技术保证通信过程中重要数据的机密性。
对象：浏览器到网站的信道
理由：事实 F-002 记录协议为 HTTP；事实 F-003 记录口令以明文出现。通信过程中的重要数据没有机密性保护。
修改建议：为信道加上机密性保护后再复测。本阶段只做丙档预检，不切换配置。

### 重要数据传输机密性
参考结论：不符合
事实编号：F-002、F-003
条款出处：条款卡 APP-TRANS-CONF（GB/T 39786）
原文摘录：应采用密码技术保证重要数据在传输过程中的机密性。
对象：重要数据传输
理由：事实 F-002 记录协议为 HTTP；事实 F-003 记录口令以明文出现。通信过程中的重要数据没有机密性保护。
修改建议：为信道加上机密性保护后再复测。本阶段只做丙档预检，不切换配置。

### 算法合规性
参考结论：不符合
事实编号：F-002、F-004、F-005
条款出处：条款卡 通用检查（通用检查，不单独打分）
原文摘录：国际算法出现在重要数据保护上时，预检标成需要处理。
对象：信道、口令、手机号
理由：事实 F-002 的信道算法族为无；事实 F-004 的口令没有密码算法；事实 F-005 的手机号没有密码算法。重要数据保护没有全部使用 SM2、SM3、SM4。
修改建议：已加密不等于算法合规。国际算法或明文都要单独标出。

## 未提供

### 物理访问身份鉴别
参考结论：未提供
条款出处：条款卡 PHY-AUTH（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 电子门禁记录存储完整性
参考结论：未提供
条款出处：条款卡 PHY-GATE（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 视频监控记录存储完整性
参考结论：未提供
条款出处：条款卡 PHY-VIDEO（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 密码应用安全管理制度
参考结论：未提供
条款出处：条款卡 MGMT-POLICY（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 操作规程
参考结论：未提供
条款出处：条款卡 MGMT-PROCEDURE（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 制度修订
参考结论：未提供
条款出处：条款卡 MGMT-REVIEW（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 制度发布
参考结论：未提供
条款出处：条款卡 MGMT-PUBLISH（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 制度执行记录
参考结论：未提供
条款出处：条款卡 MGMT-RECORD（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 人员遵守法律法规
参考结论：未提供
条款出处：条款卡 PE-LAW（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 岗位责任
参考结论：未提供
条款出处：条款卡 PE-DUTY（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 上岗培训
参考结论：未提供
条款出处：条款卡 PE-TRAIN（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 人员考核
参考结论：未提供
条款出处：条款卡 PE-ASSESS（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 保密与调离
参考结论：未提供
条款出处：条款卡 PE-SECRET（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 密码应用方案
参考结论：未提供
条款出处：条款卡 BUILD-SCHEME（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 密钥安全管理策略
参考结论：未提供
条款出处：条款卡 BUILD-KEY（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 按方案实施
参考结论：未提供
条款出处：条款卡 BUILD-IMPL（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 运行前评估
参考结论：未提供
条款出处：条款卡 BUILD-EVAL（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 运行中执行与复评
参考结论：未提供
条款出处：条款卡 BUILD-RUN（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 应急策略
参考结论：未提供
条款出处：条款卡 EMG-PREP（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 应急启动
参考结论：未提供
条款出处：条款卡 EMG-ACT（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

### 处置后报告
参考结论：未提供
条款出处：条款卡 EMG-REPORT（GB/T 39786）
理由：本次提交里没有该条制度文件，本项保持未提供。

## 证据不足

### 设备身份鉴别
参考结论：证据不足
事实编号：F-014
条款出处：条款卡 DEV-AUTH（GB/T 39786）
理由：事实 F-014：配置导出没有设备登录鉴别措施。看不出来的项不写成不符合。

### 远程管理通道
参考结论：证据不足
事实编号：F-008
条款出处：条款卡 DEV-REMOTE（GB/T 39786）
理由：事实 F-008：配置导出的路由里没有远程管理入口。看不出来的项不写成不符合。

### 系统资源访问控制信息完整性
参考结论：证据不足
事实编号：F-013
条款出处：条款卡 DEV-ACL（GB/T 39786）
理由：事实 F-013：配置导出没有系统资源访问控制信息的完整性措施。看不出来的项不写成不符合。

### 重要信息资源安全标记完整性
参考结论：证据不足
事实编号：F-009
条款出处：条款卡 DEV-LABEL（GB/T 39786）
理由：事实 F-009：配置导出没有安全标记完整性措施。看不出来的项不写成不符合。

### 日志记录完整性
参考结论：证据不足
事实编号：F-010
条款出处：条款卡 DEV-LOG（GB/T 39786）
理由：事实 F-010：配置导出没有日志完整性措施。看不出来的项不写成不符合。

### 重要可执行程序完整性
参考结论：证据不足
事实编号：F-011
条款出处：条款卡 DEV-BIN（GB/T 39786）
理由：事实 F-011：配置导出没有重要可执行程序完整性措施。看不出来的项不写成不符合。

### 访问控制信息完整性
参考结论：证据不足
事实编号：F-013
条款出处：条款卡 APP-ACL（GB/T 39786）
理由：事实 F-013：配置导出没有应用访问控制信息的完整性措施。看不出来的项不写成不符合。

### 重要数据传输完整性
参考结论：证据不足
事实编号：F-015
条款出处：条款卡 APP-TRANS-INT（GB/T 39786）
理由：事实 F-015：配置导出没有传输完整性措施。看不出来的项不写成不符合。

### 重要数据存储完整性
参考结论：证据不足
事实编号：F-007
条款出处：条款卡 APP-STORE-INT（GB/T 39786）
理由：事实 F-007：用户表导出里没有完整性字段。看不出来的项不写成不符合。

### 不可否认性
参考结论：证据不足
事实编号：F-012
条款出处：条款卡 APP-NR（GB/T 39786）
理由：事实 F-012：配置导出没有不可否认证据。看不出来的项不写成不符合。

## 其余参考结论

## 采集事实

- F-001（current_profile）：{"grade": "丙", "entry": "http://127.0.0.1:8000"}
- F-002（channel_facts）：{"protocol": "HTTP", "suite": "无", "cert_signature_algorithm": null, "note": "丙档夹具"}
- F-003（login_observation）：{"observed": true, "password_in_clear": true, "protocol": "HTTP", "suite": "无"}
- F-004（field_storage）：{"field": "口令", "storage": "plaintext", "algorithm": null}
- F-005（field_storage）：{"field": "手机号", "storage": "plaintext", "algorithm": null}
- F-006（current_profile）：{"topic": "app_login", "method": "plaintext"}
- F-007（current_profile）：{"topic": "user_columns", "columns": ["id", "username", "password", "phone"], "integrity_columns": []}
- F-008（current_profile）：{"topic": "routes", "paths": ["/", "/login", "/profile", "/logout", "/health"], "remote_admin": false}
- F-009（current_profile）：{"topic": "security_label", "present": false}
- F-010（current_profile）：{"topic": "log_integrity", "present": false}
- F-011（current_profile）：{"topic": "executable_integrity", "present": false}
- F-012（current_profile）：{"topic": "non_repudiation", "present": false}
- F-013（current_profile）：{"topic": "access_control_integrity", "present": false}
- F-014（current_profile）：{"topic": "device_login", "present": false}
- F-015（current_profile）：{"topic": "transfer_integrity", "present": false}
- F-CL-PHY-AUTH（current_profile）：{"clause_id": "PHY-AUTH", "filename": ""}
- F-CL-PHY-GATE（current_profile）：{"clause_id": "PHY-GATE", "filename": ""}
- F-CL-PHY-VIDEO（current_profile）：{"clause_id": "PHY-VIDEO", "filename": ""}
- F-CL-MGMT-POLICY（current_profile）：{"clause_id": "MGMT-POLICY", "filename": ""}
- F-CL-MGMT-PROCEDURE（current_profile）：{"clause_id": "MGMT-PROCEDURE", "filename": ""}
- F-CL-MGMT-REVIEW（current_profile）：{"clause_id": "MGMT-REVIEW", "filename": ""}
- F-CL-MGMT-PUBLISH（current_profile）：{"clause_id": "MGMT-PUBLISH", "filename": ""}
- F-CL-MGMT-RECORD（current_profile）：{"clause_id": "MGMT-RECORD", "filename": ""}
- F-CL-PE-LAW（current_profile）：{"clause_id": "PE-LAW", "filename": ""}
- F-CL-PE-DUTY（current_profile）：{"clause_id": "PE-DUTY", "filename": ""}
- F-CL-PE-TRAIN（current_profile）：{"clause_id": "PE-TRAIN", "filename": ""}
- F-CL-PE-ASSESS（current_profile）：{"clause_id": "PE-ASSESS", "filename": ""}
- F-CL-PE-SECRET（current_profile）：{"clause_id": "PE-SECRET", "filename": ""}
- F-CL-BUILD-SCHEME（current_profile）：{"clause_id": "BUILD-SCHEME", "filename": ""}
- F-CL-BUILD-KEY（current_profile）：{"clause_id": "BUILD-KEY", "filename": ""}
- F-CL-BUILD-IMPL（current_profile）：{"clause_id": "BUILD-IMPL", "filename": ""}
- F-CL-BUILD-EVAL（current_profile）：{"clause_id": "BUILD-EVAL", "filename": ""}
- F-CL-BUILD-RUN（current_profile）：{"clause_id": "BUILD-RUN", "filename": ""}
- F-CL-EMG-PREP（current_profile）：{"clause_id": "EMG-PREP", "filename": ""}
- F-CL-EMG-ACT（current_profile）：{"clause_id": "EMG-ACT", "filename": ""}
- F-CL-EMG-REPORT（current_profile）：{"clause_id": "EMG-REPORT", "filename": ""}
