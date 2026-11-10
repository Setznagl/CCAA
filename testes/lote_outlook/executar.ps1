[CmdletBinding()]
param(
    [ValidateSet('Rascunhos', 'Enviar', 'Teste')][string]$Modo,
    [string]$EmailTeste
)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

function Assert-Fields($Object, [string[]]$Names) {
    $actual = @($Object.PSObject.Properties.Name)
    if (@(Compare-Object $actual $Names).Count -ne 0) { throw 'Campos inesperados ou ausentes no JSON.' }
}
function Assert-Text($Value, [bool]$AllowEmpty = $true) {
    if ($Value -isnot [string] -or $Value -match '[\x00-\x1f\x7f]' -or (!$AllowEmpty -and $Value.Length -eq 0)) {
        throw 'Texto inválido ou controle de cabeçalho no lote.'
    }
}
function Assert-Emails($Value, [bool]$Required = $false, [bool]$Single = $false) {
    Assert-Text $Value (!$Required)
    if ($Value -eq '') { return }
    $parts = @($Value.Split(';'))
    if ($Single -and $parts.Count -ne 1) { throw 'Informe um único e-mail.' }
    foreach ($email in $parts) {
        if ($email -notmatch '^[A-Za-z0-9.!#$%&''*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+$' -or $email.Length -gt 254) {
            throw 'E-mail inválido: use endereços simples separados por ponto e vírgula, sem espaços.'
        }
        $parsed = New-Object Net.Mail.MailAddress($email)
        if ($parsed.Address -cne $email) { throw 'Endereço não canônico.' }
    }
}
function Read-Lote([string]$Directory) {
    $strictUtf8 = New-Object Text.UTF8Encoding($false, $true)
    $manifestPath = Join-Path $Directory 'lote.json'
    $htmlPath = Join-Path $Directory 'mensagem.html'
    $m = [IO.File]::ReadAllText($manifestPath, $strictUtf8) | ConvertFrom-Json
    Assert-Fields $m @('version','batch_id','html_sha256','remetente','rows')
    if (($m.version -isnot [int] -and $m.version -isnot [long]) -or $m.version -ne 1) { throw 'Versão do lote não suportada.' }
    foreach ($h in @($m.batch_id, $m.html_sha256)) {
        if ($h -isnot [string] -or $h -cnotmatch '^[0-9a-f]{64}$') { throw 'Hash inválido.' }
    }
    Assert-Emails $m.remetente $false $true
    if ($m.rows -isnot [array] -or $m.rows.Count -lt 1 -or $m.rows.Count -gt 500) { throw 'O lote deve conter de 1 a 500 linhas.' }
    $ids = @{}
    foreach ($row in $m.rows) {
        Assert-Fields $row @('id','para','cc','cco','assunto')
        if ($row.id -isnot [string] -or $row.id -cnotmatch '^[0-9a-f]{64}$' -or $ids.ContainsKey($row.id)) { throw 'ID inválido ou repetido.' }
        $ids[$row.id] = $true
        Assert-Emails $row.para $true
        Assert-Emails $row.cc
        Assert-Emails $row.cco
        Assert-Text $row.assunto $false
        if ($row.assunto.Length -gt 998) { throw 'Assunto excessivamente longo.' }
    }
    $bytes = [IO.File]::ReadAllBytes($htmlPath)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $hash = ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant() } finally { $sha.Dispose() }
    if ($hash -cne $m.html_sha256) { throw 'O HTML foi alterado. Gere novamente o pacote aprovado.' }
    $html = $strictUtf8.GetString($bytes).TrimStart([char]0xfeff)
    if ([string]::IsNullOrWhiteSpace($html)) { throw 'HTML vazio.' }
    return [pscustomobject]@{ Manifest=$m; Html=$html }
}

function Get-TextHash([string]$Text) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text)))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
function Write-State($State, [string]$Path) {
    $temp = $Path + '.' + [Guid]::NewGuid().ToString('N') + '.tmp'
    $bytes = [Text.Encoding]::UTF8.GetBytes(($State | ConvertTo-Json -Depth 12))
    try {
        $stream = New-Object IO.FileStream($temp, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try { $stream.Write($bytes, 0, $bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
        if ([IO.File]::Exists($Path)) { [IO.File]::Replace($temp, $Path, [NullString]::Value) }
        else { [IO.File]::Move($temp, $Path) }
    } finally { if ([IO.File]::Exists($temp)) { [IO.File]::Delete($temp) } }
}
function Read-State([string]$Path, $Manifest, [string]$Fingerprint) {
    $s = @{ version=1; batch_id=$Manifest.batch_id; manifest_sha256=$Fingerprint; account=''; rows=@{} }
    if (![IO.File]::Exists($Path)) { return $s }
    try {
        $saved = [IO.File]::ReadAllText($Path, [Text.Encoding]::UTF8) | ConvertFrom-Json
        Assert-Fields $saved @('version','batch_id','manifest_sha256','account','rows')
        if ($saved.version -ne 1 -or $saved.batch_id -cne $Manifest.batch_id -or $saved.manifest_sha256 -cne $Fingerprint) { throw 'Lote diferente do estado local.' }
        Assert-Emails $saved.account $true $true
        $s.account = $saved.account
        $validIds = @{}
        foreach ($row in $Manifest.rows) { $validIds[$row.id] = $true }
        if ($saved.rows -isnot [pscustomobject]) { throw 'Estado sem mapa de linhas.' }
        foreach ($property in $saved.rows.PSObject.Properties) {
            $id = $property.Name
            $item = $property.Value
            if (!$validIds.ContainsKey($id) -and $id -cnotmatch '^test-[0-9a-f]{64}$') { throw 'ID desconhecido no estado.' }
            Assert-Fields $item @('status','entry_id','store_id')
            Assert-Text $item.entry_id
            Assert-Text $item.store_id
            if ($item.status -notin @('Draft','Submitted')) { throw 'Operação interrompida, com erro ou resultado incerto.' }
            if ($item.status -eq 'Draft' -and (!$item.entry_id -or !$item.store_id -or $id.StartsWith('test-'))) { throw 'Identidade de rascunho inválida.' }
            $s.rows[$id] = @{ status=$item.status; entry_id=$item.entry_id; store_id=$item.store_id }
        }
    } catch { throw ('Estado local bloqueado: ' + $_.Exception.Message + ' Confira manualmente Rascunhos, Caixa de Saída e Itens Enviados no Outlook. Não apague o estado para tentar de novo.') }
    return $s
}
function New-Outlook {
    try { return [Runtime.InteropServices.Marshal]::GetActiveObject('Outlook.Application') }
    catch { return New-Object -ComObject Outlook.Application }
}
function Set-ApprovedMail($Mail, $Row, [string]$Html, $Account) {
    if ($Mail.Class -ne 43 -or $Mail.Sent -or $Mail.Submitted) { throw 'O item não é um rascunho disponível.' }
    while ($Mail.Recipients.Count -gt 0) { $Mail.Recipients.Remove(1) }
    while ($Mail.ReplyRecipients.Count -gt 0) { $Mail.ReplyRecipients.Remove(1) }
    while ($Mail.Attachments.Count -gt 0) { $Mail.Attachments.Remove(1) }
    # Remover delegação inserida durante revisão; a conta verificada é a única origem permitida.
    $Mail.SentOnBehalfOfName = ''
    $Mail.SendUsingAccount = $Account
    $Mail.To = $Row.para
    $Mail.CC = $Row.cc
    $Mail.BCC = $Row.cco
    $Mail.Subject = $Row.assunto
    $Mail.HTMLBody = $Html
    if (!$Mail.Recipients.ResolveAll()) { throw 'O Outlook não resolveu todos os destinatários.' }
}
function Invoke-Lote([string]$Directory, [string]$Mode, [string]$TestEmail) {
    $package = Read-Lote $Directory
    $m = $package.Manifest
    if (!$Mode) {
        $choice = Read-Host 'R = rascunhos (padrão), E = enviar, T = teste isolado'
        switch ($choice.ToUpperInvariant()) {
            '' { $Mode='Rascunhos' }; 'R' { $Mode='Rascunhos' }; 'E' { $Mode='Enviar' }; 'T' { $Mode='Teste' }
            default { throw 'Opção inválida. Nada foi enviado.' }
        }
    }
    if ($Mode -notin @('Rascunhos','Enviar','Teste')) { throw 'Modo inválido.' }
    if ($Mode -ne 'Teste' -and $TestEmail) { throw 'EmailTeste só pode ser usado no modo Teste.' }
    if ($Mode -eq 'Teste') {
        if (!$TestEmail) { $TestEmail = Read-Host 'Único destinatário do teste (sem CC/CCO)' }
        Assert-Emails $TestEmail $true $true
    }
    if (!$env:LOCALAPPDATA -or ![IO.Path]::IsPathRooted($env:LOCALAPPDATA)) { throw 'LOCALAPPDATA indisponível.' }
    $stateDir = Join-Path (Join-Path $env:LOCALAPPDATA 'CCAA/Lotes') $m.batch_id
    [IO.Directory]::CreateDirectory($stateDir) | Out-Null
    $statePath = Join-Path $stateDir 'estado.json'
    try { $lock = New-Object IO.FileStream((Join-Path $stateDir 'execucao.lock'), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None) }
    catch { throw 'Este lote já está em execução ou o estado local não está acessível.' }
    try {
        $fingerprint = (Get-FileHash -LiteralPath (Join-Path $Directory 'lote.json') -Algorithm SHA256).Hash.ToLowerInvariant()
        $state = Read-State $statePath $m $fingerprint
        $rows = @($m.rows)
        if ($Mode -eq 'Teste') {
            $rows = @([pscustomobject]@{ id=('test-' + (Get-TextHash $TestEmail.ToLowerInvariant())); para=$TestEmail; cc=''; cco=''; assunto=('[TESTE] ' + $m.rows[0].assunto) })
        }
        $pending = @($rows | Where-Object { !$state.rows.ContainsKey($_.id) -or ($Mode -eq 'Enviar' -and $state.rows[$_.id].status -eq 'Draft') })
        if ($pending.Count -eq 0) { Write-Host 'Nenhuma operação pendente. Rascunhos existentes e submissões foram preservados.'; return }
        $outlook = New-Outlook
        $accounts = $outlook.Session.Accounts
        if ($accounts.Count -lt 1) { throw 'Nenhuma conta configurada no Outlook clássico.' }
        $account = $null
        if ($m.remetente -eq '') { $account = $accounts.Item(1) }
        else {
            for ($i=1; $i -le $accounts.Count; $i++) {
                $candidate = $accounts.Item($i)
                if ($candidate.SmtpAddress -ieq $m.remetente) {
                    if ($null -ne $account) { throw 'Remetente ambíguo nas contas do Outlook.' }
                    $account = $candidate
                }
            }
        }
        if ($null -eq $account) { throw 'O remetente solicitado não existe em Session.Accounts. Não é permitido enviar como endereço arbitrário.' }
        $sender = [string]$account.SmtpAddress
        Assert-Emails $sender $true $true
        if ($state.account -and $state.account -ine $sender) { throw 'A conta do Outlook mudou desde a primeira execução. Estado bloqueado.' }
        Write-Host ('Conta de envio: ' + $sender)
        if ($m.remetente -eq '') { Write-Host 'Remetente vazio: conta padrão da sessão (primeira conta). Confira o endereço acima.' }
        Write-Host ('Modo: ' + $Mode + '; mensagens pendentes: ' + $pending.Count)
        if ($Mode -eq 'Teste') { Write-Host ('DESTINO ÚNICO DO TESTE: ' + $TestEmail + ' (CC e CCO vazios; nenhuma linha real será enviada).') }
        $drafts = @{}
        # Preflight de TODOS os rascunhos antes de salvar ou enviar qualquer linha.
        foreach ($row in $pending) {
            if ($state.rows.ContainsKey($row.id)) {
                $saved = $state.rows[$row.id]
                try {
                    $mail = $outlook.Session.GetItemFromID($saved.entry_id, $saved.store_id)
                    if ($mail.Class -ne 43 -or $mail.Sent -or $mail.Submitted -or $mail.EntryID -cne $saved.entry_id -or $mail.Parent.StoreID -cne $saved.store_id) { throw 'Identidade ou situação alterada.' }
                    $drafts[$row.id] = $mail
                } catch { throw 'Não foi possível verificar um rascunho salvo. Confira manualmente o Outlook; o bridge não recriará a mensagem.' }
            }
        }
        if ($Mode -eq 'Rascunhos') {
            if ((Read-Host 'Confirma esta conta e a criação dos rascunhos? Digite SIM') -cne 'SIM') { throw 'Cancelado. Nenhum rascunho criado.' }
        } else {
            $expected = 'ENVIAR ' + $pending.Count
            if ((Read-Host ('Envio REAL pela conta ' + $sender + '. Digite exatamente ' + $expected)) -cne $expected) { throw 'Confirmação não corresponde. Nada foi enviado.' }
        }
        $state.account = $sender
        Write-State $state $statePath
        foreach ($row in $pending) {
            $entry = @{ status='InProgressSave'; entry_id=''; store_id='' }
            if ($drafts.ContainsKey($row.id)) {
                $entry.entry_id = $state.rows[$row.id].entry_id
                $entry.store_id = $state.rows[$row.id].store_id
            }
            if ($Mode -ne 'Rascunhos') { $entry.status='InProgressSend' }
            $state.rows[$row.id] = $entry
            # Persistir a intenção ANTES de tocar no item COM: interrupções nunca são retentadas.
            Write-State $state $statePath
            try {
                if ($drafts.ContainsKey($row.id)) { $mail = $drafts[$row.id] }
                else { $mail = $outlook.CreateItem(0) }
                Set-ApprovedMail $mail $row $package.Html $account
                if ($Mode -eq 'Rascunhos') {
                    $mail.Save()
                    if (!$mail.EntryID -or !$mail.Parent.StoreID) { throw 'O Outlook não devolveu a identidade do rascunho.' }
                    $entry.entry_id = [string]$mail.EntryID
                    $entry.store_id = [string]$mail.Parent.StoreID
                    $entry.status = 'Draft'
                } else {
                    Start-Sleep -Seconds 2
                    $mail.Send()
                    $entry.status = 'Submitted'
                }
                Write-State $state $statePath
                Write-Host ($entry.status + ': ' + $row.id)
            } catch {
                $entry.status = 'Uncertain'
                try { Write-State $state $statePath } catch { Write-Warning 'Não foi possível registrar o erro; a intenção anterior permanece bloqueada.' }
                throw ('Operação com resultado incerto. Não haverá retentativa. Confira manualmente o Outlook. Causa: ' + $_.Exception.Message)
            }
        }
        Write-Host 'Concluído. Submitted significa submetido ao Outlook, NÃO entregue. A Caixa de Saída depende do próprio Outlook e da conexão.'
    } finally { $lock.Dispose() }
}

if ($MyInvocation.InvocationName -ne '.') {
    try { Invoke-Lote -Directory $PSScriptRoot -Mode $Modo -TestEmail $EmailTeste }
    catch { Write-Host ('ERRO: ' + $_.Exception.Message) -ForegroundColor Red; exit 1 }
}
