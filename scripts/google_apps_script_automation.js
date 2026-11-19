/**
 * GOOGLE APPS SCRIPT - PORTAL WEB & SINCRONIZAÇÃO EM PARALELO
 * Lista Oficial: 'Suporte Captação - Programação de eventos - Streaming'
 * 
 * Funcionalidades:
 * 1. doGet:
 *    - Se acessado pelo navegador (URL padrão): Renderiza um Portal Web interativo,
 *      moderno, responsivo com busca instantânea, filtros por canal, data e status.
 *    - Se chamado com '?format=json' ou '?api=1': Retorna JSON puro para integrações Python.
 * 2. doPost:
 *    - Recebe novos eventos enviados pelo Monitor de Esportes em tempo real e insere com desduplicação.
 */

function formatarDataBR(val, ss) {
  if (!val) return "";
  if (val instanceof Date) {
    return Utilities.formatDate(val, ss ? ss.getSpreadsheetTimeZone() : "America/Sao_Paulo", "dd/MM/yyyy");
  }
  const s = String(val).trim();
  if (s.includes("T")) {
    const dOnly = s.split("T")[0];
    const p = dOnly.split("-");
    if (p.length === 3) return p[2] + "/" + p[1] + "/" + p[0];
  }
  return s;
}

/**
 * MENU SUPERIOR NO GOOGLE SHEETS
 * Aparece automaticamente ao abrir a planilha
 */
function onOpen() {
  try {
    SpreadsheetApp.getUi()
      .createMenu("⚡ Suporte Captação")
      .addItem("🎨 Formatar Toda a Planilha (890+ Linhas)", "formatarTodaPlanilha")
      .addItem("🛡️ Ativar Formatação Condicional Automática", "configurarFormatacaoCondicional")
      .addSeparator()
      .addItem("📢 Enviar Agenda de Transmissões para o Google Chat", "menuEnviarAgendaGoogleChat")
      .addItem("⏰ Configurar Disparo Diário Automático (09:00)", "configurarDisparoDiarioAgenda")
      .addToUi();
  } catch (e) {
    // Modo headless / sem UI
  }
}

/**
 * FORMATA 100% DA PLANILHA EM ALTA PERFORMANCE (OPERAÇÕES MATRICIAIS)
 * Aplica badges de cores idênticos ao SharePoint em todas as linhas existentes
 */
function formatarTodaPlanilha() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName("Programação de eventos - Stream") || ss.getActiveSheet();
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return 0;

  const numRows = lastRow - 1;
  const numCols = 11;
  const range = sheet.getRange(2, 1, numRows, numCols);
  const values = range.getValues();

  const backgrounds = [];
  const fontColors = [];
  const fontWeights = [];
  const alignments = [];

  for (let i = 0; i < numRows; i++) {
    const rowVal = values[i];
    const rBg = [];
    const rFont = [];
    const rWeight = [];
    const rAlign = [];

    const canalStr = String(rowVal[7] || "").toLowerCase().trim();
    const pvidStr = String(rowVal[8] || "").trim();
    const statusStr = String(rowVal[9] || "").toLowerCase().trim();
    const progStr = String(rowVal[10] || "").toLowerCase().trim();

    // Cor de fundo suave padrão da linha (Warm Beige como no SharePoint)
    const baseBg = "#FFFBEB";
    const baseText = "#0F172A";

    for (let j = 0; j < numCols; j++) {
      let cellBg = baseBg;
      let cellFont = baseText;
      let cellWeight = "normal";
      let cellAlign = "center";

      if (j === 0) { // Anexos
        cellAlign = "center";
      } else if (j === 1) { // Mês
        cellAlign = "center";
      } else if (j === 2) { // Data
        cellAlign = "center";
      } else if (j === 3) { // Horário
        cellAlign = "center";
      } else if (j === 4) { // Campeonato
        cellAlign = "left";
      } else if (j === 5) { // Partida (Verde escuro negrito)
        cellAlign = "left";
        cellFont = "#166534";
        cellWeight = "bold";
      } else if (j === 6) { // Responsavel gravação
        cellAlign = "left";
      } else if (j === 7) { // Canal de Transmissão (Badge oficial)
        cellAlign = "center";
        cellWeight = "bold";
        if (canalStr.includes("cazé") || canalStr.includes("caze")) {
          cellBg = "#DCFCE7"; cellFont = "#166534";
        } else if (canalStr.includes("prime") || canalStr.includes("amazon")) {
          cellBg = "#00509E"; cellFont = "#FFFFFF";
        } else if (canalStr.includes("netflix")) {
          cellBg = "#7F4F24"; cellFont = "#FFFFFF";
        } else if (canalStr.includes("tnt") || canalStr.includes("max") || canalStr.includes("hbo")) {
          cellBg = "#6B21A8"; cellFont = "#FFFFFF";
        } else if (canalStr.includes("dazn")) {
          cellBg = "#0F172A"; cellFont = "#F8FAFC";
        } else if (canalStr.includes("record")) {
          cellBg = "#1E40AF"; cellFont = "#FFFFFF";
        } else if (canalStr.includes("sport") || canalStr.includes("premiere")) {
          cellBg = "#1E3A8A"; cellFont = "#FFFFFF";
        } else if (canalStr.includes("disney")) {
          cellBg = "#1E293B"; cellFont = "#FFFFFF";
        } else if (canalStr.includes("paramount")) {
          cellBg = "#0284C7"; cellFont = "#FFFFFF";
        } else if (canalStr.includes("globo") || canalStr.includes("ge")) {
          cellBg = "#E11D48"; cellFont = "#FFFFFF";
        } else if (canalStr && canalStr !== "nenhuma") {
          cellBg = "#334155"; cellFont = "#FFFFFF";
        }
      } else if (j === 8) { // PVID TV BOX (Badge Verde Petróleo)
        cellAlign = "center";
        if (pvidStr) {
          cellBg = "#0D5C75"; cellFont = "#FFFFFF"; cellWeight = "bold";
        }
      } else if (j === 9) { // Status de Entrega
        cellAlign = "center";
        cellWeight = "bold";
        if (statusStr.includes("exibido") && !statusStr.includes("não") && !statusStr.includes("nao")) {
          cellBg = "#DCFCE7"; cellFont = "#166534";
        } else if (statusStr.includes("não") || statusStr.includes("nao") || statusStr.includes("cancel")) {
          cellBg = "#FEE2E2"; cellFont = "#991B1B";
        } else {
          cellBg = "#FEF3C7"; cellFont = "#92400E"; // Pendente
        }
      } else if (j === 10) { // Programado
        cellAlign = "center";
        cellWeight = "bold";
        if (progStr.includes("sim")) {
          cellBg = "#DCFCE7"; cellFont = "#166534";
        } else {
          cellBg = "#F1F5F9"; cellFont = "#475569";
        }
      }

      rBg.push(cellBg);
      rFont.push(cellFont);
      rWeight.push(cellWeight);
      rAlign.push(cellAlign);
    }

    backgrounds.push(rBg);
    fontColors.push(rFont);
    fontWeights.push(rWeight);
    alignments.push(rAlign);
  }

  // Aplica as formatações em lote único ultrarrápido
  range.setBackgrounds(backgrounds);
  range.setFontColors(fontColors);
  range.setFontWeights(fontWeights);
  range.setHorizontalAlignments(alignments);
  range.setVerticalAlignment("middle");
  range.setFontFamily("Segoe UI");
  range.setFontSize(10);
  range.setBorder(true, true, true, true, true, true, "#E2E8F0", SpreadsheetApp.BorderStyle.SOLID);

  // Altura padronizada de 24px em todas as linhas de dados
  sheet.setRowHeights(2, numRows, 24);

  // Cabeçalho Oficial
  const headRange = sheet.getRange(1, 1, 1, 11);
  headRange.setBackground("#F8FAFC");
  headRange.setFontColor("#1E293B");
  headRange.setFontWeight("bold");
  headRange.setFontFamily("Segoe UI");
  headRange.setFontSize(10);
  headRange.setVerticalAlignment("middle");
  headRange.setBorder(true, true, true, true, true, true, "#CBD5E1", SpreadsheetApp.BorderStyle.SOLID);
  sheet.setRowHeight(1, 28);
  sheet.setFrozenRows(1);

  return numRows;
}

/**
 * FORMATAÇÃO CONDICIONAL AUTOMÁTICA NATIVA
 * Garante que qualquer linha nova adicionada no futuro seja colorida automaticamente!
 */
function configurarFormatacaoCondicional() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName("Programação de eventos - Stream") || ss.getActiveSheet();
  sheet.clearConditionalFormatRules();

  const rules = [];
  const canalRange = sheet.getRange("H2:H5000");
  const pvidRange = sheet.getRange("I2:I5000");
  const statusRange = sheet.getRange("J2:J5000");
  const progRange = sheet.getRange("K2:K5000");

  // Regras de Canais
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextContains("Cazé").setBackground("#DCFCE7").setFontColor("#166534").setBold(true).setRanges([canalRange]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextContains("Prime").setBackground("#00509E").setFontColor("#FFFFFF").setBold(true).setRanges([canalRange]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextContains("Netflix").setBackground("#7F4F24").setFontColor("#FFFFFF").setBold(true).setRanges([canalRange]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextContains("TNT").setBackground("#6B21A8").setFontColor("#FFFFFF").setBold(true).setRanges([canalRange]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextContains("Max").setBackground("#6B21A8").setFontColor("#FFFFFF").setBold(true).setRanges([canalRange]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextContains("dazn").setBackground("#0F172A").setFontColor("#F8FAFC").setBold(true).setRanges([canalRange]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextContains("Record").setBackground("#1E40AF").setFontColor("#FFFFFF").setBold(true).setRanges([canalRange]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextContains("Sport").setBackground("#1E3A8A").setFontColor("#FFFFFF").setBold(true).setRanges([canalRange]).build());

  // Regra de PVID (Qualquer texto não vazio)
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenCellNotEmpty().setBackground("#0D5C75").setFontColor("#FFFFFF").setBold(true).setRanges([pvidRange]).build());

  // Regras de Status
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextContains("Exibido").setBackground("#DCFCE7").setFontColor("#166534").setBold(true).setRanges([statusRange]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextContains("Não").setBackground("#FEE2E2").setFontColor("#991B1B").setBold(true).setRanges([statusRange]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextContains("Pendente").setBackground("#FEF3C7").setFontColor("#92400E").setBold(true).setRanges([statusRange]).build());

  // Regras de Programado
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextContains("SIM").setBackground("#DCFCE7").setFontColor("#166534").setBold(true).setRanges([progRange]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextContains("NÃO").setBackground("#F1F5F9").setFontColor("#475569").setBold(true).setRanges([progRange]).build());

  sheet.setConditionalFormatRules(rules);
}

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const ss = SpreadsheetApp.getActiveSpreadsheet();

    // 1. Ação Especial: Disparo da Agenda de Streaming para o Google Chat
    if (data.action === "send_chat_agenda") {
      const resChat = enviarAgendaGoogleChat(data.webhook_url);
      return ContentService.createTextOutput(JSON.stringify(resChat))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // 2. Manipulação da Lista de Ocorrências (API REST para PowerShell / Cássio)
    if (data.resource === "ocorrencias") {
      let sheetOc = ss.getSheetByName("Painel de Ocorrências");
      if (!sheetOc) {
        sheetOc = ss.insertSheet("Painel de Ocorrências");
        sheetOc.appendRow([
          "ID", "Status", "Criado Em", "Host", "CS", "Veículo",
          "Equipamento", "Tipo de Problema", "Em Recuperação",
          "Gravação Streaming", "Informar Operação", "Ações Executadas",
          "Área Responsável", "Redmine"
        ]);
        sheetOc.getRange(1, 1, 1, 14).setBackground("#0F172A").setFontColor("#FFFFFF").setFontWeight("bold");
        sheetOc.setFrozenRows(1);
      }

      if (data.action === "insert") {
        const item = data.item || data;
        const newId = String(item.id || sheetOc.getLastRow());
        const criadoEm = item.Criado || formatarDataBR(new Date(), ss);
        sheetOc.appendRow([
          newId,
          item.Status || "Em andamento",
          criadoEm,
          item.Host || "-",
          item.CS || "01",
          item.Veiculo || "Todos",
          item.Equipamento || "ATRIA",
          item.TipoProblema || "Sem sinal",
          item.EmRecuperacao || "Não",
          item.GravacaoStreaming || "Não",
          item.InformarOperacao ? "SIM" : "NÃO",
          item.AcoesExecutadas || "-",
          item.AreaResponsavel || "N1",
          item.Redmine || ""
        ]);
        return ContentService.createTextOutput(JSON.stringify({
          status: "success",
          action: "insert",
          id: newId,
          message: "Ocorrência inserida com sucesso no Painel de Ocorrências do Google."
        })).setMimeType(ContentService.MimeType.JSON);
      }

      if (data.action === "update" && data.id) {
        const lastR = sheetOc.getLastRow();
        let updated = false;
        if (lastR > 1) {
          const ids = sheetOc.getRange(2, 1, lastR - 1, 1).getValues();
          for (let rowIdx = 0; rowIdx < ids.length; rowIdx++) {
            if (String(ids[rowIdx][0]) === String(data.id)) {
              const actualRow = rowIdx + 2;
              if (data.item.Status) sheetOc.getRange(actualRow, 2).setValue(data.item.Status);
              if (data.item.AcoesExecutadas) sheetOc.getRange(actualRow, 12).setValue(data.item.AcoesExecutadas);
              updated = true;
              break;
            }
          }
        }
        return ContentService.createTextOutput(JSON.stringify({
          status: updated ? "success" : "not_found",
          id: data.id,
          updated: updated
        })).setMimeType(ContentService.MimeType.JSON);
      }
    }

    const sheet = ss.getSheetByName("Programação de eventos - Stream") || ss.getActiveSheet();
    
    // Ação: Formatar toda a planilha imediatamente
    if (data.action === "format_all") {
      const formatadas = formatarTodaPlanilha();
      configurarFormatacaoCondicional();
      return ContentService.createTextOutput(JSON.stringify({
        status: "success",
        action: "format_all",
        linhas_formatadas: formatadas
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // Suporte para substituição completa em bloco (batch rápido)
    if (data.action === "replace_all" && Array.isArray(data.events)) {
      const lastR = sheet.getLastRow();
      if (lastR > 1) {
        sheet.getRange(2, 1, lastR - 1, 11).clearContent();
      }
      if (data.events.length > 0) {
        const rows = data.events.map(ev => [
          ev.anexos || "",
          ev.mes || "Novembro",
          ev.data || "",
          ev.horario || ev.hora || "",
          ev.campeonato || "CBF - Brasileirão Série A",
          ev.partida || "",
          ev.responsavel || "Cleber BL01 e Backup",
          ev.canal || "Amazon Prime",
          ev.pvid || "",
          ev.status || ev.status_entrega || "Pendente",
          ev.programado || "NÃO"
        ]);
        sheet.getRange(2, 1, rows.length, 11).setValues(rows);
        formatarTodaPlanilha();
        configurarFormatacaoCondicional();
      }
      return ContentService.createTextOutput(JSON.stringify({
        status: "success",
        action: "replace_all",
        total: data.events.length
      })).setMimeType(ContentService.MimeType.JSON);
    }

    const events = data.events || (Array.isArray(data) ? data : [data]);
    let inseridos = 0;
    
    // Obter dados existentes para evitar duplicatas por Partida + Data + Horário + Canal
    const lastRow = sheet.getLastRow();
    const chavesExistentes = new Set();
    if (lastRow > 1) {
      const rows = sheet.getRange(2, 1, lastRow - 1, 11).getValues();
      rows.forEach(r => {
        const dStr = formatarDataBR(r[2], ss).replace(/[^0-9]/g, '');
        const pStr = String(r[5] || "").toLowerCase().replace(/[^a-z0-9]/g, '');
        const hStr = String(r[3] || "").toLowerCase().replace(/[^a-z0-9]/g, '');
        const cStr = String(r[7] || "").toLowerCase().replace(/[^a-z0-9]/g, '');
        const k = `${pStr}_${dStr}_${hStr}_${cStr}`;
        if (k) chavesExistentes.add(k);
      });
    }
    
    const meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
    
    events.forEach(ev => {
      const partida = ev.partida || "";
      const dataStr = formatarDataBR(ev.data || "", ss);
      const horaStr = ev.hora || ev.horario || "";
      const canalStr = ev.canal || "Amazon Prime";
      
      const dClean = dataStr.replace(/[^0-9]/g, '');
      const pClean = String(partida).toLowerCase().replace(/[^a-z0-9]/g, '');
      const hClean = String(horaStr).toLowerCase().replace(/[^a-z0-9]/g, '');
      const cClean = String(canalStr).toLowerCase().replace(/[^a-z0-9]/g, '');
      const chave = `${pClean}_${dClean}_${hClean}_${cClean}`;
      
      if (chavesExistentes.has(chave)) {
        return; // Pula duplicata
      }
      
      let mesStr = ev.mes || "";
      if (!mesStr && dataStr.includes("/")) {
        const partes = dataStr.split("/");
        if (partes.length >= 2) {
          const mIdx = parseInt(partes[1], 10) - 1;
          if (mIdx >= 0 && mIdx < 12) mesStr = meses[mIdx];
        }
      }
      
      let pvidStr = ev.pvid || "";
      if (!pvidStr) {
        const cLow = canalStr.toLowerCase();
        if (cLow.includes("cazé") || cLow.includes("caze")) pvidStr = "CAZETV - PV3623";
        else if (cLow.includes("prime") || cLow.includes("amazon")) pvidStr = "Prime Video - PV3687";
        else if (cLow.includes("netflix")) pvidStr = "Netflix - PV3679";
        else if (cLow.includes("tnt") || cLow.includes("max")) pvidStr = "TNT - 316";
        else pvidStr = `${canalStr} - PVBOX`;
      }
      
      sheet.appendRow([
        "", // 1. Anexos
        mesStr || "Novembro", // 2. Mês
        dataStr, // 3. Data
        horaStr, // 4. Horário
        ev.campeonato || "CBF - Brasileirão Série A", // 5. Campeonato
        partida, // 6. Partida
        ev.responsavel || "Cleber BL01 e Backup", // 7. Responsavel gravação
        canalStr, // 8. Canal de Transmissão
        pvidStr, // 9. PVID TV BOX
        ev.status || ev.status_entrega || "Pendente", // 10. Status de Entrega
        ev.programado || "NÃO" // 11. Programado
      ]);
      
      chavesExistentes.add(chave);
      inseridos++;
    });

    // Se houve novos itens inseridos, reaplica formatação visual completa
    if (inseridos > 0) {
      formatarTodaPlanilha();
    }
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      total_processados: events.length,
      inseridos: inseridos
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * FUNÇÕES DE DISPARO DA AGENDA PARA O GOOGLE CHAT
 * Substitui o antigo fluxo do Power Automate / Teams
 */

function menuEnviarAgendaGoogleChat() {
  const ui = SpreadsheetApp.getUi();
  const props = PropertiesService.getScriptProperties();
  let webhook = props.getProperty("GOOGLE_CHAT_WEBHOOK_URL");

  if (!webhook) {
    const prompt = ui.prompt(
      "Configuração do Google Chat",
      "Cole a URL do Webhook do espaço 'Streaming - Gravações':",
      ui.ButtonSet.OK_CANCEL
    );
    if (prompt.getSelectedButton() === ui.Button.OK) {
      webhook = prompt.getResponseText().trim();
      if (webhook) {
        props.setProperty("GOOGLE_CHAT_WEBHOOK_URL", webhook);
      } else {
        ui.alert("Operação cancelada: Webhook não fornecido.");
        return;
      }
    } else {
      return;
    }
  }

  const res = enviarAgendaGoogleChat(webhook);
  if (res.status === "success") {
    ui.alert("✅ Sucesso!", "A agenda foi postada no grupo 'Streaming - Gravações' do Google Chat!\nHoje: " + res.hoje + " jogo(s)\nAmanhã: " + res.amanha + " jogo(s)", ui.ButtonSet.OK);
  } else {
    ui.alert("❌ Erro", "Falha ao disparar para o Google Chat: " + (res.body || res.message), ui.ButtonSet.OK);
  }
}

function configurarDisparoDiarioAgenda() {
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(t => {
    if (t.getHandlerFunction() === "enviarAgendaGoogleChat") {
      ScriptApp.deleteTrigger(t);
    }
  });

  ScriptApp.newTrigger("enviarAgendaGoogleChat")
    .timeBased()
    .everyDays(1)
    .atHour(9)
    .create();

  try {
    SpreadsheetApp.getUi().alert("⏰ Gatilho Ativado", "O disparo diário automático da Agenda de Transmissões foi agendado para rodar todos os dias às 09:00 no Google Chat!", SpreadsheetApp.getUi().ButtonSet.OK);
  } catch(e) {}
}

function enviarAgendaGoogleChat(webhookUrl) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName("Programação de eventos - Stream") || ss.getActiveSheet();
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) {
    return { status: "empty", message: "Nenhum evento na planilha." };
  }

  const tz = ss.getSpreadsheetTimeZone() || "America/Sao_Paulo";
  const hoje = new Date();
  const amanha = new Date(hoje.getTime() + 24 * 60 * 60 * 1000);

  const hojeStr = Utilities.formatDate(hoje, tz, "dd/MM/yyyy");
  const amanhaStr = Utilities.formatDate(amanha, tz, "dd/MM/yyyy");

  const values = sheet.getRange(2, 1, lastRow - 1, 11).getValues();
  const jogosHoje = [];
  const jogosAmanha = [];

  for (let i = 0; i < values.length; i++) {
    const row = values[i];
    const dataCell = formatarDataBR(row[2], ss);
    const ev = {
      partida: String(row[5] || "").trim(),
      horario: String(row[3] || "").trim(),
      responsavel: String(row[6] || "Marcos BL01 e Backup").trim(),
      canal: String(row[7] || "").trim(),
      pvid: String(row[8] || (row[7] ? row[7] + " - TV BOX" : "")).trim()
    };
    if (dataCell === hojeStr) {
      jogosHoje.push(ev);
    } else if (dataCell === amanhaStr) {
      jogosAmanha.push(ev);
    }
  }

  const url = webhookUrl || PropertiesService.getScriptProperties().getProperty("GOOGLE_CHAT_WEBHOOK_URL");
  if (!url) {
    return { status: "missing_webhook", message: "Webhook do Google Chat não configurado." };
  }

  const payload = montarCardAgendaGoogleChat(hojeStr, jogosHoje, amanhaStr, jogosAmanha);
  const options = {
    method: "post",
    contentType: "application/json; charset=UTF-8",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch(url, options);
  return {
    status: response.getResponseCode() === 200 ? "success" : "error",
    code: response.getResponseCode(),
    body: response.getContentText(),
    hoje: jogosHoje.length,
    amanha: jogosAmanha.length
  };
}

function montarCardAgendaGoogleChat(hojeStr, jogosHoje, amanhaStr, jogosAmanha) {
  const sections = [];

  // Seção Hoje
  const widgetsHoje = [];
  if (jogosHoje.length === 0) {
    widgetsHoje.push({
      decoratedText: {
        text: "<i>Nenhuma transmissão programada para hoje.</i>"
      }
    });
  } else {
    jogosHoje.forEach(j => {
      widgetsHoje.push({
        decoratedText: {
          topLabel: (j.horario || "--:--") + " • " + j.responsavel,
          text: "<b>" + j.partida + "</b>",
          bottomLabel: "📺 " + j.pvid,
          wrapText: true
        }
      });
    });
  }
  sections.push({
    header: "Hoje - " + hojeStr,
    widgets: widgetsHoje
  });

  // Seção Amanhã
  const widgetsAmanha = [];
  if (jogosAmanha.length === 0) {
    widgetsAmanha.push({
      decoratedText: {
        text: "<i>Nenhuma transmissão programada para amanhã.</i>"
      }
    });
  } else {
    jogosAmanha.forEach(j => {
      widgetsAmanha.push({
        decoratedText: {
          topLabel: (j.horario || "--:--") + " • " + j.responsavel,
          text: "<b>" + j.partida + "</b>",
          bottomLabel: "📺 " + j.pvid,
          wrapText: true
        }
      });
    });
  }
  sections.push({
    header: "Amanhã - " + amanhaStr,
    widgets: widgetsAmanha
  });

  return {
    cardsV2: [
      {
        cardId: "agenda-streaming-" + hojeStr.replace(/\//g, "-"),
        card: {
          header: {
            title: "Agenda de Transmissões",
            subtitle: "Programação de jogos de hoje e amanhã",
            imageUrl: "https://fonts.gstatic.com/s/i/short-term/release/googlestyles/sports_soccer/default/48px.png",
            imageType: "CIRCLE"
          },
          sections: sections
        }
      }
    ]
  };
}

function doGet(e) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // 1. Ação Especial: Disparo ou consulta da Agenda do Google Chat via GET
  if (e && e.parameter && e.parameter.action === "send_chat_agenda") {
    const resChat = enviarAgendaGoogleChat(e.parameter.webhook_url);
    return ContentService.createTextOutput(JSON.stringify(resChat)).setMimeType(ContentService.MimeType.JSON);
  }

  // 2. Consulta de Ocorrências (API REST para PowerShell / Cássio)
  if (e && e.parameter && e.parameter.resource === "ocorrencias") {
    const sheetOc = ss.getSheetByName("Painel de Ocorrências");
    if (!sheetOc || sheetOc.getLastRow() < 2) {
      return ContentService.createTextOutput(JSON.stringify([])).setMimeType(ContentService.MimeType.JSON);
    }
    const vals = sheetOc.getRange(2, 1, sheetOc.getLastRow() - 1, 14).getValues();
    let ocs = vals.map(r => ({
      id: String(r[0]),
      Status: r[1],
      Criado: r[2],
      Host: r[3],
      CS: r[4],
      Veiculo: r[5],
      Equipamento: r[6],
      TipoProblema: r[7],
      EmRecuperacao: r[8],
      GravacaoStreaming: r[9],
      InformarOperacao: r[10] === "SIM",
      AcoesExecutadas: r[11],
      AreaResponsavel: r[12],
      Redmine: r[13]
    }));

    if (e.parameter.status) {
      ocs = ocs.filter(o => String(o.Status).toLowerCase() === e.parameter.status.toLowerCase());
    }
    if (e.parameter.host) {
      ocs = ocs.filter(o => String(o.Host).toLowerCase().includes(e.parameter.host.toLowerCase()));
    }
    return ContentService.createTextOutput(JSON.stringify(ocs)).setMimeType(ContentService.MimeType.JSON);
  }

  const sheet = ss.getSheetByName("Programação de eventos - Stream") || ss.getActiveSheet();
  const lastRow = sheet.getLastRow();
  
  let results = [];
  if (lastRow > 1) {
    const values = sheet.getRange(2, 1, lastRow - 1, 11).getValues();
    results = values.map(r => ({
      anexos: r[0],
      mes: r[1],
      data: formatarDataBR(r[2], ss),
      horario: r[3],
      campeonato: r[4],
      partida: r[5],
      responsavel: r[6],
      canal: r[7],
      pvid: r[8],
      status_entrega: r[9],
      programado: r[10]
    }));
  }
  
  // Se chamado com ?format=json ou ?api=1, retorna JSON puro para o Monitor_Esportes ou PowerShell
  if (e && e.parameter && (e.parameter.format === 'json' || e.parameter.api === '1' || e.parameter.resource === 'streaming')) {
    return ContentService.createTextOutput(JSON.stringify(results)).setMimeType(ContentService.MimeType.JSON);
  }
  
  // Caso contrário, gera a Página Web Oficial interativa
  const htmlContent = renderWebPage(results);
  return HtmlService.createHtmlOutput(htmlContent)
    .setTitle("Programação de Eventos - Streaming | Suporte Captação")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function renderWebPage(events) {
  const jsonString = JSON.stringify(events);
  
  return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Programação de Eventos - Streaming</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --sp-header-bg: #F8FAFC;
      --sp-border: #E2E8F0;
      --sp-row-bg: #FFFBEB;
      --sp-text: #1E293B;
      --sp-caze-bg: #DCFCE7;
      --sp-caze-txt: #166534;
      --sp-prime-bg: #00509E;
      --sp-prime-txt: #FFFFFF;
      --sp-netflix-bg: #7F4F24;
      --sp-netflix-txt: #FFFFFF;
      --sp-tnt-bg: #6B21A8;
      --sp-tnt-txt: #FFFFFF;
      --sp-dazn-bg: #0F172A;
      --sp-dazn-txt: #F8FAFC;
      --sp-pvid-bg: #0D5C75;
      --sp-pvid-txt: #FFFFFF;
      --sp-pend-bg: #FEF3C7;
      --sp-pend-txt: #92400E;
      --sp-exib-bg: #DCFCE7;
      --sp-exib-txt: #166534;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
      background: #F1F5F9;
      color: var(--sp-text);
      padding: 16px;
    }
    .container {
      max-width: 1400px;
      margin: 0 auto;
      background: #FFFFFF;
      border-radius: 12px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.06);
      overflow: hidden;
      border: 1px solid var(--sp-border);
    }
    .header-bar {
      background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
      color: #FFFFFF;
      padding: 20px 24px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }
    .header-title h1 {
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }
    .header-title p {
      font-size: 13px;
      color: #94A3B8;
      margin-top: 4px;
    }
    .stats-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .stat-pill {
      background: rgba(255,255,255,0.1);
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .controls-bar {
      background: #FFFFFF;
      padding: 16px 24px;
      border-bottom: 1px solid var(--sp-border);
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
    }
    .search-box {
      flex: 1;
      min-width: 260px;
      position: relative;
    }
    .search-input {
      width: 100%;
      padding: 10px 16px 10px 38px;
      border-radius: 8px;
      border: 1px solid #CBD5E1;
      font-size: 14px;
      outline: none;
      transition: all 0.2s;
    }
    .search-input:focus {
      border-color: #2563EB;
      box-shadow: 0 0 0 3px rgba(37,99,235,0.15);
    }
    .search-icon {
      position: absolute;
      left: 12px;
      top: 50%;
      transform: translateY(-50%);
      color: #94A3B8;
      font-size: 15px;
    }
    .filter-group {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .filter-select {
      padding: 9px 14px;
      border-radius: 8px;
      border: 1px solid #CBD5E1;
      font-size: 13px;
      background: #FFFFFF;
      font-weight: 500;
      cursor: pointer;
      outline: none;
    }
    .btn-action {
      background: #0284C7;
      color: #FFFFFF;
      border: none;
      padding: 9px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: background 0.2s;
    }
    .btn-action:hover { background: #0369A1; }
    .table-wrapper {
      overflow-x: auto;
      max-height: 75vh;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 13px;
    }
    thead th {
      background: var(--sp-header-bg);
      color: #475569;
      font-weight: 700;
      padding: 12px 14px;
      border-bottom: 2px solid #CBD5E1;
      border-right: 1px solid var(--sp-border);
      position: sticky;
      top: 0;
      z-index: 10;
      white-space: nowrap;
    }
    tbody tr {
      background: var(--sp-row-bg);
      border-bottom: 1px solid var(--sp-border);
      transition: background 0.15s;
    }
    tbody tr:hover {
      background: #FEF3C7;
    }
    tbody td {
      padding: 10px 14px;
      border-right: 1px solid var(--sp-border);
      vertical-align: middle;
      white-space: nowrap;
    }
    .td-center { text-align: center; }
    .partida-cell {
      font-weight: 700;
      color: #166534;
      white-space: normal;
      min-width: 220px;
    }
    .badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 700;
      text-align: center;
      letter-spacing: 0.02em;
    }
    .badge-caze { background: var(--sp-caze-bg); color: var(--sp-caze-txt); }
    .badge-prime { background: var(--sp-prime-bg); color: var(--sp-prime-txt); }
    .badge-netflix { background: var(--sp-netflix-bg); color: var(--sp-netflix-txt); }
    .badge-tnt { background: var(--sp-tnt-bg); color: var(--sp-tnt-txt); }
    .badge-dazn { background: var(--sp-dazn-bg); color: var(--sp-dazn-txt); }
    .badge-record { background: #1E40AF; color: #FFFFFF; }
    .badge-sportv { background: #1E3A8A; color: #FFFFFF; }
    .badge-disney { background: #1E293B; color: #FFFFFF; }
    .badge-paramount { background: #0284C7; color: #FFFFFF; }
    .badge-globo { background: #E11D48; color: #FFFFFF; }
    .badge-default { background: #334155; color: #FFFFFF; }
    .badge-pvid { background: var(--sp-pvid-bg); color: var(--sp-pvid-txt); font-family: monospace; font-size: 11px; }
    .badge-pendente { background: var(--sp-pend-bg); color: var(--sp-pend-txt); }
    .badge-exibido { background: var(--sp-exib-bg); color: var(--sp-exib-txt); }
    .badge-nao-exibido { background: #FEE2E2; color: #991B1B; }
    .footer-bar {
      padding: 12px 24px;
      background: #F8FAFC;
      border-top: 1px solid var(--sp-border);
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: #64748B;
      flex-wrap: wrap;
      gap: 8px;
    }
    @media (max-width: 768px) {
      body { padding: 8px; }
      .header-bar { padding: 14px 16px; }
      .controls-bar { padding: 12px 16px; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header-bar">
      <div class="header-title">
        <h1>⚽ Suporte Captação - Programação de Eventos (Streaming)</h1>
        <p>Espelho Web Oficial em Tempo Real | Sincronizado com SharePoint e Monitor de Esportes</p>
      </div>
      <div class="stats-bar">
        <div class="stat-pill">Total: <span id="count-total">0</span></div>
        <div class="stat-pill" style="background:#166534;">Cazé TV: <span id="count-caze">0</span></div>
        <div class="stat-pill" style="background:#00509E;">Amazon Prime: <span id="count-prime">0</span></div>
        <div class="stat-pill" style="background:#7F4F24;">Netflix: <span id="count-netflix">0</span></div>
      </div>
    </div>
    
    <div class="controls-bar">
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="text" id="search-input" class="search-input" placeholder="Pesquisar por time, partida, campeonato, canal ou data...">
      </div>
      <div class="filter-group">
        <select id="filter-canal" class="filter-select">
          <option value="">Todos os Canais</option>
          <option value="Cazé TV">Cazé TV</option>
          <option value="Amazon Prime">Amazon Prime</option>
          <option value="Netflix">Netflix</option>
          <option value="TNT">TNT / Max</option>
          <option value="dazn">DAZN</option>
        </select>
        <select id="filter-status" class="filter-select">
          <option value="">Todos os Status</option>
          <option value="Pendente">Pendente</option>
          <option value="Exibido">Exibido</option>
          <option value="Não Exibido">Não Exibido</option>
        </select>
        <button class="btn-action" onclick="window.print()">🖨️ Imprimir</button>
      </div>
    </div>
    
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th class="td-center">#</th>
            <th class="td-center">Mês</th>
            <th class="td-center">Data</th>
            <th class="td-center">Horário</th>
            <th>Campeonato</th>
            <th>Partida</th>
            <th>Responsável Gravação</th>
            <th class="td-center">Canal de Transmissão</th>
            <th class="td-center">PVID TV BOX</th>
            <th class="td-center">Status de Entrega</th>
            <th class="td-center">Programado</th>
          </tr>
        </thead>
        <tbody id="table-body">
          <!-- Linhas renderizadas via Javascript -->
        </tbody>
      </table>
    </div>
    
    <div class="footer-bar">
      <div>Mostrando <b id="count-showing">0</b> eventos filtrados</div>
      <div>Atualização Automática Conectada via Google Apps Script & Monitor de Esportes</div>
    </div>
  </div>

  <script>
    const allEvents = ${jsonString};
    
    function getChannelBadge(canal) {
      const c = String(canal || "").toLowerCase();
      if (c.includes("cazé") || c.includes("caze")) return '<span class="badge badge-caze">' + canal + '</span>';
      if (c.includes("prime") || c.includes("amazon")) return '<span class="badge badge-prime">' + canal + '</span>';
      if (c.includes("netflix")) return '<span class="badge badge-netflix">' + canal + '</span>';
      if (c.includes("tnt") || c.includes("max") || c.includes("hbo")) return '<span class="badge badge-tnt">' + canal + '</span>';
      if (c.includes("dazn")) return '<span class="badge badge-dazn">' + canal + '</span>';
      if (c.includes("record")) return '<span class="badge badge-record">' + canal + '</span>';
      if (c.includes("sport") || c.includes("premiere")) return '<span class="badge badge-sportv">' + canal + '</span>';
      if (c.includes("disney")) return '<span class="badge badge-disney">' + canal + '</span>';
      if (c.includes("paramount")) return '<span class="badge badge-paramount">' + canal + '</span>';
      if (c.includes("globo") || c.includes("ge")) return '<span class="badge badge-globo">' + canal + '</span>';
      return '<span class="badge badge-default">' + (canal || "-") + '</span>';
    }

    function getStatusBadge(status) {
      const s = String(status || "").toLowerCase();
      if (s.includes("exibido") && !s.includes("não")) return '<span class="badge badge-exibido">' + status + '</span>';
      if (s.includes("não") || s.includes("nao") || s.includes("cancelado")) return '<span class="badge badge-nao-exibido">' + status + '</span>';
      return '<span class="badge badge-pendente">' + (status || "Pendente") + '</span>';
    }

    function renderTable() {
      const q = document.getElementById("search-input").value.toLowerCase();
      const fCanal = document.getElementById("filter-canal").value.toLowerCase();
      const fStatus = document.getElementById("filter-status").value.toLowerCase();
      
      const tbody = document.getElementById("table-body");
      tbody.innerHTML = "";
      
      let count = 0;
      let cazeCount = 0;
      let primeCount = 0;
      let netflixCount = 0;
      
      allEvents.forEach((ev, idx) => {
        const cStr = String(ev.canal || "").toLowerCase();
        if (cStr.includes("cazé") || cStr.includes("caze")) cazeCount++;
        if (cStr.includes("prime") || cStr.includes("amazon")) primeCount++;
        if (cStr.includes("netflix")) netflixCount++;
        
        // Filtros
        if (fCanal && !cStr.includes(fCanal)) return;
        if (fStatus && !String(ev.status_entrega || "").toLowerCase().includes(fStatus)) return;
        
        // Busca
        if (q) {
          const fullText = (
            ev.partida + " " + ev.campeonato + " " + ev.data + " " +
            ev.canal + " " + ev.responsavel + " " + ev.pvid
          ).toLowerCase();
          if (!fullText.includes(q)) return;
        }
        
        count++;
        const tr = document.createElement("tr");
        tr.innerHTML = \`
          <td class="td-center" style="color:#64748B; font-weight:600;">\${count}</td>
          <td class="td-center">\${ev.mes || '-'}</td>
          <td class="td-center" style="font-weight:600;">\${ev.data || '-'}</td>
          <td class="td-center">\${ev.horario || '-'}</td>
          <td>\${ev.campeonato || '-'}</td>
          <td class="partida-cell">\${ev.partida || '-'}</td>
          <td>\${ev.responsavel || '-'}</td>
          <td class="td-center">\${getChannelBadge(ev.canal)}</td>
          <td class="td-center"><span class="badge badge-pvid">\${ev.pvid || '-'}</span></td>
          <td class="td-center">\${getStatusBadge(ev.status_entrega)}</td>
          <td class="td-center">\${ev.programado || 'NÃO'}</td>
        \`;
        tbody.appendChild(tr);
      });
      
      document.getElementById("count-total").innerText = allEvents.length;
      document.getElementById("count-caze").innerText = cazeCount;
      document.getElementById("count-prime").innerText = primeCount;
      document.getElementById("count-netflix").innerText = netflixCount;
      document.getElementById("count-showing").innerText = count;
    }

    document.getElementById("search-input").addEventListener("input", renderTable);
    document.getElementById("filter-canal").addEventListener("change", renderTable);
    document.getElementById("filter-status").addEventListener("change", renderTable);

    renderTable();
  </script>
</body>
</html>`;
}
