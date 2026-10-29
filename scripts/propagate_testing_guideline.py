import os
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = r"E:\desenvolvimento"

DIRECTIVE_HEADER = "## 🧪 DIRETRIZ OBRIGATÓRIA DE TESTES E VALIDAÇÃO REAL"
DIRECTIVE_TEXT = """
## 🧪 DIRETRIZ OBRIGATÓRIA DE TESTES E VALIDAÇÃO REAL

> [!IMPORTANT]
> **OBRIGATORIEDADE DE TESTES E VALIDAÇÃO REAL A CADA NOVA FUNÇÃO OU CORREÇÃO**
> Sempre que desenvolver ou entregar uma função nova, modificação arquitetural ou correção de bug neste projeto, o agente DEVE OBRIGATORIAMENTE escrever e executar testes automatizados reais (unitários, integração e/ou validação de ponta a ponta E2E) comprovando o funcionamento correto antes de concluir a resposta. NUNCA entregar código baseado em suposições sem validação prática.
"""

# Ignorar pastas de cópias, temporárias ou desnecessárias
IGNORE_KEYWORDS = ["copia", "copy", "temp", "tmp", "node_modules", ".git", ".venv", "env", "uploads", "log"]

updated_count = 0
created_count = 0

for item in os.listdir(BASE_DIR):
    item_path = os.path.join(BASE_DIR, item)
    if not os.path.isdir(item_path):
        continue
    
    item_lower = item.lower()
    if any(k in item_lower for k in IGNORE_KEYWORDS):
        continue
    
    md_path = os.path.join(item_path, "GEMINI.md")
    
    if os.path.exists(md_path):
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
            if DIRECTIVE_HEADER not in content:
                content = content.rstrip() + "\n\n" + DIRECTIVE_TEXT.strip() + "\n"
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"[ATUALIZADO] {item}/GEMINI.md")
                updated_count += 1
            else:
                print(f"[JÁ EXISTE] {item}/GEMINI.md")
        except Exception as e:
            print(f"[ERRO] Falha ao atualizar {item}/GEMINI.md: {e}")
    else:
        try:
            title = f"# DIRETRIZES DE PROJETO — {item}\n"
            content = title + DIRECTIVE_TEXT.strip() + "\n"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[CRIADO] {item}/GEMINI.md")
            created_count += 1
        except Exception as e:
            print(f"[ERRO] Falha ao criar {item}/GEMINI.md: {e}")

print(f"\nResumo: {created_count} arquivos criados, {updated_count} atualizados.")
