# -*- coding: utf-8 -*-
"""
Alerta Urbano v3.0 — Backend Oficial (Flask + SQLite)
Arquitetura: 3 Pilares Exclusivos (Pets | Segurança Imprensa | Utilidade Pública Oficial)
Blindagem Anti-Fake News: Público cadastra EXCLUSIVAMENTE Pets.
Segurança e Utilidade Pública são alimentadas exclusivamente pelo Robô Coletor Oficial.
"""
import os
import re
import json
import sqlite3
import time
import hashlib
import urllib.request
import urllib.parse
import html
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, make_response, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder="static", template_folder="static")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB máx por foto
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

DB_PATH = os.path.join(BASE_DIR, "alertas_cascavel.db")
ROBO_API_TOKEN = os.environ.get("ALERTA_ROBO_TOKEN", "vortice_robo_oficial_2026")
ADMIN_TOKEN = os.environ.get("ALERTA_ADMIN_TOKEN", "admin_cascavel")

# Governança rígida de tipos por pilar (v3.0)
TIPOS_PET = {"pet", "pet_perdido", "pet_avistado", "pet_encontrado"}
TIPOS_SEGURANCA = {"seguranca", "assalto", "furto", "suspeito"}
TIPOS_TRANSITO = {
    "transito", "ponto_seguro", "policia_presente", "via_bloqueada",
    "semaforo", "semaforo_defeito", "acidente", "acidente_via", "arvore_caida", "buraco"
}
TIPOS_UTILIDADE = {
    "utilidade",
    "utilidade_clima",
    "utilidade_agua",
    "utilidade_luz",
    "utilidade_interdicao",
    "utilidade_geral",
    "escuro",
}
TIPOS_BLOQUEADOS_LEGADO = {
    "radar", "radar_fixo", "radar_40", "radar_50", "radar_60",
    "camera_semaforo", "lombada", "comercio", "batalhao_pm", "delegacia",
    "guarda_municipal", "prf",
}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def normalizar_telefone(tel):
    if not tel:
        return ""
    digits = re.sub(r"\D+", "", str(tel))
    if len(digits) < 10 or len(digits) > 13:
        return ""
    if len(digits) in (10, 11) and not digits.startswith("55"):
        digits = "55" + digits
    return digits


def inferir_pilar(tipo):
    t = (tipo or "").strip().lower()
    if t in TIPOS_PET or t.startswith("pet"):
        return "pet"
    if t in TIPOS_SEGURANCA:
        return "seguranca"
    if t in TIPOS_TRANSITO or t.startswith("transito") or "seguro" in t or "policia" in t or "bloque" in t:
        return "transito"
    if t in TIPOS_UTILIDADE or t.startswith("utilidade"):
        return "utilidade"
    return "legado"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            pilar TEXT DEFAULT 'pet',
            cidade TEXT DEFAULT 'Cascavel',
            titulo TEXT NOT NULL,
            descricao TEXT,
            rua TEXT,
            bairro TEXT,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            peso INTEGER DEFAULT 1,
            confirmacoes INTEGER DEFAULT 1,
            ativo INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            foto_url TEXT,
            contato TEXT,
            recompensa TEXT,
            link_noticia TEXT,
            autor_token TEXT,
            votos_passou INTEGER DEFAULT 0,
            fonte_tipo TEXT DEFAULT 'comunidade_pet',
            fonte_nome TEXT DEFAULT 'Comunidade',
            especie TEXT DEFAULT '',
            porte TEXT DEFAULT '',
            status_pet TEXT DEFAULT '',
            pet_pai_id INTEGER,
            severidade TEXT DEFAULT 'normal',
            consentimento_contato INTEGER DEFAULT 0
        )
    """)

    # Migração segura para bancos existentes (v2.1 -> v3.0)
    cur.execute("PRAGMA table_info(alertas)")
    cols = {r[1] for r in cur.fetchall()}

    novas_colunas = [
        ("autor_token", "TEXT"),
        ("votos_passou", "INTEGER DEFAULT 0"),
        ("link_noticia", "TEXT"),
        ("fonte_tipo", "TEXT DEFAULT 'comunidade_pet'"),
        ("cidade", "TEXT DEFAULT 'Cascavel'"),
        ("pilar", "TEXT DEFAULT 'pet'"),
        ("fonte_nome", "TEXT DEFAULT 'Comunidade'"),
        ("especie", "TEXT DEFAULT ''"),
        ("porte", "TEXT DEFAULT ''"),
        ("status_pet", "TEXT DEFAULT ''"),
        ("pet_pai_id", "INTEGER"),
        ("severidade", "TEXT DEFAULT 'normal'"),
        ("consentimento_contato", "INTEGER DEFAULT 0"),
        ("contato_avistador", "TEXT DEFAULT ''"),
        ("avistador_nome", "TEXT DEFAULT ''"),
        ("subtipo_evento", "TEXT DEFAULT 'avistamento'"),
        ("castrado", "INTEGER DEFAULT 0"),
        ("vacinado", "INTEGER DEFAULT 0"),
        ("faixa_etaria", "TEXT DEFAULT 'adulto'"),
        ("sexo", "TEXT DEFAULT 'indefinido'"),
        ("sigiloso", "INTEGER DEFAULT 0"),
        ("orgao_destino", "TEXT DEFAULT ''"),
    ]
    for col_name, col_def in novas_colunas:
        if col_name not in cols:
            cur.execute(f"ALTER TABLE alertas ADD COLUMN {col_name} {col_def};")

    # Índices para performance do Dashboard Slim e Mapa de Calor
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alertas_ativo_pilar ON alertas (ativo, pilar, cidade);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alertas_pet_pai ON alertas (pet_pai_id);")

    # Tabela de Perfil / Cadastro do Cidadão (v3.1 + FCM Push)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            autor_token TEXT UNIQUE NOT NULL,
            nome TEXT DEFAULT '',
            whatsapp TEXT DEFAULT '',
            bairro TEXT DEFAULT 'Centro',
            cidade TEXT DEFAULT 'Cascavel',
            foto_url TEXT DEFAULT '',
            fcm_token TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("PRAGMA table_info(usuarios)")
    ucols = {r[1] for r in cur.fetchall()}
    if "fcm_token" not in ucols:
        cur.execute("ALTER TABLE usuarios ADD COLUMN fcm_token TEXT DEFAULT '';")

    # Higienização e classificação v3.0 (desativa legados de trânsito/radar/semáforo e não-pets do público)
    placeholders = ",".join("?" for _ in TIPOS_BLOQUEADOS_LEGADO)
    cur.execute(
        f"UPDATE alertas SET ativo = 0, pilar = 'legado' WHERE LOWER(tipo) IN ({placeholders}) AND ativo = 1",
        tuple(TIPOS_BLOQUEADOS_LEGADO),
    )

    # Qualquer registro antigo enviado por 'cidadao_alerta' que NÃO seja pet é desativado (governança v3.0)
    cur.execute("""
        UPDATE alertas
        SET ativo = 0, pilar = 'legado'
        WHERE fonte_tipo IN ('cidadao_alerta', 'parceiro_transito', 'oficial_transitar')
          AND LOWER(tipo) NOT LIKE 'pet%'
          AND ativo = 1
    """)

    # Normaliza pilares de registros válidos existentes
    cur.execute("""
        UPDATE alertas
        SET pilar = 'pet',
            cidade = COALESCE(NULLIF(cidade, ''), 'Cascavel'),
            fonte_nome = CASE
                WHEN fonte_tipo = 'imprensa' AND (fonte_nome IS NULL OR fonte_nome = '' OR fonte_nome = 'Comunidade') THEN 'CGN'
                ELSE COALESCE(NULLIF(fonte_nome, ''), 'Comunidade')
            END,
            status_pet = CASE
                WHEN status_pet IS NOT NULL AND status_pet != '' THEN status_pet
                WHEN LOWER(tipo) = 'pet_avistado' OR LOWER(titulo) LIKE '%encontrado%' OR LOWER(titulo) LIKE '%avistado%' THEN 'avistado'
                ELSE 'desaparecido'
            END
        WHERE LOWER(tipo) LIKE 'pet%'
    """)
    cur.execute("""
        UPDATE alertas
        SET pilar = 'seguranca',
            cidade = COALESCE(NULLIF(cidade, ''), 'Cascavel'),
            fonte_nome = CASE
                WHEN fonte_nome IS NOT NULL AND fonte_nome != '' AND fonte_nome != 'Comunidade' THEN fonte_nome
                WHEN LOWER(COALESCE(descricao, '')) LIKE '%catve%' OR LOWER(COALESCE(link_noticia, '')) LIKE '%catve%' THEN 'CATVE'
                ELSE 'CGN'
            END
        WHERE LOWER(tipo) IN ('seguranca', 'assalto', 'furto', 'suspeito')
          AND fonte_tipo IN ('imprensa', 'robo_oficial')
    """)
    cur.execute("""
        UPDATE alertas
        SET pilar = 'utilidade',
            cidade = COALESCE(NULLIF(cidade, ''), 'Cascavel'),
            fonte_nome = CASE
                WHEN fonte_nome IS NOT NULL AND fonte_nome != '' AND fonte_nome != 'Comunidade' THEN fonte_nome
                WHEN LOWER(COALESCE(descricao, '')) LIKE '%inmet%' THEN 'INMET'
                WHEN LOWER(COALESCE(descricao, '')) LIKE '%sanepar%' THEN 'Sanepar'
                WHEN LOWER(COALESCE(descricao, '')) LIKE '%copel%' THEN 'Copel'
                WHEN LOWER(COALESCE(descricao, '')) LIKE '%transitar%' OR LOWER(COALESCE(descricao, '')) LIKE '%cettrans%' THEN 'Transitar'
                WHEN LOWER(COALESCE(descricao, '')) LIKE '%prefeitura%' THEN 'Prefeitura'
                WHEN LOWER(COALESCE(descricao, '')) LIKE '%catve%' THEN 'CATVE'
                ELSE 'CGN'
            END
        WHERE (LOWER(tipo) LIKE 'utilidade%' OR LOWER(tipo) = 'escuro')
          AND fonte_tipo IN ('imprensa', 'robo_oficial')
    """)

    # LGPD: limpa telefones de registros já inativos/encerrados
    cur.execute("UPDATE alertas SET contato = '' WHERE ativo = 0 AND contato IS NOT NULL AND contato != ''")

    conn.commit()
    conn.close()


@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/")
def index():
    resp = make_response(send_from_directory("static", "index.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.route("/privacidade")
@app.route("/politica-privacidade")
@app.route("/politica_privacidade.html")
def politica_privacidade():
    return send_from_directory("static", "politica_privacidade.html")


@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json", mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    resp = send_from_directory("static", "sw.js", mimetype="application/javascript")
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@app.route("/api/ping")
def ping():
    return jsonify({
        "ok": True,
        "app": "Alerta Urbano",
        "version": "3.0.0",
        "cidade_padrao": "Cascavel",
        "ts": int(time.time()),
    })


@app.route("/baixar-apk")
@app.route("/ALERTA_URBANO_CASCAVEL.apk")
@app.route("/app.apk")
@app.route("/download")
def baixar_apk():
    apk_path = os.path.join(BASE_DIR, "ALERTA_URBANO_CASCAVEL.apk")
    if not os.path.exists(apk_path):
        apk_path = os.path.join(BASE_DIR, "android_app", "app", "build", "outputs", "apk", "debug", "app-debug.apk")
    if not os.path.exists(apk_path):
        return "APK ainda sendo gerado...", 404
    return send_from_directory(
        os.path.dirname(apk_path),
        os.path.basename(apk_path),
        as_attachment=True,
        download_name="Alerta_Urbano_v3.6.6_Cascavel.apk",
        mimetype="application/vnd.android.package-archive",
    )


@app.route("/api/falar")
def api_falar():
    """Sintetiza alertas de voz exclusivos (padrão: voz masculina pt-BR-AntonioNeural)."""
    texto = request.args.get("texto", "").strip()
    if not texto:
        return jsonify({"error": "Texto vazio"}), 400

    voz_param = request.args.get("voz", "masculina").strip().lower()
    voice_id = "pt-BR-FranciscaNeural" if voz_param == "feminina" else "pt-BR-AntonioNeural"

    cache_key = f"{voice_id}:{texto.lower()}"
    h = hashlib.md5(cache_key.encode("utf-8")).hexdigest()
    cache_dir = os.path.join(BASE_DIR, "static", "audios_tts")
    os.makedirs(cache_dir, exist_ok=True)
    filepath = os.path.join(cache_dir, f"{h}.mp3")

    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        return send_file(filepath, mimetype="audio/mpeg")

    try:
        import asyncio
        import edge_tts

        async def _synthesize():
            comm = edge_tts.Communicate(texto, voice_id)
            await comm.save(filepath)

        asyncio.run(_synthesize())
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            return send_file(filepath, mimetype="audio/mpeg")
    except Exception as e:
        print(f"[TTS SERVER] Erro ao gerar fala: {e}")

    return jsonify({"error": "Falha na síntese de áudio"}), 500


@app.route("/api/upload", methods=["POST"])
def upload_foto():
    if "foto" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    file = request.files["foto"]
    if file.filename == "":
        return jsonify({"error": "Arquivo vazio"}), 400
    if file and allowed_file(file.filename):
        filename = f"pet_{int(time.time())}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        return jsonify({"url": f"/static/uploads/{filename}"}), 201
    return jsonify({"error": "Formato de arquivo não suportado (use PNG, JPG ou WEBP)"}), 400


_CLIMA_CACHE = {"ts": 0, "data": None}

WMO_DESC = {
    0: ("Céu limpo", "☀️"),
    1: ("Predomínio de sol", "🌤️"),
    2: ("Parcialmente nublado", "⛅"),
    3: ("Nublado", "☁️"),
    45: ("Nevoeiro", "🌫️"),
    48: ("Nevoeiro", "🌫️"),
    51: ("Garoa leve", "🌦️"),
    53: ("Garoa moderada", "🌦️"),
    55: ("Garoa forte", "🌧️"),
    61: ("Chuva leve", "🌦️"),
    63: ("Chuva moderada", "🌧️"),
    65: ("Chuva forte", "🌧️"),
    80: ("Pancadas leves", "🌦️"),
    81: ("Pancadas de chuva", "🌧️"),
    82: ("Chuva intensa", "⛈️"),
    95: ("Tempestade", "⛈️"),
    96: ("Tempestade com granizo", "⛈️"),
    99: ("Tempestade severa", "⛈️"),
}


@app.route("/api/clima", methods=["GET"])
def api_clima():
    """Retorna clima em tempo real de Cascavel (Open-Meteo, cache 10min) + alertas oficiais ativos."""
    cidade = request.args.get("cidade", "Cascavel").strip()
    agora_ts = time.time()

    if not _CLIMA_CACHE["data"] or (agora_ts - _CLIMA_CACHE["ts"] > 600):
        try:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                "?latitude=-24.9555&longitude=-53.4550"
                "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,precipitation"
                "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
                "&timezone=America%2FSao_Paulo&forecast_days=1"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "AlertaUrbano/3.1"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            cur_w = raw.get("current", {})
            day_w = raw.get("daily", {})
            wcode = int(cur_w.get("weather_code", 0))
            cond_txt, cond_ico = WMO_DESC.get(wcode, ("Tempo instável", "⛅"))
            _CLIMA_CACHE["data"] = {
                "cidade": cidade,
                "temp": round(float(cur_w.get("temperature_2m", 23))),
                "sensacao": round(float(cur_w.get("apparent_temperature", 23))),
                "umidade": int(cur_w.get("relative_humidity_2m", 65)),
                "vento": round(float(cur_w.get("wind_speed_10m", 10))),
                "condicao": cond_txt,
                "icone": cond_ico,
                "max": round(float((day_w.get("temperature_2m_max") or [27])[0])),
                "min": round(float((day_w.get("temperature_2m_min") or [18])[0])),
                "chance_chuva": int((day_w.get("precipitation_probability_max") or [0])[0]),
            }
            _CLIMA_CACHE["ts"] = agora_ts
        except Exception as e:
            print(f"[CLIMA] Falha Open-Meteo: {e}")
            if not _CLIMA_CACHE["data"]:
                _CLIMA_CACHE["data"] = {
                    "cidade": cidade, "temp": 24, "sensacao": 24, "umidade": 65,
                    "vento": 12, "condicao": "Tempo em monitoramento", "icone": "⛅",
                    "max": 27, "min": 18, "chance_chuva": 20,
                }

    # Busca alertas climáticos oficiais de Cascavel (prioridade absoluta: INMET / Simepar / Defesa Civil)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, titulo, descricao, severidade, fonte_nome, link_noticia, created_at
        FROM alertas
        WHERE ativo = 1
          AND pilar = 'utilidade'
          AND tipo = 'utilidade_clima'
          AND fonte_nome IN ('INMET', 'Simepar', 'Defesa Civil', 'Prefeitura')
          AND LOWER(COALESCE(cidade, 'Cascavel')) = LOWER(?)
          AND datetime(created_at, '+36 hours') >= datetime('now', 'localtime')
        ORDER BY
            CASE severidade WHEN 'critico' THEN 1 WHEN 'alerta' THEN 2 WHEN 'atencao' THEN 3 ELSE 4 END,
            created_at DESC
        LIMIT 5
    """, (cidade,))
    alertas_clima = [dict(r) for r in cur.fetchall()]
    conn.close()

    nivel = "normal"
    if alertas_clima:
        sev0 = (alertas_clima[0].get("severidade") or "atencao").lower()
        nivel = "vermelho" if sev0 == "critico" else ("laranja" if sev0 == "alerta" else "amarelo")

    resp_data = dict(_CLIMA_CACHE["data"])
    resp_data["nivel_alerta"] = nivel
    resp_data["alertas"] = alertas_clima
    return jsonify(resp_data)


@app.route("/api/perfil", methods=["GET", "POST"])
def api_perfil():
    """Cadastro e consulta de perfil do cidadão (Nome, WhatsApp, Bairro, Foto)."""
    if request.method == "GET":
        token = request.args.get("autor_token", "").strip()
        if not token:
            return jsonify({"perfil": None})
        conn = get_db()
        row = conn.execute("SELECT autor_token, nome, whatsapp, bairro, cidade, foto_url FROM usuarios WHERE autor_token = ?", (token,)).fetchone()
        conn.close()
        return jsonify({"perfil": dict(row) if row else None})

    data = request.json or {}
    token = (data.get("autor_token") or "").strip()[:100]
    if not token:
        return jsonify({"error": "Token do dispositivo ausente."}), 400

    nome = (data.get("nome") or "").strip()[:100]
    whatsapp = normalizar_telefone(data.get("whatsapp") or "")
    bairro = (data.get("bairro") or "Centro").strip()[:80]
    cidade = (data.get("cidade") or "Cascavel").strip()[:80]
    foto_url = (data.get("foto_url") or "").strip()[:300]
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO usuarios (autor_token, nome, whatsapp, bairro, cidade, foto_url, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(autor_token) DO UPDATE SET
            nome = excluded.nome,
            whatsapp = excluded.whatsapp,
            bairro = excluded.bairro,
            cidade = excluded.cidade,
            foto_url = CASE WHEN excluded.foto_url != '' THEN excluded.foto_url ELSE usuarios.foto_url END,
            updated_at = excluded.updated_at
    """, (token, nome, whatsapp, bairro, cidade, foto_url, agora, agora))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "nome": nome, "bairro": bairro})


@app.route("/api/resumo", methods=["GET"])
def resumo_dashboard():
    """Resumo ultra-leve para os cards e banner climático do Dashboard Slim."""
    cidade = request.args.get("cidade", "Cascavel").strip()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            SUM(CASE WHEN pilar = 'pet' AND status_pet != 'avistado' AND pet_pai_id IS NULL THEN 1 ELSE 0 END) AS pets_perdidos,
            SUM(CASE WHEN pilar = 'pet' AND (status_pet = 'avistado' OR pet_pai_id IS NOT NULL) THEN 1 ELSE 0 END) AS pets_avistados,
            SUM(CASE WHEN pilar = 'seguranca' AND datetime(created_at, '+48 hours') >= datetime('now', 'localtime') THEN 1 ELSE 0 END) AS seguranca,
            SUM(CASE WHEN pilar = 'utilidade' AND datetime(created_at, '+48 hours') >= datetime('now', 'localtime') THEN 1 ELSE 0 END) AS utilidade
        FROM alertas
        WHERE ativo = 1
          AND LOWER(COALESCE(cidade, 'Cascavel')) = LOWER(?)
          AND pilar IN ('pet', 'seguranca', 'utilidade')
    """, (cidade,))
    counts = dict(cur.fetchone() or {})

    cur.execute("""
        SELECT id, titulo, descricao, severidade, fonte_nome, link_noticia, created_at
        FROM alertas
        WHERE ativo = 1
          AND pilar = 'utilidade'
          AND tipo = 'utilidade_clima'
          AND LOWER(COALESCE(cidade, 'Cascavel')) = LOWER(?)
          AND datetime(created_at, '+36 hours') >= datetime('now', 'localtime')
        ORDER BY
            CASE severidade WHEN 'critico' THEN 1 WHEN 'alerta' THEN 2 WHEN 'atencao' THEN 3 ELSE 4 END,
            created_at DESC
        LIMIT 1
    """, (cidade,))
    clima_row = cur.fetchone()
    conn.close()

    return jsonify({
        "cidade": cidade,
        "pets_perdidos": counts.get("pets_perdidos") or 0,
        "pets_avistados": counts.get("pets_avistados") or 0,
        "seguranca": counts.get("seguranca") or 0,
        "utilidade": counts.get("utilidade") or 0,
        "alerta_clima": dict(clima_row) if clima_row else None,
        "ts": int(time.time()),
    })


@app.route("/api/alertas", methods=["GET"])
def listar_alertas():
    """
    Lista exclusivamente registros ativos dos 3 pilares v3.0:
    - pet (desaparecidos, adoção responsável, sos público e comunitários)
    - seguranca (imprensa oficial; últimas 48h)
    - utilidade (fontes oficiais/imprensa; últimas 48h)
    * Denúncias sigilosas de maus-tratos NUNCA aparecem na listagem pública aberta!
    """
    cidade = request.args.get("cidade", "Cascavel").strip()
    pilar = request.args.get("pilar", "").strip().lower()
    autor_token = request.args.get("autor_token", "").strip()

    conn = get_db()
    cur = conn.cursor()

    params = [cidade]
    pilar_clause = ""
    if pilar in ("pet", "seguranca", "utilidade", "transito"):
        pilar_clause = " AND pilar = ?"
        params.append(pilar)

    sigiloso_clause = " AND (COALESCE(sigiloso, 0) = 0 OR (autor_token != '' AND autor_token = ?))"
    params.append(autor_token)

    cur.execute(f"""
        SELECT * FROM alertas
        WHERE ativo = 1
          AND LOWER(COALESCE(cidade, 'Cascavel')) = LOWER(?)
          AND pilar IN ('pet', 'seguranca', 'utilidade', 'transito')
          {pilar_clause}
          {sigiloso_clause}
          AND (
            pilar = 'pet'
            OR (pilar IN ('seguranca', 'utilidade') AND datetime(created_at, '+48 hours') >= datetime('now', 'localtime'))
            OR (pilar = 'transito' AND datetime(created_at, '+24 hours') >= datetime('now', 'localtime'))
          )
        ORDER BY
            CASE WHEN tipo = 'utilidade_clima' THEN 0 ELSE 1 END,
            created_at DESC
        LIMIT 250
    """, params)
    rows = [dict(r) for r in cur.fetchall()]

    # Anexa contagem de avistamentos para cada pet desaparecido
    cur.execute("""
        SELECT pet_pai_id, COUNT(*) as total
        FROM alertas
        WHERE ativo = 1 AND pet_pai_id IS NOT NULL
        GROUP BY pet_pai_id
    """)
    avistamentos_map = {r["pet_pai_id"]: r["total"] for r in cur.fetchall()}
    conn.close()

    for r in rows:
        r["avistamentos_count"] = avistamentos_map.get(r["id"], 0)
        r["tem_tutor_notificavel"] = bool(r.get("autor_token")) and r.get("fonte_tipo") != "imprensa"
        # Se for pet para adoção solidária e tutor autorizou LGPD, disponibiliza flag de contato
        eh_adocao = r.get("tipo") == "pet_adocao" or r.get("status_pet") == "adocao"
        r["tem_contato_adocao"] = bool(r.get("contato")) and eh_adocao and bool(r.get("consentimento_contato"))
        if not eh_adocao:
            r["contato"] = ""
        r["contato_avistador"] = ""

    return jsonify(rows)


@app.route("/api/alertas", methods=["POST"])
def criar_alerta():
    """
    BLINDAGEM ANTI-FAKE NEWS v3.0 + HUB PET COMPLETO (Desaparecidos, Adoção e SOS):
    - Requisições públicas (usuário comum) criam registros de PETS:
      * pet_perdido (desaparecido)
      * pet_avistado (visto na rua)
      * pet_adocao (adoção solidária / responsável)
      * pet_sos_rua (animal atropelado / em risco urgente na via pública)
      * pet_denuncia_maustratos (denúncia sigilosa com dossiê oficial)
    - Registros de Segurança e Utilidade Pública exigem X-Robo-Token válido.
    """
    data = request.json or {}
    robo_token = request.headers.get("X-Robo-Token") or data.get("robo_token", "")
    eh_robo_autorizado = robo_token in (ROBO_API_TOKEN, ADMIN_TOKEN)

    tipo = (data.get("tipo") or "pet_perdido").strip().lower()
    if tipo == "pet":
        tipo = "pet_perdido"

    pilar = inferir_pilar(tipo)

    if pilar == "legado":
        return jsonify({
            "error": "Categoria descontinuada na versão 3.0. O Alerta Urbano foca exclusivamente em Pets, Segurança Oficial e Utilidade Pública."
        }), 400

    if not eh_robo_autorizado and pilar not in ("pet", "transito"):
        return jsonify({
            "error": "Acesso restrito: alertas de Segurança são alimentados exclusivamente por fontes oficiais e imprensa."
        }), 403

    lat = data.get("lat")
    lng = data.get("lng")
    if lat is None or lng is None:
        return jsonify({"error": "Localização (latitude e longitude) é obrigatória."}), 400

    titulo_padrao = "Pet Desaparecido"
    if tipo == "pet_avistado": titulo_padrao = "Pet Avistado"
    elif tipo == "pet_adocao": titulo_padrao = "Pet para Adoção"
    elif tipo == "pet_sos_rua": titulo_padrao = "Animal em Risco (Socorro Urgente)"
    elif tipo == "pet_denuncia_maustratos": titulo_padrao = "Denúncia de Maus-Tratos"
    elif tipo == "ponto_seguro": titulo_padrao = "Ponto Seguro • Policiamento Presente"
    elif tipo == "via_bloqueada": titulo_padrao = "Trânsito • Via Bloqueada"

    titulo = (data.get("titulo") or titulo_padrao).strip()[:120]
    descricao = (data.get("descricao") or "").strip()[:600]
    rua = (data.get("rua") or "").strip()[:120]
    bairro = (data.get("bairro") or "Cascavel").strip()[:80]
    cidade = (data.get("cidade") or "Cascavel").strip()[:80]
    foto_url = (data.get("foto_url") or "").strip()
    recompensa = (data.get("recompensa") or "").strip()[:60]
    autor_token = (data.get("autor_token") or "").strip()[:100]
    especie = (data.get("especie") or "").strip()[:40]
    porte = (data.get("porte") or "").strip()[:40]
    pet_pai_id = data.get("pet_pai_id")
    severidade = (data.get("severidade") or "normal").strip().lower()
    link_noticia = (data.get("link_noticia") or "").strip()

    # Campos novos: Adoção Solidária e Denúncias
    castrado = 1 if data.get("castrado") else 0
    vacinado = 1 if data.get("vacinado") else 0
    faixa_etaria = (data.get("faixa_etaria") or "adulto").strip()[:30]
    sexo = (data.get("sexo") or "indefinido").strip()[:20]
    sigiloso = 1 if (data.get("sigiloso") or tipo == "pet_denuncia_maustratos") else 0
    orgao_destino = (data.get("orgao_destino") or "").strip()[:60]

    # LGPD: armazena WhatsApp apenas com consentimento explícito
    consentimento = 1 if data.get("consentimento_contato") else 0
    contato_bruto = data.get("contato") or ""
    contato = normalizar_telefone(contato_bruto) if (pilar == "pet" and consentimento) else ""

    if pilar == "pet":
        if tipo == "pet_adocao":
            status_pet = "adocao"
        elif tipo == "pet_sos_rua":
            status_pet = "sos_rua"
        elif tipo == "pet_denuncia_maustratos":
            status_pet = "maustratos"
        elif tipo == "pet_avistado" or pet_pai_id:
            status_pet = "avistado"
        else:
            status_pet = "desaparecido"
        fonte_tipo = "imprensa" if eh_robo_autorizado and data.get("fonte_tipo") == "imprensa" else "comunidade_pet"
        fonte_nome = (data.get("fonte_nome") or ("CGN" if fonte_tipo == "imprensa" else "Comunidade")).strip()
    else:
        status_pet = ""
        fonte_tipo = "robo_oficial"
        fonte_nome = (data.get("fonte_nome") or "Imprensa Oficial").strip()

    conn = get_db()
    cur = conn.cursor()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO alertas (
            tipo, pilar, cidade, titulo, descricao, rua, bairro, lat, lng,
            peso, foto_url, contato, recompensa, link_noticia, autor_token,
            fonte_tipo, fonte_nome, especie, porte, status_pet, pet_pai_id,
            severidade, consentimento_contato, castrado, vacinado, faixa_etaria,
            sexo, sigiloso, orgao_destino, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tipo, pilar, cidade, titulo, descricao, rua, bairro, float(lat), float(lng),
        foto_url, contato, recompensa, link_noticia, autor_token,
        fonte_tipo, fonte_nome, especie, porte, status_pet, pet_pai_id,
        severidade, consentimento, castrado, vacinado, faixa_etaria,
        sexo, sigiloso, orgao_destino, agora,
    ))
    novo_id = cur.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "id": novo_id, "pilar": pilar, "tipo": tipo, "sigiloso": sigiloso}), 201
    conn.close()

    return jsonify({"status": "ok", "id": novo_id, "pilar": pilar, "tipo": tipo}), 201


def enviar_push_firebase(fcm_token, titulo, corpo, dados=None):
    """
    Envia Notificação Push via Firebase Cloud Messaging (HTTP v1 / Admin SDK) quando configurado.
    100% gratuito via Google Firebase; falha silenciosa se ainda não houver credencial no servidor.
    """
    if not fcm_token:
        return False
    cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    cred_path = os.path.join(BASE_DIR, "firebase_service_account.json")
    if not cred_json and not os.path.exists(cred_path):
        return False
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
        if not firebase_admin._apps:
            if cred_json:
                cred = credentials.Certificate(json.loads(cred_json))
            else:
                cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        msg = messaging.Message(
            notification=messaging.Notification(title=titulo, body=corpo),
            data={str(k): str(v) for k, v in (dados or {}).items()},
            token=fcm_token,
        )
        messaging.send(msg)
        return True
    except Exception as e:
        print(f"[FCM PUSH] Aviso ao enviar push: {e}")
        return False


@app.route("/api/fcm/registrar", methods=["POST"])
def registrar_fcm_token():
    """Vincula o token Push do Firebase do celular Android ao autor_token do usuário."""
    data = request.json or {}
    autor_token = (data.get("autor_token") or "").strip()[:100]
    fcm_token = (data.get("fcm_token") or "").strip()[:400]
    if not autor_token or not fcm_token:
        return jsonify({"error": "autor_token e fcm_token obrigatórios"}), 400
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    conn.execute("""
        INSERT INTO usuarios (autor_token, fcm_token, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(autor_token) DO UPDATE SET fcm_token = excluded.fcm_token, updated_at = excluded.updated_at
    """, (autor_token, fcm_token, agora, agora))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/meus-avistamentos", methods=["GET"])
def listar_meus_avistamentos():
    """
    PRIVACIDADE BLINDADA v3.3:
    Retorna EXCLUSIVAMENTE para o tutor (autor_token dono do pet) os avistamentos e resgates recebidos,
    incluindo a foto enviada por quem resgatou e o WhatsApp SOMENTE se autorizado.
    """
    token = request.args.get("autor_token", "").strip()
    if not token:
        return jsonify([])
    conn = get_db()
    rows = conn.execute("""
        SELECT
            av.id, av.pet_pai_id, pai.titulo AS pet_titulo,
            av.descricao, av.bairro, av.lat, av.lng, av.foto_url,
            av.contato_avistador, av.avistador_nome,
            COALESCE(NULLIF(av.subtipo_evento, ''), 'avistamento') AS subtipo_evento,
            av.created_at
        FROM alertas av
        JOIN alertas pai ON pai.id = av.pet_pai_id
        WHERE av.ativo = 1
          AND pai.autor_token = ?
        ORDER BY
            CASE WHEN av.subtipo_evento = 'resgatado' THEN 0 ELSE 1 END,
            av.created_at DESC
        LIMIT 40
    """, (token,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/pets/<int:pet_id>/trilha", methods=["GET"])
def trilha_cronologica_pet(pet_id):
    """
    Retorna a Trilha Cronológica completa de um Pet (ponto inicial + avistamentos/resgates em ordem de horário)
    para desenhar o caminho do animal no mapa (ZERO exposição de telefones).
    """
    conn = get_db()
    pai = conn.execute("""
        SELECT id, titulo, bairro, lat, lng, foto_url, created_at, status_pet
        FROM alertas
        WHERE id = ? AND pilar = 'pet'
    """, (pet_id,)).fetchone()
    if not pai:
        conn.close()
        return jsonify({"error": "Pet não encontrado"}), 404

    eventos = conn.execute("""
        SELECT id, descricao, bairro, lat, lng, foto_url,
               COALESCE(NULLIF(subtipo_evento, ''), 'avistamento') AS subtipo_evento,
               created_at
        FROM alertas
        WHERE pet_pai_id = ? AND ativo = 1
        ORDER BY created_at ASC
    """, (pet_id,)).fetchall()
    conn.close()

    pontos = [{
        "id": pai["id"],
        "etapa": 0,
        "tipo": "inicio",
        "titulo": "Ponto inicial do desaparecimento",
        "bairro": pai["bairro"] or "Cascavel",
        "lat": pai["lat"],
        "lng": pai["lng"],
        "foto_url": pai["foto_url"] or "",
        "created_at": pai["created_at"],
    }]
    for idx, ev in enumerate(eventos, start=1):
        eh_resg = ev["subtipo_evento"] == "resgatado"
        pontos.append({
            "id": ev["id"],
            "etapa": idx,
            "tipo": "resgatado" if eh_resg else "avistamento",
            "titulo": "Possível Resgate (foto enviada)" if eh_resg else f"Avistamento #{idx}",
            "descricao": ev["descricao"] or "",
            "bairro": ev["bairro"] or pai["bairro"] or "Cascavel",
            "lat": ev["lat"],
            "lng": ev["lng"],
            "foto_url": ev["foto_url"] or "",
            "created_at": ev["created_at"],
        })

    return jsonify({
        "pet_id": pai["id"],
        "pet_titulo": pai["titulo"],
        "total_eventos": len(eventos),
        "pontos": pontos,
    })


@app.route("/api/avistamentos/<int:av_id>/descartar", methods=["POST"])
def descartar_avistamento_tutor(av_id):
    """Permite EXCLUSIVAMENTE ao tutor do pet pai descartar um possível resgate/avistamento ('Não é o meu pet')."""
    data = request.json or {}
    token = (data.get("autor_token") or "").strip()
    conn = get_db()
    row = conn.execute("""
        SELECT av.id, pai.autor_token AS tutor_token
        FROM alertas av
        JOIN alertas pai ON pai.id = av.pet_pai_id
        WHERE av.id = ?
    """, (av_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Evento não encontrado"}), 404
    if row["tutor_token"] and token != row["tutor_token"] and token != ADMIN_TOKEN:
        conn.close()
        return jsonify({"error": "Apenas o tutor pode descartar este registro."}), 403
    conn.execute("UPDATE alertas SET ativo = 0, contato_avistador = '' WHERE id = ?", (av_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "descartado": av_id})


@app.route("/api/pets/<int:pet_id>/avistamento", methods=["POST"])
def registrar_avistamento_pet(pet_id):
    """
    Registra um ponto de avistamento vinculado a um Pet Desaparecido:
    - Quem avista NUNCA recebe o WhatsApp do tutor.
    - Opcionalmente, quem avista pode liberar seu contato EXCLUSIVAMENTE para o tutor.
    - Dispara notificação Push via Firebase para o celular do tutor.
    """
    data = request.json or {}
    lat = data.get("lat")
    lng = data.get("lng")
    if lat is None or lng is None:
        return jsonify({"error": "Localização do avistamento é obrigatória."}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, titulo, bairro, cidade, especie, porte, foto_url, autor_token
        FROM alertas
        WHERE id = ? AND pilar = 'pet' AND ativo = 1
    """, (pet_id,))
    pet_pai = cur.fetchone()
    if not pet_pai:
        conn.close()
        return jsonify({"error": "Pet não encontrado ou já encerrado."}), 404

    subtipo = (data.get("subtipo_evento") or "avistamento").strip().lower()
    if subtipo not in ("avistamento", "resgatado"):
        subtipo = "avistamento"
    eh_resgate = (subtipo == "resgatado")

    obs = (data.get("descricao") or (
        "Possível resgate: usuário segurou o animal e enviou foto para confirmação do tutor."
        if eh_resgate else "Pet avistado neste local por um usuário do Alerta Urbano."
    )).strip()[:400]
    foto_avistamento = (data.get("foto_url") or ("" if eh_resgate else (pet_pai["foto_url"] or ""))).strip()
    bairro = (data.get("bairro") or pet_pai["bairro"] or "Cascavel").strip()
    autor_token = (data.get("autor_token") or "").strip()[:100]
    permitir_contato = bool(data.get("permitir_contato_tutor"))
    contato_av = normalizar_telefone(data.get("contato_avistador") or "") if permitir_contato else ""
    avistador_nome = (data.get("avistador_nome") or "").strip()[:60] if permitir_contato else ""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO alertas (
            tipo, pilar, cidade, titulo, descricao, rua, bairro, lat, lng,
            peso, foto_url, autor_token, fonte_tipo, fonte_nome,
            especie, porte, status_pet, pet_pai_id, contato_avistador, avistador_nome, subtipo_evento, created_at
        )
        VALUES ('pet_avistado', 'pet', ?, ?, ?, ?, ?, ?, ?, 2, ?, ?, 'comunidade_pet', 'Comunidade', ?, ?, 'avistado', ?, ?, ?, ?, ?)
    """, (
        pet_pai["cidade"] or "Cascavel",
        f"{'Resgatado' if eh_resgate else 'Avistado'}: {pet_pai['titulo']}",
        obs,
        bairro,
        bairro,
        float(lat),
        float(lng),
        foto_avistamento,
        autor_token,
        pet_pai["especie"] or "",
        pet_pai["porte"] or "",
        pet_id,
        contato_av,
        avistador_nome,
        subtipo,
        agora,
    ))
    avistamento_id = cur.lastrowid
    cur.execute("UPDATE alertas SET confirmacoes = confirmacoes + 1, peso = peso + 1 WHERE id = ?", (pet_id,))

    # Busca token Firebase do tutor para disparar Push na tela bloqueada
    tutor_fcm = ""
    if pet_pai["autor_token"]:
        u_row = cur.execute("SELECT fcm_token FROM usuarios WHERE autor_token = ?", (pet_pai["autor_token"],)).fetchone()
        if u_row and u_row["fcm_token"]:
            tutor_fcm = u_row["fcm_token"]

    conn.commit()
    conn.close()

    push_enviado = False
    if tutor_fcm:
        push_titulo = f"🛟 POSSÍVEL RESGATE: {pet_pai['titulo']}!" if eh_resgate else f"🐾 {pet_pai['titulo']} foi avistado!"
        push_corpo = (
            f"Alguém segurou um animal parecido em {bairro} e enviou foto para você confirmar!"
            if eh_resgate else f"Alguém marcou Visto Aqui agora em {bairro}. Toque para ver a trilha no mapa."
        )
        push_enviado = enviar_push_firebase(
            tutor_fcm,
            push_titulo,
            push_corpo,
            {"pet_id": pet_id, "avistamento_id": avistamento_id, "subtipo": subtipo, "lat": lat, "lng": lng},
        )

    return jsonify({
        "status": "ok",
        "avistamento_id": avistamento_id,
        "pet_pai_id": pet_id,
        "subtipo_evento": subtipo,
        "push_enviado": push_enviado,
    }), 201


@app.route("/api/alertas/<int:alerta_id>/confirmar", methods=["POST"])
def confirmar_alerta(alerta_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE alertas SET confirmacoes = confirmacoes + 1, peso = peso + 1 WHERE id = ?", (alerta_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/alertas/<int:alerta_id>/renovar", methods=["POST"])
def renovar_alerta(alerta_id):
    data = request.json or {}
    token = data.get("autor_token") or request.args.get("autor_token", "")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, pilar, autor_token FROM alertas WHERE id = ?", (alerta_id,))
    alerta = cur.fetchone()
    if not alerta:
        conn.close()
        return jsonify({"error": "Registro não encontrado."}), 404

    db_autor_token = alerta["autor_token"]
    if db_autor_token and token != db_autor_token and token != ADMIN_TOKEN:
        conn.close()
        return jsonify({"error": "Apenas o autor deste registro pode renová-lo."}), 403

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("UPDATE alertas SET created_at = ?, ativo = 1 WHERE id = ?", (agora, alerta_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "renovado": alerta_id, "novo_created_at": agora})


@app.route("/api/alertas/<int:alerta_id>/encontrado", methods=["POST"])
@app.route("/api/alertas/<int:alerta_id>/desativar", methods=["POST"])
@app.route("/api/alertas/<int:alerta_id>", methods=["DELETE"])
def desativar_alerta(alerta_id):
    """
    Regra Suprema do Rigo + LGPD:
    - Somente o autor (autor_token) ou admin pode encerrar um registro de Pet.
    - Ao encerrar, limpa automaticamente o telefone/WhatsApp (contato = '') por LGPD.
    """
    data = request.json or {}
    token = data.get("autor_token") or request.args.get("autor_token", "")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, pilar, autor_token FROM alertas WHERE id = ?", (alerta_id,))
    alerta = cur.fetchone()
    if not alerta:
        conn.close()
        return jsonify({"error": "Registro não encontrado."}), 404

    db_autor_token = alerta["autor_token"]
    if db_autor_token and token != db_autor_token and token != ADMIN_TOKEN:
        conn.close()
        return jsonify({
            "error": "Acesso negado. Apenas o autor que cadastrou este registro tem permissão para encerrá-lo."
        }), 403

    eh_encontrado = request.path.endswith("/encontrado")
    if eh_encontrado:
        cur.execute("UPDATE alertas SET ativo = 0, status_pet = 'encontrado', contato = '', contato_avistador = '' WHERE id = ? OR pet_pai_id = ?", (alerta_id, alerta_id))
    else:
        cur.execute("UPDATE alertas SET ativo = 0, contato = '', contato_avistador = '' WHERE id = ? OR pet_pai_id = ?", (alerta_id, alerta_id))

    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "desativado": alerta_id, "encontrado": eh_encontrado})


@app.route("/api/pets/<int:pet_id>/adotar", methods=["GET"])
def obter_contato_adocao(pet_id):
    import urllib.parse
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, titulo, contato, consentimento_contato, bairro, cidade, tipo, status_pet FROM alertas WHERE id = ? AND ativo = 1", (pet_id,))
    pet = cur.fetchone()
    conn.close()
    if not pet:
        return jsonify({"error": "Pet não encontrado ou já adotado."}), 404
    p = dict(pet)
    if not p.get("contato") or not p.get("consentimento_contato"):
        return jsonify({"error": "Tutor não disponibilizou contato via WhatsApp para este pet."}), 400
    msg = urllib.parse.quote(f"Olá! Vi o pet '{p.get('titulo')}' anunciado para adoção responsável no Alerta Urbano Cascavel. Gostaria de saber mais informações!")
    wa_url = f"https://wa.me/{p.get('contato')}?text={msg}"
    return jsonify({"status": "ok", "whatsapp_url": wa_url, "titulo": p.get("titulo")})


@app.route("/api/denuncias/<int:alerta_id>/dossie", methods=["GET"])
def gerar_dossie_denuncia(alerta_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM alertas WHERE id = ?", (alerta_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Registro não encontrado"}), 404
    a = dict(row)
    dossie_texto = (
        f"🚨 DOSSIÊ DE REGISTRO — BEM-ESTAR ANIMAL (CASCAVEL/PR)\n"
        f"--------------------------------------------------\n"
        f"Tipo de Ocorrência: {a.get('titulo')}\n"
        f"Data/Hora: {a.get('created_at')}\n"
        f"Bairro: {a.get('bairro', 'Cascavel')}\n"
        f"Localização GPS: {a.get('lat')}, {a.get('lng')}\n"
        f"Localização Maps: https://maps.google.com/?q={a.get('lat')},{a.get('lng')}\n"
        f"Espécie/Porte: {a.get('especie', '')} ({a.get('porte', '')})\n"
        f"Relato dos Fatos:\n{a.get('descricao', 'Sem descrição adicional.')}\n"
        f"{'Foto registrada: ' + a.get('foto_url') if a.get('foto_url') else ''}\n"
        f"--------------------------------------------------\n"
        f"Órgãos Oficiais de Cascavel:\n"
        f"• SEMA / Bem-Estar Animal: Ouvidoria 156 / Atende.net\n"
        f"• Polícia Civil do Paraná (15ª SDP / Delegacia Cidadã): policiacivil.pr.gov.br\n"
        f"• Polícia Militar Ambiental (Força Verde): 190 ou 181"
    )
    return jsonify({
        "status": "ok",
        "id": alerta_id,
        "dossie_texto": dossie_texto,
        "links_oficiais": {
            "sema_ouvidoria": "https://cascavel.atende.net",
            "delegacia_cidada": "https://www.policiacivil.pr.gov.br",
            "pm_ambiental": "tel:190"
        }
    })


@app.route("/cartaz/<int:alerta_id>")
def ver_cartaz(alerta_id):
    """
    Cartaz Oficial de Utilidade Pública — Alerta Urbano Cascavel.
    Visualmente otimizado para abertura imediata no WhatsApp e redes sociais.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM alertas WHERE id = ?", (alerta_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Alerta Urbano Cascavel</title>
  <style>
    body { font-family: -apple-system, sans-serif; background: #09090b; color: #fff; text-align: center; padding: 40px 20px; }
    .card { background: #18181b; max-width: 420px; margin: 0 auto; padding: 30px; border-radius: 20px; border: 2px solid #27272a; }
    .btn { display: inline-block; background: #FED700; color: #000; font-weight: 800; padding: 12px 24px; border-radius: 999px; text-decoration: none; margin-top: 20px; }
  </style>
</head>
<body>
  <div class="card">
    <h2>Alerta Concluído</h2>
    <p style="margin-top:10px; color:#a1a1aa;">Este registro foi marcado como localizado ou encerrado pelo autor.</p>
    <a href="/download" class="btn">Baixar Alerta Urbano</a>
  </div>
</body>
</html>""", 404

    a = dict(row)
    titulo = html.escape(a.get("titulo") or "Alerta Pet")
    bairro = html.escape(a.get("bairro") or "Cascavel")
    descricao = html.escape(a.get("descricao") or "Sem detalhes adicionais informados.")
    status_pet = (a.get("status_pet") or "").lower()
    tipo = (a.get("tipo") or "").lower()
    foto_url = a.get("foto_url") or "https://alerta-urbano-cascavel.onrender.com/static/logo_bolha_pura.png?v=60"
    especie = html.escape(a.get("especie") or "")
    porte = html.escape(a.get("porte") or "")
    recompensa = html.escape(a.get("recompensa") or "")
    contato = a.get("contato") or ""

    if status_pet == "desaparecido":
        badge_bg = "#DC2626"
        badge_txt = "#FFFFFF"
        badge_label = "🚨 PET DESAPARECIDO"
        og_status = "Desaparecido"
    elif status_pet == "avistado" or "avistad" in tipo:
        badge_bg = "#FED700"
        badge_txt = "#000000"
        badge_label = "👁️ ANIMAL AVISTADO NA RUA"
        og_status = "Avistado na rua"
    elif "adocao" in tipo:
        badge_bg = "#009B3A"
        badge_txt = "#FFFFFF"
        badge_label = "💚 ADOÇÃO RESPONSÁVEL"
        og_status = "Para Adoção"
    else:
        badge_bg = "#FED700"
        badge_txt = "#000000"
        badge_label = "📢 COMUNICADO CÍVICO"
        og_status = "Alerta"

    og_title = f"{titulo} ({og_status} em Cascavel/PR)"
    og_desc = f"Bairro: {bairro}. Toque para ver foto e detalhes completos no Alerta Urbano."
    download_url = "https://alerta-urbano-cascavel.onrender.com/download"
    cartaz_url = f"https://alerta-urbano-cascavel.onrender.com/cartaz/{alerta_id}"

    msg_whatsapp = (
        f"📢 *ALERTA URBANO CASCAVEL*\n"
        f"🐾 *{badge_label}*\n\n"
        f"🐶 *Nome:* {titulo}\n"
        f"📍 *Bairro:* {bairro} • Cascavel/PR\n"
        f"{f'📏 *Porte:* {porte} • {especie}' + chr(10) if porte or especie else ''}"
        f"{f'💰 *Recompensa:* {recompensa}' + chr(10) if recompensa else ''}"
        f"📝 *Detalhes:* {descricao}\n\n"
        f"🖼️ *VER CARTAZ OFICIAL COM FOTO:*\n"
        f"👉 {cartaz_url}\n\n"
        f"📱 *Baixe o App Comunitário de Cascavel:*\n"
        f"👉 {download_url}"
    )
    msg_wa_encoded = urllib.parse.quote(msg_whatsapp)

    btn_contato_html = ""
    if contato and any(c.isdigit() for c in contato):
        num_limpo = "".join(filter(str.isdigit, contato))
        if len(num_limpo) in (10, 11):
            num_limpo = "55" + num_limpo
        wa_tutor_msg = urllib.parse.quote(f"Olá, vi o cartaz do {titulo} no Alerta Urbano e tenho informações!")
        btn_contato_html = f"""
        <a href="https://wa.me/{num_limpo}?text={wa_tutor_msg}" target="_blank" class="btn-action btn-tutor">
          💬 Falar com o Tutor no WhatsApp
        </a>
        """

    tag_porte_html = f'<span class="tag-pill">{porte}</span>' if porte else ''
    tag_especie_html = f'<span class="tag-pill">{especie}</span>' if especie else ''
    tag_recompensa_html = f'<span class="tag-pill" style="background:#dc2626;color:#fff;">💰 Recompensa: {recompensa}</span>' if recompensa else ''

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>{og_title}</title>
  
  <!-- OpenGraph WhatsApp & Redes Sociais -->
  <meta property="og:type" content="article">
  <meta property="og:title" content="{og_title}">
  <meta property="og:description" content="{og_desc}">
  <meta property="og:image" content="{foto_url}">
  <meta property="og:url" content="{cartaz_url}">
  <meta property="og:site_name" content="Alerta Urbano Cascavel">
  
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{og_title}">
  <meta name="twitter:description" content="{og_desc}">
  <meta name="twitter:image" content="{foto_url}">

  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0f172a;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 100vh;
      padding: 0 0 40px;
    }}
    .topbar {{
      width: 100%;
      background: #009B3A;
      padding: 12px 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      color: #ffffff;
      box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    }}
    .topbar img {{
      width: 32px;
      height: 32px;
      border-radius: 50%;
      border: 2px solid #FED700;
    }}
    .topbar-text {{
      display: flex;
      flex-direction: column;
      line-height: 1.15;
    }}
    .topbar-title {{ font-size: 15px; font-weight: 900; letter-spacing: 0.5px; }}
    .topbar-sub {{ font-size: 11px; font-weight: 700; color: #FED700; letter-spacing: 0.8px; }}

    .container {{
      width: 100%;
      max-width: 440px;
      padding: 16px 14px;
    }}
    
    .cartaz-box {{
      background: #FED700;
      border: 2.5px solid #000000;
      border-radius: 20px;
      overflow: hidden;
      box-shadow: 0 16px 40px rgba(0,0,0,0.5);
    }}
    .badge-status {{
      background: {badge_bg};
      color: {badge_txt};
      font-size: 13.5px;
      font-weight: 900;
      text-align: center;
      padding: 10px 14px;
      letter-spacing: 1px;
      border-bottom: 2px solid #000000;
    }}
    .photo-wrap {{
      width: 100%;
      max-height: 280px;
      background: #000000;
      overflow: hidden;
      position: relative;
    }}
    .photo-wrap img {{
      width: 100%;
      height: 100%;
      max-height: 280px;
      object-fit: cover;
      display: block;
    }}
    .cartaz-body {{
      padding: 16px 16px 18px;
    }}
    .pet-name {{
      font-size: 24px;
      font-weight: 900;
      color: #000000;
      line-height: 1.15;
      text-align: center;
      margin-bottom: 4px;
    }}
    .pet-bairro {{
      font-size: 13px;
      font-weight: 800;
      color: #000000;
      text-align: center;
      opacity: 0.9;
      margin-bottom: 12px;
      letter-spacing: 0.6px;
    }}
    .tags-grid {{
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 6px;
      margin-bottom: 12px;
    }}
    .tag-pill {{
      background: #000000;
      color: #FED700;
      font-size: 11px;
      font-weight: 800;
      padding: 5px 10px;
      border-radius: 999px;
    }}
    .desc-box {{
      background: #FFFFFF;
      border: 1.5px solid #000000;
      border-radius: 12px;
      padding: 12px;
      font-size: 13px;
      line-height: 1.45;
      color: #0f172a;
      margin-bottom: 14px;
      font-weight: 500;
    }}

    .actions-wrap {{
      display: flex;
      flex-direction: column;
      gap: 9px;
    }}
    .btn-action {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 13px 18px;
      border-radius: 14px;
      text-decoration: none;
      font-size: 14px;
      font-weight: 900;
      border: 2px solid #000000;
      cursor: pointer;
      text-align: center;
      box-shadow: 0 4px 12px rgba(0,0,0,0.2);
      transition: transform 0.1s ease;
    }}
    .btn-action:active {{ transform: scale(0.98); }}
    .btn-tutor {{
      background: #22c55e;
      color: #FFFFFF;
      border-color: #15803d;
    }}
    .btn-whatsapp {{
      background: #000000;
      color: #FFFFFF;
    }}
    .btn-download {{
      background: #009B3A;
      color: #FFFFFF;
      border-color: #007028;
    }}
    
    .app-promo-card {{
      margin-top: 18px;
      background: #1e293b;
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 16px;
      padding: 16px;
      color: #ffffff;
      text-align: center;
    }}
    .app-promo-card h4 {{
      font-size: 14px;
      font-weight: 800;
      color: #FED700;
      margin-bottom: 6px;
    }}
    .app-promo-card p {{
      font-size: 12px;
      color: #cbd5e1;
      line-height: 1.4;
      margin-bottom: 12px;
    }}
    .btn-promo {{
      display: inline-block;
      background: #FED700;
      color: #000000;
      font-size: 13px;
      font-weight: 900;
      padding: 10px 20px;
      border-radius: 999px;
      text-decoration: none;
    }}
  </style>
</head>
<body>

  <header class="topbar">
    <img src="/static/logo_bolha_pura.png?v=60" alt="Alerta Urbano">
    <div class="topbar-text">
      <span class="topbar-title">ALERTA URBANO</span>
      <span class="topbar-sub">CASCAVEL • PARANÁ</span>
    </div>
  </header>

  <main class="container">
    <article class="cartaz-box">
      <div class="badge-status">{badge_label}</div>
      <div class="photo-wrap">
        <img src="{foto_url}" alt="{titulo}">
      </div>
      <div class="cartaz-body">
        <h1 class="pet-name">{titulo}</h1>
        <div class="pet-bairro">BAIRRO {bairro.upper()} • CASCAVEL</div>

        <div class="tags-grid">
          {tag_porte_html}
          {tag_especie_html}
          {tag_recompensa_html}
        </div>

        <div class="desc-box">
          {descricao}
        </div>

        <div class="actions-wrap">
          {btn_contato_html}
          <a href="https://api.whatsapp.com/send?text={msg_wa_encoded}" class="btn-action btn-whatsapp">
            ↗️ Compartilhar este Cartaz no WhatsApp
          </a>
        </div>
      </div>
    </article>

    <section class="app-promo-card">
      <h4>ALERTA URBANO CASCAVEL</h4>
      <p>Rede comunitária gratuita para monitoramento em tempo real de pets desaparecidos, segurança pública e avisos de trânsito em Cascavel.</p>
      <a href="{download_url}" class="btn-promo">Baixar Aplicativo Oficial</a>
    </section>
  </main>

</body>
</html>"""
    return html_content


# Inicializa/migra banco ao importar (compatível com Gunicorn no Render)
init_db()

if __name__ == "__main__":
    print("Iniciando Alerta Urbano v3.0 na porta 5000...")
    app.run(host="0.0.0.0", port=5000, debug=False)
