import json
from api import handle_request   # api.py charge les kernels tout seul

if __name__ == "__main__":
    res = handle_request({
        "date": "22/12/2026",
        "criteria": [
            {"type": "illumination", "op": ">", "value": 50},
            {"type": "illumination", "op": "<", "value": 100},
        ],
        "mode": "all",
        "advanced": {"grid_step_deg": 1, "range_days": 1, "step_hours": 3},
    })

    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(res, f, separators=(",", ":"))

    print("result.json écrit :", res["n_tested"], "points testés,",
          res["n_matching"], "retenus")