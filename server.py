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
    "camera_semaforo", "semaforo", "lombada", "buraco", "acidente",
    "transito", "policia", "comercio", "batalhao_pm", "delegacia",
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
    ]
    for col_name, col_def in novas_colunas:
        if col_name not in cols:
            cur.execute(f"ALTER TABLE alertas ADD COLUMN {col_name} {col_def};")

    # Índices para performance do Dashboard Slim e Mapa de Calor
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alertas_ativo_pilar ON alertas (ativo, pilar, cidade);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alertas_pet_pai ON alertas (pet_pai_id);")

    # Tabela de Perfil / Cadastro do Cidadão (v3.1)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            autor_token TEXT UNIQUE NOT NULL,
            nome TEXT DEFAULT '',
            whatsapp TEXT DEFAULT '',
            bairro TEXT DEFAULT 'Centro',
            cidade TEXT DEFAULT 'Cascavel',
            foto_url TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

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
        download_name="Alerta_Urbano_v3.apk",
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
    - pet (comunidade + achados/perdidos imprensa; 7 dias para imprensa/renováveis para comunidade)
    - seguranca (imprensa oficial; últimas 48h)
    - utilidade (fontes oficiais/imprensa; últimas 48h)
    """
    cidade = request.args.get("cidade", "Cascavel").strip()
    pilar = request.args.get("pilar", "").strip().lower()

    conn = get_db()
    cur = conn.cursor()

    params = [cidade]
    pilar_clause = ""
    if pilar in ("pet", "seguranca", "utilidade"):
        pilar_clause = " AND pilar = ?"
        params.append(pilar)

    cur.execute(f"""
        SELECT * FROM alertas
        WHERE ativo = 1
          AND LOWER(COALESCE(cidade, 'Cascavel')) = LOWER(?)
          AND pilar IN ('pet', 'seguranca', 'utilidade')
          {pilar_clause}
          AND (
            pilar = 'pet'
            OR (pilar IN ('seguranca', 'utilidade') AND datetime(created_at, '+48 hours') >= datetime('now', 'localtime'))
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
        # Privacidade: sinaliza se tem WhatsApp sem precisar expor desnecessariamente se não houver consentimento
        r["tem_whatsapp"] = bool(r.get("contato"))

    return jsonify(rows)


@app.route("/api/alertas", methods=["POST"])
def criar_alerta():
    """
    BLINDAGEM ANTI-FAKE NEWS v3.0:
    - Requisições públicas (usuário comum) SÓ podem criar registros de PETS (pet_perdido / pet_avistado).
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

    if not eh_robo_autorizado and pilar != "pet":
        return jsonify({
            "error": "Acesso restrito: alertas de Segurança e Utilidade Pública são alimentados exclusivamente por fontes oficiais e imprensa."
        }), 403

    lat = data.get("lat")
    lng = data.get("lng")
    if lat is None or lng is None:
        return jsonify({"error": "Localização (latitude e longitude) é obrigatória."}), 400

    titulo = (data.get("titulo") or ("Pet Desaparecido" if tipo == "pet_perdido" else "Pet Avistado")).strip()[:120]
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

    # LGPD: só armazena WhatsApp se houver consentimento explícito no formulário de Pet
    consentimento = 1 if data.get("consentimento_contato") else 0
    contato_bruto = data.get("contato") or ""
    contato = normalizar_telefone(contato_bruto) if (pilar == "pet" and consentimento) else ""

    if pilar == "pet":
        status_pet = "avistado" if tipo == "pet_avistado" or pet_pai_id else "desaparecido"
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
            severidade, consentimento_contato, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tipo, pilar, cidade, titulo, descricao, rua, bairro, float(lat), float(lng),
        foto_url, contato, recompensa, link_noticia, autor_token,
        fonte_tipo, fonte_nome, especie, porte, status_pet, pet_pai_id,
        severidade, consentimento, agora,
    ))
    novo_id = cur.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "id": novo_id, "pilar": pilar, "tipo": tipo}), 201


@app.route("/api/pets/<int:pet_id>/avistamento", methods=["POST"])
def registrar_avistamento_pet(pet_id):
    """Registra um ponto de avistamento vinculado a um Pet Desaparecido (constrói trilha/calor)."""
    data = request.json or {}
    lat = data.get("lat")
    lng = data.get("lng")
    if lat is None or lng is None:
        return jsonify({"error": "Localização do avistamento é obrigatória."}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, titulo, bairro, cidade, especie, porte, foto_url FROM alertas WHERE id = ? AND pilar = 'pet' AND ativo = 1", (pet_id,))
    pet_pai = cur.fetchone()
    if not pet_pai:
        conn.close()
        return jsonify({"error": "Pet não encontrado ou já encerrado."}), 404

    obs = (data.get("descricao") or "Pet avistado neste local por um usuário do Alerta Urbano.").strip()[:400]
    foto_avistamento = (data.get("foto_url") or pet_pai["foto_url"] or "").strip()
    bairro = (data.get("bairro") or pet_pai["bairro"] or "Cascavel").strip()
    autor_token = (data.get("autor_token") or "").strip()[:100]
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO alertas (
            tipo, pilar, cidade, titulo, descricao, rua, bairro, lat, lng,
            peso, foto_url, autor_token, fonte_tipo, fonte_nome,
            especie, porte, status_pet, pet_pai_id, created_at
        )
        VALUES ('pet_avistado', 'pet', ?, ?, ?, ?, ?, ?, ?, 2, ?, ?, 'comunidade_pet', 'Comunidade', ?, ?, 'avistado', ?, ?)
    """, (
        pet_pai["cidade"] or "Cascavel",
        f"Avistado: {pet_pai['titulo']}",
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
        agora,
    ))
    avistamento_id = cur.lastrowid
    cur.execute("UPDATE alertas SET confirmacoes = confirmacoes + 1, peso = peso + 1 WHERE id = ?", (pet_id,))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "avistamento_id": avistamento_id, "pet_pai_id": pet_id}), 201


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
        cur.execute("UPDATE alertas SET ativo = 0, status_pet = 'encontrado', contato = '' WHERE id = ? OR pet_pai_id = ?", (alerta_id, alerta_id))
    else:
        cur.execute("UPDATE alertas SET ativo = 0, contato = '' WHERE id = ? OR pet_pai_id = ?", (alerta_id, alerta_id))

    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "desativado": alerta_id, "encontrado": eh_encontrado})


# Inicializa/migra banco ao importar (compatível com Gunicorn no Render)
init_db()

if __name__ == "__main__":
    print("Iniciando Alerta Urbano v3.0 na porta 5000...")
    app.run(host="0.0.0.0", port=5000, debug=False)
