import subprocess
import os
import jwt
import sys
import hashlib
import zlib
import requests
from gen3.auth import Gen3Auth
from gen3.file import Gen3File
from gen3.index import Gen3Index
from urllib.parse import urlparse
# ---------- CONFIG ----------
COMMONS = "https://omix3.test.biocommons.org.au"
CREDENTIALS = "/Users/nalava/Downloads/cred5.json"
AUTHZ = ["/programs/program1/projects/synthetic_dataset_1"]  # project write access
#AUTHZ = ["/programs/program1/projects/synthetic_dataset_2"]  # project write access
# ----------------------------

def compute_hashes(filepath):
    """Compute md5, sha1, sha256, sha512, crc32, and file size"""
    hashes = {
        "md5": hashlib.md5(),
        "sha1": hashlib.sha1(),
        "sha256": hashlib.sha256(),
        "sha512": hashlib.sha512(),
    }
    crc32 = 0
    size = 0
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            size += len(chunk)
            for h in hashes.values():
                h.update(chunk)
            crc32 = zlib.crc32(chunk, crc32)
    return {
        "md5": hashes["md5"].hexdigest(),
        "sha1": hashes["sha1"].hexdigest(),
        "sha256": hashes["sha256"].hexdigest(),
        "sha512": hashes["sha512"].hexdigest(),
        "crc32c": format(crc32 & 0xFFFFFFFF, "08x"),
    }, size


def find_existing_record(index, hashes, size=None):
    """
    Try to find an existing record in Indexd using supported hashes.
    Returns the record dict if found, otherwise None.
    """
    supported_hashes = ["md5", "sha1", "sha256", "sha512"]

    for hash_type in supported_hashes:
        hash_value = hashes.get(hash_type)
        if not hash_value:
            continue
        params = {"hashes": {hash_type: hash_value}}
        if size is not None:
            params["size"] = size
        try:
            result = index.get_with_params(params=params)
            if result is None:
                print(f"Debug: No result for {hash_type}")
                continue
            # Indexd may return a single record or a dict with 'records'
            if "records" in result and result["records"]:
                record = result["records"][0]
                print(f"⚠️ Found existing record by {hash_type}: {record['did']}")
                return record
            elif "did" in result:
                print(f"⚠️ Found existing record by {hash_type}: {result['did']}")
                return result
        except requests.exceptions.HTTPError as e:
            print(f"Debug: HTTPError for {hash_type}: {e}")
            continue
        except Exception as e:
            print(f"Debug: Other error for {hash_type}: {e}")
            continue
    return None

def get_uploader(auth):
    try:
        token = auth.get_access_token()
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded.get("context", {}).get("user", {}).get("name", "unknown-user")
    except Exception:
        return "unknown-user"
def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <file_to_upload>")
        sys.exit(1)
    FILEPATH = sys.argv[1]
    if not os.path.isfile(FILEPATH):
        raise FileNotFoundError(f"File not found: {FILEPATH}")

    # Step 1: Authenticate
    auth = Gen3Auth(endpoint=COMMONS, refresh_file=CREDENTIALS)
    file_obj = Gen3File(auth)
    index = Gen3Index(auth)

    # Step 2: Compute hashes and size
    hashes, size = compute_hashes(FILEPATH)

    # Step 3: Check if file already exists
    record = find_existing_record(index, hashes, size=size)
    if record:
        print("⚠️ File already exists in Indexd. Skipping upload.")
        print(f"GUID: {record['did']}")
        print(f"S3 URL: {record['urls'][0]}")
        return

    # Step 4: Upload file to S3 via Gen3File (creates blank GUID)
    upload_info = file_obj.upload_file(FILEPATH, authz=AUTHZ)
    guid = upload_info["guid"]
    presigned_url = upload_info["url"]
    print(f"GUID assigned: {guid}")

    # Step 5: Upload file content
    with open(FILEPATH, "rb") as f:
        r = requests.put(presigned_url, data=f)
    r.raise_for_status()
    print("✅ Upload successful!")
    
    uploader_id = get_uploader(auth)

    print(uploader_id)
    # Step 6: Update blank record with hashes + size
    blank = index.get_record(guid)
    rev = blank["rev"]

    try:
        index.update_blank(
            guid=guid,
            rev=rev,
            hashes=hashes,
            size=size,
            authz=AUTHZ
        )
        print("✅ Hashes and size updated successfully!")
    except Exception as e:
        print(f"❌ Failed to update hashes/size: {e}")

    # Step 7: Update other metadata if needed
    parsed_url = urlparse(presigned_url)
    # presigned_url format: https://endpoint/bucket/key?params
    path_parts = parsed_url.path.lstrip('/').split('/', 1)
    
    if len(path_parts) >= 2:
        bucket = path_parts[0]
        key = path_parts[1]
    
    bucket_url = f"s3://{bucket}/{key}"
    print(f"Debug - S3 URL: {bucket_url}")

    print(f"Debug - S3 URL: {bucket_url}")
    urls_metadata = {bucket_url: {}}
    record = index.update_record(
        guid=guid,
        file_name=os.path.basename(FILEPATH),
        urls=[bucket_url],
        authz=AUTHZ,
        urls_metadata=urls_metadata,
	metadata={"uploader": uploader_id},
    )
    print("\n✅ Final Indexd record:")
    print(record)

if __name__ == "__main__":
    main()
