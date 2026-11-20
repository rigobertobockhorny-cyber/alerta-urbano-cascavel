# -*- coding: utf-8 -*-
"""
Robô Coletor Multi-Fontes v3.0 — Alerta Urbano (Cascavel - PR)
Alimentação 100% Oficial & Imprensa para os pilares:
  - Segurança Hiperlocal (CGN, CATVE)
  - Utilidade Pública (CGN, CATVE, INMET, Sanepar, Copel, Transitar, Prefeitura de Cascavel)
  - Achados & Perdidos / Pets (CGN Pets)

ZERO notícias de trânsito comum / radares / buracos (não competimos com Waze/Maps/Uber).
"""

import os
import sys
import re
import time
import random
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from html import unescape

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATHS = [
    os.path.join(BASE_DIR, "alertas_cascavel.db"),
    os.path.abspath(os.path.join(BASE_DIR, "..", "DEPLOY_NUVEM_ALERTA_URBANO", "alertas_cascavel.db")),
]

CIDADE_PADRAO = "Cascavel"

# Dicionário de Bairros e Vias de Cascavel - PR com Coordenadas Base
COORDENADAS_CASCAVEL = {
    "centro": (-24.9555, -53.4550),
    "brasmadeira": (-24.9120, -53.4350),
    "santa cruz": (-24.9650, -53.5050),
    "cascavel velho": (-24.9780, -53.4280),
    "interlagos": (-24.9210, -53.4420),
    "parque sao paulo": (-24.9720, -53.4560),
    "parque são paulo": (-24.9720, -53.4560),
    "neva": (-24.9660, -53.4680),
    "cancelli": (-24.9450, -53.4750),
    "country": (-24.9380, -53.4480),
    "sao cristovao": (-24.9420, -53.4280),
    "são cristóvão": (-24.9420, -53.4280),
    "coqueiral": (-24.9540, -53.4850),
    "alto alegre": (-24.9580, -53.4980),
    "santa felicidade": (-24.9920, -53.4550),
    "14 de novembro": (-24.9850, -53.4720),
    "quatorze de novembro": (-24.9850, -53.4720),
    "floresta": (-24.9250, -53.4220),
    "morumbi": (-24.9520, -53.3980),
    "periolo": (-24.9450, -53.4120),
    "pacaembu": (-24.9650, -53.4350),
    "recanto tropical": (-24.9480, -53.5020),
    "tropical": (-24.9480, -53.5020),
    "universitário": (-24.9820, -53.4520),
    "universitario": (-24.9820, -53.4520),
    "guaruja": (-24.9880, -53.4780),
    "guarujá": (-24.9880, -53.4780),
    "taruma": (-24.9180, -53.4180),
    "tarumã": (-24.9180, -53.4180),
    "clarito": (-24.9150, -53.4250),
    "esmeralda": (-24.9680, -53.5220),
    "santo onofre": (-24.9620, -53.5010),
    "cataratas": (-24.9580, -53.4150),
    "claudete": (-24.9350, -53.4750),
    "pioneiros catarinenses": (-24.9640, -53.4680),
    "maria luiza": (-24.9680, -53.4480),
    "cidade verde": (-24.9750, -53.5150),
    "canada": (-24.9320, -53.4580),
    "canadá": (-24.9320, -53.4580),
    "santos dumont": (-24.9580, -53.5150),
    "jardim cristal": (-24.9390, -53.4890),
    "consolata": (-24.9280, -53.4050),
    "avenida brasil": (-24.9570, -53.4560),
    "av. brasil": (-24.9570, -53.4560),
    "av brasil": (-24.9570, -53.4560),
    "tancredo neves": (-24.9590, -53.4780),
    "rua parana": (-24.9540, -53.4580),
    "rua paraná": (-24.9540, -53.4580),
    "carlos gomes": (-24.9650, -53.4520),
    "barão do cerro azul": (-24.9600, -53.4510),
    "barao do cerro azul": (-24.9600, -53.4510),
    "trevo cataratas": (-24.9560, -53.4110),
    "trevo do guarujá": (-24.9890, -53.4750),
}

OUTRAS_CIDADES = [
    "toledo", "foz do iguaçu", "foz do iguacu", "curitiba", "maringá", "maringa",
    "londrina", "pato branco", "francisco beltrão", "ibiporã", "ibipora", "ponta grossa",
    "guaraniaçu", "guaraniacu", "santa tereza do oeste", "céu azul", "ceu azul",
    "capitão leônidas marques", "capitao leonidas", "marechal cândido rondon",
    "marechal candido", "corbélia", "corbelia", "cafelândia", "cafelandia",
    "medianeira", "matelândia", "matelandia", "são miguel do iguaçu",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def limpar_html(texto):
    if not texto:
        return ""
    limpo = re.sub(r"<[^>]+>", " ", str(texto))
    limpo = unescape(limpo)
    return re.sub(r"\s+", " ", limpo).strip()


def eh_outra_cidade(texto_lower):
    if "cascavel" in texto_lower:
        return False
    return any(
        f"em {c}" in texto_lower or f"no {c}" in texto_lower or f"na {c}" in texto_lower or f"de {c}" in texto_lower
        for c in OUTRAS_CIDADES
    )


def identificar_local_cascavel(texto):
    t = (texto or "").lower()
    for chave, (lat, lng) in COORDENADAS_CASCAVEL.items():
        if chave in t:
            j_lat = lat + random.uniform(-0.0005, 0.0005)
            j_lng = lng + random.uniform(-0.0005, 0.0005)
            return chave.title(), j_lat, j_lng
    j_lat = -24.9565 + random.uniform(-0.007, 0.007)
    j_lng = -53.4570 + random.uniform(-0.007, 0.007)
    return "Cascavel", j_lat, j_lng


def classificar_v3(texto):
    """
    Classifica uma notícia estritamente nos pilares v3.0:
      - utilidade (clima, água/Sanepar, luz/Copel, interdição/Transitar, utilidade geral)
      - seguranca (assalto, furto, suspeito/ocorrência policial)
    Retorna (pilar, tipo, titulo_curto, severidade, fonte_override) ou None se irrelevante.
    NÃO captura acidentes/trânsito comum nem radares!
    """
    t = (texto or "").lower()

    # 1. UTILIDADE PÚBLICA — CLIMA SEVERO
    if any(k in t for k in [
        "vendaval", "tempestade", "granizo", "chuva intensa", "chuvas intensas",
        "alerta laranja", "alerta amarelo", "alerta vermelho", "inmet", "simepar",
        "rajadas de vento", "alagamento", "enxurrada", "destelhamento", "queda de árvore", "queda de arvore"
    ]):
        sev = "critico" if any(k in t for k in ["vermelho", "grande perigo", "destelhamento"]) else (
            "alerta" if any(k in t for k in ["laranja", "vendaval", "granizo", "tempestade"]) else "atencao"
        )
        return ("utilidade", "utilidade_clima", "Alerta Climático", sev, None)

    # 2. UTILIDADE PÚBLICA — ÁGUA / SANEPAR
    if any(k in t for k in [
        "sanepar", "falta de água", "falta de agua", "sem água", "sem agua",
        "abastecimento de água", "abastecimento de agua", "rompimento de rede", "desabastecimento"
    ]):
        return ("utilidade", "utilidade_agua", "Falta de Água • Sanepar", "atencao", "Sanepar" if "sanepar" in t else None)

    # 3. UTILIDADE PÚBLICA — ENERGIA / COPEL
    if any(k in t for k in [
        "copel", "falta de luz", "falta de energia", "sem luz", "sem energia",
        "apagão", "apagao", "desligamento programado", "rede elétrica", "rede eletrica",
        "fio caído", "fio caido", "fios energizados"
    ]):
        return ("utilidade", "utilidade_luz", "Energia • Copel", "atencao", "Copel" if "copel" in t else None)

    # 4. UTILIDADE PÚBLICA — RUAS FECHADAS / INTERDIÇÕES / TRANSITAR / PREFEITURA
    if any(k in t for k in [
        "rua fechada", "ruas fechadas", "interdição", "interdicao", "interditada", "interditado",
        "bloqueio de via", "bloqueio viário", "transitar", "cettrans", "desvio no trânsito",
        "desvio no transito", "obras na via", "recape", "semáforo apagado", "semaforo apagado"
    ]):
        return ("utilidade", "utilidade_interdicao", "Via Interditada", "normal", "Transitar" if ("transitar" in t or "cettrans" in t) else None)

    # 5. UTILIDADE PÚBLICA — SERVIÇOS ESSENCIAIS / SAÚDE / DEFESA CIVIL
    if any(k in t for k in [
        "hemocentro", "doação de sangue", "doacao de sangue", "defesa civil",
        "upa ", "vacinação", "vacinacao", "dengue", "enxame de abelhas", "incêndio em vegetação", "incendio em vegetacao"
    ]):
        return ("utilidade", "utilidade_geral", "Utilidade Pública", "normal", None)

    # 6. SEGURANÇA HIPERLOCAL — ASSALTO / ROUBO
    if any(k in t for k in ["assalto", "roubo", "roubado", "arma de fogo", "armado", "rendido", "refém", "refem"]):
        return ("seguranca", "assalto", "Alerta de Roubo", "alerta", None)

    # 7. SEGURANÇA HIPERLOCAL — FURTO
    if any(k in t for k in ["furto", "furtado", "arrombamento", "arrombou", "subtraído", "subtraido", "fios de cobre"]):
        return ("seguranca", "furto", "Alerta de Furto", "atencao", None)

    # 8. SEGURANÇA HIPERLOCAL — OCORRÊNCIA POLICIAL RELEVANTE
    if any(k in t for k in [
        "preso", "mandado de prisão", "foragido", "tráfico", "trafico",
        "apreensão de drogas", "arma apreendida", "rocam", "gde", "choque", "homicídio", "homicidio", "disparos de arma"
    ]):
        return ("seguranca", "suspeito", "Ocorrência Policial", "normal", None)

    return None


def fetch_url(url, timeout=12):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def minerar_cgn():
    """Feed RSS oficial da CGN: Segurança + Utilidade Pública de Cascavel."""
    alertas = []
    try:
        xml_data = fetch_url("https://cgn.inf.br/feed")
        root = ET.fromstring(xml_data)
        items = root.findall(".//item")
        print(f"📰 CGN: {len(items)} notícias analisadas.")

        for item in items:
            title = limpar_html(item.findtext("title", ""))
            desc = limpar_html(item.findtext("description", ""))
            link = (item.findtext("link", "") or "").strip()
            cats = " ".join(c.text for c in item.findall("category") if c.text)
            texto_full = f"{title} {desc} {cats}"

            if eh_outra_cidade(texto_full.lower()):
                continue

            clf = classificar_v3(texto_full)
            if not clf:
                continue

            pilar, tipo, titulo_curto, severidade, fonte_ov = clf
            bairro, lat, lng = identificar_local_cascavel(texto_full)
            alertas.append({
                "pilar": pilar,
                "tipo": tipo,
                "titulo": titulo_curto,
                "descricao": title if len(title) <= 220 else title[:217] + "...",
                "rua": bairro,
                "bairro": bairro,
                "lat": lat,
                "lng": lng,
                "link": link,
                "fonte_nome": fonte_ov or "CGN",
                "severidade": severidade,
            })
    except Exception as e:
        print(f"⚠️ CGN indisponível neste ciclo: {e}")
    return alertas


def minerar_catve():
    """Seções Policial e Cidades da CATVE (sem trânsito comum)."""
    urls = ["https://catve.com/policial", "https://catve.com"]
    links = set()
    for u in urls:
        try:
            html = fetch_url(u, timeout=10).decode("utf-8", errors="ignore")
            for path in re.findall(r'href=["\'](/noticia/(?:6|8|9|10)/[^"\']+)["\']', html):
                links.add(path)
        except Exception as e:
            print(f"⚠️ CATVE ({u}) falhou: {e}")

    print(f"📺 CATVE: {len(links)} manchetes analisadas.")
    alertas = []
    for path_url in links:
        slug_texto = path_url.split("/")[-1].replace("-", " ")
        if eh_outra_cidade(slug_texto.lower()):
            continue

        clf = classificar_v3(slug_texto)
        if not clf:
            continue

        pilar, tipo, titulo_curto, severidade, fonte_ov = clf
        bairro, lat, lng = identificar_local_cascavel(slug_texto)
        alertas.append({
            "pilar": pilar,
            "tipo": tipo,
            "titulo": titulo_curto,
            "descricao": slug_texto.capitalize(),
            "rua": bairro,
            "bairro": bairro,
            "lat": lat,
            "lng": lng,
            "link": f"https://catve.com{path_url}",
            "fonte_nome": fonte_ov or "CATVE",
            "severidade": severidade,
        })
    return alertas


def minerar_inmet():
    """Feed oficial público do INMET (Alert-AS RSS) filtrado para Cascavel / Paraná."""
    alertas = []
    urls_inmet = [
        "https://apiprevmet3.inmet.gov.br/avisos/rss",
        "https://alertas2.inmet.gov.br/rss",
    ]
    xml_data = None
    for u in urls_inmet:
        try:
            xml_data = fetch_url(u, timeout=10)
            if xml_data:
                break
        except Exception:
            continue

    if not xml_data:
        print("🌦️ INMET: feed RSS temporariamente indisponível neste ciclo.")
        return []

    try:
        root = ET.fromstring(xml_data)
        items = root.findall(".//item")
        print(f"🌦️ INMET: {len(items)} avisos nacionais analisados.")
        for item in items:
            title = limpar_html(item.findtext("title", ""))
            desc = limpar_html(item.findtext("description", ""))
            link = (item.findtext("link", "") or "https://avisos.inmet.gov.br/").strip()
            texto = f"{title} {desc}".lower()

            # Filtra especificamente por Cascavel ou Oeste Paranaense
            if not any(k in texto for k in ["cascavel", "oeste paranaense"]):
                continue

            sev = "critico" if "grande perigo" in texto or "vermelho" in texto else (
                "alerta" if "perigo." in texto or "laranja" in texto or "severo" in texto else "atencao"
            )
            alertas.append({
                "pilar": "utilidade",
                "tipo": "utilidade_clima",
                "titulo": title[:90] if title else "Alerta Meteorológico INMET",
                "descricao": (desc[:260] + "...") if len(desc) > 260 else (desc or title),
                "rua": "Toda Cascavel",
                "bairro": "Cascavel",
                "lat": -24.9555,
                "lng": -53.4550,
                "link": link,
                "fonte_nome": "INMET",
                "severidade": sev,
            })
    except Exception as e:
        print(f"⚠️ Erro ao interpretar XML do INMET: {e}")

    return alertas


def minerar_portal_publico(nome_fonte, urls, tipo_padrao, titulo_padrao):
    """
    Coletor genérico de páginas públicas de notícias/avisos (Sanepar, Copel, Prefeitura, Transitar).
    Respeita totalmente páginas públicas — nunca tenta login ou bypass de proteção.
    """
    encontrados = []
    seen = set()
    for url in urls:
        try:
            html = fetch_url(url, timeout=10).decode("utf-8", errors="ignore")
            # Extrai links com texto visível
            matches = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
            for href, inner in matches:
                texto = limpar_html(inner)
                if len(texto) < 22 or len(texto) > 220:
                    continue
                t_low = texto.lower()
                # Exige menção a Cascavel quando for órgão estadual (Sanepar/Copel)
                if nome_fonte in ("Sanepar", "Copel") and "cascavel" not in t_low:
                    continue
                if eh_outra_cidade(t_low):
                    continue

                clf = classificar_v3(texto)
                if nome_fonte in ("Prefeitura", "Transitar") and not clf:
                    # Só aproveita notícias da Prefeitura/Transitar que sejam de utilidade real
                    continue

                full_url = href if href.startswith("http") else urllib.request.urljoin(url, href)
                if full_url in seen:
                    continue
                seen.add(full_url)

                pilar = "utilidade"
                tipo = clf[1] if clf and clf[0] == "utilidade" else tipo_padrao
                titulo_curto = clf[2] if clf and clf[0] == "utilidade" else titulo_padrao
                severidade = clf[3] if clf else "normal"
                bairro, lat, lng = identificar_local_cascavel(texto)

                encontrados.append({
                    "pilar": pilar,
                    "tipo": tipo,
                    "titulo": titulo_curto,
                    "descricao": texto,
                    "rua": bairro,
                    "bairro": bairro,
                    "lat": lat,
                    "lng": lng,
                    "link": full_url,
                    "fonte_nome": nome_fonte,
                    "severidade": severidade,
                })
        except Exception as e:
            print(f"⚠️ {nome_fonte} ({url}): indisponível ({e})")

    print(f"🏛️ {nome_fonte}: {len(encontrados)} comunicados oficiais de Cascavel encontrados.")
    return encontrados[:8]


def minerar_cgn_pets():
    """Varre a seção oficial de Achados e Perdidos da CGN (Pets de Cascavel)."""
    url = "https://cgn.inf.br/achados-e-perdidos"
    try:
        html = fetch_url(url, timeout=12).decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"⚠️ CGN Pets indisponível: {e}")
        return []

    items = re.findall(r'<a[^>]*href=[\'"](https://cgn\.inf\.br/noticia/\d+/[^\'"]+)[\'"][^>]*>(.*?)</a>', html, re.DOTALL)
    pets = []
    palavras_pet = ["cachorr", "gato", "gata", "calopsita", "cão", "cadela", "filhote", "poodle", "pitbull", "pastor", "shih", "pinscher", "pet"]
    seen = set()

    for item_url, inner in items:
        if item_url in seen:
            continue
        seen.add(item_url)
        texto = limpar_html(inner)
        lower = texto.lower()
        if not any(p in lower for p in palavras_pet):
            continue

        img_m = re.search(r'src=[\'"]([^\'"]+\.(?:jpg|jpeg|png|webp))[\'"]', inner)
        foto = img_m.group(1) if img_m else ""
        clean_text = re.sub(r'^\d+\s+de\s+[a-zç]+\s+de\s+\d+\s*\|\s*\d+:\d+', '', texto).strip()

        eh_avistado = any(k in lower for k in ["encontrado", "encontrada", "resgatado", "avistado"])
        nome_pet = "Animal Encontrado" if eh_avistado else "Pet Desaparecido"
        m_nome = re.search(r'(Cachorr[ao]|Gat[ao]|Calopsita|Cadela)\s+([A-ZÁÉÍÓÚÂÊÔÃÕ][a-záéíóúâêôãõ]+)', clean_text)
        if m_nome:
            nome_pet = f"{m_nome.group(1)} {m_nome.group(2)}"

        especie = "Gato" if ("gato" in lower or "gata" in lower) else ("Ave" if "calopsita" in lower else "Cachorro")
        bairro, lat, lng = identificar_local_cascavel(clean_text)

        pets.append({
            "pilar": "pet",
            "tipo": "pet_avistado" if eh_avistado else "pet_perdido",
            "titulo": nome_pet,
            "descricao": clean_text,
            "rua": bairro,
            "bairro": bairro,
            "lat": lat,
            "lng": lng,
            "foto_url": foto,
            "link": item_url,
            "fonte_nome": "CGN",
            "especie": especie,
            "status_pet": "avistado" if eh_avistado else "desaparecido",
            "severidade": "normal",
        })

    print(f"🐾 CGN Pets: {len(pets)} animais identificados.")
    return pets


def salvar_alertas_no_banco(alertas):
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_inseridos_geral = 0

    for db_path in DB_PATHS:
        if not os.path.exists(os.path.dirname(db_path)) or not os.path.exists(db_path):
            continue

        try:
            conn = sqlite3.connect(db_path, timeout=30.0)
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL;")

            # Garante colunas v3.0 caso o banco do deploy ainda não tenha rodado server.py
            cur.execute("PRAGMA table_info(alertas)")
            cols = {r[1] for r in cur.fetchall()}
            for col_name, col_def in [
                ("cidade", "TEXT DEFAULT 'Cascavel'"),
                ("pilar", "TEXT DEFAULT 'pet'"),
                ("fonte_nome", "TEXT DEFAULT 'Comunidade'"),
                ("especie", "TEXT DEFAULT ''"),
                ("porte", "TEXT DEFAULT ''"),
                ("status_pet", "TEXT DEFAULT ''"),
                ("pet_pai_id", "INTEGER"),
                ("severidade", "TEXT DEFAULT 'normal'"),
                ("consentimento_contato", "INTEGER DEFAULT 0"),
            ]:
                if col_name not in cols:
                    cur.execute(f"ALTER TABLE alertas ADD COLUMN {col_name} {col_def};")

            inseridos = 0
            for a in alertas:
                link = a.get("link", "")
                desc_prefix = (a.get("descricao") or "")[:48]

                # Deduplicação por link exato OU prefixo da descrição
                if link:
                    cur.execute("SELECT id FROM alertas WHERE link_noticia = ?", (link,))
                    if cur.fetchone():
                        continue
                if desc_prefix:
                    cur.execute("SELECT id FROM alertas WHERE descricao LIKE ?", (f"{desc_prefix}%",))
                    if cur.fetchone():
                        continue

                fonte_tipo = "imprensa" if a["pilar"] == "pet" else "robo_oficial"
                cur.execute("""
                    INSERT INTO alertas (
                        tipo, pilar, cidade, titulo, descricao, rua, bairro, lat, lng,
                        peso, created_at, ativo, link_noticia, foto_url,
                        fonte_tipo, fonte_nome, especie, status_pet, severidade
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 1, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    a["tipo"],
                    a["pilar"],
                    CIDADE_PADRAO,
                    a["titulo"],
                    a["descricao"],
                    a["rua"],
                    a["bairro"],
                    a["lat"],
                    a["lng"],
                    agora,
                    link,
                    a.get("foto_url", ""),
                    fonte_tipo,
                    a.get("fonte_nome", "Imprensa"),
                    a.get("especie", ""),
                    a.get("status_pet", ""),
                    a.get("severidade", "normal"),
                ))
                inseridos += 1

            conn.commit()
            conn.close()
            print(f"💾 [{os.path.basename(os.path.dirname(db_path))}] {inseridos} novos registros oficiais salvos.")
            total_inseridos_geral = max(total_inseridos_geral, inseridos)
        except Exception as e:
            print(f"❌ Erro ao salvar em {db_path}: {e}")

    return total_inseridos_geral


def executar_ciclo():
    print(f"\n[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] 🤖 Robô Coletor v3.0 — Varredura Multi-Fontes (Cascavel)...")
    todos = []
    todos += minerar_cgn()
    todos += minerar_catve()
    todos += minerar_inmet()
    todos += minerar_portal_publico(
        "Sanepar",
        ["https://site.sanepar.com.br/noticias"],
        "utilidade_agua",
        "Falta de Água • Sanepar",
    )
    todos += minerar_portal_publico(
        "Copel",
        ["https://www.copel.com/site/noticias/"],
        "utilidade_luz",
        "Energia • Copel",
    )
    todos += minerar_portal_publico(
        "Prefeitura",
        ["https://cascavel.atende.net/cidadao/noticia"],
        "utilidade_geral",
        "Prefeitura de Cascavel",
    )
    todos += minerar_portal_publico(
        "Transitar",
        ["https://transitarcascavel.com.br/noticias/"],
        "utilidade_interdicao",
        "Via Interditada • Transitar",
    )
    todos += minerar_cgn_pets()

    print(f"🎯 Total capturado neste ciclo: {len(todos)} registros qualificados (zero trânsito comum/radares).")
    inseridos = salvar_alertas_no_banco(todos)
    print(f"✅ Ciclo v3.0 concluído: {inseridos} novos itens adicionados!\n")


if __name__ == "__main__":
    executar_ciclo()

    if "--loop" in sys.argv:
        print("🔁 Robô v3.0 em modo contínuo (15 em 15 minutos). CTRL+C para sair.")
        while True:
            time.sleep(15 * 60)
            executar_ciclo()
