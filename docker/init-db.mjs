import fs from 'node:fs';
const path = process.env.DB_PATH || '/data/db.json';
const exists = fs.existsSync(path);
const data = exists ? JSON.parse(fs.readFileSync(path, 'utf8').replace(/^\uFEFF/, '')) : {};
if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('Invalid database');
let changed = !exists;
for (const [key, defaultValue] of Object.entries({todos: [], events: [], timeTreeSync: {}})) {
    if (data[key] === undefined) { data[key] = defaultValue; changed = true; }
}
if (!Array.isArray(data.todos) || !Array.isArray(data.events) || !data.timeTreeSync || typeof data.timeTreeSync !== 'object' || Array.isArray(data.timeTreeSync)) throw new Error('Invalid database collections');
if (changed) {
    fs.writeFileSync(path + '.tmp', JSON.stringify(data, null, 2) + '\n');
    fs.renameSync(path + '.tmp', path);
}
