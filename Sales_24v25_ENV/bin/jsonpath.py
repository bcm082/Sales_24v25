#!/Users/brunomartins/Documents/brunodev/Sales_24v25/Sales_24v25_ENV/bin/python3.12
import sys
from jsonpath_rw.bin.jsonpath import entry_point
if __name__ == '__main__':
    if sys.argv[0].endswith('.exe'):
        sys.argv[0] = sys.argv[0][:-4]
    sys.exit(entry_point())
