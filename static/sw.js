// Service Worker - Alerta Urbano v3.9.1 (Anti-Cold Start & Instant Branded Boot Shield)
const CACHE_NAME = 'alerta-urbano-v391';

const COLD_START_HTML = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Alerta Urbano Cascavel • Sincronizando</title>
  <style>
    * { margin:0; padding:0; box-sizing:border-box; font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body {
      background: #009B3A;
      color: #FFFFFF;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px;
      text-align: center;
      user-select: none;
    }
    .emblem {
      width: 90px;
      height: 90px;
      background: #FED700;
      border-radius: 22px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 22px;
      box-shadow: 0 12px 30px rgba(0,0,0,0.3);
    }
    .title {
      font-size: 26px;
      font-weight: 900;
      letter-spacing: 0.8px;
      margin-bottom: 4px;
      color: #FFFFFF;
    }
    .subtitle {
      font-size: 13px;
      font-weight: 800;
      color: #FED700;
      letter-spacing: 1.4px;
      margin-bottom: 32px;
    }
    .progress-box {
      width: 100%;
      max-width: 320px;
      background: rgba(0,0,0,0.25);
      border-radius: 999px;
      height: 12px;
      padding: 2px;
      margin-bottom: 14px;
      overflow: hidden;
      border: 1px solid rgba(254, 215, 0, 0.45);
    }
    .progress-fill {
      height: 100%;
      background: #FED700;
      border-radius: 999px;
      width: 20%;
      transition: width 0.35s ease;
    }
    .percent-txt {
      font-size: 14px;
      font-weight: 900;
      color: #FED700;
      margin-bottom: 12px;
    }
    .status-msg {
      font-size: 14px;
      font-weight: 700;
      color: #FFFFFF;
      margin-bottom: 24px;
      min-height: 22px;
    }
    .footer-note {
      font-size: 11px;
      font-weight: 800;
      color: rgba(255,255,255,0.85);
      letter-spacing: 0.8px;
    }
  </style>
</head>
<body>
  <div class="emblem">
    <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="#000000" stroke-width="2.3">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      <path d="m9 12 2 2 4-4"/>
    </svg>
  </div>
  <div class="title">ALERTA URBANO</div>
  <div class="subtitle">CASCAVEL • PARANÁ</div>
  <div class="progress-box">
    <div class="progress-fill" id="p-bar"></div>
  </div>
  <div class="percent-txt" id="p-percent">20%</div>
  <div class="status-msg" id="p-msg">Conectando aos servidores seguros de Cascavel...</div>
  <div class="footer-note">REDE DE PROTEÇÃO E ALERTA URBANO EM TEMPO REAL</div>
  <script>
    let pct = 20;
    const bar = document.getElementById('p-bar');
    const pTxt = document.getElementById('p-percent');
    const msg = document.getElementById('p-msg');
    const msgs = [
      "Conectando aos servidores seguros de Cascavel...",
      "Sincronizando rede de radares e ocorrências...",
      "Preparando mapa e esteiras de proteção...",
      "Carregando alertas em tempo real...",
      "Servidores sincronizados! Abrindo..."
    ];
    let msgIdx = 0;
    const stepTimer = setInterval(() => {
      if (pct < 94) {
        pct += Math.floor(Math.random() * 9) + 4;
        if (pct > 94) pct = 94;
        bar.style.width = pct + '%';
        pTxt.textContent = pct + '%';
        if (pct > 35 && msgIdx === 0) { msgIdx = 1; msg.textContent = msgs[1]; }
        if (pct > 60 && msgIdx === 1) { msgIdx = 2; msg.textContent = msgs[2]; }
        if (pct > 80 && msgIdx === 2) { msgIdx = 3; msg.textContent = msgs[3]; }
      }
    }, 450);

    function pingCentral() {
      fetch('/api/ping?t=' + Date.now(), { cache: 'no-store' })
        .then(r => {
          if (r.ok) return r.json();
          throw new Error('Not ready');
        })
        .then(data => {
          clearInterval(stepTimer);
          bar.style.width = '100%';
          pTxt.textContent = '100%';
          msg.textContent = msgs[4];
          setTimeout(() => {
            window.location.reload();
          }, 350);
        })
        .catch(() => {
          setTimeout(pingCentral, 1600);
        });
    }
    setTimeout(pingCentral, 1200);
  </script>
</body>
</html>`;

self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(k => caches.delete(k))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  const isHtml = req.mode === 'navigate' || (req.headers.get('accept') && req.headers.get('accept').includes('text/html'));

  if (isHtml) {
    event.respondWith(
      fetch(req)
        .then(async response => {
          // Se Render responder com 502/503 ou página de cold start crua
          if (response.status === 502 || response.status === 503) {
            return new Response(COLD_START_HTML, {
              headers: { 'Content-Type': 'text/html; charset=utf-8' }
            });
          }
          const clone = response.clone();
          try {
            const text = await clone.text();
            if (text.includes('APPLICATION LOADING') || text.includes('INCOMING HTTP REQUEST DETECTED') || (text.includes('Render') && text.includes('START BUILDING ON RENDER'))) {
              return new Response(COLD_START_HTML, {
                headers: { 'Content-Type': 'text/html; charset=utf-8' }
              });
            }
          } catch (_) {}
          return response;
        })
        .catch(() => {
          return new Response(COLD_START_HTML, {
            headers: { 'Content-Type': 'text/html; charset=utf-8' }
          });
        })
    );
    return;
  }

  // Requisições normais (API, estáticos): rede direta sem estragar dados em tempo real
  event.respondWith(
    fetch(req).catch(() => caches.match(req))
  );
});
