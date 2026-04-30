import fs from 'fs';

function processFile(filename: string) {
  let content = fs.readFileSync(filename, 'utf8');
  
  content = content.replace(/<html>[\s\S]*?<body[^>]*>/i, '<template>\n<div class="h-full w-full relative flex">');
  content = content.replace(/<body[^>]*>/i, '<template>\n<div class="h-full w-full relative flex">');
  content = content.replace(/<\/body>[\s\S]*?<\/html>/i, '</div>\n</template>');
  content = content.replace(/<\/body>/i, '</div>\n</template>');
  
  content = content.replace(/<script src="https:\/\/cdn\.tailwindcss\.com.*?"><\/script>/ig, '');
  content = content.replace(/<script id="tailwind-config">[\s\S]*?<\/script>/ig, '');
  
  // We want to remove the left nav and top header, because they are centralized now.
  // We can just find the `<nav ... w-60 ...>` and `<header ... ML-60 ...>` and remove them.
  // It's safer to just do a basic string search.
  
  fs.writeFileSync(filename, content);
  console.log('Processed', filename);
}

['src/views/Graph.vue', 'src/views/Portrait.vue', 'src/views/Intelligence.vue'].forEach(processFile);
