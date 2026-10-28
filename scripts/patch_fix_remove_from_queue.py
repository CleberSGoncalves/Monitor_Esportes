import os

path = os.path.join("modules", "live_channel_monitor.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Adicionar o método remove_from_queue
target_method = "    def clean_queue_keep_active(self) -> int:"
method_code = '''    def remove_from_queue(self, vid: str) -> bool:
        """Remove explicitamente um evento da fila de monitoramento e análise."""
        with self.lock:
            ev = self.state["events"].get(vid)
            if ev:
                ev["selected"] = False
                ev["user_unselected"] = True
                ev["auto_queued"] = False
            if "active_queue" in self.state and vid in self.state["active_queue"]:
                self.state["active_queue"].remove(vid)
            self._changed()
            return True

    def clean_queue_keep_active(self) -> int:'''

if "def remove_from_queue" not in content:
    assert target_method in content, "Target clean_queue_keep_active não encontrado"
    content = content.replace(target_method, method_code, 1)

# 2. Blindar a chamada da linha 685 com try/except
target_call = "            self.remove_from_queue(vid)"
safe_call = '''            try:
                self.remove_from_queue(vid)
            except Exception as ex_rm:
                self.log(f"⚠️ Aviso ao remover da fila: {ex_rm}")'''

if target_call in content:
    content = content.replace(target_call, safe_call, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("live_channel_monitor.py corrigido com sucesso!")
