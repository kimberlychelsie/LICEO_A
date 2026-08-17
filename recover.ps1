$logPath = "C:\Users\Maris Junterial\.gemini\antigravity-ide\brain\74898c54-6e5d-462a-b304-cd6bbf7a914e\.system_generated\logs\transcript_full.jsonl"
$lines = Get-Content -Path $logPath -Encoding UTF8 -Tail 200
foreach ($line in $lines) {
    if ($line -match "USER_EXPLICIT" -and $line -match "Managing 1 unique titles in your repositor") {
        $json = $line | ConvertFrom-Json
        $content = $json.content
        $start = $content.IndexOf("[diff_block_start]")
        $end = $content.IndexOf("[diff_block_end]")
        if ($start -ge 0 -and $end -gt $start) {
            $diff = $content.Substring($start, $end - $start)
            $recovered = @()
            foreach ($dline in $diff -split "`n") {
                if ($dline.StartsWith("-")) {
                    $recovered += $dline.Substring(1)
                }
            }
            [IO.File]::WriteAllLines("c:\Users\Maris Junterial\OneDrive\Documents\GitHub\LICEO_A\templates\librarian_books_inventory.html", $recovered, [System.Text.Encoding]::UTF8)
            Write-Host "File recovered successfully!"
            break
        }
    }
}
