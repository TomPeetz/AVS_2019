from os import path
from io import StringIO
from ModMap import *
from pprint import pprint
import yaml
import shutil
import traceback
import json


def prepare(x, debug):
    sourcenet = path.abspath(path.join('..', '..', 'Experimente/Netconvert_Mit_Python/Maps/Minimal/SUMO_Netz', 'minimal.net.xml'))
    sourcesim = path.abspath(path.join('..', '..', 'Experimente/Netconvert_Mit_Python/Maps/Minimal/SUMO_Netz'))

    with open(path.join('..', 'searchspace.json'), 'r') as f:
        json_data = json.loads(f.read())


    netconv = load_netconvert_binary()
    tmpd, plain_files = cnvt_net_to_plain(net_path=sourcenet,
                      netcnvt_bin=netconv,
                      plain_output_prefix='test')
    for nodeId, mod in x:
        if nodeId.startswith('i-'):
            nid = nodeId.replace('i-', '')
            if (mod == 'intersection_priority'):
                debug.write("Not modifying intersection %s\n" % nid)
                continue
            debug.write("Changing intersection %s to roundabout\n" % nid)
            change_node_to_roundabout(nid, '', plain_files=plain_files)
        elif nodeId.startswith('r-'):
            nid = nodeId.replace('r-', '')
            if (mod == 'roundabout'):
                debug.write("Not modifying roundabout %s\n" % nid)
                continue
            debug.write("Changing roundabout %s to intersection\n" % nid)
            rdata = next(x for x in json_data['roundabouts'] if x['id'] == nid)

            # TODO: specify priority
            change_roundabout_to_node(rdata['edges'], rdata['nodes'], '', plain_files=plain_files)

    tmpsim = path.join(tmpd, 'Simulation')
    modifiednet = path.join(tmpsim, 'minimal.net.xml')

    shutil.copytree(sourcesim, tmpsim)
    cnvt_plain_to_net(netcnvt_bin=netconv, plain_files=plain_files, new_net_path=modifiednet, verbose=False)

    trips = path.join(tmpsim, 'trips.trips.xml')

    subprocess.Popen(args = ['/usr/share/sumo/tools/randomTrips.py', '-n', modifiednet, '-o', trips]).wait()

    return path.join(tmpsim, 'test.sumocfg')


def sumo(x):
    f = open("debug.log", "w")

    try:
        f.write("Decision vector:\n")
        pprint(x, f)
        f.write("\n")

        cfg = prepare(x, f)
        args = ["sumo", "-c", cfg, "--threads", "1"]

        with subprocess.Popen(args,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as proc:
            stdout, stderr = proc.communicate()
            f.write("\nstdout\n")
            f.write(stdout.decode('utf-8'))
            f.write("\nstderr\n")
            f.write(stderr.decode('utf-8'))
            f.write("\n")

            stdout = list(map(lambda x: x, stdout.decode('utf-8').splitlines()))
            #stderr = stderr.decode('utf-8').splitlines()

        sidx = list(map(lambda x: 'Statistics (avg):' in x, stdout)).index(True)
        eidx = list(map(lambda x: 'DepartDelay' in x, stdout)).index(True)
        strs = StringIO('\n'.join(stdout[sidx:eidx+1]))
        y = yaml.safe_load(strs)

        f.write("Statistics:\n")
        pprint(y, f)
        f.write("\n")

        f.write("Returning: ")
        f.write(str(y.get('Statistics (avg)').get('WaitingTime')))
        f.write("\n")

        return y.get('Statistics (avg)').get('TimeLoss')

    except Exception as e:
        f.write("\nException:\n")
        #pprint(e, f)
        traceback.print_exc(file=f)
    finally:
        f.close()
