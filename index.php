<?php

require 'vendor/autoload.php';

use Spatie\Browsershot\Browsershot;

// 获取GET参数
$coverUrl = isset($_GET['cover']) ? $_GET['cover'] : 'cover.jpg';
$title = isset($_GET['title']) ? $_GET['title'] : 'Sample Song';
$artist = isset($_GET['artist']) ? $_GET['artist'] : 'Sample Artist';
$lyricsUrl = isset($_GET['lyrics']) ? $_GET['lyrics'] : '';
$maxLines = 150; // 最大行数限制

// 下载歌词内容
if ($lyricsUrl) {
    $lyrics = file_get_contents($lyricsUrl);
    $lyrics = htmlspecialchars($lyrics); // 对特殊字符进行编码

    // 使用正则表达式去除时间戳
    $lyrics = preg_replace('/\[\d{2}:\d{2}\.\d{2}\]/', '', $lyrics);
    $lyrics = preg_replace('/\[\d{2}:\d{2}\.\d{3}\]/', '', $lyrics);

    $lyricsLines = explode("\n", $lyrics);
    if (count($lyricsLines) > $maxLines) {
        $lyricsLines = array_slice($lyricsLines, 0, $maxLines);
        $lyricsLines[] = '歌词太长了，剩下的省略了...'; // 添加省略号
    }
    $lyrics = implode('<br>', $lyricsLines); // 转换换行符为 <br>
} else {
    $lyrics = 'Line 1 of the lyrics<br>Line 2 of the lyrics<br>Line 3 of the lyrics';
}

// 读取模板内容
$template = file_get_contents('template.html');

// 替换占位符
$template = str_replace("[Music::IMAGE]", $coverUrl, $template);
$template = str_replace("[Music::TITLE]", $title, $template);
$template = str_replace("[Music::ARTIST]", $artist, $template);
$template = str_replace("[Music::LYRICS]", $lyrics, $template);

// 生成截图并直接输出
header('Content-Type: image/png');
echo Browsershot::html($template)
    ->windowSize(1200, 675) // 设置初始窗口大小，可以根据需要调整
    ->fullPage() // 截取整个页面
    ->screenshot();

?>

