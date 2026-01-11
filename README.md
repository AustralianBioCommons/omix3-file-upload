# OMIX3 File Upload and Indexd Script

This repository contains a Python script to upload files to OMIX3 storage and update Indexd records using the Gen3 SDK.

---

## Prerequisites

1. **Gen3 Credentials**: You must have a cred.json file containing your Gen3 API token with appropriate write permissions to the target project.
2. **Access to S3 Bucket**: Ensure that your Gen3 project is configured with an S3 bucket where files can be uploaded.
3. **Python Environment**: Python 3.10+ is recommended.
---

## Python Environment Setup

### Step 1: Create a virtual environment

```bash
python3 -m venv ~/gen3_env
```
### Step 2: Activate the environment

## Linux/macOS:

```bash
source ~/gen3_env/bin/activate
```

## Windows:

```bash
gen3_env\Scripts\activate
```
### Step 3: Install required packages
```bash
pip install -r requirements.txt
```

#### Packages used in the script:

1. gen3.auth and gen3.file (from gen3)
2. requests (for HTTP uploads)
3. PyJWT (for decoding token information)
4. boto3, botocore, jmespath, s3transfer (if using S3 uploads)

## Script Usage
### Step1: Configure credentials

In the script ( scripts/gen3sdk_upload_file.py ), there is a variable called CREDENTIALS that points to your Gen3 credentials file:

```bash
CREDENTIALS = "/path/to/the/cred.json"
```
➡️ Update this path to point to your actual Gen3 credentials file before running the script.

### Step 1: Run the script
```bash
python scripts/gen3sdk_upload_file.py <file_to_upload>
```
#### Example:
```bash
python scripts/gen3sdk_upload_file.py ~/path/to/test_s3_in_01.txt
```

### Step2: File Downloading
```bash
Usage:
  Single file:   python gen3sdk_download_file.py <GUID> [output_dir]
  Multiple files: python gen3sdk_download_file.py <GUID1> <GUID2> ... [output_dir]
```
#### Examples:
```bash
  python gen3sdk_download_file.py 0479c9c6-89bc-4717-8952-763ccb555eba
  python gen3sdk_download_file.py guid1 guid2 guid3 ./my_downloads/
```

### Step3: Find File
```bash
Usage:
  python gen3sdk_find_record.py <DID>
```
#### Examples:
```bash
  python gen3_find_record.py PREFIX/58e1f28d-8a77-409d-8ac8-7c5cb6ffc853
```
-------------------

## Project Admin Utilities

This repository includes utility scripts for updating project metadata values in the Gen3 Data Commons and synchronizing Discovery UI configuration. These scripts are intended for administrators with Gen3 credentials.

### 1. Update availability
#### Purpose
update_availability.py updates the availability_type property of a Gen3 project (e.g., Open, Restricted) via the Gen3 Submission GraphQL interface.
This is useful when changing dataset access levels after ingesting data or after policy decisions.
#### Example Usage
```bash
python update_availability.py \
  -p program1 \
  -j synthetic_dataset_3 \
  -a Restricted \
  -c ~/path/to/the/credentials.json
```
#### Expected Output
The script fetches current metadata, applies the new value, and then prints the updated project information.

### 2. Sync to Discovery
#### Purpose
sync_explorer_to_discovery.py synchronizes metadata from the Explorer configuration and Elasticsearch index into the Discovery UI backend. This ensures that datasets updated via ETL or availability changes are reflected in the Discovery UI.
Before running the sync script, update CREDENTIALS_FILE inside:
```bash
sync_explorer_to_discovery.py
```
#### Example:
```bash
CREDENTIALS_FILE = "/path/to/credentials.json"
```
Then run:
```bash
python sync_explorer_to_discovery.py
```
### 3. Services that must be restarted
Changes to availability_type, project metadata, or Discovery data require a refresh of certain Gen3 components.
Depending on deployment method (Helm, ArgoCD, docker-compose), restart:
```bash
sheepdog
peregrine
etl
guppy
frontend
```
### 4. Verifying Updates in the UI
After restarts, changes will be visible in:
#### ✔ Discovery UI
Check for:
updated availability_type badge (e.g., Restricted / Open)
updated dataset metadata
updated project card visibility
#### ✔ GraphQL (Peregrine)
Query project or program to confirm the metadata:

#### Example:
```bash
query {
  project(accessibility: accessible){
    name
    availability_type
  }
}
```
