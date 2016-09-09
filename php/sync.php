<?php

$url = "http://example.com/sync";

$response = file_get_contents($url);
print_r($response . "\n");

?>
