#!/bin/bash
mongod --dbpath mongodb --port 1234 --bind_ip_all --directoryperdb --journal --noprealloc
