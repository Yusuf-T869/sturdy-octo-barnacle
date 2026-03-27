import logging
import os
import io
import json
import random
import string
import pandas as pd
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Dict, List


import azure.functions as func
from azure.storage.blob import BlobServiceClient


app = func.FunctionApp()


@dataclass
class Pools:
   cifs: List[str]
   party_ids: List[str]
   account_numbers: List[str]


def utc_now() -> datetime:
   return datetime.now(timezone.utc)


def fmt_ingestion_ts(ts: datetime) -> str:
   return ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def fmt_event_date(ts: datetime) -> str:
   return ts.date().isoformat()


def fmt_us_dt(ts: datetime) -> str:
   return ts.strftime("%m/%d/%Y %-I:%M:%S %p")


def rand_digits(n: int) -> str:
   return "".join(random.choice(string.digits) for _ in range(n))


def rand_token(n: int = 24) -> str:
   alphabet = string.ascii_letters + string.digits
   return "".join(random.choice(alphabet) for _ in range(n))


def choice_or_new(pool: List[str], new_fn, reuse_prob: float = 0.7):
   if pool and random.random() < reuse_prob:
       return random.choice(pool)
   return new_fn()


def minified_json(obj: Any) -> str:
   return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def make_raw_event(payload: Dict[str, Any]) -> str:
   outer = {"event": "POST_INSERT", "payload": minified_json(payload)}
   return minified_json(outer)


# --- Payload Generators---


def base_payload(entity_id: str, type_id: str, type_name: str, class_id: str, class_name: str, title: str, create_dt: str) -> Dict[str, Any]:
   return {
       "_entityId": entity_id, "_typeId": type_id, "_typeName": type_name,
       "_classId": class_id, "_className": class_name, "_title": title,
       "_createHistory": {"createdByUserName": "", "createDate": create_dt},
       "_fileExtension": "",
   }


def gen_notes_payload(pools: Pools, now: datetime) -> Dict[str, Any]:
   note_type = random.choice(["Customer Note", "Account Note", "Case Note"])
   create_dt = fmt_us_dt(now)
   cif = choice_or_new(pools.cifs, lambda: str(random.randint(10000, 99999)))
  
   payload = base_payload(str(9000000 + random.randint(1, 999999)), "100171", note_type, "100009", "Notes", f"Note {cif}", create_dt)
   payload.update({"cif": cif, "partyId": choice_or_new(pools.party_ids, lambda: f"P-{rand_token(10)}"), "note Text": "Mock content"})
   return payload


def generate_payload(pools: Pools, now: datetime) -> Dict[str, Any]:
   return gen_notes_payload(pools, now)


def build_rows(pools: Pools, n: int) -> pd.DataFrame:
   rows = []
   for _ in range(n):
       now = utc_now()
       payload = generate_payload(pools, now)
       rows.append({
           "RAW_EVENT": make_raw_event(payload),
           "EVENT_TYPE": "POST_INSERT",
           "EVENT_DATE": fmt_event_date(now),
           "INGESTION_TS": fmt_ingestion_ts(now),
       })
   return pd.DataFrame(rows)


# -----------------------------
# Azure Function Trigger
# -----------------------------


@app.timer_trigger(schedule="0 */2 * * * *", arg_name="myTimer", run_on_startup=False)
def timer_trigger(myTimer: func.TimerRequest) -> None:
   connect_str = os.getenv("DESTINATION_STORAGE_CONN")
   container_name = os.getenv("DESTINATION_CONTAINER_NAME")
   blob_name = os.getenv("CSV_FILENAME")


   if not connect_str or not container_name:
       logging.error("Faltan variables de entorno de Azure Storage.")
       return


   try:
       blob_service_client = BlobServiceClient.from_connection_string(connect_str)
       container_client = blob_service_client.get_container_client(container_name)
       blob_client = container_client.get_blob_client(blob_name)


       existing_df = pd.DataFrame()
       pools = Pools(cifs=[], party_ids=[], account_numbers=[])


       if blob_client.exists():
           stream = blob_client.download_blob().readall()
           existing_df = pd.read_csv(io.BytesIO(stream))
          
           cifs, pids, accts = [], [], []
           for s in existing_df["RAW_EVENT"].tail(500).tolist():
               try:
                   p = json.loads(json.loads(s)["payload"])
                   if "cif" in p: cifs.append(str(p["cif"]))
                   if "partyId" in p: pids.append(str(p["partyId"]))
                   if "account Number" in p: accts.append(str(p["account Number"]))
               except: continue
           pools = Pools(cifs=list(set(cifs)), party_ids=list(set(pids)), account_numbers=list(set(accts)))


       n = random.randint(1, 10)
       new_rows_df = build_rows(pools, n)


       final_df = pd.concat([existing_df, new_rows_df], ignore_index=True)
      
       output = io.StringIO()
       final_df.to_csv(output, index=False)
      
       blob_client.upload_blob(output.getvalue(), overwrite=True)
      
       logging.info(f"Éxito: Se agregaron {n} filas al archivo {blob_name}")


   except Exception as e:
       logging.error(f"Error en el proceso: {str(e)}")
