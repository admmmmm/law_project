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

fixFile('src/views/Intelligence.vue', [
  ['2023-DF-0912', '案件-2023-0912'],
]);
