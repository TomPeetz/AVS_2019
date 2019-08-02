from os import path
from io import StringIO
from ModMap import *
from pprint import pprint
# ~ import yaml
import shutil
import traceback
import json


def prepare(x, debug):
    sourcenet = path.abspath(path.join('..', 'TAPASCologne-0.32.0/', 'cologne.net.xml'))
    sourcesim = path.abspath(path.join('..', 'TAPASCologne-0.32.0/'))
    #sourcenet = path.abspath(path.join('..', 'map', 'minimal.net.xml'))
    #sourcesim = path.abspath(path.join('..', 'map'))

    # ~ debug.write("Net %s\n" % sourcenet)

    with open(path.join('searchspace.json'), 'r') as f:
        json_data = json.loads(f.read())


    netconv = load_netconvert_binary()
    tmpd, plain_files = cnvt_net_to_plain(net_path=sourcenet,
                      netcnvt_bin=netconv,
                      plain_output_prefix='test')

    netrepr = Net_Repr(plain_files)

    for nodeId, mod in x:
        if nodeId.startswith('i-'):
            nid = nodeId.replace('i-', '')
            # ~ if (mod == 'intersection_priority'):
                # ~ debug.write("Not modifying intersection %s\n" % nid)
                # ~ continue
            # ~ debug.write("Changing intersection %s to roundabout\n" % nid)
            mod_params = mod.split(" ")
            op, *_ = mod_params
            if op == "do_nothing":
                pass
            elif op == "right_before_left":
                change_intersection_to_right_before_left(nid, netrepr)
            elif op == "traffic_light_right_on_red":
                change_intersection_to_traffic_light_right_on_red(nid, netrepr)
            elif op == "traffic_light":
                change_intersection_to_traffic_light(nid, netrepr)
            elif op == "roundabout":
                change_intersection_to_roundabout(nid, op, e_id_1, e_id_2, netrepr)
            elif op == "priority":
                _, e_id_1, e_id_2 = mod_params
                change_intersection_right_of_way(nid, op, e_id_1, e_id_2, netrepr)
            elif op == "priority_stop":
                _, e_id_1, e_id_2 = mod_params
                change_intersection_right_of_way(nid, op, e_id_1, e_id_2, netrepr)
            else:
                pass
            
            # ~ change_node_to_roundabout(nid, netrepr)
        elif nodeId.startswith('r-'):
            nid = nodeId.replace('r-', '')
            # ~ if (mod == 'roundabout'):
                # ~ debug.write("Not modifying roundabout %s\n" % nid)
                # ~ continue
            # ~ debug.write("Changing roundabout %s to intersection\n" % nid)
            
            mod_params = mod.split(" ")
            op, *_ = mod_params
            rdata = next(x for x in json_data['roundabouts'] if x['id'] == nid)
            
            if op == "do_nothing":
                pass
            elif op == "right_before_left":
               change_roundabout_to_right_before_left(' '.join(rdata['edges']), ' '.join(rdata['nodes']), netrepr)
            elif op == "traffic_light_right_on_red":
                change_roundabout_to_traffic_light_right_on_red(' '.join(rdata['edges']), ' '.join(rdata['nodes']), netrepr)
            elif op == "traffic_light":
                change_roundabout_to_traffic_light(' '.join(rdata['edges']), ' '.join(rdata['nodes']), netrepr)
            elif op == "priority":
                _, e_id_1, e_id_2 = mod_params
                change_roundabout_right_of_way(' '.join(rdata['edges']), ' '.join(rdata['nodes']), op, e_id_1, e_id_2, netrepr)
            elif op == "priority_stop":
                _, e_id_1, e_id_2 = mod_params
                change_roundabout_right_of_way(' '.join(rdata['edges']), ' '.join(rdata['nodes']), op, e_id_1, e_id_2, netrepr)
            else:
                pass
            
            

            # TODO: specify priority
            # ~ change_roundabout_to_node(' '.join(rdata['edges']), ' '.join(rdata['nodes']), netrepr)

    tmpsim = path.join(tmpd, 'Simulation')
    modifiednet = path.join(tmpsim, 'minimal.net.xml')
    pprint(tmpsim)
    shutil.copytree(sourcesim, tmpsim)
    netrepr.write_to_plain()
    cnvt_plain_to_net(netcnvt_bin=netconv, plain_files=plain_files, new_net_path=modifiednet, verbose=False)

    # ~ trips = path.join(tmpsim, 'trips.trips.xml')

    # ~ subprocess.Popen(args = [os.path.join(os.environ['SUMO_HOME'], 'tools', 'randomTrips.py'), '-n', modifiednet, '-o', trips]).wait()

    return path.join(tmpsim, 'test.sumocfg')


def sumo(x):
    f = open("debug.log", "w")

    try:
        f.write("Decision vector:\n")
        pprint(x, f)
        f.write("\n")

        cfg = prepare(x, f)
        args = ["sumo", "-c", cfg]#, "--threads", "1"]

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
