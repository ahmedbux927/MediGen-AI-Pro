' v87.43: starts the MediGen server with no window. Used by the "MediGen Server" task (see SETUP_AUTO_START.bat).
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
logDir = dir & "\logs"
If Not fso.FolderExists(logDir) Then fso.CreateFolder(logDir)
If Not fso.FileExists(dir & "\.env") Then WScript.Quit 1
' give Windows networking and the MySQL service a moment after login
WScript.Sleep 20000
sh.CurrentDirectory = dir
sh.Run "cmd /c python app.py >> """ & logDir & "\autostart.log"" 2>&1", 0, False
