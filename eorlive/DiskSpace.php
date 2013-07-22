<?php


ini_set('display_errors',1);
error_reporting(E_ALL);

function getSymbolByQuantity($bytes){
$symbols=array('B','KiB','MiB','GiB','TiB','PiB','EiB','ZiB','YiB');
$exp = floor(log($bytes)/log(1024));
return sprintf('%.2f '.$symbols[$exp],($bytes/pow(1024,floor($exp))));
}


$freespace = getSymbolByQuantity(disk_free_space("/nfs/eor-02/r2"));
echo "$freespace";


?>