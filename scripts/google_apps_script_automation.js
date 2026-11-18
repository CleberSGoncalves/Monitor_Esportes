/**
 * GOOGLE APPS SCRIPT - SINCRONIZAÇÃO EM PARALELO DE EVENTOS ESPORTIVOS
 * Espelho Oficial da Lista SharePoint: 'Suporte Captação - Programação de eventos - Streaming'
 * 
 * 11 Colunas Oficiais do SharePoint:
 * 1. Anexos
 * 2. Mês
 * 3. Data
 * 4. Horário
 * 5. Campeonato
 * 6. Partida
 * 7. Responsavel gravação
 * 8. Canal de Transmissão
 * 9. PVID TV BOX
 * 10. Status de Entrega
 * 11. Programado
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

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName("Programação de eventos - Stream") || ss.getActiveSheet();
    
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
      
      // Mapeia o Mês automaticamente pela data se não fornecido
      let mesStr = ev.mes || "";
      if (!mesStr && dataStr.includes("/")) {
        const partes = dataStr.split("/");
        if (partes.length >= 2) {
          const mIdx = parseInt(partes[1], 10) - 1;
          if (mIdx >= 0 && mIdx < 12) mesStr = meses[mIdx];
        }
      }
      
      // Mapeia PVID TV BOX sugerido pelo canal
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

function doGet(e) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName("Programação de eventos - Stream") || ss.getActiveSheet();
  const lastRow = sheet.getLastRow();
  
  if (lastRow <= 1) {
    return ContentService.createTextOutput(JSON.stringify([])).setMimeType(ContentService.MimeType.JSON);
  }
  
  const values = sheet.getRange(2, 1, lastRow - 1, 11).getValues();
  const results = values.map(r => ({
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
  
  return ContentService.createTextOutput(JSON.stringify(results)).setMimeType(ContentService.MimeType.JSON);
}
