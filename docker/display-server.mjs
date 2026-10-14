import http from 'node:http';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {mediaIndex} from './media-index.mjs';

const appDirectory=process.env.APP_DIRECTORY || '/app';
const publicDirectory=path.join(appDirectory,'public');
const mediaDirectory=process.env.MEDIA_DIRECTORY || path.join(publicDirectory,'media');
const port=Number(process.env.PORT || 3000);
const internalPort=Number(process.env.JSON_SERVER_INTERNAL_PORT || 3001);
const binary=process.env.JSON_SERVER_BIN || '/app/node_modules/json-server/lib/bin.js';
const child=spawn(process.execPath,[binary,process.env.DB_PATH || '/data/db.json','--static',publicDirectory,'--host','127.0.0.1','--port',String(internalPort)],{stdio:'inherit',cwd:appDirectory});

const server=http.createServer((request,response)=>{
    const pathname=new URL(request.url,'http://localhost').pathname;
    if(pathname==='/media-list.json' || pathname==='/api/media') {
        if(request.method!=='GET' && request.method!=='HEAD') {
            response.writeHead(405,{'Allow':'GET, HEAD'});response.end();return;
        }
        try {
            const data=JSON.stringify(mediaIndex(mediaDirectory));
            response.writeHead(200,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Timetable-Media':'live-v3'});
            response.end(request.method==='HEAD' ? undefined : data);
        } catch {
            console.error('Medienordner kann nicht gelesen werden. Mount und Dateirechte prüfen.');
            response.writeHead(503,{'Content-Type':'application/json','Cache-Control':'no-store'});
            response.end(JSON.stringify({error:'Medienordner kann nicht gelesen werden.'}));
        }
        return;
    }
    const applicationFile=['/','/index.html','/calendar.js','/tasks.js','/media.js','/version.json'].includes(pathname);
    const headers={...request.headers};
    if(applicationFile) {
        delete headers['if-none-match'];
        delete headers['if-modified-since'];
    }
    const proxy=http.request({hostname:'127.0.0.1',port:internalPort,path:pathname==='/'?'/index.html':request.url,method:request.method,headers},upstream=>{
        const responseHeaders={...upstream.headers};
        if(applicationFile) {
            responseHeaders['cache-control']='no-store, max-age=0';
            delete responseHeaders.etag;
            delete responseHeaders['last-modified'];
        }
        response.writeHead(upstream.statusCode || 502,responseHeaders);
        upstream.pipe(response);
    });
    proxy.on('error',()=>{if(!response.headersSent)response.writeHead(502);response.end('Webserver startet noch.');});
    request.on('aborted',()=>proxy.destroy());
    request.pipe(proxy);
});
server.listen(port,'0.0.0.0',()=>console.log('Tagesdisplay mit direkter Medienerkennung: Port '+port));
function shutdown(signal) {server.close();child.kill(signal);}
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>shutdown(signal));
child.on('error',()=>{server.close();process.exitCode=1;});
child.on('exit',(code,signal)=>{server.close();process.exitCode=code ?? (signal==='SIGTERM'?0:1);});
server.on('error',()=>{child.kill();process.exitCode=1;});
