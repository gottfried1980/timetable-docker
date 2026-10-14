import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';

const root=process.argv[2] || '/app';
const manifest=JSON.parse(fs.readFileSync(path.join(root,'release-manifest.json'),'utf8'));
for (const [name, expected] of Object.entries(manifest.files)) {
    const data=fs.readFileSync(path.join(root,name));
    const actual=createHash('sha256').update(data).digest('hex');
    if(actual!==expected)throw new Error('Release-Datei stimmt nicht: '+name);
}
for(const name of ['public/index.html','public/media.js']) {
    if(/youtube/i.test(fs.readFileSync(path.join(root,name),'utf8')))throw new Error('Veralteter externer Player gefunden: '+name);
}
console.log('Release geprüft: '+manifest.release+' — ausschließlich lokaler Player.');
