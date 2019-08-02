from mpi4py import MPI
from hyperopt import hp, tpe, fmin
from hyperopt.mongoexp import MongoTrials
from pprint import pprint
import os
import tempfile
import subprocess
import time
import fobj
import json
import uuid
import argparse

parser = argparse.ArgumentParser(description='TrafficSimulation')
parser.add_argument('--mongo', type=str, help='Address of mongodb')
parser.add_argument('--fun_evals', type=int, help='Number of objective function evaluations')

args = parser.parse_args()





comm = MPI.COMM_WORLD
size = comm.size
rank = comm.rank
status = MPI.Status()


def generate_search_space():
    with open('searchspace.json', 'r') as f:
        json_data = json.loads(f.read())

    searchspace = []
    for intersection in json_data['intersections']:
        searchspace.append(('i-'+intersection['id'], hp.choice('choice-' + intersection['id'], intersection['allowedModifications'])))
    for roundabout in json_data['roundabouts']:
        raid = '-'.join(roundabout['nodes'])
        mods = roundabout['allowedModifications']
        searchspace.append(('r-'+raid, hp.choice('choice-'+raid, mods)))
    return searchspace


if rank == 0:
    for r in range(0, 1):
        msg = []
        #for worker in range(0, size-1):
        #    xmls = {}
        #    files = os.listdir('Example')
        #    for file in files:
        #        xmls[file] = open("Example/"+file, "r").read()
        #    msg.append(xmls)

        for n in range(0, size-1):
            print("%d: sending to %d" % (rank, n + 1))
            #comm.send(msg[n], dest=n+1)
            comm.send('asd', dest=n+1)

        space = generate_search_space()

        trials = MongoTrials('mongo://%s:1234/test_db/jobs' % args.mongo, exp_key=str(uuid.uuid4()))

        best = fmin(fn=fobj.sumo,
                    space=space,
                    trials=trials,
                    algo=tpe.suggest,
                    max_evals=args.fun_evals
        )

        with open('res.log', 'w') as res:
            pprint(best, res)

        for n in range(0, size-1):
            data = comm.recv(status=status)
            #print("%d: %s" % (status.source, data))

            #print("%d ==========" % status.source)
            print("%d returncode %d" % (status.source, data['returncode']))
            #print("%d stdout:" % status.source)
            #for l in data['stdout']:
            #    print("%d %s|" % (status.source, l))
            #print("%d stderr:" % status.source)
            #for l in data['stderr']:
            #    print("%d %s" % (status.source, l))
            #stdout = data['stdout']
            #sidx = list(map(lambda x: 'Performance' in x, stdout)).index(True)
            #eidx = list(map(lambda x: 'DepartDelay' in x, stdout)).index(True)
            #strs = StringIO('\n'.join(stdout[sidx:eidx+1]))
            #y = yaml.safe_load(strs)
            #print(y)
            #print(y.get('Statistics (avg)').get('WaitingTime'))

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

        print("%d: received %d" % (rank, len(data)))
        #for i, (k, v) in enumerate(data.items()):
        #    with open(path.join(dir.name, k), "w") as f:
        #        f.write(v)

        sstdout = []
        with subprocess.Popen(
            args = ['./worker.sh', '--mongo=%s:1234/test_db' % args.mongo, '--poll-interval=0.1', '--last-job-timeout=1.0'],
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT
        ) as proc:
            endtime = time.time() + 30
            while True:
                l = proc.stdout.readline()
                if l is None: break
                l = l.decode('utf-8').splitlines()[0]
                print("%d: %s" % (rank, l))

                sstdout.append(l)
                if 'no job found' not in l:
                    endtime = time.time() + 30
                if time.time() > endtime:
                    break
            print('%d: no work left, exiting' % rank)
            proc.kill()
        output = {"returncode": proc.returncode, "stdout": sstdout}
        comm.send(output, 0)

    print("%d exiting" % (rank))
