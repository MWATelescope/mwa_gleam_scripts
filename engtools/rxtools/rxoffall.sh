#!/bin/bash
for i in {1..9}; do
 echo Shutting down DC rails on rec0$i
 ssh mwa@rec0$i bin/receiver_power off
done
for i in {0..6}; do
 echo Shutting down DC rails on rec1$i
 ssh mwa@rec1$i bin/receiver_power off
done
