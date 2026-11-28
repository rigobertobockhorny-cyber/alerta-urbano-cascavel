// Service Worker - Alerta Pet Brasil v3.13.18 (Terroso Profundo & Instant Branded Boot Shield)
const CACHE_NAME = 'alerta-pet-brasil-v31318';

const COLD_START_HTML = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Alerta Pet Brasil • Conectando</title>
  <style>
    * { margin:0; padding:0; box-sizing:border-box; font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body {
      background: #2E2417; /* TERROSO PROFUNDO NOBRE */
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
      width: 96px;
      height: 96px;
      background: transparent;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 16px;
      filter: drop-shadow(0 8px 24px rgba(0,0,0,0.45));
    }
    .title {
      font-size: 26px;
      font-weight: 900;
      letter-spacing: 1.2px;
      margin-bottom: 4px;
      color: #FFFFFF;
    }
    .subtitle {
      font-size: 13px;
      font-weight: 800;
      color: #FED700;
      letter-spacing: 2px;
      margin-bottom: 28px;
    }
    .progress-box {
      width: 100%;
      max-width: 300px;
      background: rgba(0,0,0,0.35);
      border-radius: 999px;
      height: 10px;
      padding: 2px;
      margin-bottom: 14px;
      overflow: hidden;
      border: 1px solid rgba(254, 215, 0, 0.45);
    }
    .progress-fill {
      height: 100%;
      background: #FED700;
      border-radius: 999px;
      width: 25%;
      transition: width 0.35s ease;
    }
    .percent-txt {
      font-size: 13.5px;
      font-weight: 900;
      color: #FED700;
      margin-bottom: 10px;
    }
    .status-msg {
      font-size: 13.5px;
      font-weight: 700;
      color: #FAF7F2;
      margin-bottom: 22px;
      min-height: 22px;
    }
    .footer-note {
      font-size: 11px;
      font-weight: 800;
      color: rgba(254, 215, 0, 0.9);
      letter-spacing: 1px;
    }
  </style>
</head>
<body>
  <div class="emblem">
    <svg viewBox="0 0 512 512" style="width:100%; height:100%; overflow:visible;">
      <path d="M115.2 359.3 L109.4 379.5 L110.4 409.3 L117.1 425.6 L124.8 436.2 L137.3 447.7 L144.0 450.6 L198.8 450.6 L217.1 444.9 L244.9 439.1 L270.9 440.1 L309.3 450.6 L365.1 450.6 L378.5 442.9 L389.1 432.4 L397.8 417.9 L401.6 402.6 L401.6 382.4 L399.7 371.8 L393.0 353.6 L386.2 342.0 L371.8 323.8 L348.7 301.7 L341.1 292.0 L305.5 238.2 L288.2 223.8 L274.7 218.0 L264.2 216.1 L244.0 216.1 L235.3 218.0 L223.8 223.8 L214.2 231.5 L199.8 247.8 L162.3 300.7 L138.3 323.8 L129.6 334.3 Z" fill="#FED700"/>
      <path d="M78.7 170.0 L64.3 178.6 L53.7 195.0 L49.8 211.3 L49.8 224.8 L54.6 244.9 L66.2 266.1 L78.7 278.6 L95.0 287.2 L101.7 289.2 L113.3 289.2 L129.6 281.5 L136.3 274.7 L142.1 264.2 L146.9 244.0 L146.9 235.3 L143.1 216.1 L135.4 198.8 L119.0 179.6 L103.7 170.9 L96.9 169.0 Z" fill="#FED700"/>
      <path d="M177.7 62.3 L167.1 65.2 L153.6 75.8 L146.9 85.4 L142.1 96.0 L138.3 117.1 L140.2 144.0 L143.1 155.6 L148.8 168.1 L165.2 189.2 L182.5 198.8 L200.7 199.8 L208.4 197.9 L216.1 193.0 L228.6 179.6 L236.3 161.3 L239.2 146.9 L239.2 130.6 L233.4 105.6 L227.6 93.1 L219.0 80.6 L207.5 70.0 L196.9 64.3 Z" fill="#FED700"/>
      <path d="M338.2 60.4 L327.6 60.4 L318.0 63.3 L307.4 69.1 L294.9 80.6 L288.2 89.2 L279.5 106.5 L273.8 128.7 L273.8 154.6 L279.5 174.8 L284.4 183.4 L294.0 194.0 L303.6 199.8 L314.1 202.7 L322.8 202.7 L333.4 199.8 L347.8 191.1 L359.3 179.6 L370.9 159.4 L376.6 141.1 L377.6 108.5 L371.8 88.3 L358.4 70.0 L349.7 64.3 Z" fill="#FED700"/>
      <path d="M439.1 170.0 L417.9 170.0 L398.7 179.6 L382.4 196.9 L371.8 218.0 L368.9 231.5 L368.9 251.7 L370.9 261.3 L376.6 272.8 L382.4 279.5 L393.0 286.3 L401.6 289.2 L414.1 289.2 L426.6 285.3 L435.2 280.5 L451.6 265.1 L464.1 243.0 L468.9 222.8 L468.9 209.4 L464.1 192.1 L453.5 177.7 Z" fill="#FED700"/>
    </svg>
  </div>
  <div class="title">ALERTA PET BRASIL</div>
  <div class="subtitle">CASCAVEL • PARANÁ</div>
  <div class="progress-box">
    <div class="progress-fill" id="p-bar"></div>
  </div>
  <div class="percent-txt" id="p-percent">25%</div>
  <div class="status-msg" id="p-msg">Conectando à rede Alerta Pet Brasil...</div>
  <div class="footer-note">QUEM AMA, CUIDA E PROCURA JUNTO</div>
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
