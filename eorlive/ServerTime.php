<?php
$time1 = Time();
$response = date("Y-m-d H:i:s",$time1);
$bostonzone=date_default_timezone_get();
date_default_timezone_set("America/Phoenix");
$time1 = Time();
$response=$response.date("Y-m-d H:i:s",$time1);
date_default_timezone_set("America/Seattle");
$response=$response.date("Y-m-d H:i:s",Time());
date_default_timezone_set("Australia/Sydney");
$response=$response.date("Y-m-d H:i:s",Time());
date_default_timezone_set("Australia/Perth");
$response=$response.date("Y-m-d H:i:s",Time());
date_default_timezone_set("Asia/Kolkata");
$response=$response.date("Y-m-d H:i:s",Time());
date_default_timezone_set("UTC");
$response=$response.date("Y-m-d H:i:s",Time());
date_default_timezone_set($bostonzone);
echo $response;
?>

