<? php
ini_set('display_errors',1); 
error_reporting(E_ALL);     
//$infoXML = new SimpleXMLElement("<obsInfo></obsInfo>");
$host="eor-db.mit.edu";
$dbname="mwa";
$user="mwa";
$password="BowTie";
$dbconn=pg_connect("host=$host dbname=$dbname user=$user password=$password") or die ("could not connect to server \n");

$query = "select * from obsc_mwa_setting where starttime<=gpsnow() and endtime>gpsnow()";
$result = pg_query($dbconn,$query) or die('Query Failed');
$obs = pg_fetch_row($result);
echo '<?xml version="1.0" encoding="ISO-8859-1"?><obsquery>';
if(!empty($obs)){
	echo '<isobs>'.'1'.'</isobs>';

	/*
	$infoXML->addAttribute('observation_number',obs[0]);
	$infoXML->addAttribute('starttime',obs[1]);
	$infoXML->addAttribute('stoptime',obs[2]);
	$infoXML->addAttribute('obsname',obs[3]);
	$infoXML->addAttribute('mode',obs[4]);	
	$infoXML->addAttribute('mode_params',obs[5]);
	$infoXML->addAttribute('dec_phase_center',obs[6]);	
	$infoXML->addAttribute('dec_phase_center',obs[7]);
	$infoXML->addAttribute('ra_phase_center',obs[8]);
	$infoXML->addAttribute('projectid',obs[9]);
	*/
}
else
{
	echo '<isobs>'.'0'.'</isobs>';
}
echo '</obsquery>';
?>