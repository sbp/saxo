#!/bin/bash

# http://inamidst.com/saxo/
# Created by Sean B. Palmer

USER=sax

echo '$' HOME=/tmp/sax
HOME=/tmp/sax
echo

DUX=$(python3 -c 'import os; print(os.path.expanduser("~"))')

if [ $DUX != /tmp/sax ]
then echo Error: '$HOME' is not /tmp/sax
    exit 1
fi

if [ ! -f saxo ]
then echo Error: saxo script not found
    exit 1
fi

function saxo() {
    echo '$' saxo $@
    ./saxo $@
    echo
}

function record() {
    echo '$' $@
    $@
    echo
}


####################################

record : Testing create, 01

record rm -rf /tmp/sax
record touch /tmp/sax

saxo create

record rm /tmp/sax


####################################

record : Testing create, 02

record rm -rf /tmp/sax

record mkdir /tmp/sax

record touch /tmp/sax/.saxo

saxo create


####################################

record : Testing create, 03

record rm -rf /tmp/sax

record mkdir -p /tmp/sax/.saxo

saxo create


####################################

record : Testing create, 04

record rm -rf /tmp/sax

saxo create

saxo create


####################################

record : Testing start, 01

record rm -rf /tmp/sax

mkdir -p /tmp/sax/.saxo

echo garbage > /tmp/sax/.saxo/config

saxo start

saxo stop


####################################

record : Testing start, 02

record rm -rf /tmp/sax

record mkdir -p /tmp/sax/.saxo

record touch /tmp/sax/.saxo/config

record chmod 000 /tmp/sax/.saxo/config

saxo start

saxo stop

# record chmod 644 /tmp/sax/.saxo/config


####################################

record : Testing start, 03

record rm -rf /tmp/sax

record mkdir -p /tmp/sax/.saxo

record touch /tmp/sax/.saxo/config

record chmod 000 /tmp/sax/.saxo

saxo start

record chmod 755 /tmp/sax/.saxo


####################################

record : Testing options, 01

record rm -rf /tmp/sax

mkdir /tmp/sax

saxo

saxo --help

saxo --version | \
    sed -E 's/[0-9]+\.[0-9]+\.[0-9]+-[0-9]+/VERSION/'

saxo create

saxo -f start | head -n 7

echo


####################################

record : Cleanup

record rm -rf /tmp/sax
