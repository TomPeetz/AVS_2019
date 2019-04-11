from mpi4py import MPI

comm = MPI.COMM_WORLD
size = comm.size
rank = comm.rank

if rank == 0:
    for r in range(0, 10):
        xmls = []
        for n in range(0, 3):
            #xmls += open("%d.xml" % (n+1), "r").read()
            xmls = ["1", "2", "3", "4"]
        #print(xmls)
        print("%d: sending" % (rank))
        comm.scatter(xmls, root=0)
        data = (rank + 1) ** 2
        #comm.gather(data, root=0)


else:
    print("%d: start" % (rank))
    data = comm.recv(source=0)
    print("%d:" % (rank))
    print(data)
    #comm.send(1.2, 0)
