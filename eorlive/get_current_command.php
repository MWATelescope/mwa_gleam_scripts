<?php
header("Content-type: text/xml");
$host="ngas01.ivec.org";
$host="eor-db.mit.edu";
$dbname="mwa";
$user="mwa";
$password="BowTie";


$dbconn=pg_connect("host=$host dbname=$dbname user=$user password=$password") or die ("could not connect to server \n");
$query = "select observation_number, obsname, projectid from obsc_mwa_setting where starttime<=gpsnow() and stoptime>gpsnow()";
$result = pg_query($dbconn,$query) or die('Query Failed');
$obs = pg_fetch_row($result);


echo "<?xml version='1.0' encoding='ISO-8859-1'?>";
echo"<obsquery>";
echo "<curobs>";
if(!empty($obs)){
  $observation_number=$obs[0];
  $query = "select count(*) from (select observation_num from data_files where observation_num = $observation_number) as foo;";
  $result = pg_query($dbconn,$query) or die('Query Failed');
  $files = pg_fetch_row($result);
  $query = "select timestamp_gps($observation_number);";
  $date_result=pg_query($dbconn,$query) or die('Query Failed');
  $date_result=pg_fetch_row($date_result);
  echo "<isobs>1</isobs>";
  echo "<observation_number>".$obs[0]."</observation_number>";
  echo "<obsname>".$obs[1]."</obsname>";
  echo "<projectid>".$obs[2]."</projectid>";
  echo "<files>".$files[0]."</files>";
  echo "<date>".$date_result[0]."</date>";
}
else
  {
    echo "<isobs>"."0"."</isobs>";
  }
echo "</curobs>";

echo "<lastobs1>";
$query = "select observation_number,obsname, projectid from obsc_mwa_setting where stoptime<gpsnow() and (projectid='G0009' or projectid='G0010') order by observation_number desc limit 2";
$result = pg_query($dbconn,$query) or die("Query Failed");
$obs = pg_fetch_row($result);
$observation_number=$obs[0];
$query = "select count(*) from (select observation_num from data_files where observation_num=$observation_number) as foo;";
$fresult=pg_query($dbconn,$query) or die('query failed');
$files = pg_fetch_row($fresult);
$query = "select timestamp_gps($observation_number);";
$date_result=pg_query($dbconn,$query) or die('Query Failed');
$date_result=pg_fetch_row($date_result);
echo "<observation_number>".$obs[0]."</observation_number>";
echo "<obsname>".$obs[1]."</obsname>";
echo "<files>".$files[0]."</files>";
echo "<date>".$date_result[0]."</date>";
echo "<projectid>".$obs[2]."</projectid>";
echo "</lastobs1>";

echo "<lastobs2>";
$obs = pg_fetch_row($result);
$observation_number=$obs[0];
$query = "select count(*) from (select observation_num from data_files where observation_num=$observation_number)as foo;";
$fresult=pg_query($dbconn,$query) or die('query failed');
$files=pg_fetch_row($fresult);
$query = "select timestamp_gps($observation_number);";
$date_result=pg_query($dbconn,$query) or die('Query Failed');
$date_result=pg_fetch_row($date_result);
echo "<observation_number>".$obs[0]."</observation_number>";
echo "<obsname>".$obs[1]."</obsname>";
echo "<files>".$files[0]."</files>";
echo "<date>".$date_result[0]."</date>";
echo "<projectid>".$obs[2]."</projectid>";
echo "</lastobs2>";

echo "</obsquery>";
?>