import fs from 'fs';

function fixFile(filename: string, replacements: [RegExp | string, string][]) {
  let content = fs.readFileSync(filename, 'utf8');
  for (const [search, replace] of replacements) {
    if (typeof search === 'string') {
        content = content.split(search).join(replace);
    } else {
        content = content.replace(search, replace);
    }
  }
  fs.writeFileSync(filename, content);
}

// 1. Remove English visible text
fixFile('src/views/Graph.vue', [
  ['TW-P99283-01', '综研-99283-01'],
  ['账户_4420_HK', '账户_4420_香港']
]);

fixFile('src/views/Portrait.vue', [
  ['MAC', '物理网卡'],
  ['延迟: 12ms', '延迟: 12毫秒']
]);

fixFile('src/views/Intelligence.vue', [
  ['2024-DF-0912', '案件-2024-0912'],
  ['A04', '甲04'],
  ['f9a2...', '校验段...']
]);

fixFile('src/views/Dashboard.vue', [
  ['主体A', '目标甲'],
  ['主体C', '目标丙']
]);

