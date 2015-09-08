#!/bin/bash

if [[ $1 ]]
then
    if [[ -d $1 ]]
    then
        find $1 -type d -exec chmod 755 {} +
        find $1 -type f -exec chmod 644 {} +
    else
        echo "$1 doesn't exist or isn't a directory"
        exit 1
    fi
else
    echo "Usage: make_readable.sh /path/to/base/dir whose contents you want to make readable."
    exit 1
fi

exit 0
