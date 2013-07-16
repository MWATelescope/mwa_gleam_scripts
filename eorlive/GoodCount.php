<?php
$k=$_GET['rx_id'];
$host = "eor-db.mit.edu";
$dbname="mwa";
$user="mwa";
$password="BowTie";
$dbconn = pg_connect("host=$host dbname=$dbname user=$user password=$password") or die ("could not connect to server\n");
$resultstr="";
$query = "select count(*) from (select distinct on (rr.observation_number,rx_state_good) rr.observation_number from recv_readiness rr inner join obsc_mwa_setting oc on rr.observation_number=oc.observation_number where rr.rx_id=$k and rr.observation_number > (gpsnow()-12*3600) and oc.mode!='standby' and rr.rx_state_good='t') as foo;";
$result=pg_query($dbconn,$query) or die('Query Failed');
$row=pg_fetch_row($result);
$resultstr=$resultstr." Rx $k: $row[0] \n";
echo "$resultstr";
?>