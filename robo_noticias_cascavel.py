# -*- coding: utf-8 -*-
"""
Robô Minerador de Notícias em Tempo Real - Cascavel (CGN & CATVE)
Lê notícias policiais e de trânsito em tempo real, extrai local/bairro,
geolocaliza em Cascavel e alimenta os bancos de dados oficiais:
1) C:\\PROJETOS\\5-FERRAMENTAS\\ALERTA_CASCAVEL\\alertas_cascavel.db
2) C:\\PROJETOS\\5-FERRAMENTAS\\DEPLOY_NUVEM_ALERTA_URBANO\\alertas_cascavel.db
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATHS = [
    os.path.join(BASE_DIR, "alertas_cascavel.db"),
    os.path.abspath(os.path.join(BASE_DIR, "..", "DEPLOY_NUVEM_ALERTA_URBANO", "alertas_cascavel.db"))
]

# Dicionário de Bairros e Pontos de Referência de Cascavel com Coordenadas Base
COORDENADAS_CASCAVEL = {
    # Bairros Principais
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
    
    # Vias e Trevos Críticos
    "trevo cataratas": (-24.9560, -53.4110),
    "trevo da portal": (-24.9790, -53.4150),
    "trevo da frentte": (-24.9850, -53.4300),
    "trevo do guarujá": (-24.9890, -53.4750),
    "avenida brasil": (-24.9570, -53.4560),
    "av. brasil": (-24.9570, -53.4560),
    "av brasil": (-24.9570, -53.4560),
    "tancredo neves": (-24.9590, -53.4780),
    "rua parana": (-24.9540, -53.4580),
    "rua paraná": (-24.9540, -53.4580),
    "rio grande do sul": (-24.9560, -53.4590),
    "carlos gomes": (-24.9650, -53.4520),
    "barão do cerro azul": (-24.9600, -53.4510),
    "barao do cerro azul": (-24.9600, -53.4510),
    "br-277": (-24.9820, -53.4420),
    "br 277": (-24.9820, -53.4420),
    "br-467": (-24.9350, -53.4380),
    "br 467": (-24.9350, -53.4380),
    "prc-467": (-24.9350, -53.4380),
    "pr-180": (-24.9950, -53.4890),
}

# Cidades vizinhas a descartar para manter o foco 100% em Cascavel
OUTRAS_CIDADES = [
    "toledo", "foz do iguaçu", "foz do iguacu", "curitiba", "maringá", "maringa", 
    "londrina", "pato branco", "francisco beltrão", "ibiporã", "ibipora", "ponta grossa", 
    "guaraniaçu", "guaraniacu", "santa tereza do oeste", "céu azul", "ceu azul", 
    "capitão leônidas marques", "capitao leonidas", "marechal cândido rondon", "marechal candido"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def identificar_local_cascavel(texto):
    """Encontra bairro, rua ou trevo mencionado no texto e retorna (bairro_nome, lat, lng)."""
    t = texto.lower()
    for chave, (lat, lng) in COORDENADAS_CASCAVEL.items():
        if chave in t:
            j_lat = lat + random.uniform(-0.0006, 0.0006)
            j_lng = lng + random.uniform(-0.0006, 0.0006)
            return chave.title(), j_lat, j_lng
    
    # Se não citou bairro específico mas é Cascavel, coloca na área central com dispersão
    j_lat = -24.9578 + random.uniform(-0.010, 0.010)
    j_lng = -53.4595 + random.uniform(-0.010, 0.010)
    return "Cascavel", j_lat, j_lng

def classificar_ocorrencia(texto):
    """Classifica a notícia em tipo ('acidente', 'assalto', 'furto', 'suspeito', 'escuro') e título padronizado."""
    t = texto.lower()

    if any(k in t for k in ["acidente", "colisão", "colisao", "capotou", "capotamento", "batida", "atropelamento", "abalroamento", "carro sai da pista", "cai de moto"]):
        return "acidente", "ACIDENTE"
    
    if any(k in t for k in ["assalto", "roubo", "arma de fogo", "armado", "rendido", "refém"]):
        return "assalto", "ASSALTO"

    if any(k in t for k in ["furto", "arrombamento", "furtado", "subtraído", "arrombou", "fios de cobre", "furta"]):
        return "furto", "FURTO"

    if any(k in t for k in ["preso", "mandado", "foragido", "tráfico", "droga", "maconha", "cocaína", "apreensão", "suspeito", "gde", "choque", "rocam", "pm", "agride", "agressão", "arma apreendida"]):
        return "suspeito", "SUSPEITO"

    if any(k in t for k in ["sem luz", "apagão", "apagao", "poste", "semáforo", "falta de energia"]):
        return "escuro", "SEM LUZ"

    return None, None

def minerar_cgn():
    """Lê o feed RSS da CGN em tempo real e extrai notícias policiais/trânsito de Cascavel."""
    alertas_encontrados = []
    try:
        req = urllib.request.Request("https://cgn.inf.br/feed", headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        items = root.findall(".//item")
        print(f"📰 CGN: {len(items)} notícias lidas do feed oficial.")

        for item in items:
            title = item.find("title").text if item.find("title") is not None else ""
            desc = item.find("description").text if item.find("description") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            cats = [c.text.lower() for c in item.findall("category") if c.text]

            texto_completo = f"{title} {desc} {' '.join(cats)}"
            texto_lower = texto_completo.lower()

            # Descarta outras cidades
            if any(f"em {c}" in texto_lower or f"no {c}" in texto_lower or f"na {c}" in texto_lower for c in OUTRAS_CIDADES):
                continue

            tipo, titulo_curto = classificar_ocorrencia(texto_completo)
            if not tipo:
                continue

            bairro, lat, lng = identificar_local_cascavel(texto_completo)
            clean_desc = re.sub(r'<[^>]+>', '', desc).strip()
            if len(clean_desc) > 160:
                clean_desc = clean_desc[:157] + "..."

            alertas_encontrados.append({
                "origem": "CGN",
                "tipo": tipo,
                "titulo": titulo_curto,
                "descricao": f"{title} (Fonte: CGN)",
                "rua": bairro,
                "bairro": bairro if bairro != "Cascavel" else "Cascavel",
                "lat": lat,
                "lng": lng,
                "link": link
            })
    except Exception as e:
        print(f"❌ Erro ao minerar CGN: {e}")

    return alertas_encontrados

def minerar_catve():
    """Varre seções oficiais do CATVE: /transito, /policial e capa principal."""
    urls = [
        "https://catve.com/transito",
        "https://catve.com/policial",
        "https://catve.com"
    ]
    links = set()
    for u in urls:
        try:
            req = urllib.request.Request(u, headers=HEADERS)
            html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
            for path in re.findall(r'href=["\'](/noticia/(?:8|9|6)/[^"\']+)["\']', html):
                links.add(path)
        except Exception as e:
            print(f"❌ Erro ao acessar {u}: {e}")

    print(f"📺 CATVE: {len(links)} notícias policiais/trânsito encontradas.")
    alertas_encontrados = []

    for path_url in links:
        slug = path_url.split('/')[-1]
        slug_texto = slug.replace('-', ' ')
        slug_lower = slug_texto.lower()

        # Descarta notícias explícitas de cidades vizinhas
        if any(f"em {c}" in slug_lower or f"no {c}" in slug_lower or f"na {c}" in slug_lower for c in OUTRAS_CIDADES):
            continue

        tipo, titulo_curto = classificar_ocorrencia(slug_texto)
        if not tipo:
            continue

        bairro, lat, lng = identificar_local_cascavel(slug_texto)
        titulo_limpo = slug_texto.capitalize()

        alertas_encontrados.append({
            "origem": "CATVE",
            "tipo": tipo,
            "titulo": titulo_curto,
            "descricao": f"{titulo_limpo} (Fonte: CATVE)",
            "rua": bairro,
            "bairro": bairro if bairro != "Cascavel" else "Cascavel",
            "lat": lat,
            "lng": lng,
            "link": f"https://catve.com{path_url}"
        })

    return alertas_encontrados

def minerar_cgn_pets():
    """Varre a seção oficial de Achados e Perdidos da CGN em busca de animais desaparecidos."""
    print("🐾 Minerando Achados & Perdidos (Pets) da CGN...")
    url = "https://cgn.inf.br/achados-e-perdidos"

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=12).read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"❌ Erro ao acessar Achados e Perdidos da CGN: {e}")
        return []

    items = re.findall(r'<a[^>]*href=[\'"](https://cgn\.inf\.br/noticia/\d+/[^\'"]+)[\'"][^>]*>(.*?)</a>', html, re.DOTALL)
    pets_encontrados = []
    palavras_pet = ["cachorr", "gato", "gata", "calopsita", "cão", "cadela", "filhote", "poodle", "pitbull", "pastor"]
    seen = set()

    for item_url, inner in items:
        if item_url in seen: continue
        seen.add(item_url)

        texto = re.sub(r'<[^>]+>', ' ', inner).strip()
        lower = texto.lower()

        if any(p in lower for p in palavras_pet):
            img_m = re.search(r'src=[\'"]([^\'"]+\.(?:jpg|jpeg|png|webp))[\'"]', inner)
            foto = img_m.group(1) if img_m else ""

            clean_text = re.sub(r'^\d+\s+de\s+[a-zç]+\s+de\s+\d+\s*\|\s*\d+:\d+', '', texto).strip()

            nome_pet = "Pet Desaparecido"
            m_nome = re.search(r'(Cachorr[ao]|Gat[ao]|Calopsita|Cadela)\s+([A-ZÁÉÍÓÚÂÊÔÃÕ][a-záéíóúâêôãõ]+)', clean_text)
            if m_nome:
                nome_pet = f"{m_nome.group(1)} {m_nome.group(2)}"
            elif "encontrado" in lower:
                nome_pet = "Animal Encontrado"

            bairro, lat, lng = identificar_local_cascavel(clean_text)

            pets_encontrados.append({
                "origem": "CGN PETS",
                "tipo": "pet",
                "titulo": nome_pet,
                "descricao": clean_text + " (Fonte: CGN Achados & Perdidos)",
                "rua": bairro,
                "bairro": bairro,
                "lat": lat,
                "lng": lng,
                "foto_url": foto,
                "link": item_url
            })

    print(f"🐾 Achados & Perdidos CGN: {len(pets_encontrados)} animais identificados.")
    return pets_encontrados

def salvar_alertas_no_banco(alertas):
    """Insere novos alertas em TODOS os bancos de dados configurados (local e deploy)."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_inseridos_geral = 0

    for db_path in DB_PATHS:
        if not os.path.exists(os.path.dirname(db_path)):
            continue

        try:
            conn = sqlite3.connect(db_path, timeout=30.0)
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL;")

            inseridos = 0
            for a in alertas:
                desc_prefix = a["descricao"][:40]
                cur.execute("SELECT id FROM alertas WHERE descricao LIKE ?", (f"{desc_prefix}%",))
                if cur.fetchone():
                    continue

                cur.execute("""
                    INSERT INTO alertas (tipo, titulo, descricao, rua, bairro, lat, lng, peso, created_at, ativo, link_noticia, foto_url, fonte_tipo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, 1, ?, ?, 'imprensa')
                """, (a["tipo"], a["titulo"], a["descricao"], a["rua"], a["bairro"], a["lat"], a["lng"], agora, a.get("link", ""), a.get("foto_url", "")))
                inseridos += 1

            conn.commit()
            conn.close()
            print(f"💾 [{os.path.basename(os.path.dirname(db_path))}] {inseridos} novos alertas inseridos.")
            total_inseridos_geral = max(total_inseridos_geral, inseridos)
        except Exception as e:
            print(f"❌ Erro ao salvar em {db_path}: {e}")

    return total_inseridos_geral

def executar_ciclo():
    print(f"\n[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] 🤖 Iniciando varredura CGN & CATVE...")
    alertas_cgn = minerar_cgn()
    alertas_catve = minerar_catve()
    alertas_pets = minerar_cgn_pets()
    total_encontrados = alertas_cgn + alertas_catve + alertas_pets
    print(f"🎯 Total de {len(total_encontrados)} notícias de interesse filtradas.")
    inseridos = salvar_alertas_no_banco(total_encontrados)
    print(f"✅ Varredura concluída: {inseridos} novos alertas inseridos no mapa!\n")

if __name__ == "__main__":
    executar_ciclo()

    if "--loop" in sys.argv:
        print("🔁 Robô em modo sentinela contínuo (executa a cada 15 minutos). Pressione CTRL+C para sair.")
        while True:
            time.sleep(15 * 60)
            executar_ciclo()
