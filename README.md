# AVS_2019

Benötigt wird: openmpi, sumo, libpython, mongodb

Ebenfalls alle in requirements.txt genannten python packages

mongodb starten
```
mongod --dbpath . --port 1234 --directoryperdb --journal --noprealloc
```

Zuerst wird für die genutzte Karte der Search Space erzeugt

```
python GenerateSearchSpace.py
```
Dies erzeugt die Datei searchspace.json, in der alle möglichen Variationen gelistet sind

```
mpiexec -np 3 python TrafficSimulation.py
```
Führt die Simulation mit 2 Workern aus
