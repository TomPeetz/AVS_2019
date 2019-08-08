
#!/bin/bash

slaves=`cat slaves`
i=2
for slave in $slaves;
do
  echo "Stopping and unregistering vm on $slave"
  ssh -i id.mpi inf1704@$slave << EOF
    export PATH=$PATH:/usr/local/bin
    VBoxManage controlvm simo poweroff
    sleep 5
    VBoxManage unregistervm simo
    sleep 1
    mkdir -p ~/AVS_2019/vbox
EOF
  echo "Copying new vm to $slave"
  rsync --progress -av -e "ssh -i id.mpi" ~/AVS_2019/vbox/simo inf1704@$slave:~/AVS_2019/vbox
  echo "Registering and starting vm on $slave"
  ssh -i id.mpi inf1704@$slave << EOF
    export PATH=$PATH:/usr/local/bin
    VBoxManage registervm ~/AVS_2019/vbox/simo/simo.vbox
    VBoxManage modifyvm simo --macaddress1 auto
    VBoxManage modifyvm simo --macaddress2 auto
    VBoxManage startvm --type headless simo
EOF

  sleep 30

  if [ $i -ne 8 ]; then
    echo "Deleting arp cache"
    sudo arp -a -d
    echo "Configuring pup$i"

    NEWIP=`expr $i \+ 100`

    NEWNAME=$i
    if [ $i -lt 10 ]; then
        NEWNAME="0$i"
    fi

    ssh -i id.mpi -p2222 dennis@10.0.0.108 << EOF
      sudo -s
      echo "Changing hostname to pup$NEWNAME"
      echo pup$NEWNAME > /etc/hostname
      hostname
      echo "Changing ip address to 10.0.0.$NEWIP"
      echo "s/10.0.0.108/10.0.0.$NEWIP/g"
      sed -i "s/10.0.0.108/10.0.0.$NEWIP/g" /etc/netplan/50-cloud-init.yaml
      reboot
EOF
    fi
    let i++

done
