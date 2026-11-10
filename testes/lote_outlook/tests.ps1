$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
if (-not (Test-Path "$here/executar.ps1")) { throw 'ASSERT: runnable bridge must exist' }
. "$here/executar.ps1"
function Assert($value, $message) { if (-not $value) { throw "ASSERT: $message" } }
function Reject($action, $message) {
    $failed = $false
    try { & $action } catch { $failed = $true }
    Assert $failed $message
}
$fixture = Join-Path $here '.test-fixture'
[IO.Directory]::CreateDirectory($fixture) | Out-Null
try {
    $utf8 = New-Object Text.UTF8Encoding($false)
    [IO.File]::WriteAllText((Join-Path $fixture 'mensagem.html'), '<html><body>Olá</body></html>', $utf8)
    $row = [ordered]@{ id=('a'*64); para='one@example.org;two@example.org'; cc='copy@example.org'; cco='hidden@example.org'; assunto='Assunto aprovado' }
    $manifest = [ordered]@{ version=1; batch_id=('b'*64); html_sha256=(Get-FileHash (Join-Path $fixture 'mensagem.html') -Algorithm SHA256).Hash.ToLowerInvariant(); remetente=''; rows=@($row) }
    function Save-Fixture { [IO.File]::WriteAllText((Join-Path $fixture 'lote.json'), ($manifest | ConvertTo-Json -Depth 10), $utf8) }
    Save-Fixture
    $read = Read-Lote $fixture
    Assert ($read.Manifest.rows.Count -eq 1) 'valid batch accepted'
    $row.para = "one@example.org`r`nBcc: evil@example.org"
    Save-Fixture
    Reject { Read-Lote $fixture } 'header injection rejected'
    $row.para = 'one@example.org;two@example.org'
    $manifest.rows = @($row, $row)
    Save-Fixture
    Reject { Read-Lote $fixture } 'duplicate row ids rejected'
    $manifest.rows = @($row)
    $manifest.html_sha256 = 'c'*64
    Save-Fixture
    Reject { Read-Lote $fixture } 'changed HTML rejected'
    Write-Host 'PASS: validation boundaries'
    $manifest.html_sha256 = (Get-FileHash (Join-Path $fixture 'mensagem.html') -Algorithm SHA256).Hash.ToLowerInvariant()
    Save-Fixture
    Assert ([bool](Get-Command Invoke-Lote -ErrorAction SilentlyContinue)) 'lifecycle entrypoint exists'
    Add-Type @'
using System;
using System.Collections.Generic;
using System.IO;
public class FakeRecipients {
 public int Count { get; set; }
 public void Remove(int index) { Count--; }
 public bool ResolveAll() { return true; }
}
public class FakeAttachments {
 public int Count { get; set; }
 public void Remove(int index) { Count--; }
}
public class FakeFolder { public string StoreID = "store"; }
public class FakeAccount { public string SmtpAddress = "sender@example.org"; }
public class FakeAccounts {
 public int Count = 1;
 public FakeAccount Account = new FakeAccount();
 public FakeAccount Item(int index) { return Account; }
}
public class FakeMail {
 public int Class = 43;
 public bool Sent = false, Submitted = false;
 public string EntryID = "entry", To = "", CC = "", BCC = "", Subject = "", HTMLBody = "", StatePath;
 public FakeFolder Parent = new FakeFolder();
 public FakeAccount SendUsingAccount;
 public FakeRecipients Recipients = new FakeRecipients(), ReplyRecipients = new FakeRecipients();
 public FakeAttachments Attachments = new FakeAttachments();
    public int Saves, Sends;
    public string SentOnBehalfOfName = "";
 public bool FailSave, FailSend;
 public void Save() {
  if (!File.ReadAllText(StatePath).Contains("InProgressSave")) throw new Exception("Save without durable intent");
  Saves++; if (FailSave) throw new Exception("simulated save failure");
 }
 public void Send() {
  if (!File.ReadAllText(StatePath).Contains("InProgressSend")) throw new Exception("Send without durable intent");
  Sends++; if (FailSend) throw new Exception("simulated transport uncertainty");
 }
}
public class FakeSession {
 public FakeAccounts Accounts = new FakeAccounts();
 public FakeMail Mail;
 public int Loads;
 public FakeMail GetItemFromID(string entry, string store) {
  if (entry != Mail.EntryID || store != Mail.Parent.StoreID) throw new Exception("wrong draft identity");
  Loads++; return Mail;
 }
}
public class FakeOutlook {
 public FakeSession Session = new FakeSession();
 public int Creates;
 public FakeMail CreateItem(int kind) { Creates++; return Session.Mail; }
}
'@
    $oldLocal = $env:LOCALAPPDATA
    $env:LOCALAPPDATA = Join-Path $fixture 'local'
    $script:answers = New-Object 'System.Collections.Generic.Queue[string]'
    function Read-Host($Prompt) { if ($script:answers.Count -eq 0) { throw "Unexpected prompt: $Prompt" }; return $script:answers.Dequeue() }
    $script:outlook = New-Object FakeOutlook
    $script:outlook.Session.Mail = New-Object FakeMail
    $script:mail = $script:outlook.Session.Mail
    $statePath = Join-Path $env:LOCALAPPDATA ('CCAA/Lotes/' + $manifest.batch_id + '/estado.json')
    $script:mail.StatePath = $statePath
    $script:connections = 0
    function New-Outlook { $script:connections++; return $script:outlook }
    $script:delays = 0
    function Start-Sleep($Seconds) { Assert ($Seconds -ge 2) 'minimum send interval'; $script:delays++ }
    function Run-Bridge($mode, $testEmail = '') { Invoke-Lote -Directory $fixture -Mode $mode -TestEmail $testEmail }
    $script:answers.Enqueue('SIM')
    Run-Bridge 'Rascunhos'
    Assert ($script:mail.Saves -eq 1 -and $script:mail.Sends -eq 0) 'drafts never send'
    Assert ($script:mail.To -eq $row.para -and $script:mail.BCC -eq $row.cco) 'approved draft routing'
    $state = Get-Content -Raw $statePath | ConvertFrom-Json
    Assert ($state.rows.($row.id).status -eq 'Draft') 'draft durable state'
    Run-Bridge 'Rascunhos'
    Assert ($script:outlook.Creates -eq 1) 'repeated draft run does not duplicate'
    $script:mail.To = 'tampered@example.org'
    $script:mail.Subject = 'tampered'
    $script:mail.SentOnBehalfOfName = 'arbitrary@example.org'
    $script:mail.Attachments.Count = 1
    $script:mail.ReplyRecipients.Count = 1
    $script:answers.Enqueue('ENVIAR 1')
    Run-Bridge 'Enviar'
    Assert ($script:mail.Sends -eq 1 -and $script:outlook.Creates -eq 1) 'send saved exact draft'
    Assert ($script:outlook.Session.Loads -ge 1) 'draft loaded by identity'
    Assert ($script:mail.SentOnBehalfOfName -eq '') 'unapproved delegation cleared'
    Assert ($script:mail.To -eq $row.para -and $script:mail.Subject -eq $row.assunto) 'approved fields reapplied'
    Assert ($script:mail.Attachments.Count -eq 0 -and $script:mail.ReplyRecipients.Count -eq 0) 'unapproved extras removed'
    $state = Get-Content -Raw $statePath | ConvertFrom-Json
    Assert ($state.rows.($row.id).status -eq 'Submitted') 'submission not delivery'
    $before = $script:connections
    $savedManifest = [IO.File]::ReadAllText((Join-Path $fixture 'lote.json'))
    $row.para = 'evil@example.org'
    Save-Fixture
    Reject { Run-Bridge 'Enviar' } 'same batch id with modified manifest blocked'
    Assert ($script:connections -eq $before) 'manifest-state mismatch rejected before Outlook'
    $row.para = 'one@example.org;two@example.org'
    [IO.File]::WriteAllText((Join-Path $fixture 'lote.json'), $savedManifest, $utf8)
    Run-Bridge 'Enviar'
    Assert ($script:mail.Sends -eq 1) 'submitted row cannot repeat'
    $script:answers.Enqueue('ENVIAR 1')
    Run-Bridge 'Teste' 'test@example.org'
    Assert ($script:mail.To -eq 'test@example.org' -and $script:mail.CC -eq '' -and $script:mail.BCC -eq '') 'test isolated routing'
    Run-Bridge 'Teste' 'test@example.org'
    Assert ($script:mail.Sends -eq 2) 'test not repeated'
    Write-Host 'PASS: draft/send/test lifecycle with mocked Outlook'
    function New-Case([string]$digit) {
        $manifest.batch_id = $digit * 64
        $manifest.remetente = ''
        $manifest.rows = @($row)
        Save-Fixture
        $script:outlook = New-Object FakeOutlook
        $script:outlook.Session.Mail = New-Object FakeMail
        $script:mail = $script:outlook.Session.Mail
        $script:mail.StatePath = Join-Path $env:LOCALAPPDATA ('CCAA/Lotes/' + $manifest.batch_id + '/estado.json')
        $script:answers.Clear()
    }
    New-Case '0'
    $script:answers.Enqueue('')
    $script:answers.Enqueue('SIM')
    Run-Bridge ''
    Assert ($script:mail.Saves -eq 1 -and $script:mail.Sends -eq 0) 'interactive empty option defaults to drafts'
    New-Case '1'
    $script:answers.Enqueue('ENVIAR 2')
    Reject { Run-Bridge 'Enviar' } 'wrong local typed count rejected'
    Assert ($script:outlook.Creates -eq 0) 'cancel before CreateItem'
    New-Case '2'
    $manifest.remetente = 'absent@example.org'
    Save-Fixture
    Reject { Run-Bridge 'Rascunhos' } 'unknown sender rejected'
    Assert ($script:outlook.Creates -eq 0) 'unknown account has no mail side effects'
    New-Case '3'
    $manifest.remetente = 'sender@example.org'
    Save-Fixture
    $script:answers.Enqueue('SIM')
    Run-Bridge 'Rascunhos'
    Assert ($script:mail.SendUsingAccount.SmtpAddress -eq $manifest.remetente) 'verified explicit sender assigned'
    $script:mail.EntryID = 'moved'
    Reject { Run-Bridge 'Enviar' } 'missing saved identity refuses recreation'
    Assert ($script:outlook.Creates -eq 1 -and $script:mail.Sends -eq 0) 'missing draft never recreated'
    New-Case '4'
    $script:mail.FailSend = $true
    $script:answers.Enqueue('ENVIAR 1')
    Reject { Run-Bridge 'Enviar' } 'send error propagated'
    $failureState = Get-Content -Raw $script:mail.StatePath | ConvertFrom-Json
    Assert ($failureState.rows.($row.id).status -eq 'Uncertain') 'uncertainty durable'
    $before = $script:connections
    Reject { Run-Bridge 'Enviar' } 'uncertain send blocks rerun'
    Assert ($script:connections -eq $before -and $script:mail.Sends -eq 1) 'uncertain send no reconnect or retry'
    New-Case '5'
    $script:mail.FailSave = $true
    $script:answers.Enqueue('SIM')
    Reject { Run-Bridge 'Rascunhos' } 'save error propagated'
    Reject { Run-Bridge 'Rascunhos' } 'uncertain save blocks rerun'
    Assert ($script:mail.Saves -eq 1) 'no blind save retry'
    New-Case '6'
    $lockDir = Split-Path $script:mail.StatePath
    [IO.Directory]::CreateDirectory($lockDir) | Out-Null
    $held = New-Object IO.FileStream((Join-Path $lockDir 'execucao.lock'), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    try {
        $before = $script:connections
        Reject { Run-Bridge 'Enviar' } 'parallel execution lock'
        Assert ($script:connections -eq $before) 'lock checked before Outlook'
    } finally { $held.Dispose() }
    New-Case '7'
    $script:answers.Enqueue('SIM')
    Run-Bridge 'Rascunhos'
    $failureState = Get-Content -Raw $script:mail.StatePath | ConvertFrom-Json
    $failureState.rows.($row.id).status = 'InProgressSend'
    [IO.File]::WriteAllText($script:mail.StatePath, ($failureState | ConvertTo-Json -Depth 10), $utf8)
    Reject { Run-Bridge 'Enviar' } 'interrupted intent blocks rerun'
    [IO.File]::WriteAllText($script:mail.StatePath, '{broken', $utf8)
    Reject { Run-Bridge 'Rascunhos' } 'corrupt state never reset'
    New-Case '8'
    $bad = [ordered]@{ id=('9'*64); para='broken'; cc=''; cco=''; assunto='bad' }
    $manifest.rows = @($row, $bad)
    Save-Fixture
    $before = $script:connections
    Reject { Run-Bridge 'Enviar' } 'late invalid row prevents entire batch'
    Assert ($script:connections -eq $before -and $script:outlook.Creates -eq 0) 'closed loop validation before Outlook'
    New-Case '9'
    $before = $script:connections
    Reject { Run-Bridge 'Teste' 'a@example.org;b@example.org' } 'test must have one address'
    Reject { Run-Bridge 'Enviar' 'test@example.org' } 'test option cannot leak into send mode'
    Assert ($script:connections -eq $before) 'invalid test routing rejected before Outlook'
    $many = @()
    for ($n=0; $n -lt 501; $n++) { $many += [ordered]@{ id=$n.ToString('x64'); para='one@example.org'; cc=''; cco=''; assunto='large' } }
    $manifest.rows = $many
    Save-Fixture
    Reject { Read-Lote $fixture } 'batch above 500 rejected'
    $manifest.rows = @($many[0..499])
    Save-Fixture
    Assert ((Read-Lote $fixture).Manifest.rows.Count -eq 500) '500 rows accepted'
    Assert ($script:delays -ge 3) 'delay exercised on sends'
    Write-Host 'PASS: confirmations, accounts, uncertainty, corrupt state, locking, 500-row limit, closed-loop rejection'
    $env:LOCALAPPDATA = $oldLocal
} finally {
    [IO.Directory]::Delete($fixture, $true)
}
