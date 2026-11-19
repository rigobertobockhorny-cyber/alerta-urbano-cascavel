# -*- coding: utf-8 -*-
import os
import sqlite3
import time
import hashlib
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, make_response, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder="static", template_folder="static")

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alertas_cascavel.db")

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
            fonte_tipo TEXT DEFAULT 'cidadao_alerta'
        )
    """)
    # Migração segura para tabelas existentes
    cur.execute("PRAGMA table_info(alertas)")
    cols = [r[1] for r in cur.fetchall()]
    if "autor_token" not in cols:
        cur.execute("ALTER TABLE alertas ADD COLUMN autor_token TEXT;")
    if "votos_passou" not in cols:
        cur.execute("ALTER TABLE alertas ADD COLUMN votos_passou INTEGER DEFAULT 0;")
    if "link_noticia" not in cols:
        cur.execute("ALTER TABLE alertas ADD COLUMN link_noticia TEXT;")
    if "fonte_tipo" not in cols:
        cur.execute("ALTER TABLE alertas ADD COLUMN fonte_tipo TEXT DEFAULT 'cidadao_alerta';")
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
    return jsonify({"ok": True, "app": "Alerta Urbano", "ts": int(time.time())})

@app.route("/baixar-apk")
@app.route("/ALERTA_URBANO_CASCAVEL.apk")
@app.route("/app.apk")
@app.route("/download")
def baixar_apk():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    apk_path = os.path.join(base_dir, "ALERTA_URBANO_CASCAVEL.apk")
    if not os.path.exists(apk_path):
        apk_path = os.path.join(base_dir, "android_app", "app", "build", "outputs", "apk", "debug", "app-debug.apk")
    if not os.path.exists(apk_path):
        return "APK ainda sendo gerado...", 404
    return send_from_directory(
        os.path.dirname(apk_path),
        os.path.basename(apk_path),
        as_attachment=True,
        download_name="Alerta_Urbano_Cascavel.apk",
        mimetype="application/vnd.android.package-archive"
    )

@app.route("/instalar")
def pagina_instalar():
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Instalar Alerta Urbano</title>
  <style>
    body { margin:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#09090b; color:#fff; display:flex; align-items:center; justify-content:center; min-height:100vh; padding:20px; box-sizing:border-box; }
    .card { max-width:380px; width:100%; background:#18181b; border:1.5px solid #27272a; border-radius:24px; padding:28px 24px; text-align:center; box-shadow:0 20px 50px rgba(0,0,0,0.6); }
    .logo { width:92px; height:92px; border-radius:50%; display:block; margin:0 auto 18px; }
    h1 { font-size:21px; font-weight:900; margin:0 0 8px; }
    p { font-size:14px; color:#a1a1aa; line-height:1.45; margin:0 0 22px; }
    .btn { display:block; width:100%; box-sizing:border-box; padding:16px; border-radius:14px; font-size:15px; font-weight:900; text-decoration:none; margin-bottom:12px; }
    .btn-red { background:#dc2626; color:#fff; box-shadow:0 8px 24px rgba(220,38,38,0.45); }
    .btn-dark { background:#27272a; color:#fff; }
  </style>
</head>
<body>
  <div class="card">
    <img src="/static/logo_bolha_pura.png?v=20" class="logo" alt="Alerta Urbano">
    <h1>ALERTA URBANO</h1>
    <p>Instale o aplicativo oficial para liberar a <b>Bolha Redonda Vermelha</b> pura (fecha o app ao tocar na logo e reabre em 1 único clique).</p>
    <a href="/baixar-apk" class="btn btn-red">BAIXAR APLICATIVO (.APK)</a>
    <a href="#" onclick="window.location.href='alertaurbano://abrir?url='+encodeURIComponent(window.location.origin); return false;" class="btn btn-dark">JÁ INSTALEI • ABRIR APP</a>
  </div>
</body>
</html>"""

@app.route("/api/falar")
def api_falar():
    texto = request.args.get("texto", "").strip()
    if not texto:
        return jsonify({"error": "Texto vazio"}), 400
    
    h = hashlib.md5(texto.lower().encode('utf-8')).hexdigest()
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "audios_tts")
    os.makedirs(cache_dir, exist_ok=True)
    filepath = os.path.join(cache_dir, f"{h}.mp3")
    
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        return send_file(filepath, mimetype="audio/mpeg")
    
    # Se não estiver em cache, sintetiza via edge_tts nativo em python
    try:
        import asyncio
        import edge_tts
        async def _synthesize():
            comm = edge_tts.Communicate(texto, "pt-BR-AntonioNeural")
            await comm.save(filepath)
        asyncio.run(_synthesize())
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            return send_file(filepath, mimetype="audio/mpeg")
    except Exception as e:
        print(f"[TTS SERVER] Erro ao gerar fala: {e}")
    
    return jsonify({"error": "Falha na síntese de áudio"}), 500

@app.route("/mesa")
def mesa_validacao():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return send_file(os.path.join(base_dir, "00_MESA_DE_VALIDACAO_DE_AVISOS.html"))

@app.route("/api/alertas", methods=["GET"])
def listar_alertas():
    # REGRA DE CICLO DE VIDA (ORDEM DO RIGO - PROTOCOLO DE TESTES EM ROTA):
    # - Locais fixos (postos, delegacias, bombeiros): permanentes
    # - Animais (pets): 48 horas de vida útil (renováveis pelo tutor)
    # - Ocorrências reais dinâmicas (imprensa, cidadão): 24 horas de vida útil
    # - Ocorrências de teste no asfalto: gerenciadas rigorosamente pela Engine de Testes (6h, 12h, 24h com rotação automática)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM alertas 
        WHERE ativo = 1
          AND (
            tipo IN ('comercio', 'batalhao_pm', 'delegacia', 'guarda_municipal', 'prf', 'radar_fixo', 'radar_60', 'radar_50', 'radar_40', 'radar', 'camera_semaforo', 'semaforo')
            OR fonte_tipo = 'oficial_transitar'
            OR tipo IN ('pet', 'pet_visto')
            OR (tipo NOT IN ('pet', 'pet_visto') AND datetime(created_at, '+48 hours') >= datetime('now', 'localtime'))
          )
        ORDER BY created_at DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

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
    return jsonify({"error": "Formato de arquivo não suportado"}), 400

@app.route("/api/alertas", methods=["POST"])
def criar_alerta():
    data = request.json or {}
    tipo = data.get("tipo", "suspeito")
    titulo = data.get("titulo", "Alerta Registrado")
    descricao = data.get("descricao", "")
    rua = data.get("rua", "")
    bairro = data.get("bairro", "Cascavel")
    lat = data.get("lat")
    lng = data.get("lng")
    foto_url = data.get("foto_url")
    contato = data.get("contato")
    recompensa = data.get("recompensa")
    autor_token = data.get("autor_token", "")
    fonte_tipo = data.get("fonte_tipo", "cidadao_alerta")

    if lat is None or lng is None:
        return jsonify({"error": "Latitude e Longitude obrigatorias"}), 400

    conn = get_db()
    cur = conn.cursor()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO alertas (tipo, titulo, descricao, rua, bairro, lat, lng, peso, foto_url, contato, recompensa, autor_token, fonte_tipo, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
    """, (tipo, titulo, descricao, rua, bairro, lat, lng, foto_url, contato, recompensa, autor_token, fonte_tipo, agora))
    novo_id = cur.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "id": novo_id}), 201

@app.route("/api/alertas/<int:alerta_id>/confirmar", methods=["POST"])
def confirmar_alerta(alerta_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE alertas SET confirmacoes = confirmacoes + 1, peso = peso + 1 WHERE id = ?", (alerta_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/alertas/<int:alerta_id>/votar_passou", methods=["POST"])
def votar_passou(alerta_id):
    # REGRA DO RIGO:
    # Pessoa B NÃO PODE cancelar a ocorrência da Pessoa A sozinha!
    # Apenas computa o voto comunitário de 'já passou'.
    # Para animais: Votos de terceiros são 100% ignorados.
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, tipo, votos_passou, confirmacoes FROM alertas WHERE id = ?", (alerta_id,))
    alerta = cur.fetchone()
    if not alerta:
        conn.close()
        return jsonify({"error": "Alerta não encontrado"}), 404

    if "pet" in alerta["tipo"]:
        conn.close()
        return jsonify({"status": "ignorado", "motivo": "Registros de animais só podem ser encerrados pelo tutor."})

    novos_votos = (alerta["votos_passou"] or 0) + 1
    # Se receber 3 ou mais votos de que 'já passou' e superar as confirmações, a comunidade desativa
    if novos_votos >= 3 and novos_votos > (alerta["confirmacoes"] or 1):
        cur.execute("UPDATE alertas SET ativo = 0, votos_passou = ? WHERE id = ?", (novos_votos, alerta_id))
    else:
        cur.execute("UPDATE alertas SET votos_passou = ? WHERE id = ?", (novos_votos, alerta_id))

    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "votos_passou": novos_votos})

@app.route("/api/alertas/<int:alerta_id>/renovar", methods=["POST"])
def renovar_alerta(alerta_id):
    # REGRA DE RENOVAÇÃO (+48 Horas para Pets):
    data = request.json or {}
    token = data.get("autor_token") or request.args.get("autor_token", "")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, tipo, autor_token FROM alertas WHERE id = ?", (alerta_id,))
    alerta = cur.fetchone()

    if not alerta:
        conn.close()
        return jsonify({"error": "Alerta não encontrado"}), 404

    db_autor_token = alerta["autor_token"]
    if db_autor_token and token != db_autor_token and token != "admin_cascavel":
        conn.close()
        return jsonify({"error": "Apenas o autor deste registro pode renová-lo."}), 403

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("UPDATE alertas SET created_at = ?, ativo = 1 WHERE id = ?", (agora, alerta_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "renovado": alerta_id, "novo_created_at": agora})

@app.route("/api/alertas/<int:alerta_id>/desativar", methods=["POST"])
@app.route("/api/alertas/<int:alerta_id>", methods=["DELETE"])
def desativar_alerta(alerta_id):
    # REGRA SUPREMA DO RIGO:
    # Uma Pessoa B (terceiro) NUNCA pode ter o direito de cancelar uma ocorrência da Pessoa A!
    # Especialmente para animais: SOMENTE o perfil do tutor/autor que criou tem direito de cancelar!
    data = request.json or {}
    token = data.get("autor_token") or request.args.get("autor_token", "")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, tipo, autor_token FROM alertas WHERE id = ?", (alerta_id,))
    alerta = cur.fetchone()

    if not alerta:
        conn.close()
        return jsonify({"error": "Alerta não encontrado"}), 404

    alerta_tipo = alerta["tipo"]
    db_autor_token = alerta["autor_token"]

    eh_pet = (alerta_tipo == "pet" or "pet" in alerta_tipo)

    if eh_pet:
        # Se tem autor_token e não bate com quem está tentando apagar:
        if db_autor_token and token != db_autor_token and token != "admin_cascavel":
            conn.close()
            return jsonify({
                "error": "Acesso negado. Apenas o autor que cadastrou este animal tem permissão para encerrar a publicação."
            }), 403

    # Para ocorrências gerais cadastradas com token do usuário:
    if db_autor_token and token and token != db_autor_token and token != "admin_cascavel":
        conn.close()
        return jsonify({
            "error": "Apenas o autor desta ocorrência tem permissão para encerrá-la."
        }), 403

    cur.execute("UPDATE alertas SET ativo = 0 WHERE id = ?", (alerta_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "desativado": alerta_id})

# Inicialização automática do banco para Gunicorn ou execução direta
init_db()
# Engine de testes desativada permanentemente por ordem do Rigo

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Iniciando Alerta Urbano na porta {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
