import fs from 'fs';
import * as cheerio from 'cheerio';

function fixLayout() {
  // Fix Portrait.vue
  let content = fs.readFileSync('src/views/Portrait.vue', 'utf8');
  let $ = cheerio.load(content, null, false);
  $('header').remove(); // remove duplicates
  $('aside.fixed').each((i, el) => {
    $(el).removeClass('fixed right-0 top-14 h-[calc(100vh-3.5rem)]').addClass('flex flex-col shrink-0 overflow-hidden');
  });
  $('main.min-h-screen').removeClass('min-h-screen').addClass('flex-1 overflow-y-auto');
  
  let newHtml = $.html();
  // decode HTML entities
  newHtml = newHtml.replace(/&apos;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
  newHtml = newHtml.replace(/<main/, '<div class="flex flex-1 overflow-hidden h-full">\n<main');
  newHtml = newHtml.replace(/<\/aside>/, '</aside>\n</div>');
  content = content.replace(/<template>[\s\S]*?<\/template>/i, `<template>\n${newHtml}\n</template>`);
  fs.writeFileSync('src/views/Portrait.vue', content);

  // Fix Graph.vue
  content = fs.readFileSync('src/views/Graph.vue', 'utf8');
  $ = cheerio.load(content, null, false);
  $('aside.fixed').each((i, el) => {
    $(el).removeClass('fixed right-0 top-14 h-[calc(100vh-3.5rem)]').addClass('shrink-0');
  });
  newHtml = $.html();
  newHtml = newHtml.replace(/&apos;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
  content = content.replace(/<template>[\s\S]*?<\/template>/i, `<template>\n${newHtml}\n</template>`);
  fs.writeFileSync('src/views/Graph.vue', content);

  // Fix Intelligence.vue
  content = fs.readFileSync('src/views/Intelligence.vue', 'utf8');
  $ = cheerio.load(content, null, false);
  $('aside.fixed').each((i, el) => {
    $(el).removeClass('fixed right-0 top-14 h-[calc(100vh-3.5rem)] w-80').addClass('shrink-0 w-80 border-l');
  });
  $('main').removeClass('mr-80 min-h-screen').addClass('flex-1 overflow-y-auto');
  newHtml = $.html();
  newHtml = newHtml.replace(/&apos;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
  newHtml = newHtml.replace(/<main/, '<div class="flex flex-1 overflow-hidden h-full">\n<main');
  newHtml = newHtml.replace(/<\/aside>/, '</aside>\n</div>');
  content = content.replace(/<template>[\s\S]*?<\/template>/i, `<template>\n${newHtml}\n</template>`);
  fs.writeFileSync('src/views/Intelligence.vue', content);
}

fixLayout();
