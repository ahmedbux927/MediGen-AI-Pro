' Starts scripts\run_server.bat with no visible window. Used by the "MediGen Server" task at log on.
Set sh = CreateObject("WScript.Shell")
batPath = Replace(WScript.ScriptFullName, "run_server_hidden.vbs", "run_server.bat")
sh.Run "cmd /c """ & batPath & """", 0, False
