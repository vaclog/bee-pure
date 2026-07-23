Dim oShell, sBat
Set oShell = CreateObject("WScript.Shell")
sBat = Replace(WScript.ScriptFullName, "run_etl_ov.vbs", "run_etl_ov.bat")
oShell.Run "cmd.exe /c """ & sBat & """", 0, True
