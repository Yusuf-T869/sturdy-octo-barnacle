import logging
import os
import io
import json
import pandas as pd
import azure.functions as func
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()
# Special task update from pipelines

@app.event_grid_trigger(arg_name="event")
def event_grid_blob_trigger(event: func.EventGridEvent):
   # 1. Gain access to the blob URL from the event data
   event_data = event.get_json()
   blob_url = event_data.get("url")
  
   if not blob_url or ".csv" not in blob_url:
       return
       
   # Extract container name and blob name from the URL
   parts = blob_url.split('/')
   container_name = parts[3]
   blob_name = "/".join(parts[4:])
   
   connect_str = os.getenv("DESTINATION_STORAGE_CONN")
   output_container = "output-finxact"

   try:
       blob_service_client = BlobServiceClient.from_connection_string(connect_str)
      
       # --- Download CSV and Load into DataFrame ---
       blob_client_input = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
       stream = blob_client_input.download_blob().readall()
       df = pd.read_csv(io.BytesIO(stream))
       
       # Initialize control column if it doesn't exist
       if 'PROCESSED' not in df.columns:
           df['PROCESSED'] = False
           
       # --- Step 2: Filter Only New Rows ---
       # Filter where PROCESSED is False or NaN
       new_rows = df[df['PROCESSED'].fillna(False) == False].copy()
       
       if new_rows.empty:
           logging.info("No se encontraron filas nuevas para procesar.")
           return
           
       logging.info(f"Detectadas {len(new_rows)} filas nuevas. Iniciando generación de archivos individuales...")
       
       # --- Step 3: Generate One File Per Row ---
       container_output_client = blob_service_client.get_container_client(output_container)
      
       for index, row in new_rows.iterrows():
           # Convert row to dict for JSON export
           data_to_export = row.to_dict()
          
           # Clean up the data: remove NaN and convert to string if necessary
           data_to_export.pop('PROCESSED', None)
           
           # Define filename based on an identifier (e.g., entity_id or index)
           entity_id = data_to_export.get('_entityId', f"row_{index}")
           filename = f"event_{entity_id}.json"
           
           # Subir el archivo individual
           msg_content = json.dumps(data_to_export, indent=4)
           output_blob_client = container_output_client.get_blob_client(filename)
           output_blob_client.upload_blob(msg_content, overwrite=True)
           
       # --- Step 4: Mark as Processed and Update Source ---
       df.loc[new_rows.index, 'PROCESSED'] = True
      
       output_csv = io.StringIO()
       df.to_csv(output_csv, index=False)
       
       # Overwrite the original CSV with the flags set to True
       blob_client_input.upload_blob(output_csv.getvalue(), overwrite=True)
      
       logging.info(f"Finalizado: {len(new_rows)} archivos creados en '{output_container}'.")
       
   except Exception as e:
       logging.error(f"Error en el procesamiento individual: {str(e)}")