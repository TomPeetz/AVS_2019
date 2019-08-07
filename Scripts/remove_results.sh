#!/bin/bash

nodes=`cat nodes`

for node in $nodes; do
  echo "Cleaning $node"
  ssh -i id.mpi -p2222 dennis@$node << EOF
    rm -r ~/AVS_2019/Src/5*
    rm -r /tmp/tmp*
EOF
done
