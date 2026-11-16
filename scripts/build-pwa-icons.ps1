param()

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$projectPath = Split-Path -Parent $PSScriptRoot
$sourcePath = Join-Path $projectPath 'assets\icons\RHEMA CUC.png'
$outputPath = Join-Path $projectPath 'frontend\public\icons'
$sourceImage = [System.Drawing.Bitmap]::new($sourcePath)
try {
    # Preserve the approved gold tile and its transparent exterior exactly.
    # Android gets the complete tile, without an additional padded background.
    $variants = @(
        @{ Name = 'icon-192-v3.png'; Size = 192 },
        @{ Name = 'icon-512-v3.png'; Size = 512 },
        @{ Name = 'icon-maskable-512-v3.png'; Size = 512 },
        @{ Name = 'apple-touch-icon-v3.png'; Size = 180 }
    )
    foreach ($variant in $variants) {
        $destinationPath = Join-Path $outputPath $variant.Name
        $size = $variant.Size
        if ($sourceImage.Width -eq $size -and $sourceImage.Height -eq $size) {
            Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Force
        } else {
            $bitmap = [System.Drawing.Bitmap]::new($size, $size, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
            $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
            try {
                $graphics.Clear([System.Drawing.Color]::Transparent)
                $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
                $destination = [System.Drawing.Rectangle]::new(0, 0, $size, $size)
                $sourceRect = [System.Drawing.Rectangle]::new(0, 0, $sourceImage.Width, $sourceImage.Height)
                $graphics.DrawImage($sourceImage, $destination, $sourceRect, [System.Drawing.GraphicsUnit]::Pixel)
                $bitmap.Save($destinationPath, [System.Drawing.Imaging.ImageFormat]::Png)
            } finally {
                $graphics.Dispose()
                $bitmap.Dispose()
            }
        }
        Write-Output $variant.Name
    }
} finally {
    $sourceImage.Dispose()
}
