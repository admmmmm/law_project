import fs from 'fs';

function fixTpl(file: string) {
  let content = fs.readFileSync(file, 'utf8');
  content = content.replace(/<template>\s*<template>/g, '<template>');
  content = content.replace(/<\/template>\s*<\/template>/g, '</template>');
  fs.writeFileSync(file, content);
}
['src/views/Intelligence.vue', 'src/views/Portrait.vue'].forEach(fixTpl);
