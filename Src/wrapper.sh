#!/bin/bash

echo "wrapper.sh executed"

#source venv/bin/activate
SUMO_HOME=/usr/share/sumo python3 TrafficSimulation.py
