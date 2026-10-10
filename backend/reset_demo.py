"""Reset local demo state; parser cache is preserved only on request."""
import argparse
from backend.api import reset_demo
def main()->None:
    parser=argparse.ArgumentParser();parser.add_argument("--keep-parsers",action="store_true");args=parser.parse_args()
    reset_demo(keep_parsers=args.keep_parsers);print("Demo registry and uploads cleared")
if __name__=="__main__":main()
