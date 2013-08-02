<?php
$data=file_get_contents("http://eor-02.mit.edu:7777/QUERY?query=files_list_recent&format=list");
$data = explode("\n",$data);
$datepattern='/[0-9]{4}-[0-9]{2}-[0-9]{2}/';
$timepattern='/[0-9]{2}:[0-9]{2}:[0-9]{2}.[0-9]{3}/';
$obstimepattern='/[0-9]{14}/';
$obsidpattern='/^[0-9]{10,}_/';
if(preg_match($datepattern,$data[0],$date))
{
if(preg_match($timepattern,$data[0],$time))
{
if(preg_match($obstimepattern,$data[0],$obstime))
{
$obstime=$obstime[0];


$obsyear = substr($obstime,0,4);
$obsmonth = substr($obstime,4,2);
$obsday = substr($obstime,6,2);
$obshour = substr($obstime,8,2);
$obsminute = substr($obstime,10,2);
$obssecond = substr($obstime,12,2);
$obstimestr = "$obsyear-$obsmonth-$obsday $obshour:$obsminute:$obssecond";


date_default_timezone_set("UTC");
$obstime = strtotime($obstimestr);
date_default_timezone_set("America/New_York");
$dltime = strtotime("$date[0] $time[0]");
date_default_timezone_set("UTC");
$dldateutc=date("Y-m-d H:i:s",$dltime);
date_default_timezone_set("America/New_York");
$deltatime = ($dltime-$obstime)/86400;
preg_match($obsidpattern,$data[0],$obsid);


echo "last download $obsid[0] at $dldateutc, with observation time of $obstimestr, lag of $deltatime days";

}
else
{
echo "obstime match not found";
}
}
else
{
 echo "time match not found";
}
}
else
{
echo "date match not found";
}
?>