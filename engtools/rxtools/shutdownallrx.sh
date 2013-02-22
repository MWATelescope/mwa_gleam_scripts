#!/bin/bash
for i in {1..9}; do
 echo powering off and shutting down rec0$i
 ssh mwa@rec0$i bin/receiver_power off
 ssh mwa@rec0$i sudo shutdown -h now
done
for i in {0..6}; do
 echo powering off and shutting down rec1$i
 ssh mwa@rec1$i bin/receiver_power off
 ssh mwa@rec1$i sudo shutdown -h now
done
