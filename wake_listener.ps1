# Local-only wake phrase. The command itself is captured/transcribed by Python.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
try {
    Add-Type -AssemblyName System.Speech
    $infos = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers()
    $info = $infos | Where-Object { $_.Culture.Name -eq 'en-US' } | Select-Object -First 1
    if (-not $info) { throw 'English US speech recognizer is not installed' }
    $recognizer = [System.Speech.Recognition.SpeechRecognitionEngine]::new($info)
    $choices = [System.Speech.Recognition.Choices]::new()
    $choices.Add('Orion')
    $choices.Add('Hey Orion')
    if ($env:ORION_WAKE_WORD) { $choices.Add($env:ORION_WAKE_WORD) }
    $builder = [System.Speech.Recognition.GrammarBuilder]::new()
    $builder.Culture = $info.Culture
    $builder.Append($choices)
    $recognizer.LoadGrammar([System.Speech.Recognition.Grammar]::new($builder))
    while ($true) {
        $recognizer.SetInputToDefaultAudioDevice()
        [Console]::WriteLine('READY')
        [Console]::Out.Flush()
        $result = $recognizer.Recognize()
        if ($result -and $result.Confidence -ge 0.65) {
            $recognizer.SetInputToNull()
            [Console]::WriteLine('WAKE')
            [Console]::Out.Flush()
            if ([Console]::ReadLine() -eq $null) { break }
        }
    }
} catch {
    [Console]::WriteLine('ERROR: Speech recognizer unavailable')
    [Console]::Out.Flush()
    exit 1
} finally {
    if ($recognizer) { $recognizer.Dispose() }
}
