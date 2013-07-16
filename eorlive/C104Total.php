<?php 
$host="eor-db.mit.edu";
$dbname="mwa";
$user="mwa";
$password="BowTie";

$dbconn=pg_connect("host=$host dbname=$dbname user=$user password=$password" ) or die ("could not connect to server\n");

$pid='\'C104\'';
$query = "select starttime, stoptime from mwa_setting where projectid=$pid";
$result=pg_query($dbconn,$query) or die('Query Failed');
$totsecs = 0;
while ($row=pg_fetch_row($result)){
  $totsecs = $totsecs + $row[1]-$row[0];
}
$tothours=$totsecs/3600;
echo "$tothours";
?>