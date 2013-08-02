<?php 
$host="eor-db.mit.edu";
$dbname="mwa";
$user="mwa";
$password="BowTie";

ini_set('display_errors',1); 
 error_reporting(E_ALL);
function getTimeSymbol($seconds){
	 $symbols=array('Weeks','Days','Hours','Minutes','Seconds');
	 $minutes=$seconds/60.;
	 $hours=$minutes/60.;
	 $days=$hours/24.;
	 $weeks=$days/7.;
	 $one=1.0;
	 echo gettype($weeks);
	 echo gettype($one);
	 echo $weeks < $one;
	 if(bccomp($weeks,$one))
	 {
		return sprintf('%.2f '.$symbols[0],$weeks);
	 }
	 elseif(bccomp($days,$one))
	 {
		return sprintf('%.2f '.$symbols[1],$days);
	 }
	 elseif(bccomp($hours,$one))
	 {
		return sprintf('%.2f '.$symbols[2],$hours);
	 }
	 elseif(bccomp($minutes,$one))
	 {
		return sprintf('%.2f '.$symbols[3],$minutes);
	 }
	 else
	 {
		return sprintf('%.2f '.$symbols[4],$seconds);
	 }


}



$dbconn=pg_connect("host=$host dbname=$dbname user=$user password=$password" ) or die ("could not connect to server\n");

$pid='\'G0009\'';
$query = "select gpsnow()";
$result=pg_query($dbconn,$query) or die('Query Failed');

if($row=pg_fetch_row($result)){
	$nowtime = $row[0];
}
else
{
echo "gpsnow() is not working";
exit;
}

$query = "select * from mwa_setting where projectid=$pid and starttime>gpsnow() order by starttime asc limit 1";
$result=pg_query($dbconn,$query) or die('Query Failed');
if($row=pg_fetch_row($result)){

	$query = "select timestamp_gps($row[0])";		
	$result=pg_query($dbconn,$query);
	if($trow=pg_fetch_row($result)){
		$tstamp=$trow[0];
	}
	else
	{
		echo "timestamp_gps is not working";
		exit;
	}


	
	$obsstarttime=$row[0];
	$obsstamp=substr($tstamp,0,18);
	$obstime=strtotime($obsstamp);	
	$oldzone = date_default_timezone_get();
	date_default_timezone_set("UTC");
	$utctime=date("Y-m-d H:i:s",$obstime);
	date_default_timezone_set($oldzone);
	echo getTimeSymbol((float)$obsstarttime-(float)$nowtime)." (".$utctime.")";
				
}
else
{
	echo "No G0009 Observations Scheduled At this Time.";
}
?>