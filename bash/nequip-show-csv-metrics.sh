#!/usr/bin/env bash

if [ -z $1 ]; then DIR='.'; else DIR=$1; fi
if [ -z $2 ]; then NLINE=8; else NLINE=$2; fi
for csv in $(find $DIR -name metrics.csv | sort); do
    echo ====================================
    echo $csv;
    echo ------------------------------------
    TMPFILE=./.dgfahsdklfjhasdklfjhaskdlfgfsd
    head -n 1 $csv >| $TMPFILE; tail -n $NLINE $csv >> $TMPFILE
    python -c '
import sys
colnames = [
    "epoch",
    "step",
    "train_metric_step/forces_mae",
    #"train_metric_step/forces_maxabserr",
    "train_metric_step/per_atom_energy_mae",
    "train_metric_step/per_atom_energy_maxabserr",
]
with open(sys.argv[1]) as f:
    data = f.read().strip().split("\n")
    line_1st_lst = data[0].strip().split(",")
    assert set(colnames) <= set(line_1st_lst)
    line_index_lst = [line_1st_lst.index(i) for i in colnames]
    format_lst = ["{"+ f":<{len(i)+2}s"+"}" for i in colnames]
    for line in data:
        lst = line.strip().split(",")
        for i,fmt in zip(line_index_lst, format_lst):
            print(fmt.format(lst[i]), end="\t")
        print()
    ' $TMPFILE
done; rm -f $TMPFILE;
echo ====================================
