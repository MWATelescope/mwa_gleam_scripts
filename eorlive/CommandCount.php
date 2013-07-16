<?php
$host = "eor-db.mit.edu";
$dbname="mwa";
$user="mwa";
$password="BowTie";
$dbconn = pg_connect("host=$host dbname=$dbname user=$user password=$password") or die("could not connect to server\n");
$query = "select count(*) from (select distinct on (observation_number) observation_number, mode from obsc_mwa_setting where observation_number >(gpsnow()-12*3600) and mode!='standby' ) as foo; ";
$result=pg_query($dbconn,$query) or die('Query Failed');
$row=pg_fetch_row($result);
echo "$row[0]";
?>