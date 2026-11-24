# BÍBLIA MESTRA DO ALERTA URBANO CASCAVEL
## Manual Supremo de Engenharia, Governança, Design System, Fluxos de Tela e Pipeline de Publicação
**Documento Soberano e Obrigatório de Referência Contínua para Engenharia e IAs**
**Autoridade e Direção:** Rigo | **Engenheiro/Arquiteto de Sistemas:** Johan
**Data da Última Atualização:** 24/11/2026 | **Versão Corrente:** 3.7.4 (versionCode 18)

---

> ### PROTOCOLO DE LEITURA OBRIGATÓRIA DA IA (REGRA DE CONSISTÊNCIA ABSOLUTA)
> **ATENÇÃO MÁXIMA A QUALQUER IA QUE OPERAR ESTE PROJETO:**
> 1. É terminantemente proibido esquecer, alterar ou inverter as decisões homologadas pelo Rigo.
> 2. **NUNCA propor download manual de APK ou regredir de fase.** O projeto está oficialmente na **Google Play Store**. Todo deploy nativo é 100% automático via Google Play Developer API (`playstore_auto_deploy.py`).
> 3. **Consistência Visual é Lei:** As cores (Hex exatos), a ausência de emojis, a tipografia, os espaçamentos de safe-area e o design em blocos sólidos são invioláveis.
> 4. O Rigo dá o direcionamento técnico/negócio, e o arquiteto Johan executa ponta a ponta sem repassar tarefas manuais ao usuário.

---

## 1. VISÃO GERAL DO ECOSSISTEMA

O **Alerta Urbano Cascavel** (`com.alertaurbano.app`) é a plataforma cívica e colaborativa de inteligência em tempo real para o município de Cascavel - PR, estruturada sobre **3 Pilares Exclusivos**:
1. **Pets Desaparecidos:** Cadastro público de animais perdidos, trilhas de avistamento e resgate com foto direta ao tutor.
2. **Segurança Hiperlocal:** Notícias oficiais de ocorrências graves via robô coletor de imprensa (CGN, CATVE).
3. **Utilidade Pública:** Alertas meteorológicos do INMET e comunicados da Sanepar, Copel, Transitar e Prefeitura de Cascavel.

### Componentes Técnicos do Sistema:
* **App Nativo Android (`android_app/`):**
  * Shell nativo em Kotlin (`MainActivity.kt`) que carrega a WebView com ponte bidirecional (`AndroidBridge`).
  * Serviço de Sobreposição Flutuante (`FloatingBubbleService.kt`): Bolinha flutuante que roda sobre Waze/Maps com GPS nativo, radar de pets a 500m e síntese de áudio.
* **Servidor Central Flask & API (`server.py`):**
  * Backend Python em produção na nuvem Render (`https://alerta-urbano-cascavel.onrender.com`).
  * Repositório de deploy: `C:\PROJETOS\5-FERRAMENTAS\DEPLOY_NUVEM_ALERTA_URBANO` (branch `main`).
  * Banco de Dados SQLite (`alertas_cascavel.db`).
  * Síntese de Voz Neural Oficial (`/api/falar?voz=masculina`).
* **Frontend Web & Mobile (`static/index.html`):**
  * Single Page Application responsiva carregada dentro da WebView nativa.
* **Pipeline Google Play (`KIT_PUBLICACAO_PLAY_STORE/`):**
  * Autenticação direta com a API do Google via Service Account (`google_play_service_account.json`).
  * Chave de upload privada JKS (`alerta_urbano_upload_key.jks`).
  * Script automatizado de deploy (`playstore_auto_deploy.py`).

---

## 2. GOVERNANÇA DE PUBLICAÇÃO & REGRAS DE DEPLOY (LEI SAGRADA)

### Regra do "Nunca Mais APK Manual":
* O projeto superou a fase de testes informais de APKs avulsos.
* **Toda e qualquer atualização de código nativo gera exclusivamente um pacote `.aab` (Android App Bundle)** assinado com a chave oficial:
  * Caminho: `C:\PROJETOS\5-FERRAMENTAS\ALERTA_URBANO_CASCAVEL\KIT_PUBLICACAO_PLAY_STORE\ALERTA_URBANO_v[VERSAO].aab`
* O deploy é enviado **AUTOMATICAMENTE** para a trilha `internal` (Teste Interno) do Google Play Console executando:
  ```powershell
  python C:\PROJETOS\5-FERRAMENTAS\ALERTA_URBANO_CASCAVEL\KIT_PUBLICACAO_PLAY_STORE\CHAVE_PRIVADA_UPLOAD\playstore_auto_deploy.py
  ```
* O Google Play Console processa o commit via API e o app atualiza no celular do Rigo pela própria Play Store através do link de testador:
  `https://play.google.com/apps/internaltest/4700894699290035348`
* **O Rigo nunca deve ser instruído a baixar APK por link de navegador ou subir pacotes manualmente no Console.** A IA cuida do pipeline inteiro.

---

## 3. DESIGN SYSTEM & PALETA CROMÁTICA OFICIAL (HEXADECIMAIS EXATOS)

| Elemento / Seção | Código Hex | Função e Aplicação |
| :--- | :--- | :--- |
| **Fundo da Aba Pets (`#tab-pets`)** | `#E4D5BC` | Bege Escuro Quente e acolhedor (substituiu o amarelo estridente). |
| **Fundo da Tela "Marcar Onde Vi"** | `#E4D5BC` | Fundo idêntico à aba pets para total coerência visual. |
| **Fundo de Blocos / Cards Neutros** | `#EDE8DF` | Bege Areia / Cinzinha suave para cards, filtros e inputs. |
| **Botão Secundário / Ação Neutra** | `#DFD5C2` | Bege estruturado para botões como "Tirar Foto" e "Escolher Galeria". |
| **Botão Selecionado / CTA Primário** | `#000000` | Preto Sólido com texto Branco `#FFFFFF` (100% de contraste, zero amarelo em botão selecionado). |
| **Canopy Verde Brasil (Topo Home)** | `#009B3A` | Verde Oficial da cabeceira com clima, temperatura e esteira de avisos. |
| **Destaque Ouro Brasil** | `#FED700` | Amarelo cívico utilizado na logo da bolinha e destaques de trânsito. |
| **Alerta Vermelho / Emergência** | `#DC2626` | Vermelho sólido para ocorrências críticas e anel de clima severo. |
| **Alerta Laranja / Radar Pet** | `#F97316` / `#F59E0B` | Laranja para perigo climático e Dourado/Âmbar para zona de busca de pet. |
| **Alerta Amarelo Clima** | `#EAB308` | Amarelo para atenção meteorológica moderada. |
| **Card Pet - Fêmea** | `#FCE7F3` / `#F472B6` | Fundo rosa suave com bolhas orgânicas decorativas sem margem. |
| **Card Pet - Macho** | `#E0F2FE` / `#38BDF8` | Fundo azul suave com bolhas orgânicas decorativas sem margem. |
| **Card Pet - Adoção** | `#EDE9FE` / `#A78BFA` | Fundo lavanda / lilás para animais de adoção responsável. |

### Regras Estritas de UI:
1. **ZERO EMOJIS:** Proibido o uso de emojis em cards, títulos ou badges. Utilizar ícones SVG limpos ou texto claro.
2. **ZERO PÍLULAS REDUNDANTES NA ABA PETS:** Os cards da Aba Pets NÃO possuem pílulas repetitivas dizendo "desaparecido", "cachorro", "fêmea" no meio da foto/card quando a tela já está filtrada para isso. As pílulas descritivas são exclusivas das esteiras rotativas da Home.
3. **ESPAÇAMENTO DE SEGURANÇA (SAFE AREA):** Todas as telas roláveis terminam com no mínimo `padding-bottom: calc(env(safe-area-inset-bottom, 0px) + 80px)`, garantindo que nenhum botão fique prensado ou coberto pela barra virtual de navegação do Android.

---

## 4. ESPECIFICAÇÃO DETALHADA DAS TELAS E BOTÕES

### 4.1. ABA 1: INÍCIO (HOME — ZERO SCROLL)
* **Canopy Verde Brasil (`.home-green-canopy`):**
  * Temperatura, ícone meteorológico e condição de Cascavel (via Open-Meteo).
  * Esteira dinâmica de monitoramento climático (`.alert-ticker`): exibe em texto contínuo o status climático oficial. Ao tocar, abre o detalhe da ocorrência.
* **Curva Orgânica Brasil:** Transição visual fluida do verde para o fundo da página.
* **3 Esteiras Contínuas Destravadas:**
  * Esteira 1: Pets Desaparecidos da Cidade.
  * Esteira 2: Segurança & Utilidade Pública.
  * Esteira 3: Animais para Adoção / Ações Cívicas.
  * **Comportamento Homologado:** Destravadas para o dedo. O usuário pode arrastar o card para esquerda/direita livremente. Após soltar o dedo, uma pausa suave ocorre e a esteira retoma sua rotação normal automática.

---

### 4.2. ABA 2: PETS (CENTRAL DE ANIMAIS)
* **Fundo:** Bege Escuro Quente `#E4D5BC`.
* **Filtros Superiores (Pílulas):** `Desaparecidos`, `Avistados`, `Adoção`.
* **Sub-filtros em Linha:** `Todos`, `Cachorros`, `Gatos`, `Outros`.
* **Cards de Pets:**
  * Bloco colorido sólido com bolhas de fundo (Rosa para fêmeas, Azul para machos, Lilás para adoção).
  * Foto do pet com cantos arredondados.
  * Nome do animal em negrito preto, seguido pelo bairro e tempo de registro.
  * **Botão Primário Preto:** `[ Marcar Onde Vi ]` — abre a tela de avistamento.
  * **Botão Secundário:** `[ Pet Resgatado ]` ou `[ Ver Matéria ]` (se for notícia da CGN).

---

### 4.3. TELA COMPLETA: MARCAR ONDE VI / PET RESGATADO (`#modal-avistamento`)
* **Estrutura:** Modal em tela cheia independente (`full-screen-view`), fundo `#E4D5BC`, z-index 2600.
* **Cabeçalho:** Botão `‹ Voltar` à esquerda, título centralizado em negrito preto, botão invisível de balanceamento à direita.
* **Alternador Superior:**
  * `[ Apenas Avistei ]`: Quando selecionado, fica Preto Sólido `#000000` com letra branca.
  * `[ Pet Resgatado ]`: Quando selecionado, assume preto sólido.
* **Bloco de Foto:**
  * Área tracejada bege/cinza com preview automático ao anexar.
  * **Botão [ Tirar Foto ]:** Dispara `<input type="file" capture="environment">`. No Android nativo, ativa a câmera física através do `FileProvider` e armazena imagem em alta resolução.
  * **Botão [ Escolher da Galeria ]:** Dispara seletor de galeria do celular.
* **Seleção de Modo de Localização:**
  * `[ Meu GPS ]`: Captura coordenadas nativas de alta precisão ao confirmar.
  * `[ Alfinete no Mapa ]`: Abre o mini-mapa interativo com alfinete vermelho arrastável.
    * **Provedor:** **ESRI World Street Map** (`server.arcgisonline.com`). Totalmente livre de chaves de API, imune a bloqueios e sem marcas d'água.
  * `[ Digitar Endereço ]`: Campo de texto aberto para rua/cruzamento.
* **Campo de WhatsApp & Consentimento:** Checkbox opcional para liberar contato exclusivamente com o tutor do pet.
* **Botão de Confirmação:** `[ Enviar "Visto Aqui" ao Tutor ]` ou `[ Enviar Foto de Resgate ao Tutor ]`. Fundo preto sólido, letras brancas, com respiro de 90px para nunca sobrepor a barra do Android.

---

### 4.4. ABA 3: MAPA COMPLETO
* Mapa Leaflet cobrindo toda a tela de Cascavel.
* Pinos diferenciados: Vermelho (Segurança), Azul (Utilidade), Amarelo (Trânsito), Dourado/Roxo (Pets).
* Ferramentas: Alternador de Camada Satélite / Ruas, Centralizador no GPS do usuário e Filtros de Pilares.

---

### 4.5. ABA 4: COPILOTO (BOLINHA FLUTUANTE EM SEGUNDO PLANO)
* Hero com a logo oficial da bolinha amarela e descrição do copiloto.
* **Botão Preto Sólido:** `[ ATIVAR BOLINHA FLUTUANTE ]` — Invoca `window.AndroidAlerta.minimizarParaBolha()`.
* **Botão com Contorno:** `[ DESATIVAR BOLINHA FLUTUANTE ]`.
* **Switches de Configuração:**
  * *Pets Desaparecidos* (Prioridade Máxima — Raio 500m).
  * *Segurança Hiperlocal* (Raio 250m).
  * *Utilidade Pública* (Raio 350m).

---

## 5. ENGENHARIA DA BOLINHA FLUTUANTE & RADAR DE PETS (`FloatingBubbleService.kt`)

### A. Prioridade Absoluta para Pets:
* Ao dirigir pela cidade, os **animais desaparecidos têm prioridade 100% sobre qualquer outro alerta**.
* Alertas climáticos ou notícias gerais NÃO interrompem a detecção de pets no trânsito.

### B. Cooldowns e Cadência de Alertas ao Volante:
* **Cooldown Global entre Alertas Distintos:** **60 segundos** (`COOLDOWN_GLOBAL_MS = 60 * 1000L`). Permite ouvir pets de bairros diferentes à medida que o motorista transita por Cascavel.
* **Cooldown por Pet Idêntico:** **20 minutos** (`COOLDOWN_MS = 20 * 60 * 1000L`). Evita repetições desnecessárias se o motorista ficar parado no mesmo cruzamento.
* **Carência Inicial:** 5 segundos após ativação para não assustar o usuário na inicialização.
* **Raio de Detecção:** **500 metros** (`RAIO_PET_M = 500f`).

### C. Cores da Margem / Anel da Bolinha (`bubbleRingDrawable`):
1. **Sem Alerta Climático Ativo:** Borda 100% transparente (`Color.TRANSPARENT`). Fica **somente a bolinha amarela pura** na tela.
2. **Alerta Vermelho Crítico:** Borda vermelha sólida de 3dp (`#DC2626`).
3. **Alerta Laranja:** Borda laranja sólida de 3dp (`#F97316`).
4. **Alerta Amarelo Atenção:** Borda amarela de 3dp (`#EAB308`).
5. **Zona de Pet Perdido (Radar):** Ao entrar no raio de 500m de um animal desaparecido, a borda acende em **dourado/âmbar** (`#F59E0B`).

### D. Motor de Áudio com Redundância Ativa:
* 1. Vinheta sonora de 2 notas exclusivas (`ToneGenerator`).
* 2. Voz neural masculina do servidor via `/api/falar?voz=masculina&texto=...`.
* 3. **Fallback Automático TTS:** Se o streaming da rede móvel não iniciar em 3.8 segundos, o sintetizador nativo Android (`TextToSpeech` em português BR) assume imediatamente para que o aviso nunca seja perdido na rua.

### E. Card Visual e Interação de Toque:
* Quando o alerta dispara, um card compacto é projetado sobre o Waze/Maps com a foto do animal, o nome, o bairro e a distância em metros (ex.: `CANCELLI • A 180M`).
* Se o motorista tocar na bolinha flutuante a qualquer momento, o card do pet mais próximo é aberto na hora com opções de `[ Visto aqui ]` e `[ Ver no mapa ]`.

---

## 6. DIRETRIZES DE CONTINUIDADE PARA SESSÕES FUTURAS

1. **Atualizações de Banco de Dados:** Todo filtro climático para Cascavel deve conter estritamente `LOWER(cidade) = 'cascavel'`. Nunca utilizar termos genéricos como "Oeste Paranaense" que cobrem dezenas de outros municípios.
2. **Sincronização de Repositórios:** Qualquer modificação em `static/index.html` ou `server.py` deve ser copiada e sincronizada no repositório `DEPLOY_NUVEM_ALERTA_URBANO`, seguida de commit e push para manter o Render em paridade com o ambiente local.
3. **Compilação e Publicação:** Sempre que houver alteração em `android_app/`:
   * Incrementar `versionCode` e `versionName` no `build.gradle.kts`.
   * Compilar o bundle: `gradle.bat bundleRelease`.
   * Publicar automaticamente: `python playstore_auto_deploy.py`.
   * Atualizar este documento com a nova versão.

---
**Fim da Bíblia Mestra — Alerta Urbano Cascavel v3.7.4**
