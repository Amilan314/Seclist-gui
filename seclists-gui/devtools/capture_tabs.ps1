$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
public class Cap {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdcBlt, uint nFlags);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
  public static string Save(IntPtr hwnd, string path) {
    RECT r; GetWindowRect(hwnd, out r);
    int w = r.Right - r.Left, h = r.Bottom - r.Top;
    using (Bitmap bmp = new Bitmap(w, h))
    using (Graphics g = Graphics.FromImage(bmp)) {
      IntPtr hdc = g.GetHdc();
      bool ok = PrintWindow(hwnd, hdc, 2);
      g.ReleaseHdc(hdc);
      bmp.Save(path, ImageFormat.Png);
      return ok ? "PrintWindow ok" : "PrintWindow returned false";
    }
  }
}
"@

# Locate Python and the app without hardcoding any drive letter or user name.
$py = $null
foreach ($cand in @(
  (Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\pythonw.exe"),
  (Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\pythonw3.exe"),
  (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\pythonw3.exe"),
  (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\pythonw.exe"),
  (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\pythonw.exe"),
  (Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\pythonw.exe")
)) {
  if (-not $py -and (Test-Path $cand)) { $py = $cand }
}
if (-not $py) {
  foreach ($name in @("pythonw", "pythonw3", "python3", "python")) {
    $found = Get-Command $name -ErrorAction SilentlyContinue
    if (-not $py -and $found) { $py = $found.Source }
  }
}
if (-not $py) { Write-Host "Python 3 not found; install Python 3.10+ first."; exit 1 }

# Everything else is derived from this script's own location (<repo>[/seclists-gui]/devtools).
$appdir = Split-Path -Parent $PSScriptRoot
$app = Join-Path $appdir "SecListsAssistant.pyw"
$dir = Join-Path $appdir "data"
if (-not (Test-Path $app)) { Write-Host "app not found: $app"; exit 1 }
Write-Host "python : $py"
Write-Host "app    : $app"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

$tabs = @(
  @{ n = 0; file = "tab0-guide.png" },
  @{ n = 1; file = "tab1-preview.png" },
  @{ n = 2; file = "tab2-search.png" },
  @{ n = 3; file = "tab3-toolbox.png" },
  @{ n = 4; file = "tab4-cheatsheet.png" }
)

foreach ($t in $tabs) {
  $proc = Start-Process -FilePath $py -ArgumentList "`"$app`" --tab $($t.n)" -PassThru
  $h = [IntPtr]::Zero
  for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 500
    $proc.Refresh()
    if ($proc.MainWindowHandle -ne [IntPtr]::Zero) { $h = $proc.MainWindowHandle; break }
  }
  if ($h -eq [IntPtr]::Zero) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    Write-Host "no window for tab $($t.n)"
    continue
  }
  Start-Sleep -Seconds 3
  $out = Join-Path $dir $t.file
  $msg = [Cap]::Save($h, $out)
  Write-Host "tab $($t.n) -> $($t.file) : $msg"
  Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  Start-Sleep -Milliseconds 600
}
Write-Host "capture done"
