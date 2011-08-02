import sys
import time
sys.path.insert(1, '.')

from bein import *
from bein import store
from bein import check


@memoize(store.value, check.value)
def square(ex, x):
    time.sleep(3)
    return x*x

@memoize(store.file)
def write_hello(ex, filename=None):
    if filename == None:
        filename = unique_filename_in()
    with open(filename, 'w') as f:
        print >>f, "Hello!"
    return filename

M = MiniLIMS("testing_lims")

with execution(M) as ex:
    print square(ex, 3)
    f = write_hello(ex)
    with open(f) as q:
        for l in q:
            print l
    
