#!/usr/bin/perl
use strict;
my $ha;
my $infilename;
my $outfilename;
my $corr_command;
my $conv_command;
my $mins;
my $secs;
my $hrs;
my $basetime = 16.2114; # this is for ha=0 on the date below
my $time;
my $dec;

sub makeHeader {
    my $ha = shift();
    my $dec = shift();
    my $file = "myheader.txt";
    open(FILE,">$file") || die "Cannot open file $file\n";

    $time= $basetime + $ha*1.0027379;
    $hrs = int($time);
    $mins= int(($time-$hrs)*60.000001);
    $secs= $time-$hrs-$mins/60.0;

    printf "Time: %06.0f\n",$hrs*10000+$mins*100+$secs;

    printf FILE "# Sample UVFITS writer header file.\n";
    printf FILE "# blank lines and lines beginning with '#' are ignored\n";
    printf FILE "# line format: key value comments\n";
    printf FILE "FIELDNAME testfield\n";
    printf FILE "N_SCANS   1     # number of scans (time instants) in correlation products\n";
    printf FILE "N_INPUTS  16    # number of inputs into the correlation products\n";
    printf FILE "N_CHANS   128   # number of channels in spectrum\n";
    printf FILE "CORRTYPE  C     # correlation type to use. 'C'(cross), 'B'(both), or 'A'(auto)\n";
    printf FILE "INT_TIME  5.0   # integration time of scan (seconds)\n";
    printf FILE "FREQCENT  150.0 # observing center freq in MHz\n";
    printf FILE "BANDWIDTH 1.28  # total bandwidth in MHz\n";
    printf FILE "HA_HRS    %g  # the HA at the *start* of the scan. (hours)\n",$ha;
    printf FILE "RA_HRS    0.0   # the RA of the desired phase centre (hours)\n";
    printf FILE "DEC_DEGS  %.4f # the DEC of the desired phase centre (degs)\n",$dec;
    printf FILE "DATE      20070921  # YYYYMMDD (UTC)\n";
    printf FILE "TIME      %06.0f    # HHMMSS (UTC)\n",$hrs*10000+$mins*100+$secs;
    close(FILE);
}

$dec = -60.0;
for($ha=-2.0; $ha < 2.000001; $ha+=0.5) {
    $infilename = sprintf("simdat16_ha%0.2f.dat",$ha);
    $outfilename = sprintf("simdat16_ha_%0.2f.uvfits",$ha);
    printf("Infile: %s, outfile: %s\n",$infilename,$outfilename);
    $corr_command = sprintf("../corr_gpu_complex -n 16 -i %s -o sim16",$infilename);
    $conv_command = sprintf("./corr2uvfits -a sim16.LACSPC -c sim16.LCCSPC -o %s -H myheader.txt ",$outfilename);

    printf("corr_command is: %s\n",$corr_command);
    system($corr_command);

    makeHeader($ha,$dec);

    printf("conv_command is: %s\n",$conv_command);
    system($conv_command);
}
$dec = -20.0;
for($ha=-2.250; $ha < 2.000001; $ha+=0.5) {
    $infilename = sprintf("simdat16_ha%0.2f.dat",$ha);
    $outfilename = sprintf("simdat16_ha_%0.2f.uvfits",$ha);
    printf("Infile: %s, outfile: %s\n",$infilename,$outfilename);
    $corr_command = sprintf("../corr_gpu_complex -n 16 -i %s -o sim16",$infilename);
    $conv_command = sprintf("./corr2uvfits -a sim16.LACSPC -c sim16.LCCSPC -o %s -H myheader.txt ",$outfilename);

    printf("corr_command is: %s\n",$corr_command);
    system($corr_command);

    makeHeader($ha,$dec);

    printf("conv_command is: %s\n",$conv_command);
    system($conv_command);
}
$dec = -40.0;
for($ha=-2.10; $ha < 2.000001; $ha+=0.5) {
    $infilename = sprintf("simdat16_ha%0.2f.dat",$ha);
    $outfilename = sprintf("simdat16_ha_%0.2f.uvfits",$ha);
    printf("Infile: %s, outfile: %s\n",$infilename,$outfilename);
    $corr_command = sprintf("../corr_gpu_complex -n 16 -i %s -o sim16",$infilename);
    $conv_command = sprintf("./corr2uvfits -a sim16.LACSPC -c sim16.LCCSPC -o %s -H myheader.txt ",$outfilename);

    printf("corr_command is: %s\n",$corr_command);
    system($corr_command);

    makeHeader($ha,$dec);

    printf("conv_command is: %s\n",$conv_command);
    system($conv_command);
}
