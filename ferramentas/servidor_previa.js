// Servidor estatico minimo (com suporte a Range para video) so para pre-visualizacao local.
const http = require('http');
const fs = require('fs');
const path = require('path');

const PROJETO = path.resolve(process.argv[2] || '.');
const SCRATCH = __dirname;
const PORTA = +process.argv[3] || 8765;
const TIPOS = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml',
  '.mp4': 'video/mp4', '.wav': 'audio/wav', '.ttf': 'font/ttf', '.otf': 'font/otf', '.woff2': 'font/woff2' };

http.createServer((req, res) => {
  let url = decodeURIComponent(req.url.split('?')[0]);
  // POST /salvar?nome=x.png grava a imagem em <projeto>/pranchas/
  if (req.method === 'POST' && url === '/salvar') {
    const nome = new URL(req.url, 'http://x').searchParams.get('nome') || '';
    if (!/^[\w\-]+\.png$/.test(nome)) { res.writeHead(400); return res.end('nome invalido'); }
    const dir = path.join(PROJETO, 'pranchas');
    fs.mkdirSync(dir, { recursive: true });
    const ws = fs.createWriteStream(path.join(dir, nome));
    req.pipe(ws);
    ws.on('finish', () => { res.writeHead(200); res.end('ok'); });
    return;
  }
  let base = PROJETO;
  if (url.startsWith('/scratch/')) { base = SCRATCH; url = url.slice('/scratch'.length); }
  const arq = path.normalize(path.join(base, url));
  if (!arq.startsWith(path.normalize(base))) { res.writeHead(403); return res.end(); }
  fs.stat(arq, (err, st) => {
    if (err || !st.isFile()) { res.writeHead(404); return res.end('404'); }
    const tipo = TIPOS[path.extname(arq).toLowerCase()] || 'application/octet-stream';
    const range = req.headers.range;
    if (range) {
      const [a, b] = range.replace('bytes=', '').split('-');
      const ini = +a, fim = b ? +b : st.size - 1;
      res.writeHead(206, { 'Content-Type': tipo, 'Content-Range': `bytes ${ini}-${fim}/${st.size}`,
        'Accept-Ranges': 'bytes', 'Content-Length': fim - ini + 1 });
      fs.createReadStream(arq, { start: ini, end: fim }).pipe(res);
    } else {
      res.writeHead(200, { 'Content-Type': tipo, 'Content-Length': st.size, 'Accept-Ranges': 'bytes' });
      fs.createReadStream(arq).pipe(res);
    }
  });
}).listen(PORTA, '127.0.0.1', () => console.log('servindo em http://127.0.0.1:' + PORTA));
