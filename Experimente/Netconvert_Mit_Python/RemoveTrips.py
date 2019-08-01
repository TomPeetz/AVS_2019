#!/usr/bin/env python3

from pprint import pprint
import os
import sys
import subprocess
from pathlib import Path
import tempfile
import random
import getopt
import math

import xml.etree.ElementTree as ET

print("Lade net")

tree_net = ET.parse('cologne.net.xml')
root_net = tree_net.getroot()

print("Finde edges")

endangered_edges=[]
for child in root_net:
    if child.tag == "roundabout":
        endangered_edges += child.attrib["edges"].split(" ")
        
print("Gefundene Edges"+ str(len(endangered_edges)))

print("Lade trips")
tree_trips = ET.parse('cologne.trips.xml')
root_trips = tree_trips.getroot()

print("Suche zu löschende Trips")
trips_to_delete=[]
for child in root_trips:
    if child.tag == "trip":
        if child.attrib["from"] in endangered_edges or  child.attrib["to"] in endangered_edges:
            trips_to_delete.append(child)
            
print("Es werden: "+ str(len(trips_to_delete))+" gelöscht")
            
for trip in trips_to_delete:
    root_trips.remove(trip)
    
print("neue Datei schreiben")
tree_trips.write("modified.trips.xml")
