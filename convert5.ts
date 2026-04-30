import fs from 'fs';

function replaceInFile(filename: string, replacements: [RegExp | string, string][]) {
  let content = fs.readFileSync(filename, 'utf8');
  for (const [search, replace] of replacements) {
    content = content.replace(search, replace);
  }
  fs.writeFileSync(filename, content);
}

// Sidebar.vue
replaceInFile('src/components/Sidebar.vue', [
  ['PROSECUTION', '检察系统']
]);

// Header.vue
replaceInFile('src/components/Header.vue', [
  ['Investigator Profile', '调查员头像']
]);

// Graph.vue
replaceInFile('src/views/Graph.vue', [
  ['程伟良 (Cheng, Wei-Liang)', '程伟良'],
  ['ID: TW-P99283-01', '编号: TW-P99283-01'],
  ['黄莎莎 (Wong, Sarah)', '黄莎莎'],
  ['顶峰创投 (Zenith Ventures)', '顶峰创投'],
  ['生成全案卷宗 (PDF)', '生成全案卷宗']
]);

// Portrait.vue
replaceInFile('src/views/Portrait.vue', [
  ['#BJ-2024-0812-CN', '编号_2024_0812'],
  ['PX-992-04182', '普信-992-04182'],
  ['CHENG, WEI', '程伟'],
  ['VAL_Σ: 0.89', '指标综合值: 0.89'],
  ['AES-256', '高级加密标准'],
  ['AI 智能推理链', '智能推理链'],
  ['AI 智能推理面板', '智能推理面板']
]);

// Intelligence.vue
replaceInFile('src/views/Intelligence.vue', [
  ['HASH: f9a2...', '校验码: f9a2...'],
  ['主观意图逻辑链 (Logical Chain of Subjective Intent)', '主观意图逻辑链'],
  ['知情阶段 (Perception)', '知情阶段'],
  ['认知认同 (Cognitive Recognition)', '认知认同'],
  ['故意性 (Intentionality)', '故意性'],
  ['研判结论 (Conclusion)', '研判结论'],
  ['起诉建议书草案 (Draft Prosecution Suggestion)', '起诉建议书草案'],
  ['AI 智能研判面板', '智能研判面板'],
  ['AI 推理引擎报告', '推理引擎报告']
]);

// Dashboard.vue
replaceInFile('src/views/Dashboard.vue', [
  ['14:22:10 UTC', '14:22:10'],
  ['11:05:45 UTC', '11:05:45'],
  ['08:00:00 UTC', '08:00:00'],
  ['AI思考进程记录', '智能思考进程记录'],
  ['AI智能研判面板', '智能研判面板'],
  ['#CN-2024-4421', '中发-2024-4421'],
  ['#CN-2024-3819', '中发-2024-3819'],
  ['#CN-2024-1104', '中发-2024-1104'],
  ['#CN-2024-9912', '中发-2024-9912'],
  ['#CN-2024-2211', '中发-2024-2211'],
  ['#CN-2024-3388', '中发-2024-3388']
]);
