# Agendador de Tarefas - Azure DevOps Auto Sync
# Executa o script Python em intervalos regulares

param(
    [ValidateSet("Install", "Uninstall", "Run")]
    [string]$Action = "Run",
    
    [ValidateSet("Hourly", "Daily", "Weekly")]
    [string]$Frequency = "Daily",
    
    [int]$Hour = 9  # Horário padrão: 9:00 AM
)

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonScript = Join-Path $ScriptPath "main.py"
$TaskName = "AzureDevOpsAutoSync"
$TaskDescription = "Sincroniza User Stories do Azure DevOps para Specs em MD"
$LogPath = Join-Path $ScriptPath "logs\scheduler.log"

# Garantir que a pasta logs existe
$LogFolder = Split-Path -Parent $LogPath
if (-not (Test-Path $LogFolder)) {
    New-Item -ItemType Directory -Path $LogFolder -Force | Out-Null
}

function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$Timestamp - $Message" | Add-Content -Path $LogPath -Encoding UTF8
    Write-Host $Message
}

function Install-Task {
    Write-Host "[INFO] Instalando tarefa agendada..."
    
    # Obter caminho do Python
    $PythonPath = (Get-Command python).Source
    if (-not $PythonPath) {
        Write-Host "[ERRO] Python nao encontrado. Instale Python e adicione ao PATH"
        return
    }
    
    # Preparar trigger baseado na frequência
    switch ($Frequency) {
        "Hourly" {
            $Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
        }
        "Daily" {
            $Trigger = New-ScheduledTaskTrigger -Daily -At "$($Hour):00"
        }
        "Weekly" {
            $Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "$($Hour):00"
        }
    }
    
    # Acao
    $TaskAction = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$PythonScript`""
    
    # Configuracoes
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    
    # Registrar tarefa
    $Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest
    
    Register-ScheduledTask -TaskName $TaskName -Trigger $Trigger -Action $TaskAction -Settings $Settings -Principal $Principal -Description $TaskDescription -Force
    
    Write-Log "[OK] Tarefa agendada instalada: $TaskName"
    Write-Host "[OK] A tarefa sera executada $Frequency as $($Hour):00"
}

function Uninstall-Task {
    Write-Host "[INFO] Removendo tarefa agendada..."
    
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
        Write-Log "[OK] Tarefa $TaskName removida com sucesso"
        Write-Host "[OK] Tarefa removida"
    }
    catch {
        Write-Log "[ERRO] Erro ao remover tarefa: $_"
        Write-Host "[ERRO] Erro ao remover tarefa: $_"
    }
}

function Run-Sync {
    Write-Host "[INFO] Executando sincronizacao..."
    Write-Log "=== EXECUCAO MANUAL INICIADA ==="
    
    $PythonPath = (Get-Command python).Source
    if (-not $PythonPath) {
        Write-Host "[ERRO] Python nao encontrado"
        return
    }
    
    try {
        & $PythonPath $PythonScript
        Write-Log "[OK] Sincronizacao concluida"
        Write-Host "[OK] Sincronizacao concluida"
    }
    catch {
        Write-Log "[ERRO] Erro na execucao: $_"
        Write-Host "[ERRO] $_"
    }
}

# Executar ação
switch ($Action) {
    "Install" { Install-Task }
    "Uninstall" { Uninstall-Task }
    "Run" { Run-Sync }
}
