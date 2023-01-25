from importlib import import_module
from multiprocessing import Process


def proc_function(): 
    import_module("dive")

def start_bot_process():

    """
    import dive.py from another process
    """

    proc = Process(target=proc_function)

    proc.start()