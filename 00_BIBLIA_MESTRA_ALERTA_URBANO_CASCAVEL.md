# BÍBLIA MESTRA DO ALERTA URBANO CASCAVEL
## Manual Supremo de Engenharia, Governança, Design System, Fluxos de Tela e Pipeline de Publicação
**Documento Soberano e Obrigatório de Referência Contínua para Engenharia e IAs**
**Autoridade e Direção:** Rigo | **Engenheiro/Arquiteto de Sistemas:** Johan
**Data da Última Atualização:** 25/11/2026 | **Versão Corrente:** 3.9.5 (versionCode 21)

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

## 7. GOVERNANÇA JURÍDICA INTEGRAL, LGPD E DIRETRIZES DE COMUNIDADE (UGC)

### 7.1. Marco Regulatório e Proteção Institucional (Vórtice Mídia)
A plataforma opera sob estrita conformidade com a legislação federal brasileira e diretrizes do Google Play Console:
1. **Marco Civil da Internet (Lei nº 12.965/2014):** Guarda obrigatória de registros de conexão por 6 meses (Art. 15) e qualificação da Vórtice Mídia como provedora de aplicações de internet (Art. 5º, VII e Art. 19).
2. **Lei Geral de Proteção de Dados (Lei nº 13.709/2018 - LGPD):** Controlador definido como Vórtice Mídia; DPO/Encarregado formal (`rigobertobockhorny@gmail.com`); bases legais aplicadas (Art. 7º, I, II, V, VI e IX); e garantia dos direitos de exclusão e portabilidade (Art. 18).
3. **Código de Proteção e Defesa do Consumidor (Lei nº 8.078/1990):** Transparência inequívoca sobre serviços e limitações de responsabilidade.
4. **Legislação Ambiental e Animal:** Lei Federal nº 9.605/1998 e Lei Sansão nº 14.064/2020 — proibição irrestrita de comércio de animais, criadouros clandestinos, abuso e crueldade.
5. **Código Penal Brasileiro:** Advertência expressa quanto aos crimes de Falsidade Ideológica (Art. 299) e Falsa Comunicação de Crime ou Contravenção (Art. 340).

### 7.2. Estrutura de Documentos no Sistema
* **Modal Nativo no App (`#modal-termos` em `static/index.html`):**
  * Aba 1: `Termos de Uso` (`#painel-termos-uso`) — Objeto, 3 pilares cívicos, elegibilidade (13+ anos), proibição absoluta de comércio de animais, isenção por encontros presenciais de devolução, propriedade intelectual da Vórtice Mídia e foro em Cascavel - PR.
  * Aba 2: `Privacidade LGPD` (`#painel-privacidade-lgpd`) — Controlador e DPO, dados coletados com minimização, declaração formal de uso de GPS em primeiro plano e segundo plano (copiloto persistente sem gravação de itinerário), retenção, auto-ocultação instantânea do WhatsApp ao marcar "Pet Encontrado", e passo a passo de exclusão de conta.
  * Aba 3: `Tolerância Zero (UGC)` (`#painel-tolerancia-zero`) — Diretrizes Google Play UGC, tolerância zero contra pornografia, ódio, maus-tratos e golpes; botão "Reportar Conteúdo" em todas as fichas; SLA de análise e remoção humana em até 24 horas; e bloqueio de hardware (`autor_token`).
* **Páginas Estáticas Públicas Standalone:**
  * `static/termos_uso.html` (acessível via rotas `/termos`, `/termos-de-uso`, `/termos_uso.html`, `/diretrizes`).
  * `static/politica_privacidade.html` (acessível via rotas `/privacidade`, `/politica-privacidade`, `/politica_privacidade.html` e vinculada à ficha na Google Play Store).
* **Acessibilidade no Perfil do Cidadão (`modal-perfil`):**
  * Linhas de navegação direta para `Termos de Uso & Diretrizes`, `Política de Privacidade & LGPD`, `Tolerância Zero & Conduta (UGC)` e botão de `Excluir Minha Conta`.

---

## 8. SISTEMA DE PARCEIROS, ESTEIRA DE PROMOÇÕES E MONETIZAÇÃO LOCAL (v3.8.2)

### 8.1. Estrutura de Negócio e Compliance Google Play
* **Venda de Produtos e Serviços Físicos:** Conforme as políticas de pagamento da Google Play Store (Google Play Billing Policy), a exigência de faturamento interno do Google aplica-se estritamente a bens digitais consumidos dentro do app. Venda de serviços locais (banho/tosa, consultas, vacinas) e produtos físicos (rações, autopeças, baterias) com finalização no WhatsApp ou balcão físico do lojista é **100% permitida, legal e isenta de taxas do Google**.
* **Zero Áudio Comercial no Copiloto:** A voz TTS no trânsito é reservada estritamente para segurança e alertas cívicos. Anúncios comerciais em áudio no carro foram descartados para evitar sensação de spam, atritos de concorrência e perda de credibilidade.
* **5º Botão no Menu Inferior (`nav-parceiros`):** A barra inferior conta com 5 abas (`Início`, `Mapa`, `Pets`, `Parceiros`, `Copiloto`) em proporção ergonômica de 20% cada (`grid-template-columns: repeat(5, 1fr)`).

### 8.2. Componentes da Rede Parceira
1. **Aba Dedicada "Parceiros" (`#tab-parceiros`):**
   * Guia oficial de estabelecimentos amigos de Cascavel, com filtro de categorias (`Todos`, `🐾 Clínicas & Vet`, `🐕 Pet Shops & Ração`, `🚗 Auto Centers & Pneus`, `⛽ Postos & Serviços`).
   * Cards com Selo Oficial (`★ Empresa Amiga da Causa Animal (Ouro)` ou `🛡️ Empresa Cidadã de Cascavel`), endereço no bairro, botão direto de WhatsApp e botão para traçar rota no mapa.
   * Vitrine de produtos/serviços promocionais dos parceiros com tags de desconto (ex.: "28% OFF", "PROMOÇÃO", "SOCIAL") e botão "Pedir no WhatsApp 💬".
2. **Esteira Rolante na Aba Pets (`#esteira-parceiros-box`):**
   * Carrossel horizontal elegante posicionado entre os cards de animais e o rodapé da aba Pets, exibindo as marcas parceiras oficiais com selo e ofertas em destaque.
3. **Camada Parceiros na Aba Mapa (`#tab-mapa`):**
   * Pílula de filtro `[ Parceiros ]` no menu superior do mapa.
   * Marcadores circulares com ícones de categoria, borda dourada/verde e selo com estrela.
   * Folder Comercial (Bottom Sheet `#modal-parceiro`) exibindo detalhes completos, ofertas da semana e botões "Chamar no WhatsApp" e "Como Chegar".
4. **Tabelas do Banco de Dados e API:**
   * Tabela `parceiros`: armazena dados corporativos, coordenadas GPS, bairro, telefone de WhatsApp e selo.
   * Tabela `parceiro_produtos`: armazena até 5 produtos/serviços promocionais por parceiro com preços de/por e tag de desconto.
   * Endpoint `GET /api/parceiros`: lista parceiros ativos com produtos aninhados e suporte a filtros por categoria e esteira.

---
**Fim da Bíblia Mestra — Alerta Urbano Cascavel v3.8.2**


---

## 9. BLINDAGEM DE COLD START DO RENDER NO APP NATIVO (v3.8.3)

### 9.1. O Problema Identificado
Em momentos de inatividade, o servidor do Render entra em modo *cold start* (sleep). Ao ser reativado pelo primeiro acesso do app, o Render retornava uma página intermediária crua em fundo preto com o texto `"APPLICATION LOADING ... INCOMING HTTP REQUEST DETECTED ... START BUILDING ON RENDER TODAY"`. No app nativo Android, essa tela preta do provedor de nuvem vazava para a visão do cidadão, violando a identidade cívica do aplicativo.

### 9.2. A Solução Arquitetural no `MainActivity.kt`
1. **Adição Obrigatória da `loadingOverlay` no Topo do `rootLayout`:**
   * A camada nativa cívica (`#009B3A` Verde & `#FED700` Amarelo Ouro) é adicionada ao `FrameLayout` raiz acima do `WebView` e do `errorOverlay`.
   * Cobre 100% da viewport desde o milissegundo zero de abertura do aplicativo.
2. **Inspeção Ativa via JavaScript (`jsCheck`):**
   * Antes de descartar a tela de abertura, o app executa verificação no DOM do WebView:
     * Se o corpo ou título contiver `"Render"`, `"APPLICATION LOADING"` ou `"INCOMING HTTP REQUEST"`, o app detecta estado de *cold start*.
     * A tela nativa Alerta Urbano permanece 100% visível, atualizando a mensagem de status: *"Sincronizando com a central de Cascavel..."*.
     * Uma rotina de verificação/recarregamento é disparada a cada 2,5 segundos.
3. **Liberação Suave Exclusiva após Inicialização Real:**
   * Somente quando elementos vitais da aplicação (`#tab-inicio`, `#tab-mapa`, `#map` ou `state`) estiverem ativos no DOM é que a splash nativa realiza um `fade-out` suave (350ms, `alpha: 0f`) e é ocultada (`View.GONE`).
   * **Garantia Absoluta:** O cidadão cascavelense NUNCA visualiza páginas pretas ou referências técnicas ao Render.

---

## 10. CALIBRAÇÃO CROMÁTICA DA PÍLULA CLIMÁTICA DA HOME (v3.8.3)

### 10.1. Regra de Cores Estrita
A pílula horizontal de alertas e condições meteorológicas (`#alert-ticker`) no topo da tela inicial segue a convenção cívica:
* **Tempo Estável / Sem Alertas Ativos:** Fundo **Branco (`#FFFFFF`)**, tipografia escura nítida (`#18181B`), borda sutil verde-cívica (`1px solid rgba(0, 155, 58, 0.35)`) e sombra suave. O fundo preto padrão foi completamente eliminado.
* **Alerta Amarelo (Atenção):** Fundo `#FED700`, texto `#000000`, borda dourada.
* **Alerta Laranja (Perigo Potencial):** Fundo `#EA580C`, texto `#FFFFFF`, borda alaranjada.
* **Alerta Vermelho (Grande Perigo):** Fundo `#DC2626`, texto `#FFFFFF`, borda vermelha intensa.

---

## 11. DESBLOQUEIO E DINÂMICA FLUIDA DAS ESTEIRAS DA HOME (v3.8.3)

### 11.1. Causa Raiz do Bloqueio das Esteiras
A função `ativarEsteiraArrastavel` desativava a animação CSS (`el.style.animation = 'none'`) e calculava a meia-largura do carrossel (`el.scrollWidth / 2`) uma única vez durante o primeiro ciclo de renderização. Como os dados e imagens carregam de forma assíncrona (ou quando a aba está oculta), `scrollWidth` resultava em `0` ou valor residual minúsculo. Com `halfWidth <= 0`, o loop JS de translação ficava travado em `translate3d(0, 0, 0)`, congelando as 3 esteiras da tela principal (Pets, Utilidade e Segurança).

### 11.2. Motor de Arrasto e Loop Fluido Recalibrado
* **Auto-Recalibração Dinâmica por Frame:** No loop `requestAnimationFrame`, a meia-largura (`halfWidth`) é recalculada continuamente assim que o layout estabiliza e as imagens carregam (`Math.abs(sc.halfWidth - hw) > 8`).
* **Detecção Inteligente de Gesto:** O manipulador de toque diferencia rolagem vertical de arrasto horizontal (`Math.abs(deltaY) > Math.abs(deltaX) * 1.4`), permitindo rolagem fluida da página sem travar o dedo do usuário.
* **Retomada Automática do Fluxo:** Após o cidadão arrastar manualmente uma esteira e soltar o dedo, o fluxo suave retoma automaticamente em 1,4 segundos (velocidade calibrada de 28 px/s).

---

## 12. PÍLULA DISCRETA DE STATUS NOS CARDS DE PETS (v3.8.3)

### 12.1. Posicionamento e Estética
* **Localização:** Posicionada **abaixo da foto**, diretamente ao lado do nome do animal no bloco de conteúdo (`pet-card-content`).
* **Design Discreto (Subtle/Clean):** Fundo neutro cinza-claro (`#F4F4F5`), borda fina (`#D4D4D8`) e texto escuro de alta legibilidade (`#18181B`). Não compete visualmente com a foto nem utiliza tons berrantes.
* **Classificações Suportadas:**
  * `DESAPARECIDO` (`.pet-status-pill.desaparecido`)
  * `ANIMAL AVISTADO` (`.pet-status-pill.avistado`)
  * `PARA ADOÇÃO` (`.pet-status-pill.adocao`)
  * `ENCONTRADO` (`.pet-status-pill.encontrado`)
* **Altura Otimizada da Foto:** Redução proporcional de `230px` para `200px` no container da imagem (`.pet-card-media`), gerando uma visualização mais compacta e ergonômica na rolagem vertical da aba Pets.

---

## 13. ESTEIRAS PADRONIZADAS DE PARCEIROS (ABA PETS & ABA PARCEIROS)

### 13.1. Especificações Técnicas Unificadas
1. **Dimensões e Estilo (Narrow & Slim):**
   * Altura compacta tipo fita comercial (`padding: 10px 12px`, cantos arredondados de `16px`, borda sutil `1px solid rgba(0,0,0,0.09)`).
   * Pílulas deslizantes elegantes com estrela dourada (`⭐`), nome da empresa e tag de benefício/oferta (ex.: `⭐ Vet 24h Cascavel [🏷️ 15% OFF]`).
2. **Posicionamento Idêntico nas Duas Abas:**
   * **Na Aba Pets (`#esteira-parceiros-box`):** Localizada logo abaixo da listagem de blocos de pets e imediatamente acima do rodapé/menu inferior.
   * **Na Aba Parceiros (`#esteira-parceiros-tab-box`):** Localizada no final da lista de parceiros, logo acima do rodapé/menu inferior.
3. **Velocidade e Interação:**
   * Ambas rodam no mesmo motor contínuo (`ativarEsteiraArrastavel`) a 24 px/s com suporte a toque/arrasto manual.
   * Clique em qualquer pílula abre o Folder Comercial Completo (`abrirFolderParceiroById(id)`).
4. **Limpeza de Filtros na Aba Parceiros:**
   * Os botões de filtro por categoria da aba Parceiros foram removidos provisoriamente, mantendo o feed limpo e direto.

---
**Fim da Bíblia Mestra — Alerta Urbano Cascavel v3.8.3**


---

## 14. MESA OPERACIONAL: COCKPIT DE PARCEIROS, FATURAMENTO E RADAR DE EXPANSÃO (v3.9.0)

### 14.1. Objetivo Estratégico (Vórtice Mídia)
A **Mesa Operacional** (`/mesa` e `/admin/mesa`) é a estação de trabalho executiva e tática projetada especificamente para o Diretor (Rigo) gerenciar a expansão territorial, o mapa de balões, o faturamento recorrente (MRR) e o preenchimento de cotas exclusivas de patrocinadores em Cascavel.

### 14.2. Módulos Operacionais Integrados
1. **Mesa Tática (Mapa Interativo de Cascavel com Balões Arrastáveis):**
   * **Bandeja de Balões por Segmento:** Menu lateral com os balões de cada nicho (Clínicas Veterinárias 🐾, Pet Shops 🐕, Banho e Tosa 🛁, Auto Centers 🚗, Borracharias 🛞, Postos de Combustível ⛽, Mecânicas de Moto 🏍️, Mecânicas de Carro 🔧 e Alimentação 🍔).
   * **Drag & Drop Direto no Mapa:** O Diretor pode arrastar qualquer balão da bandeja e soltá-lo sobre a rua/bairro desejado em Cascavel, capturando as coordenadas GPS instantaneamente e abrindo o formulário comercial.
   * **Drawer de Edição e Cadastro:** Painel lateral direito para inserir/editar Razão Social, Bairro, Endereço, WhatsApp direto, Selo (Ouro ou Cidadão), Mensalidade Contratada, Dia de Vencimento, Status de Cobrança e até 3 produtos/ofertas com cálculo automático de desconto.
2. **Painel Financeiro & Controle de Faturamento:**
   * **KPIs Executivos em Tempo Real:** MRR Estimado (Mensal Recorrente), Total Recebido no Mês, Faturas a Receber / Pendentes e Total Histórico Liquidado.
   * **Extrato e Gestão de Cobranças:** Tabela detalhada de todos os parceiros com status de pagamento dinâmico (`🟢 Pago`, `🟡 Pendente / A Vencer`, `🔴 Em Atraso`).
   * **Ações de 1 Clique:** Alternância instantânea de status financeiro e botão de cobrança via WhatsApp com mensagem executiva personalizada pré-formatada.
3. **Radar de Segmentos (Metas de 5 Parceiros por Nicho):**
   * **Regra de Exclusividade Comercial:** Cota máxima fixada em **5 patrocinadores** por segmento.
   * **Monitoramento Visual de Ocupação:** Barra de progresso percentual (`X / 5`), cálculo de receita mensal gerada por aquele segmento e receita potencial máxima com a cota cheia.
   * **Alertas Comerciais Inteligentes:**
     * `🚨 Urgente:` Destaque em vermelho para segmentos com 0 parceiros (prioridade de prospecção imediata);
     * `🟡 Atenção:` Segmentos com vagas abertas (`Faltam X patrocinadores para fechar a cota`);
     * `🟢 Cota Esgotada:` Segmentos com 5/5 parceiros preenchidos.
4. **Armazenamento e Operação:**
   * Opera de forma autônoma e segura no navegador (`localStorage` com sementes comerciais realistas de Cascavel), com acesso via `http://localhost:5000/mesa` e na nuvem `https://alerta-urbano-cascavel.onrender.com/mesa`.

---

## 15. BLINDAGEM COLD-START RENDER, GOVERNANÇA DE PÍLULAS E MESA DE INCLUSÃO DE PETS (v3.9.1)

### 15.1. Blindagem Total Contra a Tela Crua do Render
* **Causa do Problema:** Servidores na camada gratuita do Render hibernam após 15 minutos sem requisições. Ao acordar, o Render interceptava a requisição HTTP e servia diretamente sua página HTML preta interna (`APPLICATION LOADING ... INCOMING HTTP REQUEST DETECTED ...`).
* **Solução em Camada Dupla (Impenetrável):**
  1. **Service Worker (`static/sw.js`):** Intercepta requisições de navegação antes de chegarem à tela do usuário. Se a resposta contiver `APPLICATION LOADING`, `Render` ou status 502/503, o Service Worker descarta o HTML cru do Render e entrega instantaneamente a tela de boot cívica do Alerta Urbano em Verde e Amarelo, com barra de progresso animada (0% a 100%) e polling automático em `/api/ping` a cada 1.6s, recarregando a página assim que o backend estiver pronto. O usuário NUNCA mais vê a tela preta do Render.
  2. **Android WebView (`MainActivity.kt`):** A camada nativa de overlay (`loadingOverlay`) permanece 100% opaca e visível até que o JavaScript da página confirme explicitamente a presença física dos elementos DOM `#tab-inicio` ou `#tab-mapa` e o estado da aplicação. Zero vazamento de tela de carregamento externo.
  3. **Keep-Alive Server:** Adicionado endpoint ultraleve `/api/ping` e `/health` em `server.py` que responde com confirmação JSON de alta performance.

### 15.2. Governança Cromática das Pílulas (Eliminação Total do Preto)
* **Padrão Oficial de Cores:**
  * **Alerta Crítico / Máximo:** Pílula **VERMELHA** (`#DC2626`) com tipografia branca de alto contraste;
  * **Alerta Moderado / Atenção:** Pílula **LARANJA** (`#EA580C`) com tipografia branca;
  * **Sem Alerta / Clima Estável:** Pílula **BRANCA** (`#FFFFFF`) com borda e tipografia no Verde Bandeira Oficial (`#009B3A`), **JAMAIS PRETO**.
* **Correção no Dark Mode:** Eliminada regra legada que forçava `background: #27272A` em `.pet-status-pill.desaparecido`. O status "Desaparecido" agora é estritamente **VERMELHO SANGUE VIBRANTE** (`#DC2626`) em qualquer modo de tema.

### 15.3. Pílula Flutuante nos Blocos Pet (`.pet-badge-overlay`)
* **Destaque Visual nos Blocos da Aba Pets:** Cada card de animal na aba Pets agora ostenta uma pílula flutuante diretamente sobreposta à fotografia no canto superior esquerdo (`position: absolute; top: 10px; left: 10px; z-index: 10;`):
  * `🚨 DESAPARECIDO`: Fundo vermelho `#DC2626`, borda branca 1.5px, sombra 3D;
  * `🏡 PARA ADOÇÃO`: Fundo verde esmeralda `#059669`, borda branca 1.5px;
  * `👀 ANIMAL AVISTADO`: Fundo âmbar alaranjado `#D97706`, borda branca 1.5px;
  * `🎉 RESGATADO / ENCONTRADO`: Fundo verde `#10B981`, borda branca 1.5px.
* E também mantida a pílula de apoio alinhada ao nome do animal logo abaixo da mídia.

### 15.4. Mesa Operacional: Módulo "Inclusão de Pets (Pontos de GPS)"
* **Bandeja de Balões de Animais:** Permite arrastar espécies pré-configuradas (🐶 Cão Macho com gravatinha, 🐩 Cadela Fêmea com lacinho, 🐱 Gato Macho com gravatinha, 🐈 Gata Fêmea com lacinho, 🍼 Ninhada de Cãezinhos, 🐾 Ninhada de Gatinhos e 🦜 Ave Doméstica) diretamente para a rua ou esquina desejada em Cascavel.
* **Georreferenciamento Reverso:** Ao soltar o balão ou clicar na via, captura Latitude e Longitude exatas com 6 casas decimais e busca automaticamente o nome da Rua e Bairro via Nominatim.
* **Raio Tático de 450 Metros:** Desenha no mapa um círculo vermelho translúcido de 450 metros de raio ao redor do animal, indicando a zona exata de geofencing auditivo do Copiloto.
* **Galeria Dark Planner Integrada (1-Click Foto):** Conectada a `/static/darkplanner_pets/catalogo.json`, exibe miniaturas das 70 fotografias de alta qualidade geradas localmente pelo Dark Planner. Com 1 clique, o Diretor seleciona a foto desejada sem precisar fazer upload manual.
* **Simulador de Áudio do Copiloto (TTS):** Botão que reproduz por síntese de voz nativa (`window.speechSynthesis`) a frase exata que o motorista ou pedestre escutará na rua:
  * *"Atenção motorista: animal desaparecido cadastrado a 400 metros na [Rua], [Bairro]. [Espécie/Sexo] [Nome]."*
* **Inserção Direta no Banco:** Botão que executa `POST /api/alertas` e grava o registro instantaneamente no SQLite (`alertas_cascavel.db`), refletindo no aplicativo e no mapa geral em tempo real.

---

## 16. ESTRUTURA DE TESTES DE CAMPO, PERFIS FICTÍCIOS DARK PLANNER E 4 TESTADORES PILOTO (v3.9.2)

### 16.1. Blindagem Tripla Anti-Cold Start (Eliminação Definitiva da Tela do Render)
* **Camada 1: Guardião Keep-Alive 24/7 (`scratch/keep_alive_render.py`):** Processo em segundo plano que dispara um ping autenticado a cada 7 minutos em `https://alerta-urbano-cascavel.onrender.com/api/ping`. Como a inatividade do Render ocorre após 15 minutos, a instância web permanece permanentemente acordada e responde em menos de 2 segundos.
* **Camada 2: Service Worker Registrado (`static/sw.js` e `static/index.html`):** Registrado oficialmente no carregamento da página. Intercepta requisições de navegação e substitui qualquer página crua do Render (`APPLICATION LOADING` / 502 / 503) pela tela oficial cívica Verde & Amarela do Alerta Urbano com barra de progresso (0% a 100%) e polling automático.
* **Camada 3: Overlay Nativo Android (`MainActivity.kt`):** Shell Kotlin com overlay impenetrável que só revela a WebView após a renderização física dos elementos cívicos do app. Compilado no APK `v3.9.2` (versionCode 20).

### 16.2. 16 Perfis Oficiais de Pessoas (Dark Planner)
* **Geração Local em Alta Definição:** 16 retratos realistas gerados pelo Dark Planner em iluminação de estúdio e luz natural, salvos em `/static/darkplanner_pessoas/` e mapeados no `catalogo_pessoas.json`:
  * **8 Mulheres (Tutoras e Testadoras):** Mariana Souza (Centro), Camila Rocha (Coqueiral), Fernanda Lima (Parque São Paulo), Beatriz Alves (Neva), Juliana Mendes (Cancelli), Ana Paula Costa (São Cristóvão), Patrícia Ribeiro (Cascavel Velho), Larissa Duarte (Santa Cruz).
  * **8 Homens (Tutores e Testadores):** Carlos Eduardo (Centro), Lucas Martins (Centro), Roberto Silveira (São Cristóvão), Felipe Santos (Neva), Rodrigo Nogueira (Coqueiral), Marcos Vinicius (Cancelli), Diego Ferreira (Pacaembu), Gabriel Toledo (Maria Luiza).
* **Sincronização no Banco:** Todos os 16 perfis registrados na tabela `usuarios` com nome, WhatsApp válido formatado, bairro de Cascavel e URL da foto.

### 16.3. Dock dos 4 Testadores de Campo Piloto (Mesa Operacional)
* **Painel Tático Inferior:** Adicionado na aba `🐾 Inclusão de Pets (GPS)` da Mesa Operacional:
  * 1. **Lucas Martins (TESTADOR-01):** Rota Centro / Neva — `homem_02_lucas.jpg`
  * 2. **Camila Rocha (TESTADORA-02):** Rota Coqueiral / Cancelli — `mulher_02_camila.jpg`
  * 3. **Roberto Silveira (TESTADOR-03):** Rota São Cristóvão / Pacaembu — `homem_03_roberto.jpg`
  * 4. **Fernanda Lima (TESTADORA-04):** Rota Parque São Paulo / Maria Luiza — `mulher_03_fernanda.jpg`
* **Botões Táticos de Simulação:**
  * `📍 400m Copiloto:` Reposiciona o testador a 380m do pet desaparecido mais próximo, faz voo de câmera no mapa e dispara o áudio TTS do Copiloto instantaneamente.
  * `👀 Avistar:` Registra avistamento em nome do testador na via correspondente com coordenadas exatas.

### 16.4. Ciclo de Vida Completo do Pet & Limpeza de Dados
* **Limpeza e Reset:** Removidos todos os alertas de pets anteriores.
* **8 Casos de Teste Estruturados com Coordenadas Reais de Cascavel:**
  * 4 Pets Desaparecidos (`status_pet: 'desaparecido'`) — Thor (Centro), Mia (Cancelli), Pingo (Coqueiral), Tico (Centro).
  * 2 Pets Avistados com Trilha Ativa (`status_pet: 'avistado'`) — Pipoca (Neva) avistado por Lucas Martins; Fred (Coqueiral) avistado por Camila Rocha.
  * 2 Pets Encontrados e Resgatados (`status_pet: 'encontrado'`) — Bob (São Cristóvão) e Luna (Parque São Paulo), com cards comemorativos verdes.
* **Ações em 1 Clique no Mapa da Mesa:** Popups com pílula de status cromática, botão para ouvir o Copiloto, botão para marcar como Encontrado (`POST /api/pets/<id>/status`), botão para simular avistamento e botão para exclusão.

---

## 17. REFORMULAÇÃO DA MESA OPERACIONAL v3.9.4: PAINEL FINANCEIRO HORIZONTAL E HUB DE 70 PERFIS & OCORRÊNCIAS

### 17.1. Redesenho Executivo do Painel Financeiro
* **Eliminação de Colunas Verticais Esticadas:** Corrigido erro de parsing de CSS que colapsava o grid em flexbox colunar.
* **Layout Horizontal Padrão de Cockpit:**
  * Topo: 4 Cards de Métricas em Grid Horizontal (`MRR Estimado`, `Total Recebido no Mês`, `Pendente / A Receber`, `Total Histórico Acumulado`).
  * Corpo: Tabela de Extrato Geral de Parceiros & Cobranças em largura total (full-width) com filtros de status e busca rápida.

### 17.2. Nova Arquitetura de "Inclusão de Perfis" (Regra Estrita 1 Tutor : 1 Pet)
* **Princípio Cívico do Rigo:** Nenhuma pessoa real perde múltiplos animais simultaneamente. Cada ocorrência deve possuir um tutor e perfil único, simulando fielmente o comportamento dos cidadãos de Cascavel.
* **Catálogo de 70 Perfis Completos (`static/darkplanner_perfis_completos.json`):**
  * 70 Tutores distintos (nomes brasileiros realistas, telefones/WhatsApp formatados, bairros de Cascavel e avatares oficiais).
  * 70 Animais correspondentes vinculados 1:1:
    * 46 Ocorrências de Pets Desaparecidos (`tipo_ocorrencia: 'desaparecido'`).
    * 24 Ocorrências para Adoção Responsável (`tipo_ocorrencia: 'adocao'`, incluindo 10 ninhadas de cães e 10 ninhadas de gatos).
* **Bandeja Lateral Esquerda com Rolagem Suave:** Filtros rápidos `Todos (70)`, `🚨 Perdidos (46)`, `🏠 Adoção (24)` e `📍 No Mapa`. Cards com dados de contato, foto do tutor e do animal, e botão direto `📍 Lançar no Mapa`.
* **Remoção Definitiva do Dock de Testadores Fictícios:** Eliminados os 4 testadores fictícios do código. Os testes em campo são conduzidos exclusivamente pela equipe real (Rigo, André e irmão).

### 17.3. Mapa Leaflet de Perfis com Renderização Nítida e Geocodificação
* **Eliminação da Tela Preta:** Contêiner `#map-pets` corrigido com altura/largura 100% e OpenStreetMap oficial em alta resolução. Múltiplos triggers de `invalidateSize(true)` ao alternar de aba.
* **Drawer Lateral de Fixação com Geocodificação Automática:** Campo de endereço com botão `📍 Buscar` (Nominatim) e suporte a arraste e clique no mapa.
* **Marcadores Personalizados com Foto e Raio do Copiloto (450m):**
  * Bordas cromáticas: Vermelho pulsante para Desaparecidos e Azul ciano para Adoção.
  * Círculo tático tracejado de 450 metros marcando o perímetro em que o motorista no veículo ouvirá a voz do Copiloto.
  * Popup completo com link direto para simulação de WhatsApp (`https://wa.me/...`) e botão para remoção do mapa.

---
## 18. REENGENHARIA DA BOLINHA FLUTUANTE & CARD CÍVICO DE RADAR DE PETS (v3.9.5)

### 18.1. Correção Definitiva da Inversão de Gatilhos
* **Ao Tocar na Bolinha Flutuante (`toggleMiniCard`):** Abre **exclusivamente o Menu Rápido de Registro de Ocorrência na Rua** (`exibirCardMenuRegistro`), com opções para registrar `[ Animal na Pista ]`, `[ Ponto Seguro ]`, `[ Perigo na Via ]` e `[ Fechar ]`.
* **Ao Dirigir e Cruzar o Raio de 500m de um Animal Desaparecido (`dispararAlertaSonoroEVisual` / `mostrarBannerTopo`):** Abre **automaticamente o Card de Ocorrência com Foto Ampliada** (`exibirCardOcorrencia`), acompanhado da vinheta sonora e síntese de voz neural.

### 18.2. Redesenho Completo do Card de Animal Desaparecido
1. **Bloco Amarelo Ouro Cívico (`#FED700`):** Fundo amarelo sólido vibrante, cantos amplamente arredondados (`22dp`), borda preta sólida de `3dp` (`#000000`) e **ZERO margem laranja**.
2. **Moldura Dedicada ("Cardzinho") para a Foto:**
   * Container emoldurado (`FrameLayout`) com cantos arredondados (`16dp`), fundo escuro de alto contraste (`#18181B`) e borda preta sólida de `2dp`.
   * **Foto ampliada em 60%:** Altura aumentada de `125dp` para `195dp` para legibilidade instantânea no suporte do carro em trânsito.
   * **Pílula de Identificação no Topo:** Badge preta com tipografia amarela negrito `🐾 ANIMAL DESAPARECIDO`.
3. **Tipografia em Preto Sólido (`#000000`):**
   * Título principal ampliado para `18sp` negrito.
   * Subtítulo de localização e distância ampliado para `13sp` negrito (`📍 BAIRRO • A X METROS`).
4. **Botões de Ação Cívica:**
   * Linha 1: `[ Visto aqui ]` e `[ Ver no mapa ]` em botões pretos sólidos com texto branco negrito e cantos arredondados de `14dp` (altura `42dp`).
   * Linha 2: `[ Fechar aviso ]` em largura total (altura `42dp`).
5. **Erradicação Total da Margem Laranja na Bolinha:**
   * Na função `atualizarAnelZonaPet`, substituído o anel âmbar/laranja por anel preto cívico de `2dp` (`#000000`), sem interferência de cores terceiras.

---

**Fim da Bíblia Mestra — Alerta Urbano Cascavel v3.9.5**
