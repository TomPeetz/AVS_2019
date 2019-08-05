#!/bin/bash

sudo apt-get install -y --no-install-recommends --no-install-suggests python3.7 python3-pip python3-setuptools python3-wheel libpython3-dev openmpi-bin libopenmpi-dev sumo sumo-tools gcc mongodb unzip

python3.7 -m pip install numpy
python3.7 -m pip install -r Src/requirements.txt

#echo -e 'y\n' | ssh-keygen -t rsa -f ~/.ssh/id_rsa -q -N ""
cp ~/id.mpi ~/.ssh/id_rsa
cp ~/id.mpi.pub ~/.ssh/id_rsa.pub
touch ~/.ssh/authorized_keys
cat ~/.ssh/id_rsa.pub > ~/.ssh/authorized_keys
