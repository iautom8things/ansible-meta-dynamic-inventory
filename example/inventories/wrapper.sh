#!/usr/bin/env sh
reldir=`dirname $0`
$reldir/ec2.py | $reldir/transformer.py $reldir/Groupingsfile
