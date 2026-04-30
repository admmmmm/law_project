import fs from 'fs';

function fixFile(filename: string) {
  let content = fs.readFileSync(filename, 'utf8');
  content = content.replace(/<aside([^>]*class="[^"]*)w-(72|80|64)([^"]*")>/g, (match, p1, p2, p3) => {
    if (!match.includes('shrink-0')) {
        return `<aside${p1}w-${p2} shrink-0${p3}>`;
    }
    return match;
  });
  content = content.replace(/<main([^>]*class="[^"]*)flex-1([^"]*")>/g, (match, p1, p2) => {
    if (!match.includes('min-w-0')) {
        return `<main${p1}flex-1 min-w-0${p2}>`;
    }
    return match;
  });
  fs.writeFileSync(filename, content);
}

const views = ['src/views/Dashboard.vue', 'src/views/Graph.vue', 'src/views/Portrait.vue', 'src/views/Intelligence.vue'];
views.forEach(fixFile);
