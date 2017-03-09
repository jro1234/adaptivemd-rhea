"""
Python script for the RPC Python call for Adaptive MD

This executes a function remotely and expects an `input.json` file to contain
a reference to the function and module as well as arguments and keyword arguments
"""


import importlib
from adaptivemd.mongodb import ObjectJSON

simplifier = ObjectJSON()

with open('input.json', 'r') as f:
    data = simplifier.from_json(f.read())

parts = data['function'].split('.')

fnc = importlib.import_module('.'.join(parts[:-1]))

fnc = getattr(fnc, parts[-1])

result = fnc(*data['args'], **data['kwargs'])

with open('output.json', 'w') as f:
    f.write(simplifier.to_json(result))