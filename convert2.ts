import fs from 'fs';
import * as cheerio from 'cheerio';

function processFile(filename: string) {
  let content = fs.readFileSync(filename, 'utf8');
  
  // Extract template content
  const templateMatch = content.match(/<template>([\s\S]*?)<\/template>/i);
  if (!templateMatch) return;
  
  const html = templateMatch[1];
  const $ = cheerio.load(html, null, false);
  
  // Remove duplicate navs or sidebars that have w-60 (the main left sidebar)
  $('nav.w-60').remove();
  $('aside.w-60').each((i, el) => {
     // Wait, graph has other asides. Check if it's the main left nav by looking at 'fixed left-0 top-0'
     const className = $(el).attr('class') || '';
     if (className.includes('fixed') && className.includes('left-0') && className.includes('w-60')) {
       $(el).remove();
     }
  });
  
  // Remove top header
  $('header').each((i, el) => {
     const className = $(el).attr('class') || '';
     if (className.includes('sticky top-0') && className.includes('z-50') && className.includes('h-14')) {
       $(el).remove();
     }
  });
  
  // Fix main margin-left (ml-60) since it's now handled by the parent layout
  $('main.ml-60').removeClass('ml-60');
  
  // Update content
  let newHtml = $.html();
  // decode HTML entities that cheerio might have added
  newHtml = newHtml.replace(/&apos;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
  
  // write back
  const newContent = content.replace(/<template>[\s\S]*?<\/template>/i, `<template>\n${newHtml}\n</template>`);
  fs.writeFileSync(filename, newContent);
  console.log('Cleaned', filename);
}

['src/views/Graph.vue', 'src/views/Portrait.vue', 'src/views/Intelligence.vue'].forEach(processFile);
