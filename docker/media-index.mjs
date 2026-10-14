import fs from 'node:fs';
import path from 'node:path';

export function mediaIndex(directory) {
    function entries(folder, extensions) {
        const location = path.join(directory, folder);
        if (!fs.existsSync(location)) return [];
        return fs.readdirSync(location, {withFileTypes:true})
            .filter(item => item.isFile() && extensions.includes(path.extname(item.name).toLowerCase()))
            .sort((a,b)=>a.name.localeCompare(b.name))
            .map(item=>({src:'media/'+folder+'/'+encodeURIComponent(item.name),title:path.parse(item.name).name}));
    }
    return {photos:entries('photos',['.jpg','.jpeg','.png','.webp']),tracks:entries('music',['.mp3','.m4a','.ogg','.wav'])};
}
