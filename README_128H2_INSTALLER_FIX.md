# 128H2 Installer Fix

This package fixes the PowerShell parser error caused by Vietnamese text encoding
inside `install_128h_extension.ps1`.

Run:

```powershell
cd D:\Projects\STT-AI-Editor
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install_128h_extension.ps1
```

Then close Premiere completely and reopen it.

Open:

```text
Window > Extensions (Legacy) > STT Audio Bridge
```
