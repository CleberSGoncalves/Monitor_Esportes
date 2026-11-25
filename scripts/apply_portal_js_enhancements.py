import os, re

build_script = r"E:\desenvolvimento\Monitor_Esportes\scripts\build_portal_web.py"
with open(build_script, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update formatCellContent in build_portal_web.py
old_format_anchor = """      if (/^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}/.test(s)) {
        return formatDate(s);
      }"""

new_format_block = """      // Auditoria e Confirmação de Jogos / Relatórios
      if (colName === 'Auditado') {
        if (val === true || String(val).toLowerCase() === 'true' || String(val) === 'Sim') {
          return '<span style="color: #10B981; font-weight: 700; font-size: 15px;" title="Auditado com Sucesso">✓</span>';
        }
        return '<span style="color: #94A3B8; font-size: 12px;">-</span>';
      }

      if (colName === 'Confianca' || colName === 'Confiança' || colName === 'Placar') {
        const sConf = String(val).trim();
        if (sConf === 'Agendado') {
          return '<span style="background: #F1F5F9; color: #475569; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 11px;">Agendado</span>';
        }
        return `<span style="background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; padding: 2px 8px; border-radius: 12px; font-weight: 700; font-size: 11px;">${sConf}</span>`;
      }

      if (colName === 'Campeonato') {
        const sCamp = String(val).trim();
        let bg = "#EFF6FF", color = "#1D4ED8", border = "#BFDBFE";
        if (sCamp.toLowerCase().includes("copa")) { bg = "#FEF3C7"; color = "#B45309"; border = "#FDE68A"; }
        else if (sCamp.toLowerCase().includes("nba")) { bg = "#FAF5FF"; color = "#7E22CE"; border = "#E9D5FF"; }
        return `<span style="background: ${bg}; color: ${color}; border: 1px solid ${border}; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 11px;">${sCamp}</span>`;
      }

      if (colName === 'Plataforma' || colName === 'Canal') {
        const sPlat = String(val).trim();
        let bg = "#F8FAFC", color = "#334155", border = "#E2E8F0";
        if (sPlat.toLowerCase().includes("prime")) { bg = "#EFF6FF"; color = "#00509E"; border = "#BFDBFE"; }
        else if (sPlat.toLowerCase().includes("caze") || sPlat.toLowerCase().includes("cazé")) { bg = "#ECFDF5"; color = "#059669"; border = "#A7F3D0"; }
        else if (sPlat.toLowerCase().includes("youtube")) { bg = "#FEF2F2"; color = "#DC2626"; border = "#FECACA"; }
        return `<span style="background: ${bg}; color: ${color}; border: 1px solid ${border}; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 11px;">${sPlat}</span>`;
      }

      if ((colName === 'Title' || colName === 'FileLeafRef' || colName === 'Arquivo / Relatório PDF') && String(val).toLowerCase().endsWith('.pdf')) {
        return `<span class="sp-pdf-pill" onclick="event.stopPropagation(); openReportPdf('${val}')" title="Clique duplo na linha ou clique aqui para abrir o PDF" style="display: inline-flex; align-items: center; gap: 4px; color: #DC2626; background: #FEF2F2; border: 1px solid #FECACA; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 11px; cursor: pointer;">📄 ${val}</span>`;
      }

      if (/^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}/.test(s)) {
        return formatDate(s);
      }"""

if old_format_anchor in code:
    code = code.replace(old_format_anchor, new_format_block, 1)
    print("Updated formatCellContent in build_portal_web.py")

# 2. Update openRealList thead for checkbox
old_thead_anchor = """      if (thead) {
        if (!listData || !listData.columns || listData.columns.length === 0) {
          thead.innerHTML = '<tr><th>Registro</th></tr>';
        } else {
          thead.innerHTML = '<tr><th class="td-center" style="width: 45px;">#</th>' + listData.columns.map(col =>
            `<th class="th-sortable" onclick="sortGenericList('${col.name}')" title="Clique para ordenar por ${col.displayName || col.name}">${col.displayName || col.name} <span id="sort-gen-${col.name}" class="sort-icon">↕</span></th>`
          ).join('') + '</tr>';
        }
      }"""

new_thead_block = """      if (thead) {
        if (!listData || !listData.columns || listData.columns.length === 0) {
          thead.innerHTML = '<tr><th>Registro</th></tr>';
        } else {
          thead.innerHTML = '<tr><th class="td-center" style="width: 36px;"><input type="checkbox" id="checkall-generic" onchange="toggleCheckAllGeneric(this.checked)" title="Selecionar todos os registros"></th><th class="td-center" style="width: 45px;">#</th>' + listData.columns.map(col =>
            `<th class="th-sortable" onclick="sortGenericList('${col.name}')" title="Clique para ordenar por ${col.displayName || col.name}">${col.displayName || col.name} <span id="sort-gen-${col.name}" class="sort-icon">↕</span></th>`
          ).join('') + '</tr>';
        }
      }"""

if old_thead_anchor in code:
    code = code.replace(old_thead_anchor, new_thead_block, 1)
    print("Updated openRealList thead with checkall checkbox")

# 3. Update filterRealListTable row rendering with checkbox and ondblclick
old_tr_anchor = """            const trClick = isGenericListGridEditMode ? "" : `onclick="openEditListItemModal(${origIdx})" style="cursor: pointer;" title="Clique para ver detalhes e editar este registro"`; return `<tr ${trClick} class="sp-list-row-clickable"><td class="td-center" style="color: #64748B;">${idx + 1}</td>${cells}</tr>`;"""

new_tr_block = """            const trClick = isGenericListGridEditMode ? "" : `onclick="openEditListItemModal(${origIdx})" ondblclick="handleRowDblClick(${origIdx})" style="cursor: pointer;" title="Clique para ver detalhes / Clique duplo para abrir relatório PDF se disponível"`;
            return `<tr ${trClick} class="sp-list-row-clickable">
              <td class="td-center" style="width: 36px;" onclick="event.stopPropagation();"><input type="checkbox" class="check-item-generic" data-orig-idx="${origIdx}" onchange="updateGenericSelectionUI()"></td>
              <td class="td-center" style="color: #64748B;">${idx + 1}</td>
              ${cells}
            </tr>`;"""

if old_tr_anchor in code:
    code = code.replace(old_tr_anchor, new_tr_block, 1)
    print("Updated filterRealListTable row template with checkbox and ondblclick")

# 4. Injetar funções globais de exclusão em lote e visualizador PDF
funcs_to_inject = """
    // ==========================================
    // FUNÇÕES DE EXCLUSÃO EM LOTE E SELEÇÃO GENÉRICA
    // ==========================================
    function toggleCheckAllGeneric(isChecked) {
      const cbs = document.querySelectorAll('.check-item-generic');
      cbs.forEach(cb => { cb.checked = isChecked; });
      updateGenericSelectionUI();
    }

    function updateGenericSelectionUI() {
      const cbs = document.querySelectorAll('.check-item-generic:checked');
      const btnDel = document.getElementById('btn-delete-generic');
      const countEl = document.getElementById('delete-count-generic');
      const canDelete = (currentRole && (currentRole.startsWith('admin') || currentRole === 'operador'));
      if (countEl) countEl.innerText = cbs.length;
      if (btnDel) {
        if (cbs.length > 0 && canDelete) {
          btnDel.style.display = 'inline-flex';
        } else {
          btnDel.style.display = 'none';
        }
      }
    }

    function deleteSelectedGenericItems() {
      const canDelete = (currentRole && (currentRole.startsWith('admin') || currentRole === 'operador'));
      if (!canDelete) {
        showToast("Permissão negada: apenas Operadores e Administradores podem excluir registros.", "error");
        return;
      }
      const checked = Array.from(document.querySelectorAll('.check-item-generic:checked'));
      if (checked.length === 0) {
        showToast("Nenhum item selecionado para exclusão.", "warning");
        return;
      }
      if (!confirm(`Deseja realmente excluir ${checked.length} item(ns) selecionado(s) desta lista?`)) {
        return;
      }
      const listData = SP_MASTER_DATA.lists && SP_MASTER_DATA.lists[currentRealListName];
      if (!listData || !listData.items) return;

      const origIndices = checked.map(cb => parseInt(cb.getAttribute('data-orig-idx'), 10)).sort((a, b) => b - a);
      origIndices.forEach(idx => {
        if (idx >= 0 && idx < listData.items.length) {
          listData.items.splice(idx, 1);
        }
      });

      // Salvar lista personalizada no localStorage
      try {
        localStorage.setItem('sp_custom_list_deleted_' + currentRealListName, JSON.stringify(listData.items));
      } catch (e) {
        console.warn("Erro ao salvar lista após exclusão:", e);
      }

      showToast(`${checked.length} item(ns) excluído(s) com sucesso!`, "success");
      const checkall = document.getElementById('checkall-generic');
      if (checkall) checkall.checked = false;
      updateGenericSelectionUI();
      filterRealListTable();
    }

    // ==========================================
    // VISUALIZADOR OFICIAL DE RELATÓRIOS PDF (DOIS CLIQUES)
    // ==========================================
    function handleRowDblClick(origIdx) {
      const listData = SP_MASTER_DATA.lists && SP_MASTER_DATA.lists[currentRealListName];
      if (!listData || !listData.items) return;
      const it = listData.items[origIdx];
      if (!it) return;
      const pdfTarget = it.pdfUrl || it.FileLeafRef || it.Title || '';
      if (String(pdfTarget).toLowerCase().endsWith('.pdf') || it.ContentType === 'Documento') {
        openReportPdf(pdfTarget);
      } else {
        openEditListItemModal(origIdx);
      }
    }

    function openReportPdf(filenameOrUrl) {
      if (!filenameOrUrl) return;
      let targetUrl = filenameOrUrl;
      if (!targetUrl.startsWith('http') && !targetUrl.startsWith('/') && !targetUrl.startsWith('reports/')) {
        let category = "futebol";
        if (currentRealListName && currentRealListName.toLowerCase().includes("nba")) category = "nba";
        else if (currentRealListName && currentRealListName.toLowerCase().includes("youtube")) category = "youtube";
        targetUrl = `reports/${category}/${filenameOrUrl}`;
      }
      const modal = document.getElementById("modal-pdf-viewer");
      const frame = document.getElementById("pdf-viewer-frame");
      const title = document.getElementById("pdf-viewer-title");
      const dl = document.getElementById("pdf-viewer-download");
      if (modal && frame) {
        if (title) title.innerText = "Relatório Oficial: " + filenameOrUrl.split("/").pop();
        if (dl) dl.href = targetUrl;
        frame.src = targetUrl;
        modal.style.display = "flex";
      } else {
        window.open(targetUrl, "_blank");
      }
    }

    function closePdfModal() {
      const modal = document.getElementById("modal-pdf-viewer");
      const frame = document.getElementById("pdf-viewer-frame");
      if (modal) modal.style.display = "none";
      if (frame) frame.src = "";
    }

    // Expor no objeto window para acessibilidade global
    window.toggleCheckAllGeneric = toggleCheckAllGeneric;
    window.updateGenericSelectionUI = updateGenericSelectionUI;
    window.deleteSelectedGenericItems = deleteSelectedGenericItems;
    window.handleRowDblClick = handleRowDblClick;
    window.openReportPdf = openReportPdf;
    window.closePdfModal = closePdfModal;
"""

if "function toggleCheckAllGeneric" not in code:
    code = code.replace("function toggleGenericListGridEdit()", funcs_to_inject + "\n    function toggleGenericListGridEdit()")
    print("Injected batch delete & PDF modal functions")

# 5. Atualizar renderTable() com ordenação decrescente por data padrão e cálculo Hoje/Amanhã
old_rtable_start = """    function renderTable() {
      initStreamingFilters();"""

new_rtable_start = """    function renderTable() {
      initStreamingFilters();
      // Ordenação padrão decrescente por data para os mais recentes no topo
      if (!streamSortCol) {
        streamSortCol = 'data';
        streamSortAsc = false;
      }"""

if old_rtable_start in code:
    code = code.replace(old_rtable_start, new_rtable_start, 1)
    print("Updated renderTable() with default date descending sort")

# Injetar o preenchimento dos cards Hoje e Amanhã em renderTable()
today_tomorrow_js = """
      // ==========================================
      // ATUALIZAR QUADROS DE DESTAQUE: HOJE E AMANHÃ
      // ==========================================
      try {
        const todayObj = new Date();
        const pad2 = n => String(n).padStart(2, '0');
        const hojeD = pad2(todayObj.getDate());
        const hojeM = pad2(todayObj.getMonth() + 1);
        const hojeY = todayObj.getFullYear();
        const hojeStr1 = `${hojeD}/${hojeM}/${hojeY}`;
        const hojeStr2 = `${hojeY}-${hojeM}-${hojeD}`;

        const tomObj = new Date(todayObj.getTime() + 86400000);
        const tomD = pad2(tomObj.getDate());
        const tomM = pad2(tomObj.getMonth() + 1);
        const tomY = tomObj.getFullYear();
        const tomStr1 = `${tomD}/${tomM}/${tomY}`;
        const tomStr2 = `${tomY}-${tomM}-${tomD}`;

        const elHojeLbl = document.getElementById("label-data-hoje");
        const elTomLbl = document.getElementById("label-data-amanha");
        if (elHojeLbl) elHojeLbl.innerText = hojeStr1;
        if (elTomLbl) elTomLbl.innerText = tomStr1;

        const eventosHoje = allEvents.filter(ev => {
          const d = String(ev.data || "").trim();
          return d.includes(hojeStr1) || d.includes(hojeStr2);
        });

        const eventosAmanha = allEvents.filter(ev => {
          const d = String(ev.data || "").trim();
          return d.includes(tomStr1) || d.includes(tomStr2);
        });

        const bHoje = document.getElementById("badge-count-hoje");
        const bAmanha = document.getElementById("badge-count-amanha");
        if (bHoje) bHoje.innerText = `${eventosHoje.length} jogo(s)`;
        if (bAmanha) bAmanha.innerText = `${eventosAmanha.length} jogo(s)`;

        const listHoje = document.getElementById("list-eventos-hoje");
        const listAmanha = document.getElementById("list-eventos-amanha");

        const renderMiniCard = (ev) => {
          const canalBadge = String(ev.canal || "").includes("Cazé") ? "background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0;" :
            (String(ev.canal || "").includes("Prime") ? "background: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE;" :
            "background: #F8FAFC; color: #475569; border: 1px solid #E2E8F0;");
          return `<div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; font-size: 12px;">
            <div style="display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1;">
              <span style="font-weight: 700; color: #0F172A; font-family: monospace; font-size: 11px; background: #E2E8F0; padding: 2px 6px; border-radius: 4px;">${ev.horario || '--:--'}</span>
              <div style="min-width: 0; flex: 1; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
                <span style="font-weight: 600; color: #1E293B;">${ev.partida || ''}</span>
                <span style="color: #64748B; font-size: 11px; margin-left: 6px;">(${ev.campeonato || ''})</span>
              </div>
            </div>
            <div style="display: flex; align-items: center; gap: 6px; margin-left: 8px;">
              <span style="font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 12px; ${canalBadge}">${ev.canal || 'Streaming'}</span>
            </div>
          </div>`;
        };

        if (listHoje) {
          if (eventosHoje.length === 0) {
            listHoje.innerHTML = '<div style="color: #94A3B8; font-size: 12px; text-align: center; padding: 12px;">Nenhum confronto agendado para hoje na base oficial.</div>';
          } else {
            listHoje.innerHTML = eventosHoje.map(renderMiniCard).join("");
          }
        }

        if (listAmanha) {
          if (eventosAmanha.length === 0) {
            listAmanha.innerHTML = '<div style="color: #94A3B8; font-size: 12px; text-align: center; padding: 12px;">Nenhum confronto agendado para amanhã na base oficial.</div>';
          } else {
            listAmanha.innerHTML = eventosAmanha.map(renderMiniCard).join("");
          }
        }
      } catch (e_tt) {
        console.warn("Erro ao atualizar destaques hoje/amanhã:", e_tt);
      }
"""

if "ATUALIZAR QUADROS DE DESTAQUE: HOJE E AMANHÃ" not in code:
    code = code.replace("if (totalEl) totalEl.innerText = count;", "if (totalEl) totalEl.innerText = count;\n" + today_tomorrow_js)
    print("Injected today/tomorrow calculation into renderTable()")

with open(build_script, "w", encoding="utf-8") as f:
    f.write(code)

print("Step 2 complete: JavaScript logic updated in build_portal_web.py")
