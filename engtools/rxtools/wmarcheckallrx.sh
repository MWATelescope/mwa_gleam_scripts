#!/bin/bash
for i in {1..9}; do
 echo testing rec0$i
 ssh mwa@rec0$i ps -ef | grep HTTP
done
for i in {0..6}; do
 echo testing rec1$i
 ssh mwa@rec1$i ps -ef | grep HTTP
done
