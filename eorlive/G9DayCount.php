<?php
$host = "eor-db.mit.edu";
$dbname="mwa";
$user="mwa";
$password="BowTie";
$dbconn=pg_connect("host=$host dbname=$dbname user=$user password=$password") or die("could not connect to server\n");
$query = "select count(*) from (select distinct on (starttime) starttime from mwa_setting where starttime>gpsnow() and stoptime<(gpsnow()+86400) and (projectid='G0009' or projectid='G0010')) as foo;";
$result=pg_query($dbconn,$query) or die('Query Failed');
$row=pg_fetch_row($result);
echo "$row[0]";
?>