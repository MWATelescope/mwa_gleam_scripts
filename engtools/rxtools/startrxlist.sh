#!/bin/bash

for i in "$@"; do
 echo "(Cold) Booting rec$i"
 ssh mwa@rec$i bash -l coldboot1
done
