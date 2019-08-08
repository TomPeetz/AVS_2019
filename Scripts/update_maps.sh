#!/bin/bash

nodes=`cat nodes`

for node in $nodes; do
  echo "Pushing map to $node"
  rsync -av -e "ssh -i id.mpi -p2222" --delete ~/AVS_2019 dennis@$node:~/AVS_2019 
done
