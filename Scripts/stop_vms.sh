#!/bin/bash

slaves=`cat slaves`

for slave in $slaves;
do
  echo "Stopping vm on $slave"
  ssh -i id.mpi $slave << EOF
    export PATH=$PATH:/usr/local/bin
    VBoxManage controlvm simo poweroff
EOF
done

echo "Stopping vm on pip08
VBoxManage controlvm simo poweroff
