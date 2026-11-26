param(
    [Parameter(Mandatory)][string]$InputJson,
    [Parameter(Mandatory)][string]$OutputWorkbook,
    [string]$PreviewPdf
)
$ErrorActionPreference = 'Stop'
$data = Get-Content -LiteralPath $InputJson -Encoding UTF8 -Raw | ConvertFrom-Json
$template = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../assets/concept-workbook.xlsx'))
$out = [IO.Path]::GetFullPath($OutputWorkbook)
if ([IO.Path]::GetExtension($out) -ne '.xlsx' -or (Test-Path -LiteralPath $out)) { throw '未作成の .xlsx を指定してください。' }
if ($PreviewPdf) {
    $pdf = [IO.Path]::GetFullPath($PreviewPdf)
    if ([IO.Path]::GetExtension($pdf) -ne '.pdf' -or (Test-Path -LiteralPath $pdf)) { throw '未作成の .pdf を指定してください。' }
}
if (($data.sheets.name -join '|') -ne '概要|スコープ|To-Be|検討事項') { throw '指定の順序で本文4シートを用意してください。' }
if ($data.history.Count -lt 1 -or $data.history.Count -gt 26 -or $data.history[-1].version -ne $data.version) { throw '変更履歴は1～26行とし、末尾の版数を表紙とそろえてください。' }
foreach ($entry in $data.history) { [void][datetime]::ParseExact($entry.date,'yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture) }
foreach ($spec in $data.sheets) {
    if (-not $spec.sections) { throw "節がありません: $($spec.name)" }
    foreach ($section in $spec.sections) {
        if (-not $section.number -or -not $section.title -or -not $section.blocks) { throw '節の項番・見出し・本文を用意してください。' }
        foreach ($block in $section.blocks) {
            if ($block.kind -notin @('label','note','table','flow','information-transfer')) { throw "不明な本文の種類です: $($block.kind)" }
            if ($block.kind -eq 'information-transfer') {
                if (-not $block.source -or -not $block.recipient -or $block.paths.Count -notin @(2,3)) { throw '情報伝達図には送り手、受け手、2～3件の経路が必要です。' }
                if ($block.workflow) {
                    foreach ($field in @('trigger','handover','handoverDetail','receipt','actionsHeading','resume')) {
                        if (-not $block.workflow.$field) { throw "引き継ぎ業務の流れに必要な項目がありません: $field" }
                    }
                }
                foreach ($path in $block.paths) {
                    if (-not $path.name -or $path.examples.Count -notin @(1,2,3) -or -not $path.method -or -not $path.recipientAction -or $path.interrupted -isnot [bool]) { throw '情報伝達図の経路には、種類、1～3件の例、伝達方法、受け手の対応、伝達が途切れる可能性の有無が必要です。' }
                }
            }
            if ($block.kind -eq 'table') {
                if (-not $block.columns -or $block.rows -isnot [array] -or -not $block.rows -or ($block.columns.Count + $block.responses.Count -gt 7)) { throw '表には見出しとデータ行が必要です。記入欄を含めて7列以内にしてください。' }
                foreach ($item in $block.rows) { if ($item.Count -ne $block.columns.Count) { throw "表の列数が一致しません: $($section.number)" } }
                foreach ($heading in $block.prefillColumns) {
                    if ($heading -notin $block.columns -or $heading -in @('No.','No','番号')) { throw "記入欄に転記する列が不正です: $heading" }
                }
            }
            if ($block.kind -eq 'flow') {
                if ($block.lanes.Count -lt 2 -or $block.lanes.Count -gt 5) { throw '図には2～5のレーンを指定してください。' }
                if ($block.nodes) {
                    $ids=@{}
                    $slots=@{}
                    foreach ($node in $block.nodes) {
                        $slot=('{0}/{1}' -f $node[1],$node[2])
                        if ($node.Count -notin @(4,5) -or -not $node[0] -or $node[1] -notin $block.lanes -or $node[2] -isnot [int] -or $node[2] -lt 0 -or -not $node[3] -or $ids.ContainsKey($node[0]) -or $slots.ContainsKey($slot)) { throw "不正な工程定義です: $($node[0])" }
                        $ids[$node[0]]=$true
                        $slots[$slot]=$true
                    }
                    if (-not $block.edges) { throw '工程間の矢印を指定してください。' }
                    foreach ($edge in $block.edges) {
                        if ($edge.Count -lt 2 -or $edge.Count -gt 4 -or -not $ids.ContainsKey($edge[0]) -or -not $ids.ContainsKey($edge[1]) -or $edge[0] -eq $edge[1] -or ($edge.Count -eq 4 -and $edge[3] -notin @('left','right'))) { throw '不正な矢印定義です。' }
                    }
                } else {
                    if (-not $block.steps) { throw '図に工程を指定してください。' }
                    foreach ($step in $block.steps) { if ($step.Count -notin @(2,3) -or $step[0] -notin $block.lanes -or -not $step[1]) { throw '工程にはレーンにある担当と作業を指定してください。' } }
                }
            }
        }
    }
}
$printEnd = 38
$exampleShift = 38
$font = 'ＭＳ 明朝'
$gray = 12632256
$line = 10921638
$tableFill = 15132390
$inputFill = 15398655
$nodeFill = 16380902
$arrowColor = 8807725

# Excelが入力文字列を式と解釈しないようにする。
function Write-Text($range,[string]$text) {
    if ($text) { $range.MergeArea.NumberFormat = '@'; $range.Value2 = ([regex]::Replace($text,'。(?=[^\r\n])',('。'+[char]10))) }
}
# 列をまたぐ値だけ結合し、左上のセルに入れる。
function Write-Span($sheet,[int]$row,[int]$start,[int]$end,[string]$text) {
    $range = $sheet.Range($sheet.Cells.Item($row,$start),$sheet.Cells.Item($row,$end))
    if ($start -ne $end) { $range.Merge() }
    Write-Text ($sheet.Cells.Item($row,$start)) $text
}
# 全角文字を考慮し、折り返しの行数を見積もる。
function Get-TextLines([string]$text,[int]$capacity) {
    $count = 0
    foreach ($part in (([regex]::Replace($text,'。(?=[^\r\n])',('。'+[char]10))) -split '\r?\n')) {
        $length = $part.Length + [regex]::Matches($part,'[^\u0000-\u007f]').Count
        $count += [Math]::Max(1,[Math]::Ceiling($length/[double]$capacity))
    }
    return $count
}
# 変更履歴の共通項目を参照するヘッダーを作る。
function Write-CommonHeader($sheet) {
    $left = @('PJ名','システム名','サブシステム名')
    $right = @('成果物名','作成','変更')
    for ($i=0; $i -lt 3; $i++) {
        $row = $i+1
        Write-Span $sheet $row 2 7 $left[$i]
        Write-Span $sheet $row 8 21 ''
        Write-Span $sheet $row 22 27 $right[$i]
        Write-Span $sheet $row 28 $printEnd ''
        $sheet.Cells.Item($row,8).Formula = ('=IF(''変更履歴''!C{0}="","",''変更履歴''!C{0})' -f $row)
        $sheet.Cells.Item($row,28).Formula = ('=IF(''変更履歴''!F{0}="","",''変更履歴''!F{0})' -f $row)
        $sheet.Rows.Item($row).RowHeight = 17
        $sheet.Range("B$($row):G$($row)").Interior.Color = $gray
        $sheet.Range("V$($row):AA$($row)").Interior.Color = $gray
        $sheet.Range("B$($row):AL$($row)").Borders.LineStyle = 1
    }
    $sheet.Range('B1:AL3').Font.Size = 9
}

# 印刷用の空欄と、印刷範囲外の記載例を同じ行に作る。
function Write-Table($sheet,[int]$row,$block,[int]$firstColumn,[int]$firstNumber) {
    $hasNumber = $block.columns[0] -in @('No.','No','番号')
    $contentColumns = @($block.columns | Select-Object -Skip ([int]$hasNumber))
    $exampleHeaders = @('No.') + $contentColumns
    $entryHeaders = @('No.') + @($contentColumns | ForEach-Object {
        $_.Replace('（仮説）','').Replace('の例','').Replace('質問例','質問').Replace('現時点の案・','')
    })
    $entryHeaders += @($block.responses | Where-Object { $_ -and $_ -ne '作成者記入欄' })
    $sets = @(@{ headers=$entryHeaders; shift=0 }, @{headers=$exampleHeaders; shift=$exampleShift})
    $rowCount = $block.rows.Count
    $lines = New-Object 'int[]' ($rowCount + 1)
    foreach ($set in $sets) {
        $layout = @()
        $weights = foreach ($heading in ($set.headers | Select-Object -Skip 1)) {
            switch -Regex ($heading) {
                '^(No\.|ID|工程ID|状態|対象)$' { 2; break }
                '記入欄|合意内容|詳細|備考|留意点|現状|説明|内容|方針|確認したい' { 6; break }
                default { 4 }
            }
        }
        $total = ($weights | Measure-Object -Sum).Sum
        $offset = $firstColumn + $set.shift
        $limit = $printEnd + $set.shift
        for ($i=0; $i -lt $set.headers.Count; $i++) {
            $span = if ($i -eq 0) { 1 } else { [Math]::Max(1,[int][Math]::Floor(($printEnd-$firstColumn)*$weights[$i-1]/$total)) }
            if ($i -eq $set.headers.Count-1) { $span = $limit+1-$offset }
            $layout += ,@($offset,($offset+$span-1))
            $offset += $span
        }
        for ($j=0; $j -le $rowCount; $j++) {
            $targetRow = $row+$j
            for ($i=0; $i -lt $set.headers.Count; $i++) {
                $start,$end = $layout[$i]
                $prefilled = $i -gt 0 -and $i -le $contentColumns.Count -and $contentColumns[$i-1] -in $block.prefillColumns
                $value = if ($j -eq 0) { [string]$set.headers[$i] } elseif ($i -eq 0) { [string]($firstNumber+$j-1) } elseif ($set.shift -or $prefilled) { [string]$block.rows[$j-1][$i-1+[int]$hasNumber] } else { '' }
                Write-Span $sheet $targetRow $start $end $value
                $cell = $sheet.Range($sheet.Cells.Item($targetRow,$start),$sheet.Cells.Item($targetRow,$end))
                if ($j -eq 0) { $cell.Interior.Color = $tableFill; $cell.Font.Bold = $true }
                elseif (-not $set.shift -and $i -gt 0 -and -not ($prefilled -and $value)) { $cell.Interior.Color = $inputFill }
                if ($i -eq 0) { $cell.HorizontalAlignment = -4108; $cell.WrapText = $false; $cell.ShrinkToFit = $true }
                [void]$cell.BorderAround(1,2,[Type]::Missing,$line)
                $capacity = [Math]::Max(3,3*($end-$start+1)-1)
                $lines[$j] = [Math]::Max($lines[$j],(Get-TextLines $value $capacity))
            }
        }
    }
    for ($j=0; $j -le $rowCount; $j++) { $sheet.Rows.Item($row+$j).RowHeight = [Math]::Min(344,[Math]::Max(26,15*$lines[$j]+7)) }
    return ($row+$rowCount+1)
}

# 左に空欄を置き、参考文は印刷範囲外に書く。
function Write-NotePair($sheet,[int]$row,[int]$firstColumn,[string]$example) {
    Write-Span $sheet $row $firstColumn $printEnd ''
    Write-Span $sheet $row ($firstColumn+$exampleShift) ($printEnd+$exampleShift) $example
    $entry = $sheet.Range($sheet.Cells.Item($row,$firstColumn),$sheet.Cells.Item($row,$printEnd))
    $entry.Interior.Color = $inputFill
    [void]$entry.BorderAround(1,2,[Type]::Missing,$line)
    $sheet.Rows.Item($row).RowHeight = [Math]::Min(344,[Math]::Max(42,16*(Get-TextLines $example 94)+8))
}

# 作図面の指定座標に、線の折れ点を残した編集可能な矢印を置く。
function Add-GraphArrow($sheet,$points,[string]$label,[double]$rightEdge,[string]$route) {
    $labelSegment = $null
    $returnsUpward = $points[-1][1] -lt $points[0][1]
    for ($i=0; $i -lt $points.Count-1; $i++) {
        $x1,$y1=$points[$i]; $x2,$y2=$points[$i+1]
        if ([Math]::Abs($x1-$x2)+[Math]::Abs($y1-$y2) -lt 0.1) { continue }
        $segment=$sheet.Shapes.AddConnector(1,$x1,$y1,$x2,$y2)
        $segment.Line.ForeColor.RGB=$arrowColor
        $segment.Line.Weight=1.1
        if ($returnsUpward) { $segment.Line.DashStyle=4 }
        if ($i -eq $points.Count-2) { $segment.Line.EndArrowheadStyle=3 }
        if (-not $labelSegment -and [Math]::Abs($y1-$y2) -lt 0.1 -and [Math]::Abs($x1-$x2) -ge 18) {
            $labelSegment=@((($x1+$x2)/2),$y1)
        }
    }
    if ($label) {
        if ($route -eq 'right') {
            $badge=$sheet.Shapes.AddTextbox(1,($rightEdge-33),($points[0][1]+16),31,12)
        } elseif (-not $labelSegment) {
            $badge=$sheet.Shapes.AddTextbox(1,($points[0][0]+8),(($points[0][1]+$points[-1][1])/2-5),48,10)
        } else {
            $badge=$sheet.Shapes.AddTextbox(1,($labelSegment[0]-36),($labelSegment[1]-12),72,12)
        }
        $badge.Fill.Visible=0
        $badge.Line.Visible=0
        $badge.TextFrame2.MarginLeft=0
        $badge.TextFrame2.MarginRight=0
        $badge.TextFrame2.MarginTop=0
        $badge.TextFrame2.MarginBottom=0
        $badge.TextFrame2.TextRange.Text=$label
        $badge.TextFrame2.TextRange.ParagraphFormat.Alignment=2
        $badge.TextFrame2.TextRange.Font.Name=$font
        $badge.TextFrame2.TextRange.Font.Size=8
        $badge.TextFrame2.TextRange.Font.Fill.ForeColor.RGB=$arrowColor
    }
}

# 役割と工程の行を指定し、分岐・横の受け渡し・戻り線を描く。
function Write-BranchFlow($sheet,[int]$row,$block) {
    Write-Span $sheet $row 5 $printEnd $block.entryTitle
    Write-Span $sheet $row 43 76 $block.title
    $sheet.Range("E$($row):BX$($row)").Font.Bold=$true
    $sheet.Rows.Item($row).RowHeight=24
    $row++
    $sheet.Rows.Item($row).RowHeight=7
    $row++
    $maxRow=0
    foreach($n in $block.nodes){$maxRow=[Math]::Max($maxRow,[int]$n[2])}
    $pitch=49
    foreach ($n in $block.nodes) {
        $lineCount = ($n[3] -split '\r?\n').Count
        $pitch = [Math]::Max($pitch,(12*$lineCount+34))
    }
    $height=31+($maxRow+1)*$pitch
    # 行高14ポイントが保存時に13.5ポイントへ丸まる場合も下端が収まるようにする。
    $last=$row+[int][Math]::Ceiling($height/13.5)-1
    $entry=$sheet.Range("F$($row):AL$($last)")
    $entry.Merge()
    $entry.Interior.Color=$inputFill
    [void]$entry.BorderAround(1,2,[Type]::Missing,$line)
    $area=$sheet.Range("AR$($row):BX$($last)")
    $area.RowHeight=14
    $left=[double]$area.Left
    $top=[double]$area.Top
    $allWidth=[double]$area.Width
    $routeWidth=15
    $bodyLeft=$left+$routeWidth
    $width=($allWidth-2*$routeWidth)/$block.lanes.Count
    for($i=0;$i -lt $block.lanes.Count;$i++){
        $x=$bodyLeft+$width*$i
        $lane=$sheet.Shapes.AddShape(1,$x,$top,$width,$height-3)
        $lane.Fill.ForeColor.RGB=16777215
        $lane.Line.ForeColor.RGB=$line
        $head=$sheet.Shapes.AddShape(1,$x,$top,$width,18)
        $head.Fill.ForeColor.RGB=15921906
        $head.Line.ForeColor.RGB=$line
        $head.TextFrame2.VerticalAnchor=3
        $head.TextFrame2.TextRange.Text=$block.lanes[$i]
        $head.TextFrame2.TextRange.ParagraphFormat.Alignment=2
        $head.TextFrame2.TextRange.Font.Name=$font
        $head.TextFrame2.TextRange.Font.Size=11
        $head.TextFrame2.TextRange.Font.Bold=-1
        $head.TextFrame2.TextRange.Font.Fill.ForeColor.RGB=0
    }
    $boxes=@{}
    foreach($n in $block.nodes){
        $laneIndex=[array]::IndexOf($block.lanes,$n[1])
        $lineCount = ($n[3] -split '\r?\n').Count
        $minHeight=if($n.Count -ge 5 -and $n[4] -eq 'decision'){28}else{24}
        $h=[Math]::Max($minHeight,(12*$lineCount+8))
        $boxes[$n[0]]=@{ x=$bodyLeft+$width*$laneIndex+12; y=$top+24+[int]$n[2]*$pitch+($pitch-18-$h)/2; w=$width-24; h=$h; row=[int]$n[2] }
    }
    foreach($edge in $block.edges){
        $from=$boxes[$edge[0]]; $to=$boxes[$edge[1]]
        $fx=$from.x+$from.w/2; $tx=$to.x+$to.w/2
        $fy=$from.y+$from.h/2; $ty=$to.y+$to.h/2
        $route=if($edge.Count -ge 4){$edge[3]}else{''}
        $caption=if($edge.Count -ge 3){[string]$edge[2]}else{''}
        if($route -in @('left','right')){
            if($route -eq 'left'){$gx=$left+5;$sx=$from.x;$ex=$to.x}else{$gx=$left+$allWidth-5;$sx=$from.x+$from.w;$ex=$to.x+$to.w}
            $points=@(@($sx,$fy),@($gx,$fy),@($gx,$ty),@($ex,$ty))
        }elseif($from.row -eq $to.row){
            if($fx -lt $tx){$sx=$from.x+$from.w;$ex=$to.x}else{$sx=$from.x;$ex=$to.x+$to.w}
            $points=@(@($sx,$fy),@($ex,$ty))
        }else{
            $startY=$from.y+$from.h
            $middle=($startY+$to.y)/2
            if([Math]::Abs($fx-$tx) -lt 0.1){$points=@(@($fx,$startY),@($tx,$to.y))}
            else{$points=@(@($fx,$startY),@($fx,$middle),@($tx,$middle),@($tx,$to.y))}
        }
        Add-GraphArrow $sheet $points $caption ($left+$allWidth) $route
    }
    foreach($n in $block.nodes){
        $b=$boxes[$n[0]]
        $decision=$n.Count -ge 5 -and $n[4] -eq 'decision'
        $shapeType=if($decision){4}else{5}
        $shape=$sheet.Shapes.AddShape($shapeType,$b.x,$b.y,$b.w,$b.h)
        $shape.Fill.ForeColor.RGB=if($decision){15137535}else{$nodeFill}
        $shape.Line.ForeColor.RGB=$arrowColor
        $shape.TextFrame2.VerticalAnchor=3
        $shape.TextFrame2.MarginTop=0
        $shape.TextFrame2.MarginBottom=0
        $shape.TextFrame2.TextRange.Text=$n[3]
        $shape.TextFrame2.TextRange.ParagraphFormat.Alignment=2
        $shape.TextFrame2.TextRange.Font.Name=$font
        $shape.TextFrame2.TextRange.Font.Size=10
        $shape.TextFrame2.TextRange.Font.Fill.ForeColor.RGB=0
    }
    return ($last+1)
}

# 枠または文字だけを、編集可能なExcel図形として置く。
function Add-TransferPanel($sheet,[double]$x,[double]$y,[double]$w,[double]$h,[string]$value,[int]$fill,[int]$border,[int]$ink,[int]$size,[bool]$bold,[bool]$leftAligned) {
    $panel = $sheet.Shapes.AddShape(5,$x,$y,$w,$h)
    if ($fill -lt 0) { $panel.Fill.Visible=0 } else { $panel.Fill.ForeColor.RGB=$fill }
    if ($border -lt 0) { $panel.Line.Visible=0 } else { $panel.Line.ForeColor.RGB=$border }
    $frame=$panel.TextFrame2
    $frame.MarginTop=0
    $frame.MarginBottom=0
    $frame.MarginLeft=6
    $frame.MarginRight=6
    $frame.VerticalAnchor=3
    $frame.TextRange.Text=$value
    $frame.TextRange.ParagraphFormat.Alignment=if ($leftAligned) { 1 } else { 2 }
    $frame.TextRange.Font.Name='游ゴシック'
    $frame.TextRange.Font.Size=$size
    $frame.TextRange.Font.Bold=if ($bold) { -1 } else { 0 }
    $frame.TextRange.Font.Fill.ForeColor.RGB=$ink
}

# 向きのある線は、終点に矢印を付ける。
function Add-TransferLine($sheet,[double]$x1,[double]$y1,[double]$x2,[double]$y2,[int]$color,[bool]$arrow) {
    $connector=$sheet.Shapes.AddConnector(1,$x1,$y1,$x2,$y2)
    $connector.Line.ForeColor.RGB=$color
    $connector.Line.Weight=1
    if ($arrow) { $connector.Line.EndArrowheadStyle=3 }
}

# 情報を蓄積する段階、担当交代、引き継ぎ、後任者の対応を縦に並べる。
function Add-TransferWorkflow($sheet,$area,$block) {
    $left=[double]$area.Left+4
    $top=[double]$area.Top
    $width=[double]$area.Width-8
    $mid=$left+$width/2
    $gutter=8
    $cardWidth=($width-$gutter*($block.paths.Count-1))/$block.paths.Count
    $boundary=0xDDDDDD
    $subtle=0x606060
    $background=0xFAFAFA
    $accents=@(0xB87D38,0x2680BD,0x5651BE)
    $workflow=$block.workflow

    # 上段は送り手と保有する情報。縦の矢印は業務段階の移行を示す。
    Add-TransferPanel $sheet $left ($top+3) $width 46 '' $background $boundary 0 10 $false $false
    Add-TransferPanel $sheet $left ($top+7) $width 19 $block.source -1 -1 0 12 $true $false
    Add-TransferPanel $sheet $left ($top+26) $width 17 $block.sourceDetail -1 -1 $subtle 10 $false $false
    Add-TransferLine $sheet $mid ($top+134) $mid ($top+146) $subtle $true
    Add-TransferPanel $sheet $left ($top+151) $width 33 $workflow.trigger $background $boundary 0 11 $false $false
    Add-TransferLine $sheet $mid ($top+188) $mid ($top+201) $subtle $true

    # 中段に現在の引き継ぎ、下段に受領後の対応と再開を置く。
    Add-TransferPanel $sheet $left ($top+206) $width 94 '' $background $boundary 0 10 $false $false
    Add-TransferPanel $sheet ($left+6) ($top+211) ($width-12) 18 $workflow.handover -1 -1 0 12 $true $true
    Add-TransferPanel $sheet ($left+6) ($top+230) ($width-12) 16 $workflow.handoverDetail -1 -1 $subtle 10 $false $true
    Add-TransferLine $sheet $mid ($top+304) $mid ($top+318) $subtle $true
    Add-TransferPanel $sheet $left ($top+324) $width 109 '' $background $boundary 0 10 $false $false
    Add-TransferPanel $sheet $left ($top+329) $width 18 $block.recipient -1 -1 0 12 $true $false
    Add-TransferPanel $sheet $left ($top+349) $width 18 $workflow.receipt -1 -1 0 11 $false $false
    Add-TransferLine $sheet $mid ($top+369) $mid ($top+381) $subtle $true
    Add-TransferPanel $sheet ($left+6) ($top+385) ($width-12) 15 $workflow.actionsHeading -1 -1 $subtle 10 $false $true
    Add-TransferLine $sheet $mid ($top+437) $mid ($top+450) $subtle $true
    Add-TransferPanel $sheet $left ($top+455) $width 33 $workflow.resume $background $boundary 0 11 $false $false

    # 同じ横位置で、情報の種類と、その伝達方法・補足作業を対応させる。
    for ($i=0; $i -lt $block.paths.Count; $i++) {
        $path=$block.paths[$i]
        $color=$accents[$i]
        $x=$left+($cardWidth+$gutter)*$i
        Add-TransferPanel $sheet $x ($top+56) $cardWidth 73 '' 0xFFFFFF $color 0 10 $false $false
        Add-TransferPanel $sheet ($x+4) ($top+60) ($cardWidth-8) 17 $path.name -1 -1 $color 11 $true $true
        for ($j=0; $j -lt $path.examples.Count; $j++) {
            Add-TransferPanel $sheet ($x+4) ($top+79+14*$j) ($cardWidth-8) 14 $path.examples[$j] -1 -1 0 10 $false $true
        }
        Add-TransferPanel $sheet ($x+6) ($top+253) ($cardWidth-12) 17 $path.method -1 -1 0 10 $true $true
        Add-TransferPanel $sheet ($x+6) ($top+274) ($cardWidth-12) 15 $path.condition -1 -1 $subtle 10 $false $true
        Add-TransferPanel $sheet ($x+6) ($top+403) ($cardWidth-12) 23 $path.recipientAction 0xFFFFFF $boundary 0 10 $false $false
    }
}

# 送り手と受け手を共通の枠にし、情報の種類ごとに現在の経路を示す。
function Add-InformationTransferDiagram($sheet,$area,$block) {
    $left=[double]$area.Left+4
    $top=[double]$area.Top
    $width=[double]$area.Width-8
    $gutter=8
    $count=$block.paths.Count
    $cardWidth=($width-$gutter*($count-1))/$count
    $mid=$left+$width/2
    $boundary=0xDDDDDD
    $subtle=0x606060
    $accent=@(0xB87D38,0x2680BD,0x5651BE)

    # 共通の送り手から、すべての情報カードへ分岐する。
    Add-TransferPanel $sheet $left ($top+3) $width 46 '' 0xFAFAFA $boundary 0 10 $false $false
    Add-TransferPanel $sheet $left ($top+6) $width 19 $block.source -1 -1 0 12 $true $false
    Add-TransferPanel $sheet $left ($top+26) $width 17 $block.sourceDetail -1 -1 $subtle 10 $false $false
    Add-TransferLine $sheet $mid ($top+53) $mid ($top+65) $subtle $false
    Add-TransferLine $sheet ($left+$cardWidth/2) ($top+60) ($left+$width-$cardWidth/2) ($top+60) $subtle $false

    # 受け手を共通の枠にし、確認・調査の内容は経路ごとに対応する位置に置く。
    Add-TransferPanel $sheet $left ($top+211) $width 45 '' 0xFAFAFA $boundary 0 10 $false $false
    Add-TransferPanel $sheet $left ($top+214) $width 18 $block.recipient -1 -1 0 12 $true $false
    for ($i=0; $i -lt $count; $i++) {
        $path=$block.paths[$i]
        $color=$accent[$i]
        $x=$left+($cardWidth+$gutter)*$i
        $cx=$x+$cardWidth/2
        Add-TransferLine $sheet $cx ($top+60) $cx ($top+70) $subtle $false
        Add-TransferPanel $sheet $x ($top+75) $cardWidth 76 '' 0xFFFFFF $color 0 10 $false $false
        Add-TransferPanel $sheet ($x+4) ($top+78) ($cardWidth-8) 17 $path.name -1 -1 $color 11 $true $true
        Add-TransferLine $sheet ($x+9) ($top+99) ($x+$cardWidth-9) ($top+99) $boundary $false
        for ($j=0; $j -lt $path.examples.Count; $j++) {
            Add-TransferPanel $sheet ($x+4) ($top+102+14*$j) ($cardWidth-8) 14 $path.examples[$j] -1 -1 0 10 $false $true
        }

        # 伝達が途切れる可能性がある経路は、受け手への矢印を「×」にする。
        Add-TransferLine $sheet $cx ($top+154) $cx ($top+162) $color $true
        Add-TransferPanel $sheet $x ($top+166) $cardWidth 15 $path.method -1 -1 0 10 $true $false
        Add-TransferPanel $sheet $x ($top+182) $cardWidth 14 $path.condition -1 -1 $subtle 9 $false $false
        if ($path.interrupted) {
            Add-TransferLine $sheet ($cx-3) ($top+199) ($cx+3) ($top+205) $color $false
            Add-TransferLine $sheet ($cx-3) ($top+205) ($cx+3) ($top+199) $color $false
        } else {
            Add-TransferLine $sheet $cx ($top+198) $cx ($top+206) $color $true
        }
        Add-TransferPanel $sheet $x ($top+233) $cardWidth 20 $path.recipientAction -1 -1 0 10 $false $false
    }
}

# 左に記入用の余白を設け、右に情報伝達図を置く。
function Write-InformationTransfer($sheet,[int]$row,$block) {
    Write-Span $sheet $row 5 $printEnd $block.entryTitle
    Write-Span $sheet $row 43 76 $block.title
    $sheet.Range("E${row}:BX${row}").Font.Bold=$true
    $sheet.Rows.Item($row).RowHeight=24
    $sheet.Rows.Item($row+1).RowHeight=7
    $row+=2
    $last=$row+18
    if ($block.workflow) { $last=$row+36 }
    $entry=$sheet.Range("F${row}:AL${last}")
    $entry.Merge()
    $entry.Interior.Color=$inputFill
    [void]$entry.BorderAround(1,2,[Type]::Missing,$line)
    $area=$sheet.Range("AR${row}:BX${last}")
    $area.RowHeight=14
    if ($block.workflow) { Add-TransferWorkflow $sheet $area $block }
    else { Add-InformationTransferDiagram $sheet $area $block }
    return ($last+1)
}

# 左は記入用の余白とし、右に編集可能なスイムレーンを作る。
function Write-Flow($sheet,[int]$row,$block) {
    if ($block.nodes) { return (Write-BranchFlow $sheet $row $block) }
    $entryTitle = if ($block.entryTitle) { $block.entryTitle } else { '業務フローの記入欄' }
    Write-Span $sheet $row 5 $printEnd $entryTitle
    Write-Span $sheet $row 43 76 $block.title
    $sheet.Range("E$($row):BX$($row)").Font.Bold = $true
    $sheet.Rows.Item($row).RowHeight = 24
    $row++
    $sheet.Rows.Item($row).RowHeight = 8
    $row++
    $hasCallout = @($block.steps | Where-Object { $_.Count -eq 3 -and $_[2] }).Count -gt 0
    $spacing = if ($hasCallout) { 52 } else { 36 }
    $height = if ($hasCallout) { 43 } else { 27 }
    $last = $row+[int][Math]::Ceiling((32+$spacing*$block.steps.Count)/16)-1
    $entry = $sheet.Range("F$($row):AL$($last)")
    $entry.Merge()
    $entry.Interior.Color = $inputFill
    [void]$entry.BorderAround(1,2,[Type]::Missing,$line)
    $area = $sheet.Range("AR$($row):BX$($last)")
    $area.RowHeight = 16
    $left = [double]$area.Left
    $top = [double]$area.Top
    $width = [double]$area.Width/$block.lanes.Count
    for ($i=0; $i -lt $block.lanes.Count; $i++) {
        $x = $left+$width*$i
        $lane = $sheet.Shapes.AddShape(1,$x,$top,$width,$area.Height-3)
        $lane.Fill.ForeColor.RGB = 16777215
        $lane.Line.ForeColor.RGB = $line
        $label = $sheet.Shapes.AddShape(1,$x,$top,$width,20)
        $label.Fill.ForeColor.RGB = 16777215
        $label.Line.ForeColor.RGB = $line
        $label.TextFrame2.VerticalAnchor = 3
        $label.TextFrame2.TextRange.Text = $block.lanes[$i]
        $label.TextFrame2.TextRange.ParagraphFormat.Alignment = 2
        $label.TextFrame2.TextRange.Font.Name = $font
        $label.TextFrame2.TextRange.Font.Bold = -1
        $label.TextFrame2.TextRange.Font.Size = 10
        $label.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = 0
    }
    $nodes = @()
    for ($i=0; $i -lt $block.steps.Count; $i++) {
        $k = [array]::IndexOf($block.lanes,$block.steps[$i][0])
        $node = $sheet.Shapes.AddShape(5,($left+$k*$width+10),($top+25+$i*$spacing),($width-20),$height)
        $node.Fill.ForeColor.RGB = $nodeFill
        $node.Line.ForeColor.RGB = $arrowColor
        $node.TextFrame2.VerticalAnchor = 3
        $nodeText = ('{0}. {1}' -f ($i+1),$block.steps[$i][1])
        if ($block.steps[$i].Count -eq 3 -and $block.steps[$i][2]) {
            $nodeText += [char]10 + '課題：' + $block.steps[$i][2]
        }
        $node.TextFrame2.TextRange.Text = $nodeText
        $node.TextFrame2.TextRange.ParagraphFormat.Alignment = 2
        $node.TextFrame2.TextRange.Font.Name = $font
        $node.TextFrame2.TextRange.Font.Size = 10
        $node.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = 0
        $nodes += $node
    }
    for ($i=0; $i -lt $nodes.Count-1; $i++) {
        $arrow = $sheet.Shapes.AddConnector(1,0,0,10,10)
        $arrow.ConnectorFormat.BeginConnect($nodes[$i],3)
        $arrow.ConnectorFormat.EndConnect($nodes[$i+1],1)
        $arrow.Line.ForeColor.RGB = $arrowColor
        $arrow.Line.Weight = 1.15
        $arrow.Line.EndArrowheadStyle = 3
    }
    return ($last+1)
}

$app = New-Object -ComObject Excel.Application
$app.Visible = $false
$app.DisplayAlerts = $false
$app.ScreenUpdating = $false
$book = $null
try {
    $book = $app.Workbooks.Open($template,0,$true)
    $style = $book.Worksheets.Item('書式')
    $style.Visible = -1
    [void]$style.Delete()
    $cover = $book.Worksheets.Item('表紙')
    Write-Text ($cover.Range('D12')) $data.project
    Write-Text ($cover.Range('D14')) $data.title
    Write-Text ($cover.Range('D16')) $data.position
    Write-Text ($cover.Range('D19')) $data.version

    # 左右の共通情報と、見出し・データの境界の二重線を設定する。
    $history = $book.Worksheets.Item('変更履歴')
    $history.Range('A1:G3').UnMerge()
    [void]$history.Range('A1:G3').Clear()
    $history.Range('A1:G7').Font.Name = $font
    $history.Range('A1:G3').Font.Size = 9
    $history.Range('A4:G7').Font.Bold = $false
    $history.Rows.Item(4).RowHeight = 28
    $history.Range('A4:G4').VerticalAlignment = -4108
    $history.Range('A:A').ColumnWidth = 4.2
    $history.Range('A1:B3').Interior.Color = $gray
    $history.Range('E1:E3').Interior.Color = $gray
    $history.Range('C1:D3').WrapText = $false
    $history.Range('C1:D3').ShrinkToFit = $true
    $history.Rows.Item(1).RowHeight = 20
    $history.Range('A7:G7').Interior.Pattern = -4142
    $history.Range('A4:G4').Interior.Pattern = -4142
    $history.Range('A4:G4').Borders.Item(9).LineStyle = -4142
    $history.Range('A7:G7').Borders.Item(9).LineStyle = -4119
    $history.Range('A8:G8').Borders.Item(8).LineStyle = -4119
    $left = @('PJ名','システム名','サブシステム名')
    $right = @('成果物名','作成','変更')
    for ($i=0; $i -lt 3; $i++) {
        $row = $i+1
        Write-Span $history $row 1 2 $left[$i]
        Write-Span $history $row 3 4 ''
        Write-Text ($history.Cells.Item($row,5)) $right[$i]
        Write-Span $history $row 6 7 ''
        $history.Range("A$($row):G$($row)").Borders.LineStyle = 1
    }
    Write-Text ($history.Range('C1')) $data.project
    Write-Text ($history.Range('C2')) $data.system
    Write-Text ($history.Range('C3')) $data.subsystem
    Write-Text ($history.Range('F1')) $data.title
    $history.Range('F2').Formula = '=TEXT(C8,"yyyy/mm/dd")&IF(G8="","","　"&G8)'
    if ($data.history.Count -gt 1) {
        $history.Range('F3').Formula = ('=TEXT(C{0},"yyyy/mm/dd")&IF(G{0}="","","　"&G{0})' -f (7+$data.history.Count))
    }
    $row = 8
    foreach ($entry in $data.history) {
        $history.Cells.Item($row,1).Value2 = [double]($row-7)
        Write-Text ($history.Cells.Item($row,2)) $entry.version
        $history.Cells.Item($row,3).Value2 = [double]([datetime]::ParseExact($entry.date,'yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture).ToOADate())
        Write-Text ($history.Cells.Item($row,4)) $entry.category
        Write-Text ($history.Cells.Item($row,5)) $entry.area
        Write-Text ($history.Cells.Item($row,6)) $entry.summary
        Write-Text ($history.Cells.Item($row,7)) $entry.author
        $history.Rows.Item($row).RowHeight = [Math]::Max(26,(Get-TextLines $entry.summary 45)*16+4)
        $row++
    }
    $history.PageSetup.PrintArea = ('$A$1:$G$'+[Math]::Max(15,$row-1))
    $index = 0
    foreach ($spec in $data.sheets) {
        $index++
        $sheet = $book.Worksheets.Add([Type]::Missing,$book.Worksheets.Item($book.Worksheets.Count))
        $sheet.Name = $spec.name

        $sheet.Range('A:BX').ColumnWidth = 3
        $used = $sheet.Range('B1:BX'+(45+($spec.sections.Count*36)))
        $used.Font.Name = $font
        $used.Font.Size = 11
        $used.VerticalAlignment = -4108
        $used.HorizontalAlignment = -4131
        $used.WrapText = $true
        Write-CommonHeader $sheet
        Write-Text ($sheet.Range('B5')) $index
        Write-Span $sheet 5 3 $printEnd $spec.name
        Write-Span $sheet 5 40 76 'こちらの記載例（参考・印刷範囲外）'
        $sheet.Range('B5:BX5').Font.Size = 17
        $sheet.Range('B5:BX5').Font.Bold = $true
        $sheet.Rows.Item(5).RowHeight = 28
        $intro = if ($spec.intro) { [string]$spec.intro } else { '色付きの欄にご記入ください。' }
        Write-Span $sheet 6 4 $printEnd $intro
        Write-Span $sheet 6 40 76 '提示側の想定に基づく記載例です。実際の状況に合わせて、左側で観点や内容を修正・追加・削除できます。'
        $sheet.Range('AN4:AR4').Merge()
        [void]$sheet.Hyperlinks.Add($sheet.Range('AN4'),'',("'{0}'!A1" -f $spec.name),'記入欄へ戻る','← 記入欄')
        $sheet.Rows.Item(6).RowHeight = [Math]::Max(43,17*(Get-TextLines $intro 103)+5)
        $row = 8
        $printStarts = @(1)
        $nextNumber = 1
        foreach ($section in $spec.sections) {
            if ($section.pageBreakBefore) { $printStarts += $row }
            Write-Text ($sheet.Cells.Item($row,3)) $section.number
            Write-Span $sheet $row 4 $printEnd $section.title
            Write-Text ($sheet.Cells.Item($row,41)) $section.number
            Write-Span $sheet $row 42 76 $section.title
            $sheet.Range("C$($row):BX$($row)").Font.Bold = $true
            $sheet.Range("C$($row):BX$($row)").Font.Size = 13
            foreach ($numberColumn in @(3,41)) {
                $numberCell = $sheet.Cells.Item($row,$numberColumn)
                $numberCell.WrapText = $false
                $numberCell.ShrinkToFit = $true
                $numberCell.Font.Size = 11
            }
            $sheet.Rows.Item($row).RowHeight = 25
            $row++
            $bodyColumn = 5
            $notes = [Collections.Generic.List[string]]::new()
            foreach ($block in $section.blocks) {
                if ($block.kind -eq 'note') { $notes.Add([string]$block.text); continue }
                if ($notes.Count) {
                    Write-NotePair $sheet $row $bodyColumn ($notes -join [char]10)
                    $notes.Clear()
                    $row++
                }
                switch ($block.kind) {
                    'label' {
                        $label = ([string]$block.text).Replace('現状の想定','現在の業務').Replace('情報源の例','情報源')
                        Write-Span $sheet $row 5 $printEnd $label
                        Write-Span $sheet $row 43 76 $block.text
                        $sheet.Cells.Item($row,5).Font.Bold = $true
                        $sheet.Cells.Item($row,43).Font.Bold = $true
                        $sheet.Rows.Item($row).RowHeight = 22
                        $bodyColumn = 6
                        $row++
                    }
                    'table' {
                        $row = (Write-Table $sheet $row $block $bodyColumn $nextNumber) + 1
                        $nextNumber += $block.rows.Count
                    }
                    'flow' { $row = (Write-Flow $sheet $row $block) + 1 }
                    'information-transfer' { $row = (Write-InformationTransfer $sheet $row $block) + 1 }
                }
            }
            if ($notes.Count) { Write-NotePair $sheet $row $bodyColumn ($notes -join [char]10); $row++ }
            $row++
        }

        $sheet.Activate()
        $app.ActiveWindow.DisplayGridlines = $false
        $app.ActiveWindow.FreezePanes = $false
        $app.ActiveWindow.Zoom = 90
        $sheet.Range('A1').Select()
        $sheet.PageSetup.Orientation = 2
        $sheet.PageSetup.PaperSize = 9
        $sheet.PageSetup.Zoom = $false
        $sheet.PageSetup.FitToPagesWide = 1
        $sheet.PageSetup.FitToPagesTall = 1
        $printAreas = for ($i=0; $i -lt $printStarts.Count; $i++) {
            $endRow = if ($i+1 -lt $printStarts.Count) { $printStarts[$i+1]-2 } else { $row-1 }
            '$A$' + $printStarts[$i] + ':$AL$' + $endRow
        }
        $sheet.PageSetup.PrintArea = $printAreas -join ','
        $sheet.PageSetup.PrintTitleRows = '$1:$3'
        $sheet.PageSetup.CenterHorizontally = $true
        Write-Output ('Prepared: {0} ({1} rows)' -f $spec.name,($row-1))
    }
    $cover.Activate()
    $cover.Range('A1').Select()
    $app.CalculateFull()
    $book.SaveAs($out,51)
    if ($PreviewPdf) { $book.ExportAsFixedFormat(0,$pdf) }
    Write-Output "Saved: $out"
} catch {
    Write-Warning $_.ScriptStackTrace
    throw
} finally {
    if ($null -ne $book) { $book.Close($false) }
    $app.Quit()
}
