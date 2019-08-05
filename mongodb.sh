#!/bin/bash
mongod --dbpath . --port 1234 --bind_ip_all --directoryperdb --journal --noprealloc
