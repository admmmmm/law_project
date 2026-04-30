import fs from 'fs';

function processFile(filename: string) {
  let content = fs.readFileSync(filename, 'utf8');
  
  content = content.replace(/[\s\S]*?<template>/i, '<template>');
  
  fs.writeFileSync(filename, content);
  console.log('Finalized', filename);
}

['src/views/Graph.vue', 'src/views/Portrait.vue', 'src/views/Intelligence.vue'].forEach(processFile);
