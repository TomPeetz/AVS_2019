#!/bin/bash

HOST="pip11"
PUB=`cat id.mpi.pub`
#ssh-keygen -t rsa -f id.mpi -q -N ""
#scp id.mpi.pub $HOST:~/.ssh/
ssh $HOST "mkdir -p ~/.ssh & touch ~/.ssh/authorized_keys & echo $PUB >> ~/.ssh/authorized_keys"
