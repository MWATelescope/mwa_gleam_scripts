#!/bin/bash
adfb1bin='dr300_adfb_pa_e2vc_rev0p2.bin'
adfb2bin='dr300_adfb_pa_e2vc_rev0p2.bin'
agfobin='x14_agfo_v6cp3_sx_with_gige_rev001.bin'

for i in "$@"; do
 echo "Booting rec$i"
 ssh mwa@rec$i bin/receiver_power all
 ssh mwa@rec$i bin/beamer_power all 
 ssh mwa@rec$i bin/arm_clock
 echo "killing usb_control, if it is running."
 pkill -f usb_control
 echo "loading $agfobin to AgFo board"
 ssh mwa@rec$i bin/load_dr_bin 0 /home/MWA/digrec/fpgabin/$agfobin
 echo "loading $adfb1bin to ADFB1 board"
 ssh mwa@rec$i bin/load_dr_bin 1 /home/MWA/digrec/fpgabin/$adfb1bin
 echo "loading $adfb2bin to ADFB2 board"
 ssh mwa@rec$i bin/load_dr_bin 2 /home/MWA/digrec/fpgabin/$adfb2bin
 ssh mwa@rec$i bin/init_dr.sh
done
