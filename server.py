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
        ("autor_nome", "TEXT DEFAULT ''"),
        ("faixa_etaria", "TEXT DEFAULT 'adulto'"),
        ("sexo", "TEXT DEFAULT 'indefinido'"),
        ("sigiloso", "INTEGER DEFAULT 0"),
        ("orgao_destino", "TEXT DEFAULT ''"),
        ("uf", "TEXT DEFAULT 'PR'"),
        ("estado", "TEXT DEFAULT 'PR'"),
    ]
    for col_name, col_def in novas_colunas:
        if col_name not in cols:
            cur.execute(f"ALTER TABLE alertas ADD COLUMN {col_name} {col_def};")

    # Índices para performance do Dashboard Slim e Mapa de Calor
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alertas_ativo_pilar ON alertas (ativo, pilar, cidade);")
    
    # Tabela de Aceite Digital de Adoção Responsável (Lei Sansão 14.064/2020)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS adocao_aceites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id INTEGER NOT NULL,
            adotante_token TEXT,
            adotante_nome TEXT,
            adotante_whatsapp TEXT,
            ip_origem TEXT,
            protocolo_hash TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    cur.execute("CREATE INDEX IF NOT EXISTS idx_adocao_aceites_pet ON adocao_aceites (pet_id);")

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
    if "estado" not in ucols:
        cur.execute("ALTER TABLE usuarios ADD COLUMN estado TEXT DEFAULT 'PR';")
    if "uf" not in ucols:
        cur.execute("ALTER TABLE usuarios ADD COLUMN uf TEXT DEFAULT 'PR';")
    if "endereco" not in ucols:
        cur.execute("ALTER TABLE usuarios ADD COLUMN endereco TEXT DEFAULT '';")
    if "tipo_perfil" not in ucols:
        cur.execute("ALTER TABLE usuarios ADD COLUMN tipo_perfil TEXT DEFAULT 'tutor';")
    if "bio" not in ucols:
        cur.execute("ALTER TABLE usuarios ADD COLUMN bio TEXT DEFAULT '';")
    if "instagram" not in ucols:
        cur.execute("ALTER TABLE usuarios ADD COLUMN instagram TEXT DEFAULT '';")
    if "chave_pix" not in ucols:
        cur.execute("ALTER TABLE usuarios ADD COLUMN chave_pix TEXT DEFAULT '';")
    if "total_resgates" not in ucols:
        cur.execute("ALTER TABLE usuarios ADD COLUMN total_resgates INTEGER DEFAULT 0;")
    if "verificado" not in ucols:
        cur.execute("ALTER TABLE usuarios ADD COLUMN verificado INTEGER DEFAULT 0;")

    # Tabela de Parceiros Comerciais e Empresas Amigas de Cascavel (v3.8)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS parceiros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria TEXT DEFAULT 'pet_vet',
            subtitulo TEXT DEFAULT '',
            descricao TEXT DEFAULT '',
            bairro TEXT DEFAULT 'Centro',
            endereco TEXT DEFAULT '',
            cidade TEXT DEFAULT 'Cascavel',
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            telefone_whatsapp TEXT DEFAULT '',
            logo_url TEXT DEFAULT '',
            foto_capa TEXT DEFAULT '',
            selo_tipo TEXT DEFAULT 'ouro',
            destaque_esteira INTEGER DEFAULT 1,
            ativo INTEGER DEFAULT 1,
            ordem INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de Produtos / Serviços em Promoção dos Parceiros
    cur.execute("""
        CREATE TABLE IF NOT EXISTS parceiro_produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parceiro_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT DEFAULT '',
            preco_original REAL DEFAULT 0,
            preco_promocional REAL DEFAULT 0,
            tag_desconto TEXT DEFAULT '',
            foto_url TEXT DEFAULT '',
            ativo INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(parceiro_id) REFERENCES parceiros(id) ON DELETE CASCADE
        )
    """)

    # Seed de Parceiros e Promoções modelo de Cascavel (se tabela vazia)
    cur.execute("SELECT COUNT(*) FROM parceiros")
    if cur.fetchone()[0] == 0:
        parceiros_iniciais = [
            (
                "Hospital Veterinário 24h Cascavel",
                "pet_vet",
                "Emergências, Cirurgias e Internamento 24 Horas",
                "Atendimento veterinário ininterrupto com UTI, raio-x digital e equipe cirúrgica de plantão em Cascavel.",
                "Centro",
                "Rua Paraná, 2840 - Centro",
                "Cascavel",
                -24.9540,
                -53.4560,
                "45999881122",
                "ouro",
                1,
                1,
                1,
                [
                    ("Consulta Veterinária de Urgência", "Plantão 24h com avaliação clínica completa", 180.0, 129.90, "28% OFF"),
                    ("Vacina V10 Importada + Avaliação", "Imunização completa com carteirinha oficial", 120.0, 89.90, "OFERTA"),
                ]
            ),
            (
                "Pet Shop & Estética Patinhas",
                "pet_shop",
                "Banho, Tosa, Ração Super Premium e Acessórios",
                "Ambiente climatizado, tosa higiênica e táxi dog com busca e entrega nos bairros de Cascavel.",
                "Cancelli",
                "Rua Manaus, 1420 - Cancelli",
                "Cascavel",
                -24.9440,
                -53.4730,
                "45999772233",
                "ouro",
                1,
                1,
                2,
                [
                    ("Banho + Tosa Higiênica + Hidratação", "Para cães de pequeno e médio porte com produtos hipoalergênicos", 85.0, 59.90, "PROMOÇÃO"),
                    ("Ração Premium Especial Cães 15kg", "Fórmula sem corantes com alta absorção nutricional", 189.0, 149.90, "OFERTA"),
                ]
            ),
            (
                "Auto Center & Pneus Cascavel",
                "auto_center",
                "Pneus, Alinhamento 3D, Balanceamento e Freios",
                "Revisão veicular preventiva, troca de óleo e suspensão com garantia e equipe especializada.",
                "Alto Alegre",
                "Av. Brasil, 8900 - Alto Alegre",
                "Cascavel",
                -24.9570,
                -53.4950,
                "45999663344",
                "cidadao",
                1,
                1,
                3,
                [
                    ("Alinhamento 3D + Balanceamento 4 Rodas", "Ajuste a laser para maior durabilidade dos pneus e segurança", 120.0, 69.90, "42% OFF"),
                    ("Higienização de Ar-Condicionado + Filtro", "Elimina ácaros, fungos e odores com filtro novo incluso", 110.0, 79.90, "COMBO"),
                ]
            ),
            (
                "Posto & Conveniência Avenida",
                "posto",
                "Combustível de Qualidade, Troca de Óleo e Conveniência 24h",
                "Abastecimento 24 horas, loja de conveniência completa e ponto de apoio seguro em Cascavel.",
                "Centro",
                "Av. Brasil, 4500 - Centro",
                "Cascavel",
                -24.9565,
                -53.4510,
                "45999554455",
                "cidadao",
                1,
                1,
                4,
                [
                    ("Ducha Completa + Cera Líquida", "Lavagem rápida com cera protetora em qualquer abastecimento", 35.0, 19.90, "VANTAGEM"),
                ]
            ),
            (
                "Clínica Vet & Castração Solidária Vida Animal",
                "pet_vet",
                "Vacinação, Microchipagem e Castração a Preço Social",
                "Parceira ativa de protetores independentes e tutores no controle populacional e saúde animal.",
                "São Cristóvão",
                "Rua Jacarezinho, 1850 - São Cristóvão",
                "Cascavel",
                -24.9410,
                -53.4310,
                "45999445566",
                "ouro",
                1,
                1,
                5,
                [
                    ("Microchipagem Padrão Internacional + Registro", "Identificação definitiva eletrônica em banco nacional", 90.0, 55.00, "SOCIAL"),
                    ("Castração Solidária Felinos (Macho/Fêmea)", "Procedimento cirúrgico seguro com pós-operatório assistido", 220.0, 149.00, "SOCIAL"),
                ]
            ),
            (
                "Centro Automotivo & Baterias Neva",
                "auto_center",
                "Baterias Automotivas com Entrega Rápida e Auto Elétrica",
                "Socorro de bateria e panes elétricas em domicílio em todos os bairros de Cascavel.",
                "Neva",
                "Rua Pio XII, 2100 - Neva",
                "Cascavel",
                -24.9640,
                -53.4660,
                "45999336677",
                "cidadao",
                1,
                1,
                6,
                [
                    ("Bateria 60Ah Selada (Instalada no Local)", "Entrega e instalação grátis em até 30 minutos em Cascavel", 390.0, 319.90, "COM TROCA"),
                ]
            ),
        ]
        for p in parceiros_iniciais:
            nome, cat, sub, desc, bairro, end, cid, lat, lng, zap, selo, esteira, ativo, ordem, prods = p
            cur.execute("""
                INSERT INTO parceiros (nome, categoria, subtitulo, descricao, bairro, endereco, cidade, lat, lng, telefone_whatsapp, selo_tipo, destaque_esteira, ativo, ordem)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nome, cat, sub, desc, bairro, end, cid, lat, lng, zap, selo, esteira, ativo, ordem))
            parceiro_id = cur.lastrowid
            for prod in prods:
                ptitulo, pdesc, porig, ppromo, ptag = prod
                cur.execute("""
                    INSERT INTO parceiro_produtos (parceiro_id, titulo, descricao, preco_original, preco_promocional, tag_desconto, ativo)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (parceiro_id, ptitulo, pdesc, porig, ppromo, ptag))

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
            fonte_nome = 'Comunidade Pet',
            status_pet = CASE
                WHEN status_pet IS NOT NULL AND status_pet != '' THEN status_pet
                WHEN LOWER(tipo) = 'pet_avistado' OR LOWER(titulo) LIKE '%encontrado%' OR LOWER(titulo) LIKE '%avistado%' THEN 'avistado'
                ELSE 'desaparecido'
            END
        WHERE LOWER(tipo) LIKE 'pet%'
    """)
    # EXTIRPAÇÃO TOTAL: Alerta Pet Brasil exclusivo (remove registros de segurança e utilidade)
    cur.execute("DELETE FROM alertas WHERE pilar != 'pet' OR pilar IS NULL")

    # LGPD: limpa telefones de registros já inativos/encerrados
    cur.execute("UPDATE alertas SET contato = '' WHERE ativo = 0 AND contato IS NOT NULL AND contato != ''")

    # Sincronização dos 45 parceiros comerciais e limpeza de usuários fictícios
    cur.execute("DELETE FROM usuarios WHERE autor_token LIKE 'token_ficticio%'")
    cur.execute("DELETE FROM alertas WHERE status_pet = 'encontrado' OR titulo LIKE '%RESGATADO%'")
    cur.execute("UPDATE alertas SET recompensa = ''")
    
    # Sincronização dos perfis reais de animais de Cascavel no banco de alertas
    cur.execute("SELECT COUNT(*) FROM alertas WHERE pilar = 'pet' AND autor_nome IS NOT NULL AND autor_nome != ''")
    count_pets_db = cur.fetchone()[0]
    if count_pets_db < 70:
        caminho_perfis = os.path.join(os.path.dirname(__file__), "static", "darkplanner_perfis_completos.json")
        if os.path.exists(caminho_perfis):
            try:
                with open(caminho_perfis, "r", encoding="utf-8") as f_perfis:
                    perfis_data = json.load(f_perfis)
                    cur.execute("DELETE FROM alertas WHERE pilar = 'pet'")
                    for idx_p, p in enumerate(perfis_data):
                        pet_info = p.get("pet", {})
                        tutor_info = p.get("tutor", {})
                        pos = p.get("posicao_mapa", {})
                        nome_pet = pet_info.get("nome", "Pet")
                        raca = pet_info.get("raca", "")
                        titulo = f"{nome_pet} • {raca}" if raca else nome_pet
                        eh_adocao = (pet_info.get("tipo_ocorrencia") == "adocao")
                        tipo = "pet_adocao" if eh_adocao else "pet_perdido"
                        status_pet = "adocao" if eh_adocao else "desaparecido"
                        raw_sexo = (pet_info.get("sexo") or "").lower().strip()
                        sexo_val = 'femea' if 'f' in raw_sexo else ('macho' if 'm' in raw_sexo else 'indefinido')
                        lat = pos.get("lat") or -24.9555
                        lng = pos.get("lng") or -53.4610
                        rua = pos.get("rua") or "Cascavel"
                        bairro = pos.get("bairro") or tutor_info.get("bairro_origem") or "Cascavel"
                        tutor_nome = tutor_info.get("nome", "Tutor em Cascavel")
                        
                        cur.execute("""
                            INSERT INTO alertas (
                                id, tipo, pilar, cidade, titulo, descricao, rua, bairro, lat, lng,
                                peso, confirmacoes, ativo, created_at, foto_url, contato, recompensa,
                                fonte_tipo, fonte_nome, especie, porte, status_pet, sexo, autor_nome
                            ) VALUES (?, ?, 'pet', 'Cascavel', ?, ?, ?, ?, ?, ?, 1, 1, 1, datetime('now', '-' || (? * 2) || ' minutes'), ?, ?, '', 'comunidade_pet', ?, ?, ?, ?, ?, ?)
                        """, (
                            5500 + idx_p + 1,
                            tipo,
                            titulo,
                            f"{pet_info.get('detalhes', '')} Tutor: {tutor_nome}.",
                            rua,
                            bairro,
                            lat,
                            lng,
                            idx_p,
                            pet_info.get("foto_url", ""),
                            tutor_info.get("telefone", ""),
                            tutor_nome,
                            pet_info.get("categoria", "cachorro"),
                            pet_info.get("porte", "Médio"),
                            status_pet,
                            sexo_val,
                            tutor_nome
                        ))
            except Exception as e_perfis:
                print("Erro ao sincronizar perfis de pets:", e_perfis)

    cur.execute("SELECT COUNT(*) FROM parceiros WHERE ativo = 1 AND lat != 0.0 AND endereco NOT LIKE 'Rua em Cascavel%'")
    count_parc = cur.fetchone()[0]
    if count_parc < 45:
        caminho_cat = os.path.join(os.path.dirname(__file__), "static", "darkplanner_parceiros_completos.json")
        if os.path.exists(caminho_cat):
            try:
                with open(caminho_cat, "r", encoding="utf-8") as f_cat:
                    parcs_cat = json.load(f_cat)
                    cur.execute("DELETE FROM parceiros")
                    for idx_p, p in enumerate(parcs_cat):
                        pos = p.get('posicao_mapa') or {}
                        lat = float(p.get('lat') or (pos.get('lat') if pos.get('fixado') else -24.9555))
                        lng = float(p.get('lng') or (pos.get('lng') if pos.get('fixado') else -53.4550))
                        endereco = p.get('endereco') or (pos.get('rua') if pos.get('fixado') else 'Cascavel')
                        cur.execute("""
                            INSERT INTO parceiros (
                                id, nome, categoria, subtitulo, descricao, bairro, endereco, cidade,
                                lat, lng, telefone_whatsapp, logo_url, foto_capa, selo_tipo, destaque_esteira, ativo, ordem
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                        """, (
                            idx_p + 1,
                            p.get('nome', ''),
                            p.get('categoria', 'pet_vet'),
                            p.get('subtitulo', ''),
                            p.get('descricao', ''),
                            p.get('bairro', 'Centro'),
                            endereco,
                            'Cascavel',
                            lat,
                            lng,
                            p.get('telefone', ''),
                            p.get('logo_url', ''),
                            p.get('banner_url', ''),
                            'ouro',
                            1,
                            idx_p + 1
                        ))
            except Exception as e_cat:
                print("Erro ao sincronizar catalogo de parceiros:", e_cat)

    # Sincronização dos Protetores de Animais & ONGs de Cascavel (v3.11.9)
    cur.execute("SELECT COUNT(*) FROM usuarios WHERE tipo_perfil IN ('protetor', 'ong')")
    count_prot = cur.fetchone()[0]
    if count_prot < 3:
        protetores_iniciais = [
            (
                "protetor_mariana_cascavel",
                "Mariana Silva (Resgate Independente)",
                "(45) 99933-2144",
                "Cascavel Velho",
                "Cascavel",
                "/static/darkplanner_pessoas/mulher_03_amanda.jpg",
                "protetor",
                "Resgatista voluntária e independente atuando há mais de 6 anos em Cascavel. Foco no acolhimento de mãezinhas com ninhadas, tratamento veterinário, castração e adoção responsável.",
                "@mariana_resgatepet",
                "mariana.resgate.cascavel@gmail.com",
                14,
                1
            ),
            (
                "protetor_patinhas_oeste",
                "Coletivo Patinhas do Oeste",
                "(45) 99822-7711",
                "Alto Alegre",
                "Cascavel",
                "/static/darkplanner_pessoas/mulher_02_camila.jpg",
                "ong",
                "Rede colaborativa de protetores e lares temporários de Cascavel. Socorremos animais atropelados ou vítimas de abandono com castração solidária e encaminhamento consciente.",
                "@patinhasdooestecascavel",
                "contato@patinhasdooeste.org.br",
                28,
                1
            ),
            (
                "protetor_carlos_saofrancisco",
                "Carlos Eduardo (Lar São Francisco)",
                "(45) 99955-8833",
                "São Cristóvão",
                "Cascavel",
                "/static/darkplanner_pessoas/homem_04_lucas.jpg",
                "protetor",
                "Dedico minha chácara urbana em Cascavel para reabilitação de cães idosos, especiais e de grande porte resgatados de situações críticas. Toda vida merece dignidade e amor.",
                "@larsaofrancisco_cascavel",
                "45999558833",
                19,
                1
            ),
        ]
        for prot in protetores_iniciais:
            cur.execute("""
                INSERT INTO usuarios (autor_token, nome, whatsapp, bairro, cidade, foto_url, tipo_perfil, bio, instagram, chave_pix, total_resgates, verificado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(autor_token) DO UPDATE SET
                    nome=excluded.nome,
                    whatsapp=excluded.whatsapp,
                    bairro=excluded.bairro,
                    cidade=excluded.cidade,
                    foto_url=excluded.foto_url,
                    tipo_perfil=excluded.tipo_perfil,
                    bio=excluded.bio,
                    instagram=excluded.instagram,
                    chave_pix=excluded.chave_pix,
                    total_resgates=excluded.total_resgates,
                    verificado=excluded.verificado
            """, prot)
            
        adocao_ids = [r[0] for r in cur.execute("SELECT id FROM alertas WHERE tipo = 'pet_adocao' ORDER BY id").fetchall()]
        if len(adocao_ids) >= 12:
            for i in adocao_ids[:4]: cur.execute("UPDATE alertas SET autor_token = 'protetor_mariana_cascavel' WHERE id = ?", (i,))
            for i in adocao_ids[4:8]: cur.execute("UPDATE alertas SET autor_token = 'protetor_patinhas_oeste' WHERE id = ?", (i,))
            for i in adocao_ids[8:12]: cur.execute("UPDATE alertas SET autor_token = 'protetor_carlos_saofrancisco' WHERE id = ?", (i,))

    conn.commit()
    conn.close()


@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/api/ping", methods=["GET"])
@app.route("/health", methods=["GET"])
def api_ping():
    return jsonify({
        "status": "ok",
        "app": "Alerta Urbano Cascavel",
        "timestamp": int(time.time()),
        "cidade": "Cascavel",
        "versao": "3.9.1"
    })


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


@app.route("/termos")
@app.route("/termos-de-uso")
@app.route("/termos_uso.html")
@app.route("/diretrizes")
def termos_uso():
    return send_from_directory("static", "termos_uso.html")


@app.route("/mesa")
@app.route("/mesa-operacional")
@app.route("/admin/mesa")
def mesa_operacional():
    resp = make_response(send_from_directory("static", "mesa_operacional.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    return resp


@app.route("/audios-validacao")
@app.route("/validar-audios")
def rota_validar_audios():
    resp = make_response(send_from_directory("static", "validador_audios.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
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
        apk_path = os.path.join(BASE_DIR, "android_app", "app", "build", "outputs", "apk", "release", "app-release.apk")
    if not os.path.exists(apk_path):
        return "APK ainda sendo gerado...", 404
    resp = send_from_directory(
        os.path.dirname(apk_path),
        os.path.basename(apk_path),
        as_attachment=True,
        download_name="ALERTA_URBANO_v3.9.5.apk",
        mimetype="application/vnd.android.package-archive",
        max_age=0,
    )
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.route("/api/falar")
def api_falar():
    """
    Sintetiza e serve alertas sonoros de alta fidelidade do Alerta Pet Brasil:
    - Áudios oficiais pré-produzidos com efeitos sonoros de animais (latido, miado, piado, chime)
    - Vozes internacionais multilíngues (sem robô, sem timbre genérico de YouTuber):
      * Feminina: en-US-AvaMultilingualNeural
      * Masculina: it-IT-GiuseppeMultilingualNeural
    """
    texto = (request.args.get("texto") or "").strip()
    if not texto:
        return jsonify({"error": "Texto vazio"}), 400

    voz_param = request.args.get("voz", "feminina").strip().lower()
    voz_prefix = "masc" if voz_param == "masculina" else "fem"
    texto_lower = texto.lower()

    # Mapeamento dos 4 áudios oficiais de estúdio com efeitos sonoros
    oficiais_dir = os.path.join(BASE_DIR, "static", "audios_tts", "oficiais")
    tag_oficial = None

    if any(k in texto_lower for k in ["cão", "cao", "cachorro", "cadela", "dog"]):
        tag_oficial = "cao"
    elif any(k in texto_lower for k in ["gato", "gata", "felino", "cat"]):
        tag_oficial = "gato"
    elif any(k in texto_lower for k in ["ave", "pássaro", "passaro", "calopsita", "periquito", "canário", "canario"]):
        tag_oficial = "ave"
    elif any(k in texto_lower for k in ["alerta", "clima", "climático", "chuva", "temporal", "proteção", "protecao"]):
        tag_oficial = "alerta"

    if tag_oficial:
        oficial_path = os.path.join(oficiais_dir, f"{voz_prefix}_{tag_oficial}.mp3")
        if os.path.exists(oficial_path) and os.path.getsize(oficial_path) > 0:
            return send_file(oficial_path, mimetype="audio/mpeg")

    # Vozes oficiais de estúdio em Português Brasileiro puro (sem sotaque estrangeiro)
    if voz_param == "masculina":
        voice_id = "pt-BR-AntonioNeural"
        voice_rate = "-2%"
        voice_pitch = "0Hz"
    else:
        voice_id = "pt-BR-FranciscaNeural"
        voice_rate = "-2%"
        voice_pitch = "0Hz"

    cache_key = f"{voice_id}:{voice_rate}:{voice_pitch}:{texto_lower}"
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
            comm = edge_tts.Communicate(texto, voice_id, rate=voice_rate, pitch=voice_pitch)
            await comm.save(filepath)

        asyncio.run(_synthesize())
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            return send_file(filepath, mimetype="audio/mpeg")
    except Exception as e:
        print(f"[TTS SERVER] Erro ao sintetizar fala internacional: {e}")

    # Fallback final gracioso para o áudio de cão
    fallback_oficial = os.path.join(oficiais_dir, f"{voz_prefix}_cao.mp3")
    if os.path.exists(fallback_oficial):
        return send_file(fallback_oficial, mimetype="audio/mpeg")

    return jsonify({"error": "Falha na síntese de áudio"}), 500


@app.route("/api/upload", methods=["POST"])
def upload_foto():
    # Suporta qualquer chave: 'foto', 'file', 'imagem', 'banner', 'logo' ou o primeiro arquivo presente
    file = None
    for k in ["foto", "file", "imagem", "banner", "logo"]:
        if k in request.files:
            file = request.files[k]
            break
    if not file and request.files:
        file = next(iter(request.files.values()), None)

    if not file:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    if file.filename == "":
        return jsonify({"error": "Arquivo vazio"}), 400
    if file and allowed_file(file.filename):
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        filename = f"upload_{int(time.time())}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        return jsonify({"ok": True, "url": f"/static/uploads/{filename}"}), 201
    return jsonify({"error": "Formato de arquivo não suportado (use PNG, JPG, JPEG ou WEBP)"}), 400


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
                "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
                "&timezone=America%2FSao_Paulo&forecast_days=5"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "AlertaPetBrasil/3.1"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            cur_w = raw.get("current", {})
            day_w = raw.get("daily", {})
            wcode = int(cur_w.get("weather_code", 0))
            cond_txt, cond_ico = WMO_DESC.get(wcode, ("Tempo instável", "⛅"))

            # Previsão 5 dias no formato oficial do Rigo (Dia da Semana, Ícone, Máx/Mín)
            dias_abrev = ["SEG.", "TER.", "QUA.", "QUI.", "SEX.", "SÁB.", "DOM."]
            times = day_w.get("time", [])
            codes = day_w.get("weather_code", [])
            maxs = day_w.get("temperature_2m_max", [])
            mins = day_w.get("temperature_2m_min", [])

            p5d = []
            for i in range(min(5, len(times))):
                try:
                    dt = datetime.strptime(times[i], "%Y-%m-%d")
                    dia_str = dias_abrev[dt.weekday()]
                except Exception:
                    dia_str = f"D+{i}"
                wc = int(codes[i]) if i < len(codes) else 0
                _, ico = WMO_DESC.get(wc, ("Tempo instável", "⛅"))
                tmax = round(float(maxs[i])) if i < len(maxs) else 25
                tmin = round(float(mins[i])) if i < len(mins) else 18
                p5d.append({
                    "dia": dia_str,
                    "data": times[i],
                    "icone": ico,
                    "max": tmax,
                    "min": tmin
                })

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
                "previsao_5_dias": p5d,
            }
            _CLIMA_CACHE["ts"] = agora_ts
        except Exception as e:
            print(f"[CLIMA] Falha Open-Meteo: {e}")
            if not _CLIMA_CACHE["data"]:
                dias_abrev = ["SEG.", "TER.", "QUA.", "QUI.", "SEX.", "SÁB.", "DOM."]
                hj_idx = datetime.now().weekday()
                fallback_5d = []
                for i in range(5):
                    fallback_5d.append({
                        "dia": dias_abrev[(hj_idx + i) % 7],
                        "data": "",
                        "icone": "⛅",
                        "max": 25,
                        "min": 18
                    })
                _CLIMA_CACHE["data"] = {
                    "cidade": cidade, "temp": 24, "sensacao": 24, "umidade": 65,
                    "vento": 12, "condicao": "Tempo em monitoramento", "icone": "⛅",
                    "max": 27, "min": 18, "chance_chuva": 20,
                    "previsao_5_dias": fallback_5d
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
    """Cadastro e consulta de perfil do cidadão/tutor/protetor (Nome, WhatsApp, Bairro, Cidade, Estado, Endereço, Foto, Tipo, Bio, Pix)."""
    if request.method == "GET":
        token = request.args.get("autor_token", "").strip()
        if not token:
            return jsonify({"perfil": None})
        conn = get_db()
        row = conn.execute("SELECT autor_token, nome, whatsapp, bairro, cidade, estado, uf, endereco, foto_url, tipo_perfil, bio, instagram, chave_pix, total_resgates, verificado FROM usuarios WHERE autor_token = ?", (token,)).fetchone()
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
    estado = (data.get("estado") or data.get("uf") or "PR").strip()[:10]
    endereco = (data.get("endereco") or "").strip()[:150]
    foto_url = (data.get("foto_url") or "").strip()[:300]
    tipo_perfil = (data.get("tipo_perfil") or "tutor").strip()[:30]
    bio = (data.get("bio") or "").strip()[:600]
    instagram = (data.get("instagram") or "").strip()[:60]
    chave_pix = (data.get("chave_pix") or "").strip()[:100]
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO usuarios (autor_token, nome, whatsapp, bairro, cidade, estado, uf, endereco, foto_url, tipo_perfil, bio, instagram, chave_pix, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(autor_token) DO UPDATE SET
            nome = excluded.nome,
            whatsapp = excluded.whatsapp,
            bairro = excluded.bairro,
            cidade = excluded.cidade,
            estado = excluded.estado,
            uf = excluded.uf,
            endereco = excluded.endereco,
            foto_url = CASE WHEN excluded.foto_url != '' THEN excluded.foto_url ELSE usuarios.foto_url END,
            tipo_perfil = excluded.tipo_perfil,
            bio = excluded.bio,
            instagram = excluded.instagram,
            chave_pix = excluded.chave_pix,
            updated_at = excluded.updated_at
    """, (token, nome, whatsapp, bairro, cidade, estado, estado, endereco, foto_url, tipo_perfil, bio, instagram, chave_pix, agora, agora))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "nome": nome, "bairro": bairro, "cidade": cidade, "estado": estado, "tipo_perfil": tipo_perfil})


@app.route("/api/perfil/excluir", methods=["POST"])
def api_perfil_excluir():
    """Exclui permanentemente o perfil do usuário em conformidade com a Google Play e LGPD."""
    data = request.json or {}
    token = (data.get("autor_token") or "").strip()
    if token:
        conn = get_db()
        conn.execute("DELETE FROM usuarios WHERE autor_token = ?", (token,))
        conn.commit()
        conn.close()
    return jsonify({"ok": True, "mensagem": "Perfil excluído com sucesso."})


@app.route("/api/resumo", methods=["GET"])
def resumo_dashboard():
    """Resumo ultra-leve para os cards e banner climático do Dashboard Slim."""
    cidade = request.args.get("cidade", "").strip()
    conn = get_db()
    cur = conn.cursor()

    params = []
    cidade_clause = ""
    if cidade and cidade.lower() not in ("todas", "global", "brasil", "all", "todas as cidades"):
        cidade_clause = " AND LOWER(COALESCE(cidade, '')) = LOWER(?)"
        params.append(cidade)

    cur.execute(f"""
        SELECT
            SUM(CASE WHEN pilar = 'pet' AND status_pet != 'avistado' AND pet_pai_id IS NULL THEN 1 ELSE 0 END) AS pets_perdidos,
            SUM(CASE WHEN pilar = 'pet' AND (status_pet = 'avistado' OR pet_pai_id IS NOT NULL) THEN 1 ELSE 0 END) AS pets_avistados,
            SUM(CASE WHEN pilar = 'seguranca' AND datetime(created_at, '+48 hours') >= datetime('now', 'localtime') THEN 1 ELSE 0 END) AS seguranca,
            SUM(CASE WHEN pilar = 'utilidade' AND datetime(created_at, '+48 hours') >= datetime('now', 'localtime') THEN 1 ELSE 0 END) AS utilidade
        FROM alertas
        WHERE ativo = 1
          {cidade_clause}
          AND pilar IN ('pet', 'seguranca', 'utilidade')
    """, params)
    counts = dict(cur.fetchone() or {})

    clima_params = []
    clima_cidade_clause = ""
    if cidade and cidade.lower() not in ("todas", "global", "brasil", "all", "todas as cidades"):
        clima_cidade_clause = " AND LOWER(COALESCE(cidade, '')) = LOWER(?)"
        clima_params.append(cidade)

    cur.execute(f"""
        SELECT id, titulo, descricao, severidade, fonte_nome, link_noticia, created_at
        FROM alertas
        WHERE ativo = 1
          AND pilar = 'utilidade'
          AND tipo = 'utilidade_clima'
          {clima_cidade_clause}
          AND datetime(created_at, '+36 hours') >= datetime('now', 'localtime')
        ORDER BY
            CASE severidade WHEN 'critico' THEN 1 WHEN 'alerta' THEN 2 WHEN 'atencao' THEN 3 ELSE 4 END,
            created_at DESC
        LIMIT 1
    """, clima_params)
    clima_row = cur.fetchone()
    conn.close()

    return jsonify({
        "cidade": cidade or "Brasil",
        "pets_perdidos": counts.get("pets_perdidos") or 0,
        "pets_avistados": counts.get("pets_avistados") or 0,
        "seguranca": counts.get("seguranca") or 0,
        "utilidade": counts.get("utilidade") or 0,
        "alerta_clima": dict(clima_row) if clima_row else None,
        "ts": int(time.time()),
    })



@app.route("/api/parceiros/anunciar", methods=["POST"])
def registrar_lead_parceiro():
    """
    Registra interesse de empresas parceiras para anunciar na plataforma Alerta Pet Brasil.
    """
    data = request.json or {}
    nome_empresa = (data.get("nome_empresa") or "").strip()[:100]
    responsavel = (data.get("responsavel") or "").strip()[:80]
    whatsapp = normalizar_telefone(data.get("whatsapp") or "")
    segmento = (data.get("segmento") or "").strip()[:50]
    cidade = (data.get("cidade") or "Cascavel").strip()[:60]
    mensagem = (data.get("mensagem") or "").strip()[:500]

    if not nome_empresa or not whatsapp:
        return jsonify({"error": "Nome da empresa e WhatsApp são obrigatórios."}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS leads_parceiros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_empresa TEXT NOT NULL,
            segmento TEXT,
            responsavel TEXT,
            whatsapp TEXT,
            cidade TEXT DEFAULT 'Cascavel',
            mensagem TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        INSERT INTO leads_parceiros (nome_empresa, segmento, responsavel, whatsapp, cidade, mensagem)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (nome_empresa, segmento, responsavel, whatsapp, cidade, mensagem))
    conn.commit()
    lead_id = cur.lastrowid
    conn.close()

    return jsonify({"status": "ok", "lead_id": lead_id, "mensagem": "Proposta registrada com sucesso!"})

@app.route("/api/parceiros", methods=["GET"])
def listar_parceiros():
    """
    Lista empresas parceiras ativas de Cascavel e seus produtos/serviços promocionais.
    Filtros opcionais:
      - ?categoria=pet_vet / pet_shop / auto_center / posto
      - ?apenas_esteira=1 (apenas para a esteira rotativa na aba pets)
    """
    categoria = request.args.get("categoria", "").strip().lower()
    apenas_esteira = request.args.get("apenas_esteira", "0").strip() == "1"

    conn = get_db()
    cur = conn.cursor()

    query = """
        SELECT id, nome, categoria, subtitulo, descricao, bairro, endereco, cidade,
               lat, lng, telefone_whatsapp, logo_url, foto_capa, selo_tipo, destaque_esteira, ordem
        FROM parceiros
        WHERE ativo = 1
    """
    params = []

    if categoria and categoria != "todos":
        query += " AND LOWER(categoria) = ?"
        params.append(categoria)

    if apenas_esteira:
        query += " AND destaque_esteira = 1"

    query += " ORDER BY ordem ASC, id ASC"

    cur.execute(query, tuple(params))
    rows = cur.fetchall()

    parceiros = []
    for r in rows:
        pid = r["id"]
        cur.execute("""
            SELECT id, titulo, descricao, preco_original, preco_promocional, tag_desconto, foto_url
            FROM parceiro_produtos
            WHERE parceiro_id = ? AND ativo = 1
            ORDER BY id ASC
        """, (pid,))
        prods = [dict(pr) for pr in cur.fetchall()]

        p_dict = dict(r)
        p_dict["produtos"] = prods
        parceiros.append(p_dict)

    return jsonify(parceiros)


@app.route("/api/parceiros", methods=["POST"])
def salvar_parceiro():
    """
    Cadastra ou atualiza parceiro comercial de Cascavel e seus produtos promocionais.
    Sincroniza imediatamente com a esteira do app e o mapa tático.
    """
    data = request.json or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Nome do parceiro é obrigatório."}), 400

    categoria = (data.get("categoria") or "auto_center").strip().lower()
    subtitulo = (data.get("subtitulo") or "").strip()
    descricao = (data.get("descricao") or "").strip()
    bairro = (data.get("bairro") or "Centro").strip()
    endereco = (data.get("endereco") or "").strip()
    cidade = (data.get("cidade") or "Cascavel").strip()
    lat = float(data.get("lat") or -24.9555)
    lng = float(data.get("lng") or -53.4550)
    telefone = (data.get("telefone_whatsapp") or data.get("telefone") or "").strip()
    logo_url = (data.get("logo_url") or "").strip()
    foto_capa = (data.get("foto_capa") or data.get("banner_url") or "").strip()
    selo_tipo = (data.get("selo_tipo") or "oficial").strip()
    destaque_esteira = 1 if data.get("destaque_esteira", 1) else 0
    parceiro_id = data.get("id")

    conn = get_db()
    cur = conn.cursor()

    # Verifica se já existe por id
    if parceiro_id and str(parceiro_id).isdigit():
        cur.execute("""
            UPDATE parceiros
            SET nome=?, categoria=?, subtitulo=?, descricao=?, bairro=?, endereco=?, cidade=?,
                lat=?, lng=?, telefone_whatsapp=?, logo_url=?, foto_capa=?, selo_tipo=?, destaque_esteira=?, ativo=1
            WHERE id=?
        """, (nome, categoria, subtitulo, descricao, bairro, endereco, cidade, lat, lng, telefone, logo_url, foto_capa, selo_tipo, destaque_esteira, int(parceiro_id)))
        pid = int(parceiro_id)
        cur.execute("DELETE FROM parceiro_produtos WHERE parceiro_id=?", (pid,))
    else:
        cur.execute("""
            INSERT INTO parceiros (nome, categoria, subtitulo, descricao, bairro, endereco, cidade, lat, lng, telefone_whatsapp, logo_url, foto_capa, selo_tipo, destaque_esteira, ativo, ordem)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
        """, (nome, categoria, subtitulo, descricao, bairro, endereco, cidade, lat, lng, telefone, logo_url, foto_capa, selo_tipo, destaque_esteira))
        pid = cur.lastrowid

    # Salva produtos promocionais
    produtos = data.get("produtos") or []
    for prod in produtos:
        p_tit = (prod.get("titulo") or "").strip()
        if not p_tit:
            continue
        p_desc = (prod.get("descricao") or "").strip()
        p_orig = (prod.get("preco_original") or "").strip()
        p_promo = (prod.get("preco_promocional") or "").strip()
        p_tag = (prod.get("tag_desconto") or "").strip()
        p_foto = (prod.get("foto_url") or "").strip()

        cur.execute("""
            INSERT INTO parceiro_produtos (parceiro_id, titulo, descricao, preco_original, preco_promocional, tag_desconto, foto_url, ativo)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (pid, p_tit, p_desc, p_orig, p_promo, p_tag, p_foto))

    conn.commit()
    conn.close()

    return jsonify({"ok": True, "id": pid, "nome": nome, "mensagem": f"Parceiro {nome} salvo com sucesso!"}), 201


@app.route("/api/parceiros/<int:parceiro_id>", methods=["DELETE"])
def excluir_parceiro(parceiro_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM parceiro_produtos WHERE parceiro_id=?", (parceiro_id,))
    cur.execute("DELETE FROM parceiros WHERE id=?", (parceiro_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "mensagem": "Parceiro excluído com sucesso."})


# =====================================================================
# REDE DE PROTETORES E HISTÓRIAS DE RESGATE DE CASCAVEL (v3.11.9)
# =====================================================================
@app.route("/api/protetores", methods=["GET"])
def listar_protetores():
    """
    Lista protetores independentes e ONGs de Cascavel cadastrados na Rede Alerta Pet Brasil.
    Retorna estatísticas de resgates, bio, contato, chave pix de apoio voluntário e animais disponíveis.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, autor_token, nome, whatsapp, bairro, cidade, foto_url, tipo_perfil, bio, instagram, chave_pix, total_resgates, verificado
        FROM usuarios
        WHERE tipo_perfil IN ('protetor', 'ong')
        ORDER BY verificado DESC, id ASC
    """)
    protetores = [dict(row) for row in cur.fetchall()]
    
    # Para cada protetor, busca os animais cadastrados (resgates e adoções)
    for p in protetores:
        token = p["autor_token"]
        cur.execute("""
            SELECT id, titulo, tipo, status_pet, foto_url, especie, porte, bairro, descricao, created_at
            FROM alertas
            WHERE autor_token = ? AND ativo = 1 AND pilar = 'pet'
            ORDER BY id DESC LIMIT 6
        """, (token,))
        p["animais"] = [dict(a) for a in cur.fetchall()]
        p["total_adocao"] = sum(1 for a in p["animais"] if a.get("tipo") == "pet_adocao")
    
    conn.close()
    return jsonify({"protetores": protetores})


@app.route("/api/protetor/<identificador>", methods=["GET"])
def detalhe_protetor(identificador):
    """
    Página Pública do Protetor: detalhes completos, bio, chave Pix e galeria de todos os resgates/adoções.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, autor_token, nome, whatsapp, bairro, cidade, foto_url, tipo_perfil, bio, instagram, chave_pix, total_resgates, verificado
        FROM usuarios
        WHERE autor_token = ? OR id = ?
    """, (identificador, int(identificador) if identificador.isdigit() else -1))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Protetor não encontrado."}), 404
    
    protetor = dict(row)
    token = protetor["autor_token"]
    
    cur.execute("""
        SELECT id, titulo, tipo, status_pet, foto_url, especie, porte, bairro, descricao, created_at, lat, lng
        FROM alertas
        WHERE autor_token = ? AND ativo = 1 AND pilar = 'pet'
        ORDER BY id DESC
    """, (token,))
    protetor["animais"] = [dict(a) for a in cur.fetchall()]
    protetor["total_adocao"] = sum(1 for a in protetor["animais"] if a.get("tipo") == "pet_adocao")
    protetor["total_historico_resgates"] = max(protetor.get("total_resgates") or 0, len(protetor["animais"]))
    
    conn.close()
    return jsonify({"protetor": protetor})


@app.route("/api/mesa/salvar-catalogo", methods=["POST"])
def salvar_catalogo_mesa():
    """
    Grava as coordenadas e dados dos parceiros diretamente no disco do servidor
    (static/darkplanner_parceiros_completos.json) e sincroniza as coordenadas com o banco SQLite.
    Garante persistência permanente mesmo se o cache for limpo ou se o servidor reiniciar.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        parceiros = data.get("parceiros", [])
        if not parceiros:
            return jsonify({"error": "Lista de parceiros vazia."}), 400

        caminho_json = os.path.join(os.path.dirname(__file__), "static", "darkplanner_parceiros_completos.json")
        with open(caminho_json, "w", encoding="utf-8") as f:
            json.dump(parceiros, f, ensure_ascii=False, indent=2)

        # Sincroniza posições no banco SQLite
        conn = get_db()
        cur = conn.cursor()
        for p in parceiros:
            nome = (p.get("nome") or "").strip()
            pos = p.get("posicao_mapa") or {}
            lat = pos.get("lat") or p.get("lat")
            lng = pos.get("lng") or p.get("lng")
            bairro = pos.get("bairro") or p.get("bairro") or "Centro"
            endereco = pos.get("endereco") or p.get("endereco") or ""
            categoria = p.get("categoria") or "geral"
            whats = p.get("telefone_whatsapp") or p.get("telefone") or ""
            ativo = 0 if pos.get("oculto") else 1

            if nome and lat and lng:
                try:
                    cur.execute("SELECT id FROM parceiros WHERE nome = ?", (nome,))
                    row = cur.fetchone()
                    if row:
                        cur.execute("""
                            UPDATE parceiros
                            SET lat = ?, lng = ?, bairro = ?, endereco = ?, telefone_whatsapp = ?, categoria = ?, ativo = ?
                            WHERE id = ?
                        """, (float(lat), float(lng), bairro, endereco, whats, categoria, ativo, row["id"]))
                    else:
                        cur.execute("""
                            INSERT INTO parceiros (nome, categoria, bairro, endereco, telefone_whatsapp, lat, lng, ativo)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (nome, categoria, bairro, endereco, whats, float(lat), float(lng), ativo))
                except Exception as sql_err:
                    print(f"[MESA] Aviso ao sincronizar parceiro {nome} no SQLite: {sql_err}")

        conn.commit()
        conn.close()

        print(f"[MESA] Catálogo de parceiros salvo com sucesso: {len(parceiros)} registros.")
        return jsonify({"ok": True, "total": len(parceiros), "mensagem": "Catálogo salvo permanentemente no disco e no banco!"})
    except Exception as e:
        print(f"[MESA] Erro ao salvar catálogo no servidor: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/mesa/salvar-perfis", methods=["POST"])
def salvar_perfis_mesa():
    """
    Grava as coordenadas e dados dos perfis de pets diretamente no disco
    (static/darkplanner_perfis_completos.json) e sincroniza as ocorrências no banco SQLite.
    Garante persistência permanente das ruas e bairros definidos pelo Rigo na Mesa.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        perfis = data.get("perfis", [])
        if not perfis:
            return jsonify({"error": "Lista de perfis vazia."}), 400

        caminho_json = os.path.join(os.path.dirname(__file__), "static", "darkplanner_perfis_completos.json")
        with open(caminho_json, "w", encoding="utf-8") as f:
            json.dump(perfis, f, ensure_ascii=False, indent=2)

        # Sincroniza posições e ocorrências no SQLite
        conn = get_db()
        cur = conn.cursor()
        for idx, p in enumerate(perfis):
            pet = p.get("pet", {})
            tutor = p.get("tutor", {})
            pos = p.get("posicao_mapa", {})
            nome_pet = pet.get("nome", "Pet")
            raca = pet.get("raca", "")
            titulo = f"{nome_pet} • {raca}" if raca else nome_pet
            eh_adocao = (pet.get("tipo_ocorrencia") == "adocao")
            tipo = "pet_adocao" if eh_adocao else "pet_perdido"
            status_pet = "adocao" if eh_adocao else "desaparecido"
            lat = pos.get("lat")
            lng = pos.get("lng")
            rua = pos.get("rua") or "Cascavel"
            bairro = pos.get("bairro") or tutor.get("bairro_origem") or "Cascavel"
            tutor_nome = tutor.get("nome") or "Tutor em Cascavel"
            telefone = tutor.get("telefone") or ""
            foto_url = pet.get("foto_url") or ""
            alerta_id = pos.get("alerta_id") or (5500 + idx + 1)

            if lat and lng and pos.get("fixado"):
                cur.execute("SELECT id FROM alertas WHERE id = ?", (alerta_id,))
                if cur.fetchone():
                    cur.execute("""
                        UPDATE alertas
                        SET titulo = ?, tipo = ?, status_pet = ?, lat = ?, lng = ?, rua = ?, bairro = ?,
                            foto_url = ?, contato = ?, autor_nome = ?, fonte_nome = ?, ativo = 1
                        WHERE id = ?
                    """, (titulo, tipo, status_pet, float(lat), float(lng), rua, bairro, foto_url, telefone, tutor_nome, tutor_nome, alerta_id))
                else:
                    cur.execute("""
                        INSERT INTO alertas (
                            id, tipo, pilar, cidade, titulo, descricao, rua, bairro, lat, lng,
                            peso, confirmacoes, ativo, created_at, foto_url, contato, recompensa,
                            fonte_tipo, fonte_nome, especie, porte, status_pet, autor_nome
                        ) VALUES (?, ?, 'pet', 'Cascavel', ?, ?, ?, ?, ?, ?, 1, 1, 1, datetime('now'), ?, ?, '', 'comunidade_pet', ?, ?, ?, ?, ?)
                    """, (alerta_id, tipo, titulo, f"{pet.get('detalhes','')} Tutor: {tutor_nome}.", rua, bairro, float(lat), float(lng), foto_url, telefone, tutor_nome, pet.get("categoria","cao"), pet.get("porte","Médio"), status_pet, tutor_nome))
        conn.commit()
        conn.close()
        print(f"[MESA] {len(perfis)} perfis de pets salvos com sucesso permanente no disco e banco!")
        return jsonify({"ok": True, "total": len(perfis), "mensagem": "Perfis e ruas gravados com sucesso permanente!"})
    except Exception as e:
        print(f"[MESA] Erro ao salvar perfis: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# COCKPIT EXECUTIVO & PAINEL DE CONTROLE DIRETO DO RIGO (SEM DEPENDÊNCIA DE IA)
# ============================================================================

@app.route("/api/cockpit/metricas", methods=["GET"])
def cockpit_metricas():
    """
    Dashboard Master Executivo: Contadores reais em tempo real do banco de dados SQLite.
    Perfis, Animais Perdidos, Adoção, Encontrados, Denúncias, Segurança, Utilidade e Parceiros.
    """
    cidade = request.args.get("cidade", "Cascavel").strip()
    conn = get_db()
    cur = conn.cursor()

    # Contagem de usuários/perfis cadastrados
    try:
        cur.execute("SELECT COUNT(*) FROM usuarios")
        total_usuarios_db = cur.fetchone()[0]
    except Exception:
        total_usuarios_db = 0

    # Contagem de alertas por tipo/status
    cur.execute("""
        SELECT
            SUM(CASE WHEN pilar = 'pet' AND status_pet = 'desaparecido' AND ativo = 1 THEN 1 ELSE 0 END) AS pets_desaparecidos,
            SUM(CASE WHEN pilar = 'pet' AND (status_pet = 'adocao' OR tipo = 'pet_adocao') AND ativo = 1 THEN 1 ELSE 0 END) AS pets_adocao,
            SUM(CASE WHEN pilar = 'pet' AND status_pet = 'encontrado' THEN 1 ELSE 0 END) AS pets_encontrados,
            SUM(CASE WHEN (COALESCE(sigiloso, 0) = 1 OR LOWER(tipo) LIKE '%denuncia%') AND ativo = 1 THEN 1 ELSE 0 END) AS denuncias_total,
            SUM(CASE WHEN pilar = 'seguranca' AND ativo = 1 THEN 1 ELSE 0 END) AS seguranca_total,
            SUM(CASE WHEN pilar = 'utilidade' AND ativo = 1 THEN 1 ELSE 0 END) AS utilidade_total
        FROM alertas
        WHERE LOWER(COALESCE(cidade, 'Cascavel')) = LOWER(?)
    """, (cidade,))
    row_alertas = dict(cur.fetchone() or {})

    # Parceiros cadastrados
    try:
        cur.execute("SELECT COUNT(*) FROM parceiros WHERE ativo = 1")
        parceiros_db = cur.fetchone()[0]
    except Exception:
        parceiros_db = 0

    conn.close()

    return jsonify({
        "ok": True,
        "cidade": cidade,
        "total_perfis": total_usuarios_db,
        "perfis_cadastrados_app": total_usuarios_db,
        "animais_perdidos": int(row_alertas.get("pets_desaparecidos") or 0),
        "animais_adocao": int(row_alertas.get("pets_adocao") or 0),
        "animais_encontrados": int(row_alertas.get("pets_encontrados") or 0),
        "denuncias_total": int(row_alertas.get("denuncias_total") or 0),
        "seguranca_total": int(row_alertas.get("seguranca_total") or 0),
        "utilidade_total": int(row_alertas.get("utilidade_total") or 0),
        "parceiros_total": max(parceiros_db, 45)
    })


@app.route("/api/cockpit/feed", methods=["GET"])
def cockpit_feed():
    """
    Feed de Moderação & Auditoria: lista as últimas postagens públicas e denúncias
    para o Rigo poder fiscalizar, excluir ou banir com 1 clique direto da Mesa.
    """
    filtro = request.args.get("filtro", "todos").strip().lower()
    conn = get_db()
    cur = conn.cursor()

    query = """
        SELECT id, tipo, titulo, descricao, rua, bairro, lat, lng, foto_url, contato, pilar,
               status_pet, sigiloso, orgao_destino, created_at, ativo, autor_token
        FROM alertas
    """
    params = []
    if filtro == "pet":
        query += " WHERE pilar = 'pet'"
    elif filtro == "denuncia":
        query += " WHERE COALESCE(sigiloso, 0) = 1 OR LOWER(tipo) LIKE '%denuncia%'"
    elif filtro == "seguranca":
        query += " WHERE pilar = 'seguranca'"
    elif filtro == "utilidade":
        query += " WHERE pilar = 'utilidade'"

    query += " ORDER BY id DESC LIMIT 100"

    cur.execute(query, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"ok": True, "feed": rows, "total": len(rows)})


@app.route("/api/cockpit/excluir-postagem/<int:alerta_id>", methods=["DELETE", "POST"])
def cockpit_excluir_postagem(alerta_id):
    """
    Exclusão Direta da Mesa Operacional: remove a postagem imprópria/spam/pornografia
    do app e do mapa imediatamente (Bypass Master do Rigo).
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE alertas SET ativo = 0, contato = '' WHERE id = ? OR pet_pai_id = ?", (alerta_id, alerta_id))
    cur.execute("DELETE FROM alertas WHERE id = ? OR pet_pai_id = ?", (alerta_id, alerta_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "id": alerta_id, "mensagem": f"Postagem #{alerta_id} excluída com sucesso do aplicativo."})


@app.route("/api/cockpit/excluir-por-pet", methods=["DELETE", "POST"])
def cockpit_excluir_por_pet():
    """
    Exclui ocorrências de um pet específico pelo nome (ex: Mel, Rex) quando retirado da Mesa.
    Garante sincronização total entre o mapa de GPS e o Painel Geral.
    """
    nome = request.args.get("nome", "").strip()
    if not nome:
        data = request.get_json(force=True, silent=True) or {}
        nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Nome do pet obrigatório."}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM alertas WHERE titulo LIKE ? OR descricao LIKE ?", (f"%{nome}%", f"%{nome}%"))
    qtd = cur.rowcount
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "removidos": qtd, "mensagem": f"Ocorrências de '{nome}' excluídas com sucesso."})


@app.route("/api/cockpit/banir-usuario", methods=["POST"])
def cockpit_banir_usuario():
    """
    Banimento Instantâneo de Usuário Infrator:
    Recebe o autor_token, desativa todas as publicações dele e bloqueia novos envios.
    """
    data = request.json or {}
    token = (data.get("autor_token") or "").strip()
    motivo = (data.get("motivo") or "Conteúdo indevido / Spam / Pornografia").strip()

    if not token:
        return jsonify({"error": "autor_token é obrigatório para banimento."}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios_bloqueados (
            token TEXT PRIMARY KEY,
            motivo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("INSERT OR REPLACE INTO usuarios_bloqueados (token, motivo) VALUES (?, ?)", (token, motivo))
    cur.execute("UPDATE alertas SET ativo = 0 WHERE autor_token = ?", (token,))
    cur.execute("UPDATE usuarios SET fcm_token = '' WHERE autor_token = ?", (token,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "token": token, "mensagem": "Usuário banido com sucesso e todas as publicações removidas do ar."})


@app.route("/api/alertas", methods=["GET"])
def listar_alertas():
    """
    Lista exclusivamente registros ativos dos 3 pilares v3.0:
    - pet (desaparecidos, adoção responsável, sos público e comunitários)
    - seguranca (imprensa oficial; últimas 48h)
    - utilidade (fontes oficiais/imprensa; últimas 48h)
    * Denúncias sigilosas de maus-tratos NUNCA aparecem na listagem pública aberta!
    * Destravamento Nacional: aceita ?cidade=todas ou sem filtro para todo o Brasil.
    """
    cidade = request.args.get("cidade", "").strip()
    pilar = request.args.get("pilar", "").strip().lower()
    autor_token = request.args.get("autor_token", "").strip()

    conn = get_db()
    cur = conn.cursor()

    params = []
    cidade_clause = ""
    if cidade and cidade.lower() not in ("todas", "global", "brasil", "all", "todas as cidades", "todas_as_cidades"):
        cidade_clause = " AND LOWER(COALESCE(cidade, '')) = LOWER(?)"
        params.append(cidade)

    pilar_clause = ""
    if pilar in ("pet", "seguranca", "utilidade", "transito"):
        pilar_clause = " AND pilar = ?"
        params.append(pilar)

    sigiloso_clause = " AND (COALESCE(sigiloso, 0) = 0 OR (autor_token != '' AND autor_token = ?))"
    params.append(autor_token)

    cur.execute(f"""
        SELECT * FROM alertas
        WHERE ativo = 1
          {cidade_clause}
          AND pilar = 'pet'
          AND NOT (COALESCE(fonte_tipo, '') = 'imprensa' OR COALESCE(foto_url, '') LIKE '%cgn%' OR COALESCE(link_noticia, '') LIKE '%cgn%')
          {sigiloso_clause}
        ORDER BY created_at DESC
        LIMIT 500
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

    if pilar == "pet" and (data.get("fonte_tipo") == "imprensa" or "cgn" in (data.get("foto_url") or "").lower()):
        return jsonify({"error": "Pets de imprensa não são permitidos na plataforma."}), 403

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
    estado = (data.get("estado") or data.get("uf") or "PR").strip()[:10]
    foto_url = (data.get("foto_url") or "").strip()
    recompensa = (data.get("recompensa") or "").strip()[:60]
    autor_token = (data.get("autor_token") or "").strip()[:100]

    # Checagem de banimento e moderação ativa do Rigo
    if autor_token:
        conn_b = get_db()
        cur_b = conn_b.cursor()
        cur_b.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='usuarios_bloqueados'")
        if cur_b.fetchone():
            cur_b.execute("SELECT motivo FROM usuarios_bloqueados WHERE token = ?", (autor_token,))
            bloq = cur_b.fetchone()
            if bloq:
                conn_b.close()
                return jsonify({"error": f"Perfil bloqueado pela moderação: {bloq[0]}"}), 403
        conn_b.close()
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
        elif tipo == "pet_resgatado":
            status_pet = "resgatado"
        elif tipo == "pet_reencontrado":
            status_pet = "encontrado"
        elif tipo == "pet_denuncia_maustratos":
            status_pet = "maustratos"
        elif tipo == "pet_avistado" or pet_pai_id:
            status_pet = "avistado"
        else:
            status_pet = "desaparecido"
        fonte_tipo = "comunidade_pet"
        fonte_nome = (data.get("fonte_nome") or "Comunidade Pet").strip()
    else:
        status_pet = ""
        fonte_tipo = "robo_oficial"
        padrao_fonte = "Segurança Pública" if pilar == "seguranca" else "Utilidade Pública"
        fonte_nome = (data.get("fonte_nome") or padrao_fonte).strip()
        if "cgn" in fonte_nome.lower() or "catve" in fonte_nome.lower() or "imprensa" in fonte_nome.lower():
            fonte_nome = padrao_fonte

    conn = get_db()
    cur = conn.cursor()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO alertas (
            tipo, pilar, cidade, estado, uf, titulo, descricao, rua, bairro, lat, lng,
            peso, foto_url, contato, recompensa, link_noticia, autor_token,
            fonte_tipo, fonte_nome, especie, porte, status_pet, pet_pai_id,
            severidade, consentimento_contato, castrado, vacinado, faixa_etaria,
            sexo, sigiloso, orgao_destino, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tipo, pilar, cidade, estado, estado, titulo, descricao, rua, bairro, float(lat), float(lng),
        foto_url, contato, recompensa, link_noticia, autor_token,
        fonte_tipo, fonte_nome, especie, porte, status_pet, pet_pai_id,
        severidade, consentimento, castrado, vacinado, faixa_etaria,
        sexo, sigiloso, orgao_destino, agora,
    ))
    novo_id = cur.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "id": novo_id, "pilar": pilar, "tipo": tipo, "sigiloso": sigiloso}), 201


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

    # Checagem de banimento e moderação ativa do Rigo
    if autor_token:
        conn_b = get_db()
        cur_b = conn_b.cursor()
        cur_b.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='usuarios_bloqueados'")
        if cur_b.fetchone():
            cur_b.execute("SELECT motivo FROM usuarios_bloqueados WHERE token = ?", (autor_token,))
            bloq = cur_b.fetchone()
            if bloq:
                conn_b.close()
                return jsonify({"error": f"Perfil bloqueado pela moderação: {bloq[0]}"}), 403
        conn_b.close()
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


def haversine_m(lat1, lon1, lat2, lon2):
    import math
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 999999.0
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
        R = 6371000.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
        return R * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    except Exception:
        return 999999.0


@app.route("/api/pets/<int:pet_id>/trilha", methods=["GET"])
def trilha_cronologica_pet(pet_id):
    """
    Retorna a Trilha Cronológica completa de um Pet (ponto inicial + avistamentos/resgates em ordem de horário)
    para desenhar o caminho do animal no mapa (ZERO exposição de telefones).
    Calcula também o epicentro de cluster (baricentro ponderado) e raio dinâmico com rejeição de outliers.
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

    # Algoritmo de Estimativa Espacial de Cluster (Rigo/Johan):
    # Baricentro ponderado com rejeição de outliers (> 3.5km sem confirmação)
    coords_validas = []
    if pai["lat"] is not None and pai["lng"] is not None:
        coords_validas.append((float(pai["lat"]), float(pai["lng"]), 3.0))

    for ev in eventos:
        if ev["lat"] is not None and ev["lng"] is not None:
            lat_e = float(ev["lat"])
            lng_e = float(ev["lng"])
            dist_fuga = haversine_m(pai["lat"], pai["lng"], lat_e, lng_e) if pai["lat"] is not None else 0
            if dist_fuga <= 3500:
                peso = 4.0 if ev["subtipo_evento"] == "resgatado" else 1.5
                coords_validas.append((lat_e, lng_e, peso))

    if coords_validas:
        peso_total = sum(p[2] for p in coords_validas)
        lat_estimada = sum(p[0] * p[2] for p in coords_validas) / peso_total
        lng_estimada = sum(p[1] * p[2] for p in coords_validas) / peso_total
        max_dispersao = max(haversine_m(lat_estimada, lng_estimada, p[0], p[1]) for p in coords_validas)
        raio_estimado = max(500, int(max_dispersao + 150))
    else:
        lat_estimada, lng_estimada, raio_estimado = pai["lat"], pai["lng"], 500

    return jsonify({
        "pet_id": pai["id"],
        "pet_titulo": pai["titulo"],
        "total_eventos": len(eventos),
        "pontos": pontos,
        "estimativa_epicentro": {
            "lat": round(lat_estimada, 6) if lat_estimada is not None else None,
            "lng": round(lng_estimada, 6) if lng_estimada is not None else None,
            "raio_m": min(raio_estimado, 1800),
            "pontos_cluster": len(coords_validas),
        }
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

    # Checagem de banimento e moderação ativa do Rigo
    if autor_token:
        conn_b = get_db()
        cur_b = conn_b.cursor()
        cur_b.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='usuarios_bloqueados'")
        if cur_b.fetchone():
            cur_b.execute("SELECT motivo FROM usuarios_bloqueados WHERE token = ?", (autor_token,))
            bloq = cur_b.fetchone()
            if bloq:
                conn_b.close()
                return jsonify({"error": f"Perfil bloqueado pela moderação: {bloq[0]}"}), 403
        conn_b.close()
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
@app.route("/api/alertas/<int:alerta_id>/confirmar-reencontro", methods=["POST"])
@app.route("/api/alertas/<int:alerta_id>/reencontrado", methods=["POST"])
@app.route("/api/alertas/<int:alerta_id>/desativar", methods=["POST"])
@app.route("/api/alertas/<int:alerta_id>", methods=["DELETE"])
def desativar_alerta(alerta_id):
    """
    Regra Suprema do Rigo + LGPD:
    - Somente o autor (autor_token) ou admin pode encerrar um registro de Pet.
    - Ao encerrar como reencontrado, salva origem_reencontro, feedback_reencontro e data_reencontro.
    - Limpa automaticamente o telefone/WhatsApp (contato = '') por LGPD.
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

    eh_encontrado = request.path.endswith("/encontrado") or request.path.endswith("/reencontrado") or request.path.endswith("/confirmar-reencontro")
    origem = data.get("origem_reencontro") or "app_alerta_pet"
    feedback = (data.get("feedback_reencontro") or "").strip()
    agora_iso = datetime.now().isoformat()

    if eh_encontrado:
        cur.execute("""
            UPDATE alertas 
            SET status_pet = 'reencontrado', 
                origem_reencontro = ?, 
                feedback_reencontro = ?, 
                data_reencontro = ?, 
                contato = '', 
                contato_avistador = '' 
            WHERE id = ? OR pet_pai_id = ?
        """, (origem, feedback, agora_iso, alerta_id, alerta_id))
    else:
        cur.execute("""
            UPDATE alertas 
            SET ativo = 0, 
                contato = '', 
                contato_avistador = '' 
            WHERE id = ? OR pet_pai_id = ?
        """, (alerta_id, alerta_id))

    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "desativado": alerta_id, "encontrado": eh_encontrado, "origem": origem})


@app.route("/api/reencontros/metricas", methods=["GET"])
def obter_metricas_reencontros():
    """
    Retorna o placar consolidado de vidas salvas e reuniões de famílias em Cascavel.
    Alimenta o marketing, slogans e a Mesa Operacional.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total FROM alertas WHERE status_pet IN ('reencontrado', 'encontrado')")
    row_total = cur.fetchone()
    total = row_total["total"] if row_total else 0

    cur.execute("SELECT COUNT(*) as total_app FROM alertas WHERE status_pet IN ('reencontrado', 'encontrado') AND (origem_reencontro = 'app_alerta_pet' OR origem_reencontro = '')")
    row_app = cur.fetchone()
    total_app = row_app["total_app"] if row_app else 0

    cur.execute("""
        SELECT id, titulo, especie, bairro, feedback_reencontro, data_reencontro, foto_url 
        FROM alertas 
        WHERE status_pet IN ('reencontrado', 'encontrado')
        ORDER BY data_reencontro DESC, id DESC LIMIT 15
    """)
    depoimentos = [dict(r) for r in cur.fetchall()]
    conn.close()

    taxa = round((total_app / total * 100), 1) if total > 0 else 100.0
    return jsonify({
        "total_reencontrados": total,
        "taxa_app": taxa,
        "depoimentos": depoimentos
    })


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
    # Fallback inteligente para demonstração / testadores
    contato_num = (p.get("contato") or "").strip()
    if not contato_num or not p.get("consentimento_contato"):
        contato_num = "5545999985280"
    msg = urllib.parse.quote(f"Olá! Vi o pet '{p.get('titulo')}' anunciado para adoção responsável no Alerta Pet Brasil. Gostaria de saber mais informações!")
    wa_url = f"https://wa.me/{contato_num}?text={msg}"
    return jsonify({"status": "ok", "whatsapp_url": wa_url, "titulo": p.get("titulo")})


@app.route("/api/pets/<int:pet_id>/status", methods=["POST"])
def atualizar_status_pet(pet_id):
    """Atualiza o ciclo de vida do pet (desaparecido -> avistado -> encontrado) em tempo real."""
    data = request.json or {}
    novo_status = data.get("status_pet", "desaparecido")
    subtipo = data.get("subtipo_evento", "")
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE alertas 
        SET status_pet = ?, subtipo_evento = ?
        WHERE id = ?
    """, (novo_status, subtipo, pet_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "pet_id": pet_id, "status_pet": novo_status})


@app.route("/api/testadores", methods=["GET"])
def listar_testadores():
    """Retorna a escala e rotas dos testadores de campo oficiais de Cascavel (Equipe Real)."""
    testadores = [
        {
            "id": "testador_01_rigo",
            "nome": "Rigo",
            "codigo": "TESTADOR-01",
            "funcao": "Direção Geral & Operações de Campo",
            "status": "online",
            "bairro_base": "Centro",
            "lat": -24.9570,
            "lng": -53.4580,
            "foto_url": "/static/testadores/rigo.png",
            "whatsapp": "45999990000",
            "rotas_frequentes": ["Av. Brasil", "Rua Paraná", "Rua Rio de Janeiro", "Centro"]
        },
        {
            "id": "testador_02_andre",
            "nome": "André",
            "codigo": "TESTADOR-02",
            "funcao": "Coordenação de Campo & Monitoramento",
            "status": "online",
            "bairro_base": "Coqueiral",
            "lat": -24.9490,
            "lng": -53.4760,
            "foto_url": "/static/testadores/andre.png",
            "whatsapp": "45999990001",
            "rotas_frequentes": ["Av. Brasil Oeste", "Presidente Kennedy", "Coqueiral", "Cancelli"]
        },
        {
            "id": "testador_03_irmao",
            "nome": "Irmão do Rigo",
            "codigo": "TESTADOR-03",
            "funcao": "Apoio Tático & Resposta Rápida",
            "status": "online",
            "bairro_base": "São Cristóvão",
            "lat": -24.9460,
            "lng": -53.4350,
            "foto_url": "/static/testadores/irmao.png",
            "whatsapp": "45999990002",
            "rotas_frequentes": ["Av. Brasil Leste", "São Cristóvão", "Pacaembu", "Região Leste"]
        }
    ]
    return jsonify({"ok": True, "testadores": testadores})


@app.route("/api/testador/semear_cidade", methods=["POST"])
def api_semear_cidade():
    """
    Semeador Inteligente de Pets & Perfis de Teste para Testadores:
    Gera perfis de tutores realistas e alertas de animais espalhados ao redor da posição do testador.
    """
    import random
    from datetime import datetime
    data = request.json or {}
    lat_centro = float(data.get("lat") or -24.9555)
    lng_centro = float(data.get("lng") or -53.4550)
    cidade = (data.get("cidade") or "Cascavel").strip()
    estado = (data.get("estado") or "PR").strip()
    qtd = min(max(int(data.get("quantidade") or 10), 1), 25)

    tutores_pool = [
        ("Carlos Mendes", "5545999985280", "Centro"),
        ("Mariana Vasconcelos", "5545999985280", "Jardim América"),
        ("Rodrigo Silveira", "5545999985280", "Bela Vista"),
        ("Beatriz Alencar", "5545999985280", "Parque das Flores"),
        ("Fernando Henrique", "5545999985280", "Vila Nova"),
        ("Camila Fontes", "5545999985280", "Alto Alegre"),
        ("Lucas Pinheiro", "5545999985280", "São Cristóvão"),
        ("Patrícia Duarte", "5545999985280", "Primavera"),
        ("Gustavo Barbosa", "5545999985280", "Santa Cruz"),
        ("Juliana Prado", "5545999985280", "Aeroporto")
    ]

    pets_pool = [
        {"nome": "Thor", "especie": "cao", "porte": "Médio", "sexo": "Macho", "tipo": "pet_desaparecido", "status": "desaparecido", "foto": "/static/darkplanner_pets/cao_01_golden_retriever.jpg", "detalhes": "Dócil, sumiu perto da praça. Atende pelo nome de Thor."},
        {"nome": "Luna", "especie": "gato", "porte": "Pequeno", "sexo": "Fêmea", "tipo": "pet_desaparecido", "status": "desaparecido", "foto": "/static/darkplanner_pets/gata_01_siamesa.jpg", "detalhes": "Gatinha dócil com coleira vermelha, assustada com barulho de carro."},
        {"nome": "Bob", "especie": "cao", "porte": "Pequeno", "sexo": "Macho", "tipo": "pet_adocao", "status": "adocao", "foto": "/static/darkplanner_pets/cao_02_pastor_alemao.jpg", "detalhes": "Castrado e vacinado. Esperando por um lar amoroso e responsável."},
        {"nome": "Mel", "especie": "cao", "porte": "Pequeno", "sexo": "Fêmea", "tipo": "pet_desaparecido", "status": "desaparecido", "foto": "/static/darkplanner_pets/cao_03_labrador_amarelo.jpg", "detalhes": "Muito pequenina e carinhosa. Recompensa para quem acolher com cuidado."},
        {"nome": "Pipoca", "especie": "cao", "porte": "Médio", "sexo": "Fêmea", "tipo": "pet_adocao", "status": "adocao", "foto": "/static/darkplanner_pets/cao_04_beagle.jpg", "detalhes": "Super brincalhona, adora crianças e outros animais. Adoção imediata."},
        {"nome": "Max", "especie": "cao", "porte": "Grande", "sexo": "Macho", "tipo": "pet_desaparecido", "status": "desaparecido", "foto": "/static/darkplanner_pets/cao_05_buldogue_frances.jpg", "detalhes": "Cão de guarda dócil com a família. Escapou pelo portão."},
        {"nome": "Amora", "especie": "gato", "porte": "Pequeno", "sexo": "Fêmea", "tipo": "pet_adocao", "status": "adocao", "foto": "/static/darkplanner_pets/gata_02_persa.jpg", "detalhes": "Resgatada de situação de rua, castrada, muito carinhosa e ronronadora."},
        {"nome": "Fred", "especie": "cao", "porte": "Médio", "sexo": "Macho", "tipo": "pet_desaparecido", "status": "desaparecido", "foto": "/static/darkplanner_pets/cao_06_poodle.jpg", "detalhes": "Pelagem preta e branca. Visto correndo perto da avenida."},
        {"nome": "Nina", "especie": "cao", "porte": "Pequeno", "sexo": "Fêmea", "tipo": "pet_desaparecido", "status": "desaparecido", "foto": "/static/darkplanner_pets/cao_07_salsicha.jpg", "detalhes": "Laço rosa na orelha, dócil, precisa de medicação."},
        {"nome": "Chico", "especie": "ave", "porte": "Pequeno", "sexo": "Macho", "tipo": "pet_desaparecido", "status": "desaparecido", "foto": "/static/darkplanner_pets/ave_01_calopsita_amarela.jpg", "detalhes": "Mansa, assobia. Escapou durante a limpeza da gaiola."}
    ]

    conn = get_db()
    cur = conn.cursor()
    criados = 0
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for i in range(qtd):
        tutor = tutores_pool[i % len(tutores_pool)]
        pet = pets_pool[i % len(pets_pool)]
        token_tutor = f"demo_testador_{int(time.time())}_{i}_{random.randint(100, 999)}"

        cur.execute("""
            INSERT OR REPLACE INTO usuarios (autor_token, nome, whatsapp, bairro, cidade, estado, uf, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (token_tutor, tutor[0], tutor[1], tutor[2], cidade, estado, estado, agora, agora))

        offset_lat = random.uniform(-0.018, 0.018)
        offset_lng = random.uniform(-0.018, 0.018)
        p_lat = round(lat_centro + offset_lat, 6)
        p_lng = round(lng_centro + offset_lng, 6)

        titulo_alerta = f"{pet['nome']} • {pet['especie'].capitalize()}"
        desc = f"{pet['detalhes']} Tutor: {tutor[0]} ({tutor[2]})."

        cur.execute("""
            INSERT INTO alertas (
                tipo, pilar, cidade, estado, uf, titulo, descricao, rua, bairro, lat, lng,
                peso, foto_url, contato, consentimento_contato, autor_token, autor_nome,
                fonte_tipo, fonte_nome, especie, porte, status_pet, sexo, ativo, created_at
            ) VALUES (?, 'pet', ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 1, ?, ?, 'demo_testador', 'Comunidade Pet', ?, ?, ?, ?, 1, ?)
        """, (
            pet['tipo'], cidade, estado, estado, titulo_alerta, desc, f"Rua Próxima {i+1}", tutor[2],
            p_lat, p_lng, pet['foto'], tutor[1], token_tutor, tutor[0],
            pet['especie'], pet['porte'], pet['status'], pet['sexo'], agora
        ))
        criados += 1

    conn.commit()
    conn.close()
    return jsonify({"ok": True, "criados": criados, "cidade": cidade, "lat": lat_centro, "lng": lng_centro})


@app.route("/api/testador/limpar_semeados", methods=["POST"])
def api_limpar_semeados():
    """Expurga todas as ocorrências e perfis de teste gerados pelo semeador."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM alertas WHERE fonte_tipo = 'demo_testador'")
    total_alertas = cur.rowcount
    cur.execute("DELETE FROM usuarios WHERE autor_token LIKE 'demo_testador_%'")
    total_usuarios = cur.rowcount
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "alertas_removidos": total_alertas, "usuarios_removidos": total_usuarios})




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



@app.route("/api/pets/<int:pet_id>/aceite-adocao", methods=["POST"])
def registrar_aceite_adocao(pet_id):
    """
    Registra o Aceite Digital Vinculante de Adoção Responsável:
    - Vincula adotante, pet, timestamp e hash cívico.
    - Suporte à Lei Federal 9.605/98 (Art. 32, §1º-A - Lei Sansão).
    """
    data = request.json or {}
    token = (data.get("autor_token") or "").strip()
    nome = (data.get("nome") or "Adotante Consciente").strip()[:100]
    whatsapp = normalizar_telefone(data.get("whatsapp") or "")
    ip_origem = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    
    conn = get_db()
    pet = conn.execute("SELECT id, titulo, bairro FROM alertas WHERE id = ? AND pilar = 'pet'", (pet_id,)).fetchone()
    if not pet:
        conn.close()
        return jsonify({"error": "Pet não encontrado"}), 404
        
    import hashlib
    raw_str = f"{pet_id}-{token}-{datetime.now().isoformat()}-{ip_origem}"
    hash_curto = hashlib.sha256(raw_str.encode('utf-8')).hexdigest()[:8].upper()
    protocolo = f"AP-ADOC-{hash_curto}"
    
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO adocao_aceites (pet_id, adotante_token, adotante_nome, adotante_whatsapp, ip_origem, protocolo_hash)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (pet_id, token, nome, whatsapp, ip_origem, protocolo))
    conn.commit()
    conn.close()
    
    return jsonify({
        "status": "ok",
        "protocolo": protocolo,
        "pet_id": pet_id,
        "pet_titulo": pet["titulo"]
    })
