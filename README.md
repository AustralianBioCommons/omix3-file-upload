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

### Step2: File Downloading
```bash
Usage:
  python gen3sdk_find_record.py <DID>
```
#### Examples:
```bash
  python gen3_find_record.py PREFIX/58e1f28d-8a77-409d-8ac8-7c5cb6ffc853
```
