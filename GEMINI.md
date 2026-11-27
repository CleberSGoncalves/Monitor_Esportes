# DIRETRIZES DE ENGENHARIA E REGRAS DE PROJETO — MONITOR_ESPORTES

> [!IMPORTANT]
> **DIRETRIZ OBRIGATÓRIA DE TESTES E VALIDAÇÃO REAL A CADA NOVA FUNÇÃO OU CORREÇÃO**
> Sempre que entregar uma função nova, modificação arquitetural ou uma correção, o agente DEVE OBRIGATORIAMENTE testar e validar de ponta a ponta (E2E) o comportamento real antes de finalizar a resposta. NUNCA entregar código sem teste real comprovado.

---

## 1. Regra dos Relatórios de Futebol (Gemini Grounding & Playwright / Selenium)
- **Página 2 Obrigatória**: Todo e qualquer relatório de auditoria de partidas de futebol (`write_expert_report`) DEVE conter obrigatoriamente a Página 2 com o bloco:
  `CONFIRMAÇÃO DE HORÁRIOS NA TRANSMISSÃO OFICIAL & COBERTURA ESPORTIVA`
- **Validação de Transmissão**: Os horários de início e término devem ser validados em múltiplos portais e fontes oficiais:
  - Súmula Eletrônica Oficial da CBF
  - ge.globo.com (Globo Esporte)
  - Lance!
  - ESPN Brasil
  - Transmissão Oficial (CazéTV / YouTube ou Amazon Prime Video)
- **Proibição de Relatórios de 1 Página**: É terminantemente proibido entregar ou publicar no SharePoint qualquer relatório oficial sem o parecer e links de referência na Página 2.

---

## 2. Regra de Isolamento de Projetos e Decoupling
- O projeto `Monitor_Esportes` opera de forma 100% nativa e autônoma.
- É estritamente proibida qualquer dependência ou leitura de arquivos de projetos externos (ex: `Streaming_Scheduler/data.csv`).
- Toda a esteira de agendamento, súmulas e cronologia é gerida pelos próprios módulos (`CBFScheduleFetcher`, `ExpertAssistant`, `ReportGenerator`).

---

## 3. Regra de Homogeneidade e Ordenação Cronológica de Agendamentos
- A lista de agendamentos no painel lateral do Dashboard e as linhas do Modal de Agendamentos devem ser sempre 100% homogêneas e idênticas.
- Toda manipulação da fila (`_load_scheduled_games`, `_save_scheduled_games`, `_update_schedule_panel_ui`, `_open_schedule_queue_modal`) deve aplicar ordenação cronológica estrita (`_sort_games_chronologically`), garantindo que o próximo confronto a acontecer seja sempre o Jogo #1 no topo.

---

## 4. Regras Globais de Serviços e Processos Windows
- Nunca iniciar servidores web (Flask/FastAPI) ou tunnels Cloudflare manualmente via terminal em segundo plano.
- Nunca executar `taskkill /f /im cloudflared.exe` ou `taskkill /f /im chrome.exe` de forma indiscriminada.
- Sempre realizar o build do executável (`python scripts/build_exe.py`), publicar a release no GitHub e efetuar o `git push origin main` ao concluir novas versões.

---

## 5. PROTOCOLO OBRIGATÓRIO DE BUILD E PUBLICAÇÃO DE RELEASE (AUTO-UPDATER)

> [!CAUTION]
> **OBRIGATÓRIO COMPILAR E PUBLICAR RELEASE NO GITHUB A CADA ATUALIZAÇÃO DA APLICAÇÃO**
> Sempre que finalizar uma rodada de melhorias, implementar novas funcionalidades ou corrigir bugs no código da aplicação, o agente DEVE OBRIGATORIAMENTE executar este fluxo completo:
> 1. **Incrementar Versão**: Atualizar o arquivo `version.json` com a nova versão semântica e changelog explicativo (ex: `"version": "2.4.36"`).
> 2. **Compilar Executável**: Executar `python scripts/build_exe.py` para gerar o `dist/Monitor_Esportes.exe` atualizado via PyInstaller.
> 3. **Publicar Release no GitHub**: Atualizar a tag no script `scripts/publish_github_release.py` e executá-lo para fazer upload do asset `.exe` no GitHub Releases.
> 4. **Backup e Push**: Executar `git add .`, `git commit -m "..."` e `git push origin main`.
> 5. **PROIBIDO FINALIZAR SEM PUBLICAR**: O agente NUNCA pode encerrar a resposta sem que a nova versão do executável esteja disponível para download no Auto-Updater da aplicação!

---

## 🧪 DIRETRIZ OBRIGATÓRIA DE TESTES E VALIDAÇÃO REAL

> [!IMPORTANT]
> **OBRIGATORIEDADE DE TESTES E VALIDAÇÃO REAL A CADA NOVA FUNÇÃO OU CORREÇÃO**
> Sempre que desenvolver ou entregar uma função nova, modificação arquitetural ou correção de bug neste projeto, o agente DEVE OBRIGATORIAMENTE escrever e executar testes automatizados reais (unitários, integração e/ou validação de ponta a ponta E2E) comprovando o funcionamento correto antes de concluir a resposta. NUNCA entregar código baseado em suposições sem validação prática.

---

## 6. PROIBIÇÃO ABSOLUTA DE LINKS E DEPENDÊNCIA DO SHAREPOINT (ZERO DEPENDÊNCIA EXTERNA)

> [!CAUTION]
> **O SHAREPOINT SERÁ DESCONTINUADO — PROIBIÇÃO DE LINKS PARA ADGBL.SHAREPOINT.COM NO PORTAL**
> 
> O objetivo central da migração para o Google Workspace / Google Sites é a **eliminação completa e definitiva do SharePoint**.
> 
> ### Regras Rígidas de Arquitetura:
> 1. **Proibição Absoluta de Links para o SharePoint**: Em nenhuma hipótese qualquer botão ("Abrir", "Visualizar", "Baixar"), menu, tabela ou biblioteca de documentos do Google Sites (`portal_web` / `docs`) pode redirecionar o usuário para `adgbl.sharepoint.com` ou exigir autenticação Microsoft.
> 2. **Repositório Local e Google Workspace Autônomo**: Todos os documentos, planilhas (ex: `Escala_de_trabalho_2026.xlsx`, SLA Interno), relatórios em PDF, arquivos de configuração e arquivos de Acesso Remoto (.RDP) devem estar armazenados diretamente no repositório da aplicação (`portal_web/reports/`, `portal_web/acessos_rdp/`, ou servidos via data URIs/visualizadores locais).
> 3. **Sobrevivência ao Desligamento do SharePoint**: O portal e o sistema devem funcionar com 100% de autonomia e disponibilidade, mesmo que o SharePoint seja desligado permanentemente hoje.
> 4. **Acesso Remoto RDP Inovador**: O Centro de Gerenciamento RDP deve prover pesquisa por cidade/praça, filtros por país e CS (CS01, CS02, CS03, PayTV), modal interativo de conexão direta com download de arquivos .rdp pré-configurados locais, e navegação em árvore por pastas de documentos RDP diretamente no repositório.
> 5. **Operações em Massa e Governança de Exclusão (RBAC)**: Todas as listas do portal devem conter seleção por checkbox individual e Check-All no cabeçalho com botão de exclusão em massa (`Excluir Selecionados`), condicionado estritamente às permissões configuradas na aba "Permissões".

---

## 7. PROTOCOLO OBRIGATÓRIO PÓS-EDIÇÃO DO PORTAL WEB (`docs/index.html` e `portal_web/index.html`)

> [!CAUTION]
> **PROIBIDO COMMITAR OU FAZER PUSH DO PORTAL SEM VALIDAÇÃO DE SINTAXE JS + PLAYWRIGHT E2E**
> Um único erro de sintaxe JS (ex: aspas não escapadas dentro de template string) derruba o `<script>` inteiro e trava **100% dos botões** do Google Sites.
> Sempre que editar `docs/index.html` ou `portal_web/index.html`, o agente DEVE obrigatoriamente antes de qualquer `git commit` / `git push`:
> 1. Extrair todos os blocos `<script>` de **ambos** os arquivos e validar com `node -c` (`returncode == 0`).
> 2. Executar teste automatizado no **Playwright** carregando ambos os arquivos, verificando:
>    - **0 erros** de `pageerror` e `console.error` no carregamento e na interação.
>    - Cliques reais nos botões/cards da página inicial (Home), Acesso Remoto (botão RDP) e Streaming (`Excluir Selecionados` com modal in-DOM `#modal-generic-confirm-delete`).
> 3. Nunca usar `window.confirm()`, `window.alert()` ou `window.prompt()` (são bloqueados silenciosamente em iframes do Google Sites).
> 4. Garantir que `docs/index.html` e `portal_web/index.html` estejam sincronizados e validados antes do `git push origin main`.

---

## 8. REGRAS OBRIGATÓRIAS DE RELATÓRIOS, FILTROS POR COLUNA E ORDENAÇÃO CRONOLÓGICA (GOOGLE SITES)

> [!CAUTION]
> **ORDENAÇÃO CRONOLÓGICA DECRESCENTE, FILTROS POR COLUNA E EXCLUSÃO NATIVOS EM TODAS AS LISTAS**
>
> 1. **Ordenação Obrigatória por Data Mais Recente no Topo**:
>    - Em todos os visualizadores de relatórios oficiais (`Relatórios de Jogos`, `Relatório Jogos YouTube`, `Relatórios de Jogos NBA`), bibliotecas de documentos (Drives) e listas de ocorrências, a ordenação padrão DEVE OBRIGATORIAMENTE posicionar os eventos e relatórios mais recentes no topo (`Data / Hora` decrescente: `timeB - timeA`).
>    - É expressamente proibida a ordenação padrão puramente alfabética por nome de arquivo quando houver campos de data/hora disponíveis.
>
> 2. **Filtros Individuais por Coluna em Todas as Listas**:
>    - Toda tabela de relatórios ou lista corporativa DEVE dispor de uma linha dedicada de filtros (`.table-filter-row`) posicionada no `<thead>` logo abaixo dos títulos das colunas.
>    - Cada coluna deve possuir seu controle de filtro interativo (campo de texto ou dropdown `<select>` com opções como "Todos", "Sim (✓)", "Não"), atuando em tempo real simultaneamente à busca global.
>    - Deve existir botão de limpeza rápida de filtros (`🧹`) no primeiro cabeçalho.
>
> 3. **Governança de Exclusão Individual e em Lote (Modal In-DOM)**:
>    - Toda linha de relatório DEVE conter um botão individual de exclusão (`🗑️ .btn-doc-delete`).
>    - A barra de comandos DEVE conter botão de exclusão em massa (`🗑️ Excluir Selecionados`).
>    - A confirmação deve utilizar estritamente modais in-DOM (`showCustomDeleteModal` / `#modal-generic-confirm-delete`) — NUNCA utilizar `window.confirm()` (bloqueado em iframes do Google Sites).
>    - A exclusão deve persistir os IDs removidos no `localStorage` (`sp_deleted_items_<driveKey>`) sem corromper o master data original em memória, e disponibilizar link/botão para "Restaurar" os itens excluídos caso o operador deseje.
>
> 4. **Rastreamento Obrigatório de PDFs em `docs/reports/` (Anti-404)**:
>    - O arquivo `.gitignore` DEVE conter estritamente `!docs/reports/` e `!docs/reports/**`.
>    - É expressamente proibido colocar `reports/` de forma genérica no `.gitignore`, o que causaria a exclusão silenciosa dos PDFs do GitHub Pages e erro 404 ao operador.

> 5. **Ordenação Interativa e Clicável por Qualquer Coluna (`sortDriveBy`)**:
>    - Todo cabeçalho de coluna em bibliotecas de relatórios (`Relatórios de Jogos`, `Relatório Jogos YouTube`, `Relatórios de Jogos NBA`) e drives genéricos DEVE ser interativo e clicável (`th.th-sortable` com `onclick="sortDriveBy('...')"`) permitindo ordenar por qualquer coluna (Campeonato, Partida, Plataforma, Canal, Placar, Confiança, Auditado, Modificado, etc.).
>    - O primeiro clique na coluna ativa ordenação ascendente (`▲`) ou decrescente para datas (`▼`), e o clique subsequente inverte a direção.
>    - Cada coluna exibe o indicador visual da direção atual (`▲`, `▼` ou `↕`).
>    - A ordenação padrão na abertura da biblioteca permanece obrigatoriamente a mais recente decrescente (`Data / Hora` `▼`).
>
> 6. **Visualização Robusta de PDFs (Dual In-DOM Modal + Pop-up com Resolução Absoluta)**:
>    - Proibição absoluta de mocks ou arquivos corrompidos (<1KB) nas pastas oficiais (`docs/reports/`) e no `sharepoint_portal_master_data.json`.
>    - Todo clique em título de relatório ou botão 'Abrir PDF' deve invocar `openReportDocument`, que resolve a URL absoluta via `new URL(encodeURI(cleanPath), baseUrl).href` (blindagem contra falta de trailing slash em `https://.../Monitor_Esportes`).
>    - O relatório é exibido imediatamente no visualizador in-DOM `#modal-pdf-viewer` (blindagem contra bloqueadores de popups em iframes do Google Sites), com botões para 'Abrir em Nova Aba' e 'Baixar PDF', além do disparo nativo via `window.open`.
>
> 7. **Obrigatoriedade de Execução de Testes Automatizados Reais (E2E) Antes de Finalizar**:
>    - Proibição absoluta de entregas baseadas em suposições sem validação prática.
>    - Toda alteração DEVE ser comprovada pela execução de testes de sintaxe (`node -c`) e testes de ponta a ponta com Selenium Headless (`test_portal_syntax_and_e2e.py`), validando a ordenação das colunas, filtros, modal de PDF e zero erros no console do navegador.
