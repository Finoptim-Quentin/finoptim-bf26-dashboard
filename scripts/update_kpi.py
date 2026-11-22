"""Met à jour data/kpi.json à partir des opportunités Odoo taguées BF26.

Ne publie que des totaux : aucun nom de client, aucune adresse, aucun lien d'accès.
Variables d'environnement :
  ODOO_API_KEY  (obligatoire, en secret GitHub)
  ODOO_URL      (défaut https://finoptim.odoo.com)
  ODOO_DB       (optionnel)
  BF_TAG_ID     (défaut 80, le tag BF26)
  BF_OBJECTIF   (défaut 76)
"""
import json
import os
import datetime
import urllib.request
from pathlib import Path

URL = os.environ.get("ODOO_URL", "https://finoptim.odoo.com").rstrip("/")
KEY = os.environ["ODOO_API_KEY"]
DB = os.environ.get("ODOO_DB", "")
TAG_ID = int(os.environ.get("BF_TAG_ID", "80"))
OBJECTIF = int(os.environ.get("BF_OBJECTIF", "76"))
OUT = Path(__file__).resolve().parent.parent / "data" / "kpi.json"


def call(model, method, body):
    headers = {
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
    }
    if DB:
        headers["X-Odoo-Database"] = DB
    req = urllib.request.Request(
        f"{URL}/json/2/{model}/{method}",
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    if isinstance(data, dict) and "records" in data:
        data = data["records"]
    return data


def main():
    leads = call(
        "crm.lead",
        "search_read",
        {
            "domain": [["tag_ids", "in", [TAG_ID]]],
            "fields": ["name", "stage_id", "expected_revenue"],
        },
    )

    inserts = accessoires = devis = 0
    ca = 0.0
    for lead in leads:
        stage = lead.get("stage_id") or [None, ""]
        stage_name = stage[1] if isinstance(stage, list) and len(stage) > 1 else ""
        name = (lead.get("name") or "").lower()
        revenue = float(lead.get("expected_revenue") or 0)
        if stage_name in ("Won", "Accepté"):
            ca += revenue
            if "insert" in name:
                inserts += 1
            else:
                accessoires += 1
        elif stage_name == "En traitement":
            devis += 1

    payload = {
        "inserts": inserts,
        "accessoires": accessoires,
        "ca_commande": round(ca),
        "devis_en_cours": devis,
        "objectif_inserts": OBJECTIF,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
