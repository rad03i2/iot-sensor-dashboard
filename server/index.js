const http = require('http');

let reading = { temperature: 25, light: 640, updatedAt: new Date().toISOString() };

const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Content-Type', 'application/json');

  if (req.url === '/api/reading') {
    reading = {
      temperature: 22 + Math.round(Math.random() * 8),
      light: 300 + Math.round(Math.random() * 500),
      updatedAt: new Date().toISOString()
    };
    res.end(JSON.stringify(reading));
    return;
  }

  res.statusCode = 404;
  res.end(JSON.stringify({ error: 'Not found' }));
});

server.listen(3000, () => console.log('IoT API running on http://localhost:3000'));
