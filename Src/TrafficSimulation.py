from mpi4py import MPI
import os
import tempfile
import subprocess
from os import path

comm = MPI.COMM_WORLD
size = comm.size
rank = comm.rank
status = MPI.Status()

#class Wrapper(object):
#    def __init__(self):
#        self.data = []
#    def write(self, stuff):
#        self.data.append(stuff)


if rank == 0:
    for r in range(0, 2):
        msg = []
        for worker in range(0, size-1):
            xmls = {}
            files = os.listdir('Example')
            for file in files:
                xmls[file] = open("Example/"+file, "r").read()
            msg.append(xmls)

        for n in range(0, size-1):
            print("%d: sending to %d" % (rank, n + 1))
            comm.send(msg[n], dest=n+1)
        for n in range(0, size-1):
            data = comm.recv(status=status)
            print("%d: %s" % (status.source, data))

    # all done, shutdown all nodes
    for n in range(0, size-1):
        comm.send([], dest=n+1, tag=99)

else:
    dir = tempfile.TemporaryDirectory()

    print("%d: start" % (rank))
    while True:
        data = comm.recv(source=0, status=status)
        if status.tag == 99:
            break
        print("%d: recevied %d" % (rank, len(data)))
        for i, (k, v) in enumerate(data.items()):
            with open(path.join(dir.name, k), "w") as f:
                f.write(v)

        args = ["sumo", "-c", path.join(dir.name, "osm.sumocfg"), "--threads", "2"]
        with subprocess.Popen(args, stdout=subprocess.PIPE) as proc:
            output = proc.stdout.read()

        comm.send(output, 0)
    print("%d exiting" % (rank))
