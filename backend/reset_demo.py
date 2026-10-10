"""Reset local demo state; parser cache is preserved only on request."""
import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.api import reset_demo
def main()->None:
    parser=argparse.ArgumentParser();parser.add_argument("--keep-parsers",action="store_true");args=parser.parse_args()
    reset_demo(keep_parsers=args.keep_parsers);print("Demo registry and uploads cleared")
if __name__=="__main__":main()
