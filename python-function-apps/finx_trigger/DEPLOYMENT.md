# Deployment Guide: finx_trigger Azure Function

## Overview

`finx_trigger` is a Python Azure Function (Timer Trigger) that generates synthetic financial "note" events every 2 minutes and appends them to a CSV blob in Azure Blob Storage.

**Function:** `timer_trigger`
**Schedule:** `0 */2 * * * *` (every 2 minutes)
**Runtime:** Python 3.11
**Hosting:** Flex Consumption plan (recommended, serverless)

---

## Prerequisites

- Azure subscription with Owner or Contributor role
- Azure CLI installed (`az --version`)
- Azure Functions Core Tools v4 (`func --version`)
- Python 3.11 installed locally
- Git access to this repository

---

## Step 1: Create a Resource Group

1. Sign in to the [Azure Portal](https://portal.azure.com).
2. Search for **Resource groups** in the top search bar.
3. Click **+ Create**.
4. Fill in:
   - **Subscription:** Your subscription
   - **Resource group:** `finx-trigger-rg` (or reuse existing like `terraform-state-rg`)
   - **Region:** East US 2 (or your preferred region)
5. Click **Review + create** → **Create**.

---

## Step 2: Create a Storage Account (for Function App runtime)

The Azure Functions runtime requires a general-purpose storage account for internal state management.

1. In the Azure Portal, search for **Storage accounts**.
2. Click **+ Create**.
3. Fill in the **Basics** tab:
   - **Subscription:** Your subscription
   - **Resource group:** Select the group from Step 1
   - **Storage account name:** `finxtriggerfuncsa` (must be globally unique, 3-24 chars, lowercase)
   - **Region:** Same as resource group
   - **Performance:** Standard
   - **Redundancy:** Locally-redundant storage (LRS)
4. Click **Review + create** → **Create**.

---

## Step 3: Create a Storage Account (for destination CSV blob)

This is where the generated CSV data lands.

1. Repeat Step 2 with a different name, e.g., `finxtriggerdestsa`.
2. After creation, go to the storage account → **Containers** → **+ Container**.
3. Create a container:
   - **Name:** `finx-trigger-data` (or your preferred name)
   - **Anonymous access level:** Private (no anonymous access)
4. Note the container name — you'll need it for app settings.

---

## Step 4: Get the Destination Storage Connection String

1. Navigate to the destination storage account (`finxtriggerdestsa`).
2. In the left menu, go to **Security + networking** → **Access keys**.
3. Click **Show** next to `key1` → **Connection string**.
4. Copy the connection string. It looks like:
   ```
   DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net
   ```
5. Save this — it becomes the `DESTINATION_STORAGE_CONN` app setting.

---

## Step 5: Create the Function App (Flex Consumption Plan)

1. In the Azure Portal, click **Create a resource**.
2. Search for **Function App** → click **Create**.
3. On the **Select a hosting option** page, choose **Flex Consumption** → click **Select**.

### Basics Tab

| Field | Value |
|---|---|
| Subscription | Your subscription |
| Resource group | `finx-trigger-rg` (from Step 1) |
| Function App name | `finx-trigger-func` (globally unique, becomes `finx-trigger-func.azurewebsites.net`) |
| Runtime stack | **Python** |
| Version | **3.11** |
| Region | Same as resource group |
| Instance size | **2048 MB** (default, sufficient for pandas) |

### Storage Tab

- **Storage account:** Select the runtime storage account from Step 2 (`finxtriggerfuncsa`).

### Monitoring Tab

- **Enable Application Insights:** Yes
- **Application Insights:** Create new or select existing

### Authentication Tab

- **Authentication type:** **Managed identity** (recommended for secure access without secrets where possible).

4. Click **Review + create** → **Create**.
5. Wait for deployment to complete. Click **Go to resource**.

---

## Step 6: Configure Application Settings

The function requires three environment variables to run.

1. In your Function App page, go to **Settings** → **Environment variables**.
2. Click **+ Add** and enter the following:

| Name | Value |
|---|---|
| `DESTINATION_STORAGE_CONN` | Connection string from Step 4 |
| `DESTINATION_CONTAINER_NAME` | `finx-trigger-data` (or your container name) |
| `CSV_FILENAME` | `finx_trigger_events.csv` (or your preferred filename) |

3. Click **Apply** → **Confirm** to save.

> **Note:** `AzureWebJobsStorage` and `FUNCTIONS_WORKER_RUNTIME` are automatically configured by Azure when you create the Function App. Do not override them.

---

## Step 7: Deploy the Code (Zip Deploy via Azure CLI)

### Option A: Manual Deploy (CLI)

From the project root:

```bash
cd python-function-apps/finx_trigger

# Package the function app (exclude local dev files)
zip -r finx-trigger-function.zip . \
  -x ".git/*" ".vscode/*" "__pycache__/*" "*.pyc" ".DS_Store" "local.settings.json"

# Deploy with remote build (handles pip install of requirements.txt)
az functionapp deployment source config-zip \
  --name finx-trigger-func \
  --resource-group finx-trigger-rg \
  --src finx-trigger-function.zip \
  --build-remote true
```

The `--build-remote true` flag tells Azure to install dependencies from `requirements.txt` on the server.

### Option B: Azure DevOps Pipeline (CI/CD)

The included `azure-pipelines.yml` automates this. To set it up:

1. In Azure DevOps, go to **Pipelines** → **New pipeline**.
2. Select your repository.
3. Choose **Existing Azure Pipelines YAML file**.
4. Set the path to `python-function-apps/finx_trigger/azure-pipelines.yml`.
5. Update the pipeline variables if needed:
   - `azureServiceConnection`: Your Azure service connection name
   - `functionAppName`: `finx-trigger-func`
   - `resourceGroup`: Your resource group name
6. Save and run.

---

## Step 8: Verify the Deployment

### Via Azure Portal

1. Navigate to your Function App → **Functions** in the left menu.
2. You should see `timer_trigger` listed.
3. Click on `timer_trigger` → **Code + Test**.
4. Click **Test/Run** → **Run** to manually trigger the function.
5. Check the **Logs** panel at the bottom for output like:
   ```
   Éxito: Se agregaron N filas al archivo finx_trigger_events.csv
   ```

### Via Azure CLI

```bash
# View recent logs
az functionapp log tail --name finx-trigger-func --resource-group finx-trigger-rg

# Check function status
az functionapp function list --name finx-trigger-func --resource-group finx-trigger-rg --output table
```

### Verify the Output Blob

1. Go to your destination storage account → **Containers** → `finx-trigger-data`.
2. You should see `finx_trigger_events.csv` appearing after the first successful run.
3. Download and open it. Expected columns: `RAW_EVENT`, `EVENT_TYPE`, `EVENT_DATE`, `INGESTION_TS`.

---

## Step 9: Monitor and Troubleshoot

### Application Insights

1. In your Function App, go to **Monitoring** → **Application Insights**.
2. Use **Live Metrics** to see real-time invocations.
3. Use **Logs (Analytics)** to query failures:
   ```kusto
   traces
   | where cloud_RoleName == "finx-trigger-func"
   | where severityLevel >= 2
   | order by timestamp desc
   | take 50
   ```

### Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| Function not appearing after deploy | Zip missing `host.json` or `requirements.txt` | Re-package and redeploy |
| `ModuleNotFoundError: No module named 'pandas'` | Remote build failed | Check `requirements.txt` is in the zip root; redeploy with `--build-remote true` |
| `AzureWebJobsStorage` error | Runtime storage not configured | Check Function App → Configuration → `AzureWebJobsStorage` |
| Timer not firing | Schedule syntax error | Verify NCRONTAB format: `0 */2 * * * *` (6 fields, seconds first) |
| Blob write errors | Connection string wrong or container missing | Verify `DESTINATION_STORAGE_CONN` and `DESTINATION_CONTAINER_NAME` |

---

## File Structure Reference

```
finx_trigger/
├── function_app.py          # Main function code (timer_trigger)
├── host.json                # Azure Functions host configuration
├── local.settings.json      # Local dev settings (git-ignored)
├── requirements.txt         # Python dependencies
├── azure-pipelines.yml      # CI/CD pipeline definition
├── .gitignore               # Git ignore rules
└── DEPLOYMENT.md            # This file
```

---

## Environment Variables Summary

| Variable | Where Set | Purpose |
|---|---|---|
| `DESTINATION_STORAGE_CONN` | App Settings (Portal/CLI) | Azure Storage connection string for destination blob |
| `DESTINATION_CONTAINER_NAME` | App Settings (Portal/CLI) | Blob container name for the CSV output |
| `CSV_FILENAME` | App Settings (Portal/CLI) | Name of the CSV blob file |
| `AzureWebJobsStorage` | Auto-configured | Runtime storage for Azure Functions internal state |
| `FUNCTIONS_WORKER_RUNTIME` | Auto-configured | Set to `python` |

---

## Cleanup

To delete all resources:

```bash
az group delete --name finx-trigger-rg --yes --no-wait
```

Or in the Azure Portal: Resource groups → `finx-trigger-rg` → **Delete resource group**.
