##!/bin/bash

slaves=`cat slaves`

for slave in $slaves;
do
  echo "Starting vm on $slave"
  ssh -i id.mpi inf1704@$slave << EOF
    export PATH=$PATH:/usr/local/bin
    VBoxManage startvm --type headless simo
EOF
done

echo "Starting vm on $slave"
VBoxManage startvm --type headless simo
