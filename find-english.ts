import fs from 'fs';
import * as cheerio from 'cheerio';

function findEnglishTexts(file: string) {
  const content = fs.readFileSync(file, 'utf8');
  // quick and dirty grab between <template> and </template>
  const match = content.match(/<template>([\s\S]*)<\/template>/);
  if (!match) return;
  const tpl = match[1];
  const $ = cheerio.load(tpl, null, false);
  
  $('*').contents().each((i, el) => {
    if (el.type === 'text') {
      const text = el.data.trim();
      if (text && /[A-Za-z]/.test(text)) {
        // filter out things like {{ ... }} or pure numbers/symbols if any,
        // but here we just print all text with A-Z in it.
        if (!text.includes('{{') && !text.includes('}}')) {
           console.log(file, ':', text);
        }
      }
    }
  });
}

['src/views/Dashboard.vue', 'src/views/Graph.vue', 'src/views/Portrait.vue', 'src/views/Intelligence.vue', 'src/components/Header.vue', 'src/components/Sidebar.vue'].forEach(findEnglishTexts);
