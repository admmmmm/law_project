export const caseInfo = {
  id: "BJJC-2026-0418",
  name: "张某涉嫌司法工作人员职务犯罪辅助分析案",
  status: "已立案侦查",
  unit: "某检察侦查部门",
  date: "2026-04-18",
  summary:
    "围绕司法工作人员张某在案件办理过程中的异常资金往来、频繁通联、关系勾连与关键时间节点行为展开辅助分析。"
};

export const evidenceFiles = [
  { name: "银行流水_张某_2026Q1.xlsx", type: "Excel", source: "银行调取", status: "已解析", entities: 18, relations: 42, risk: "高" },
  { name: "通联详单_核心人员.csv", type: "CSV", source: "运营商", status: "已解析", entities: 23, relations: 71, risk: "中" },
  { name: "讯问笔录_李某.docx", type: "Word", source: "卷宗材料", status: "已解析", entities: 9, relations: 16, risk: "中" },
  { name: "涉案财物清单.pdf", type: "PDF", source: "监察移送", status: "待复核", entities: 12, relations: 8, risk: "低" },
  { name: "出入记录_办案区.csv", type: "CSV", source: "门禁系统", status: "已解析", entities: 14, relations: 29, risk: "中" }
];

export const people = [
  { id: "p1", name: "张某", role: "核心嫌疑人", risk: 89, tags: ["司法工作人员", "关键账户", "多线重合"] },
  { id: "p2", name: "李某", role: "密切关系人", risk: 76, tags: ["频繁通联", "资金中转"] },
  { id: "p3", name: "王某", role: "资金关联人", risk: 68, tags: ["企业账户", "大额转账"] },
  { id: "p4", name: "赵某", role: "外围联系人", risk: 51, tags: ["轨迹重合"] },
  { id: "p5", name: "关联企业X", role: "资金节点", risk: 72, tags: ["过桥账户", "离岸转出"] }
];

export const graphNodes = [
  { id: "p1", label: "张某", x: 380, y: 225, type: "suspect" },
  { id: "p2", label: "李某", x: 185, y: 155, type: "person" },
  { id: "p3", label: "王某", x: 585, y: 145, type: "person" },
  { id: "p4", label: "赵某", x: 150, y: 350, type: "person" },
  { id: "p5", label: "企业X", x: 610, y: 345, type: "company" },
  { id: "a1", label: "账户A", x: 390, y: 65, type: "account" },
  { id: "a2", label: "离岸账户", x: 765, y: 260, type: "account" }
];

export const graphEdges = [
  { from: "p1", to: "p2", label: "频繁通联", kind: "contact" },
  { from: "p1", to: "a1", label: "控制账户", kind: "money" },
  { from: "p2", to: "p4", label: "共同出现", kind: "track" },
  { from: "p1", to: "p3", label: "案件关联", kind: "case" },
  { from: "p3", to: "p5", label: "资金往来", kind: "money" },
  { from: "p5", to: "a2", label: "异常转出", kind: "money" },
  { from: "a1", to: "p2", label: "分拆转账", kind: "money" }
];

export const transactions = [
  { time: "04-06 21:13", from: "账户A", to: "李某", amount: 48000, tag: "分拆转账", risk: "高" },
  { time: "04-07 00:42", from: "李某", to: "王某", amount: 52000, tag: "午夜交易", risk: "高" },
  { time: "04-08 09:35", from: "王某", to: "企业X", amount: 300000, tag: "企业过桥", risk: "中" },
  { time: "04-10 16:02", from: "企业X", to: "离岸账户", amount: 860000, tag: "异常外流", risk: "高" },
  { time: "04-12 18:20", from: "账户A", to: "赵某", amount: 12000, tag: "低额试探", risk: "中" }
];

export const collisionFindings = [
  { title: "人物 x 资金", result: "张某关系圈内出现多笔拆分转账，收款对象与密切关系人重叠。", level: "高" },
  { title: "人物 x 行为", result: "李某与赵某在关键时间窗口存在轨迹重合，并伴随高频通联。", level: "中" },
  { title: "资金 x 时间", result: "异常资金流动集中于案件关键节点前后 72 小时。", level: "高" },
  { title: "行为 x 时间", result: "案发后出现夜间登录、文件访问和通联突增。", level: "中" }
];

export const reports = [
  "建议优先核查账户A与李某之间的分拆转账记录。",
  "建议围绕企业X及离岸账户补充调取资金流向证明材料。",
  "建议复核04-06至04-10期间的通联、出入和操作日志。",
  "建议将李某列为高关联密切关系人，形成单独画像卡片。"
];
