import fs from 'fs';

function replaceInFile(filename: string, replacements: [RegExp | string, string][]) {
  let content = fs.readFileSync(filename, 'utf8');
  for (const [search, replace] of replacements) {
    content = content.replace(search, replace);
  }
  fs.writeFileSync(filename, content);
}

replaceInFile('src/views/Dashboard.vue', [
  ['#CN-4421', '中发-4421']
]);

replaceInFile('src/views/Graph.vue', [
  ['AI 智能研判面板', '智能研判面板']
]);
