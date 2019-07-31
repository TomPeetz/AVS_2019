# AVS_2019

Benötigt wird: openmpi, sumo, libpython

Ebenfalls alle in requirements.txt genannten python packages

Das script randomTrips.py von sumo in /usr/share/sumo/tools/

Zuerst wird für die genutzte Karte der Search Space erzeugt

```
python GenerateSearchSpace.py
```
Dies erzeugt die Datei searchspace.json, in der alle möglichen Variationen gelistet sind

```
mpiexec -np 3 python TrafficSimulation.py
```
Führt die Simulation mit 2 Workern aus
