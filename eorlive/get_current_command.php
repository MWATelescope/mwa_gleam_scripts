<?php
header("Content-type: text/xml");
$host="ngas01.ivec.org";
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
  echo "<isobs>1</isobs>";
  echo "<observation_number>".$obs[0]."</observation_number>";
  echo "<obsname>".$obs[1]."</obsname>";
  echo "<projectid>".$obs[2]."</projectid>";
  echo "<files>".$files[0]."</files>";
}
else
  {
    echo "<isobs>"."0"."</isobs>";
  }
echo "</curobs>";

echo "<lastobs1>";
$query = "select observation_number,obsname from obsc_mwa_setting where stoptime<gpsnow() and projectid='G0009' order by observation_number desc limit 2";
$result = pg_query($dbconn,$query) or die("Query Failed");
$obs = pg_fetch_row($result);
$observation_number=$obs[0];
$query = "select count(*) from (select observation_num from data_files where observation_num=$observation_number) as foo;";
$fresult=pg_query($dbconn,$query) or die('query failed');
$files = pg_fetch_row($fresult);
echo "<observation_number>".$obs[0]."</observation_number>";
echo "<obsname>".$obs[1]."</obsname>";
echo "<files>".$files[0]."</files>";
echo "</lastobs1>";

echo "<lastobs2>";
$obs = pg_fetch_row($result);
$observation_number=$obs[0];
$query = "select count(*) from (select observation_num from data_files where observation_num=$observation_number)as foo;";
$fresult=pg_query($dbconn,$query) or die('query failed');
$files=pg_fetch_row($fresult);
echo "<observation_number>".$obs[0]."</observation_number>";
echo "<obsname>".$obs[1]."</obsname>";
echo "<files>".$files[0]."</files>";
//now get last two observations
echo "</lastobs2>";

echo "</obsquery>";
?>