import json
import sys
from spiceypy.utils.exceptions import SpiceyError

from api import handle_request


def main():
    # La requête JSON arrive en argument ou sur stdin ; la réponse sort en JSON sur stdout
    raw = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    try:
        res = handle_request(json.loads(raw))
    except (KeyError, ValueError, TypeError, AttributeError, SpiceyError) as e:
        res = {"error": f"Requête invalide : {type(e).__name__}: {e}"}
    print(json.dumps(res, separators=(",", ":")))


if __name__ == "__main__":
    main()
