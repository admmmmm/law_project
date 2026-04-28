# 数据样本1分析与清洗入图说明

## 数据概况
- 源文件：4 个 .xls 文件
- 注册信息记录：5 条
- 交易明细记录：6081 条
- 识别账号：jerry123, tom123
- 识别身份证号：110108199807051211, 231025199102022212

## 交易统计
- 交易笔数按账号：{'tom123': 121, 'jerry123': 5960}
- 收支方向：{'入': 1523, '出': 4558}
- 交易状态：{'未知': 6081}
- 金额合计：786463.99
- 最大单笔金额：50000.0

## 清洗策略
- 删除空行，压缩多余空白，统一字段别名为英文键名。
- 从文件路径补充身份证号与微信账号，解决表内字段缺失时的主体归属问题。
- 保留原始来源文件和 sheet，便于证据追溯。
- 交易金额转为可统计数值；无法识别的字段保留原字段名。

## 图谱录入结构
- 节点数：6197
- 边数：8935
- 核心节点类型：person、id_card、phone、wechat_account、transaction、counterparty。
- 核心关系类型：OWNS_WECHAT_ACCOUNT、BOUND_TO_ID_CARD、HAS_TRANSACTION、TRANSACTS_WITH、PAYS_TO。

## 输出文件
- cleaned_registration.csv：清洗后的注册信息。
- cleaned_trades.csv：清洗后的交易明细。
- graph_import.json：可直接用于图谱录入的 nodes/edges JSON。
- graph_documents.jsonl：可供 HippoRAG 等文本索引工具录入的事实句。
