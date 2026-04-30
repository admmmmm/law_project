import fs from 'fs';

function modifyFile(file: string, replacer: (content: string) => string) {
    let content = fs.readFileSync(file, 'utf8');
    content = replacer(content);
    fs.writeFileSync(file, content);
}

// 1. Shrink Sidebar
modifyFile('src/components/Sidebar.vue', c => {
    return c.replace(/w-60/g, 'w-48').replace(/p-6/g, 'p-4');
});

// 2. Add whitespace-nowrap and remove strict English
modifyFile('src/views/Dashboard.vue', c => {
    // Add whitespace-nowrap to grid columns to prevent wrapping
    c = c.replace(/col-span-1/g, 'col-span-1 whitespace-nowrap overflow-hidden text-ellipsis');
    // Prevent cards from shrinking too much
    c = c.replace(/w-\[300px\]/g, 'w-[280px]'); 
    
    // Check for random English text
    c = c.replace(/UTC/g, ''); // "14:22:10 UTC" -> "14:22:10 "
    c = c.replace(/#CN/g, '编号');
    c = c.replace(/A/g, '甲');
    c = c.replace(/C/g, '丙');

    // Make text robust
    c = c.replace(/text-\[12px\] text-gray-500/g, 'text-[12px] text-gray-500 break-keep');
    c = c.replace(/text-\[12px\] text-gray-600/g, 'text-[12px] text-gray-600 break-keep');
    c = c.replace(/text-\[11.5px\]/g, 'text-[11.5px] break-keep');
    
    return c;
});

modifyFile('src/views/Graph.vue', c => {
    c = c.replace(/w-72/g, 'w-64');
    c = c.replace(/w-80/g, 'w-72');
    c = c.replace(/ID:/g, '识别码:');
    c = c.replace(/TW-/g, '台-');
    return c;
});

modifyFile('src/views/Portrait.vue', c => {
    c = c.replace(/w-80/g, 'w-72');
    c = c.replace('MAC', '硬件');
    c = c.replace(/VAL_Σ:/g, '综合得分:');
    c = c.replace(/<td class="p-4/g, '<td class="p-4 whitespace-nowrap');
    c = c.replace(/<span class="text-body-sm text-slate-500"/g, '<span class="text-body-sm text-slate-500 whitespace-nowrap"');
    c = c.replace(/<span class="font-data-mono text-slate-900"/g, '<span class="font-data-mono text-slate-900 whitespace-nowrap"');
    return c;
});

modifyFile('src/views/Intelligence.vue', c => {
    c = c.replace(/w-80/g, 'w-72');
    c = c.replace(/A04/g, '甲04');
    c = c.replace(/MAC/g, '硬件');
    c = c.replace(/HASH/g, '校验');
    return c;
});
