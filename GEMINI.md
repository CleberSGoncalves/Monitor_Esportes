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

## 🧪 DIRETRIZ OBRIGATÓRIA DE TESTES E VALIDAÇÃO REAL

> [!IMPORTANT]
> **OBRIGATORIEDADE DE TESTES E VALIDAÇÃO REAL A CADA NOVA FUNÇÃO OU CORREÇÃO**
> Sempre que desenvolver ou entregar uma função nova, modificação arquitetural ou correção de bug neste projeto, o agente DEVE OBRIGATORIAMENTE escrever e executar testes automatizados reais (unitários, integração e/ou validação de ponta a ponta E2E) comprovando o funcionamento correto antes de concluir a resposta. NUNCA entregar código baseado em suposições sem validação prática.
