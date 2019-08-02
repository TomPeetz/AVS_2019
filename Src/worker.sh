#!/usr/bin/env python3
import sys
import hyperopt.mongoexp
import logging
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
print(sys.argv)
sys.exit(hyperopt.mongoexp.main_worker())
