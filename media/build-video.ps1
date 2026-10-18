<#
  Renders media\knowledgewala-agentic-sdlc.mp4 (1080x1920, narrated) from video.html.
  Needs: Microsoft Edge, ffmpeg + ffprobe on PATH, Windows (uses the built-in System.Speech voice).
  .\media\build-video.ps1
#>
$ErrorActionPreference = 'Continue'   # Edge writes status text to stderr, which PS 5.1 would treat as fatal
$media = $PSScriptRoot
$out   = Join-Path $media 'out'
New-Item -ItemType Directory -Force $out | Out-Null
$edge = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe", "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edge) { throw "Microsoft Edge not found" }

$lines = @(
 "What if the AI that writes your code is never the one that checks it?",
 "One big prompt gives you code with no independent review. Knowledge Wala's workflow splits the job across fifteen focused agents for Claude Code, with human approval gates.",
 "Type slash dev workflow with an idea or a Jira ticket. It plans, then pauses for your approval before any code is written. Then a capped loop: code, test, security, performance, and review.",
 "We used it to build a real URL shortener. The loop caught a security bug where a link like a dot com at evil dot com would be accepted and redirect to the wrong host. The result: one hundred twenty seven tests and twenty six browser checks, all passing.",
 "Now the honest part. That four task app took twenty one subagent calls and about half a million tokens. For small changes, use lite mode. One suggested performance fix was benchmarked, showed no gain, and was reverted.",
 "When QA passes, a deploy planner writes your local and production instructions. A local deployment only starts when you type: approved, deploy, to local.",
 "It is open source and M I T licensed. Install it as a Claude Code plugin from Knowledge Wala on GitHub. Follow Knowledge Wala for more A I workflows."
)

Add-Type -AssemblyName System.Speech
$clips = @()
for ($i = 1; $i -le $lines.Count; $i++) {
  $png = Join-Path $out "s$i.png"; $wav = Join-Path $out "s$i.wav"; $mp4 = Join-Path $out "s$i.mp4"
  $url = "file:///" + ((Join-Path $media 'video.html') -replace '\\','/') + "?s=$i"
  & $edge --headless=new --disable-gpu --hide-scrollbars --window-size=1080,1920 --screenshot="$png" $url 2>$null | Out-Null
  Start-Sleep -Milliseconds 800
  $tts = New-Object System.Speech.Synthesis.SpeechSynthesizer
  $voice = $tts.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Name -match 'Zira|David|Aria|Guy' } | Select-Object -First 1
  if ($voice) { $tts.SelectVoice($voice.VoiceInfo.Name) }
  $tts.Rate = 0
  $tts.SetOutputToWaveFile($wav); $tts.Speak($lines[$i-1]); $tts.Dispose()
  $dur = [double](& ffprobe -v error -show_entries format=duration -of csv=p=0 $wav) + 0.9
  $fade = [Math]::Max(0.1, $dur - 0.35)
  & ffmpeg -y -v error -loop 1 -t $dur -i $png -i $wav -filter_complex "[0:v]scale=1080:1920,format=yuv420p,fade=t=in:st=0:d=0.3,fade=t=out:st=${fade}:d=0.35[v];[1:a]apad,atrim=0:$dur[a]" -map "[v]" -map "[a]" -r 30 -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 128k -shortest $mp4
  $clips += $mp4
}
$list = Join-Path $out 'list.txt'
($clips | ForEach-Object { "file '" + ($_ -replace '\\','/') + "'" }) | Set-Content $list -Encoding ascii
if ($LASTEXITCODE -ne 0) { throw "ffmpeg failed" }
$final = Join-Path $media 'knowledgewala-agentic-sdlc.mp4'
& ffmpeg -y -v error -f concat -safe 0 -i $list -c copy $final
$d = & ffprobe -v error -show_entries format=duration -of csv=p=0 $final
Write-Host ("Built {0} ({1:N1}s, {2:N1} MB)" -f $final, [double]$d, ((Get-Item $final).Length/1MB))
