!macro customHeader
  !system "echo 'Custom NSIS Header for OneToTwo'"
!macroend

!macro preInit
  ; Custom initialization
  SetRegView 64
  WriteRegExpandStr HKLM "${INSTALL_REGISTRY_KEY}" InstallLocation "$INSTDIR"
  WriteRegExpandStr HKCU "${INSTALL_REGISTRY_KEY}" InstallLocation "$INSTDIR"
  SetRegView 32
  WriteRegExpandStr HKLM "${INSTALL_REGISTRY_KEY}" InstallLocation "$INSTDIR"
  WriteRegExpandStr HKCU "${INSTALL_REGISTRY_KEY}" InstallLocation "$INSTDIR"
!macroend

!macro customInit
  ; Check if app is already running
  nsExec::ExecToStack 'tasklist /FI "IMAGENAME eq OneToTwo.exe" /NH'
  Pop $0
  Pop $1
  StrCpy $2 $1 11 -11
  StrCmp $2 "OneToTwo.exe" 0 notRunning
    MessageBox MB_OK|MB_ICONEXCLAMATION "OneToTwo is currently running. Please close it before installing." /SD IDOK
    Abort
  notRunning:
!macroend

!macro customInstall
  ; Create data directory
  CreateDirectory "$APPDATA\OneToTwo"
  CreateDirectory "$APPDATA\OneToTwo\data"
  CreateDirectory "$APPDATA\OneToTwo\logs"
  
  ; Write installation info
  FileOpen $0 "$APPDATA\OneToTwo\install.log" w
  FileWrite $0 "OneToTwo Installation Log$\r$\n"
  FileWrite $0 "Version: ${VERSION}$\r$\n"
  FileWrite $0 "Install Path: $INSTDIR$\r$\n"
  FileWrite $0 "Install Date: $\"$\"$\r$\n"
  FileClose $0
!macroend

!macro customUnInstall
  ; Ask user if they want to remove data
  MessageBox MB_YESNO|MB_ICONQUESTION "Do you want to remove all application data?$\r$\nThis includes cached data and logs." /SD IDNO IDNO keepData
    RMDir /r "$APPDATA\OneToTwo"
  keepData:
  
  ; Remove registry entries
  SetRegView 64
  DeleteRegKey HKLM "${INSTALL_REGISTRY_KEY}"
  DeleteRegKey HKCU "${INSTALL_REGISTRY_KEY}"
  SetRegView 32
  DeleteRegKey HKLM "${INSTALL_REGISTRY_KEY}"
  DeleteRegKey HKCU "${INSTALL_REGISTRY_KEY}"
!macroend

!macro customRemoveFiles
  ; Custom file removal if needed
!macroend
