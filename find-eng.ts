import fs from 'fs';
import * as cheerio from 'cheerio';

function checkFile(file: string) {
  const content = fs.readFileSync(file, 'utf8');
  const match = content.match(/<template>([\s\S]*)<\/template>/);
  if (!match) return;
  
  const $ = cheerio.load(match[1], null, false);
  
  // Remove material icons from checking
  $('.material-symbols-outlined').remove();
  
  let found = false;
  $('*').contents().each((i, el) => {
    if (el.type === 'text') {
      const text = el.data.trim();
      if (text && /[A-Za-z]/.test(text) && !text.includes('{{') && !text.includes('}}')) {
        console.log(`[${file}] English found: "${text}"`);
        found = true;
      }
    }
  });
}

['src/views/Dashboard.vue', 'src/views/Graph.vue', 'src/views/Portrait.vue', 'src/views/Intelligence.vue', 'src/components/Header.vue', 'src/components/Sidebar.vue'].forEach(checkFile);
