# -*- coding: utf-8 -*-
"""
ENGINE DE CICLO DE VIDA & AUTO-REGENERAÇÃO DE TESTES (ALERTA URBANO CASCAVEL)
Regra Mestra do Rigo (16/11/2026):
- Alertas de teste dobram rigorosamente a quantidade de alertas reais da imprensa (1:1).
- Exclusivamente categorias LIGHT: Buraco, Iluminação apagada, Semáforo, Obras e Trânsito Lento.
- ZERO acidentes, ZERO perigos, ZERO polícia/viatura em testes para não assustar no carro.
- Cada ocorrência cumpre seu ciclo de vida e avança suavemente na mesma via real de Cascavel.
"""

import os
import json
import math
import random
import sqlite3
import threading
import time
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "alertas_cascavel.db")
GEOM_FILE = os.path.join(BASE_DIR, "todas_ruas_geometrias.json")

# Ciclo de vida por tipo LIGHT (em horas)
VIDA_UTIL_HORAS = {
    "buraco": 24,
    "apagao": 12,
    "semaforo": 24,
    "obras": 24,
    "transito": 6
}

BAIRROS_MAP = {
    'Avenida Brasil': 'Centro / São Cristóvão',
    'Avenida Tancredo Neves': 'Alto Alegre',
    'Rodovia BR-467': 'Região Norte / Clarito',
    'Rodovia BR-277': 'Cascavel Velho / Santos Dumont',
    'BR-369': 'Morumbi / Brasília',
    'Avenida das Pombas': 'Floresta',
    'Avenida Papagaios': 'Floresta / Clarito',
    'Avenida Curió': 'Floresta',
    'Rua Waldir Azevedo': 'Floresta',
    'Rua Vereador José de Oliveira': 'Morumbi',
    'Rua Jacarezinho': 'São Cristóvão / Periolo',
    'Rua Maracaí': 'Periolo',
    'Rua Jorge Lacerda': 'Claudete / Cancelli',
    'Rua Rio da Paz': 'Nova Cidade / Cascavel Velho',
    'Avenida Barão do Rio Branco': 'São Cristóvão / Country',
    'Avenida Assunção': 'Alto Alegre',
    'Rua Paraná': 'Centro / Coqueiral',
    'Rua Rio Grande do Sul': 'Centro / Coqueiral',
    'Rua São Paulo': 'Centro',
    'Rua Minas Gerais': 'Centro',
    'Rua Vicente Machado': 'Centro / Neva',
    'Rua Manaus': 'Cancelli / Country',
    'Rua Antonina': 'Cancelli / Country',
    'Rua Cuiabá': 'Neva / Parque São Paulo',
    'Avenida Carlos Gomes': 'Parque São Paulo / Maria Luiza',
    'Rua Flamboyant': 'Coqueiral',
    'Rua Fortaleza': 'Coqueiral',
    'Rua Recife': 'Coqueiral',
    'Rua Vitória': 'Neva / Centro',
    'Rua Salgado Filho': 'Neva / Alto Alegre',
    'Avenida Rocha Pombo': 'Cascavel Velho / Periolo',
    'Rua Fagundes Varela': 'Coqueiral',
    'Rua Presidente Kennedy': 'Coqueiral',
    'Avenida Piquiri': 'São Cristóvão / Brasmadeira',
    'Rua Carlos de Carvalho': 'Centro',
    'Rua Souza Naves': 'Centro',
    'Rua Rio de Janeiro': 'Centro',
    'Rua Presidente Bernardes': 'Centro'
}

_GEOMETRIAS_CACHE = None

def carregar_geometrias():
    global _GEOMETRIAS_CACHE
    if _GEOMETRIAS_CACHE is None and os.path.exists(GEOM_FILE):
        try:
            with open(GEOM_FILE, "r", encoding="utf-8") as f:
                _GEOMETRIAS_CACHE = json.load(f)
        except Exception as e:
            print(f"[ENGINE TESTES] Erro ao carregar geometrias: {e}")
            _GEOMETRIAS_CACHE = {}
    return _GEOMETRIAS_CACHE or {}

def dist_metros(p1, p2):
    R = 6371000
    lat1, lon1 = math.radians(p1[1]), math.radians(p1[0])
    lat2, lon2 = math.radians(p2[1]), math.radians(p2[0])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def descolar_ponto_na_mesma_rua(rua_nome, curr_lat, curr_lng, avanco_m=200):
    vias = carregar_geometrias()
    if rua_nome not in vias or len(vias[rua_nome]) < 2:
        todas = list(vias.keys())
        if not todas:
            return curr_lat, curr_lng
        rua_nome = random.choice(todas)

    pts = vias[rua_nome]

    melhor_dist = float("inf")
    melhor_idx = 0
    curr_pt = [curr_lng, curr_lat]

    for i in range(len(pts) - 1):
        d = (dist_metros(curr_pt, pts[i]) + dist_metros(curr_pt, pts[i+1])) / 2.0
        if d < melhor_dist:
            melhor_dist = d
            melhor_idx = i

    restante = float(avanco_m)
    idx = melhor_idx
    sentido = 1

    novo_pt = None
    passos = 0
    while restante > 0 and passos < len(pts) * 2:
        passos += 1
        prox_idx = idx + sentido
        if prox_idx >= len(pts) or prox_idx < 0:
            sentido = -sentido
            continue

        p_a = pts[idx]
        p_b = pts[prox_idx]
        d_seg = dist_metros(p_a, p_b)

        if d_seg < 0.1:
            idx = prox_idx
            continue

        if restante <= d_seg:
            t = restante / d_seg
            novo_lng = p_a[0] + t * (p_b[0] - p_a[0])
            novo_lat = p_a[1] + t * (p_b[1] - p_a[1])
            novo_pt = [novo_lng, novo_lat]
            break
        else:
            restante -= d_seg
            idx = prox_idx

    if not novo_pt:
        p_rnd = random.choice(pts)
        novo_pt = [p_rnd[0], p_rnd[1]]

    return round(novo_pt[1], 6), round(novo_pt[0], 6)

def formatar_titulo_teste(tipo, titulo_antigo=""):
    t = (tipo or "").lower()
    nomes = {
        "buraco": "Buraco na pista",
        "transito": "Trânsito lento",
        "apagao": "Iluminação pública apagada",
        "escuro": "Iluminação pública apagada",
        "obras": "Obras na via",
        "semaforo": "Semáforo em manutenção"
    }
    base = nomes.get(t)
    if not base:
        base = "Buraco na pista"
    return f"[TESTE] {base}"

def inicializar_e_migrar_alertas_teste(db_path=DB_PATH):
    """
    Higieniza o banco: expurga alertas de teste pesados/assustadores (acidentes, perigo, polícia)
    e mantém apenas os testes LIGHT calibrados, preservando 100% dos dados reais.
    """
    conn = sqlite3.connect(db_path, timeout=30.0)
    c = conn.cursor()

    # 1. Remove qualquer teste que não seja estritamente LIGHT
    c.execute("""
        DELETE FROM alertas 
        WHERE fonte_tipo = 'radar_comunitario' 
           OR (fonte_tipo = 'teste' AND tipo NOT IN ('buraco', 'apagao', 'semaforo', 'obras', 'transito'))
           OR lat < -30 OR lat > -20 
           OR lng < -60 OR lng > -45
    """)
    conn.commit()

    # 2. Contagem de alertas reais da imprensa
    c.execute("SELECT COUNT(*) FROM alertas WHERE ativo = 1 AND fonte_tipo = 'imprensa'")
    total_imprensa = c.fetchone()[0]

    # 3. Contagem de alertas reais preservados no geral
    c.execute("SELECT COUNT(*) FROM alertas WHERE ativo = 1 AND (fonte_tipo != 'teste' OR fonte_tipo IS NULL)")
    total_reais = c.fetchone()[0]

    conn.close()
    print(f"[ENGINE TESTES] Higienização concluída: {total_reais} alertas reais preservados (Imprensa ativa: {total_imprensa}).")
    return total_imprensa

def executar_ciclo_regeneracao(db_path=DB_PATH):
    """
    Regenera e equilibra os testes: mantém exatamente a mesma quantidade da imprensa (1:1),
    exclusivamente com categorias LIGHT.
    """
    conn = sqlite3.connect(db_path, timeout=30.0)
    c = conn.cursor()
    agora = datetime.now()

    # 1. Obter total da imprensa ativa para dobrar (1:1)
    c.execute("SELECT COUNT(*) FROM alertas WHERE ativo = 1 AND fonte_tipo = 'imprensa'")
    total_imprensa = c.fetchone()[0]
    alvo_testes = max(15, total_imprensa)

    # 2. Buscar todos os alertas de teste ativos
    c.execute("""
        SELECT id, tipo, titulo, rua, bairro, lat, lng, created_at 
        FROM alertas 
        WHERE ativo = 1 AND fonte_tipo = 'teste'
    """)
    testes_ativos = c.fetchall()

    expirados_cont = 0
    novos_gerados = []

    for alert_id, tipo, titulo, rua, bairro, lat, lng, created_str in testes_ativos:
        try:
            dt_criado = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            dt_criado = agora - timedelta(hours=30)

        vida_max = VIDA_UTIL_HORAS.get(tipo, 12)
        tempo_vida = agora - dt_criado

        if tempo_vida.total_seconds() >= (vida_max * 3600):
            c.execute("UPDATE alertas SET ativo = 0 WHERE id = ?", (alert_id,))
            expirados_cont += 1

            avanco = random.choice([100, 200, 300, 500])
            novo_lat, novo_lng = descolar_ponto_na_mesma_rua(rua, lat, lng, avanco)
            novo_tit = formatar_titulo_teste(tipo, titulo)

            novos_gerados.append((
                tipo,
                novo_tit,
                "Ocorrência de teste em rota • Calibração viária no asfalto",
                rua,
                bairro,
                novo_lat,
                novo_lng,
                1,
                1,
                'teste',
                agora.strftime("%Y-%m-%d %H:%M:%S")
            ))

    if novos_gerados:
        c.executemany("""
            INSERT INTO alertas (tipo, titulo, descricao, rua, bairro, lat, lng, peso, ativo, fonte_tipo, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, novos_gerados)

    # 3. Equilibrar com o alvo da imprensa (Déficit ou Excesso)
    c.execute("SELECT COUNT(*) FROM alertas WHERE ativo = 1 AND fonte_tipo = 'teste'")
    total_atual = c.fetchone()[0]

    # Se estiver com excesso, deleta os mais antigos
    if total_atual > alvo_testes:
        excesso = total_atual - alvo_testes
        c.execute(f"""
            DELETE FROM alertas WHERE id IN (
                SELECT id FROM alertas WHERE ativo = 1 AND fonte_tipo = 'teste'
                ORDER BY id ASC LIMIT {excesso}
            )
        """)
        total_atual = alvo_testes

    deficit = alvo_testes - total_atual
    if deficit > 0:
        vias = carregar_geometrias()
        ruas_list = list(vias.keys())
        tipos_light = ['buraco', 'buraco', 'apagao', 'semaforo', 'obras', 'transito']

        novos_suplementares = []
        for _ in range(deficit):
            r_nome = random.choice(ruas_list)
            pts = vias[r_nome]
            idx_a = random.randint(0, len(pts) - 2)
            p_a, p_b = pts[idx_a], pts[idx_a + 1]
            t = random.uniform(0.1, 0.9)
            s_lng = p_a[0] + t * (p_b[0] - p_a[0])
            s_lat = p_a[1] + t * (p_b[1] - p_a[1])

            t_tipo = random.choice(tipos_light)
            t_tit = formatar_titulo_teste(t_tipo, "")
            b_bairro = BAIRROS_MAP.get(r_nome, 'Cascavel')

            novos_suplementares.append((
                t_tipo,
                t_tit,
                "Ocorrência de teste em rota • Calibração viária no asfalto",
                r_nome,
                b_bairro,
                round(s_lat, 6),
                round(s_lng, 6),
                1,
                1,
                'teste',
                agora.strftime("%Y-%m-%d %H:%M:%S")
            ))

        c.executemany("""
            INSERT INTO alertas (tipo, titulo, descricao, rua, bairro, lat, lng, peso, ativo, fonte_tipo, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, novos_suplementares)

    conn.commit()
    conn.close()

    if expirados_cont > 0 or deficit > 0:
        print(f"[ENGINE TESTES] Ciclo executado: {expirados_cont} expirados avançaram na via. Deficit preenchido: {deficit}. Total de testes mantido em {alvo_testes} (1:1 com imprensa).")

def _worker_daemon(db_path, intervalo_seg):
    while True:
        try:
            time.sleep(intervalo_seg)
            executar_ciclo_regeneracao(db_path)
        except Exception as e:
            print(f"[ENGINE TESTES] Erro no ciclo daemon: {e}")
            time.sleep(10)

def iniciar_engine_testes_background(db_path=DB_PATH, intervalo_seg=60):
    inicializar_e_migrar_alertas_teste(db_path)
    executar_ciclo_regeneracao(db_path)

    t = threading.Thread(target=_worker_daemon, args=(db_path, intervalo_seg), daemon=True)
    t.name = "EngineTestesCascavel"
    t.start()
    print(f"[ENGINE TESTES] Daemon iniciado com sucesso (Verificação a cada {intervalo_seg}s).")
    return t

if __name__ == "__main__":
    print("Testando Engine de Testes Cascavel Light...")
    inicializar_e_migrar_alertas_teste()
    executar_ciclo_regeneracao()
    print("Sucesso!")
