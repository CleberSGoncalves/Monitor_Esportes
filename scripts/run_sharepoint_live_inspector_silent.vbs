Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "E:\desenvolvimento\Monitor_Esportes"
WshShell.Run """C:\Python312\pythonw.exe"" ""E:\desenvolvimento\Monitor_Esportes\scripts\run_sharepoint_live_inspector.py"" --once", 0, False
Set WshShell = Nothing
