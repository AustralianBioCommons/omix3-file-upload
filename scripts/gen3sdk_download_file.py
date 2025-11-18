#!/usr/bin/env python3
"""
gen3sdk_download_file.py - Download files from Gen3 with S3-compatible storage
"""

import os
import sys
import requests
from gen3.auth import Gen3Auth
from gen3.file import Gen3File
from gen3.index import Gen3Index

# ---------- CONFIG ----------
COMMONS = "https://omix3.test.biocommons.org.au"
CREDENTIALS = "/path/to/the/cred.json"
# ----------------------------

def download_file_by_guid(guid, output_dir="./downloads"):
    """
    Download a file from Gen3 by its GUID.
    
    Args:
        guid: The file GUID/DID to download
        output_dir: Directory where the file will be saved
    """
    # Step 1: Authenticate
    auth = Gen3Auth(endpoint=COMMONS, refresh_file=CREDENTIALS)
    file_obj = Gen3File(auth)
    index = Gen3Index(auth)
    
    # Step 2: Get file metadata from Indexd
    print(f"📥 Fetching metadata for GUID: {guid}")
    try:
        record = index.get_record(guid)
    except Exception as e:
        print(f"❌ Failed to get record from Indexd: {e}")
        return None
    
    # Step 3: Extract file information
    filename = record.get("file_name", guid)
    urls = record.get("urls", [])
    size = record.get("size", 0)
    hashes = record.get("hashes", {})
    
    if not urls:
        print(f"❌ No URLs found for GUID {guid}")
        return None
    
    print(f"📄 File name: {filename}")
    print(f"📦 Size: {size} bytes")
    print(f"🔗 S3 URL: {urls[0]}")
    
    # Step 4: Get presigned download URL from Fence
    print(f"🔑 Generating presigned download URL...")
    try:
        #presigned_url = file_obj.get_presigned_url(guid, protocol="s3")
        #print(f"✅ Presigned URL obtained")
        presigned_response = file_obj.get_presigned_url(guid, protocol="s3")
        # Extract URL from response dict
        if isinstance(presigned_response, dict):
            presigned_url = presigned_response.get('url')
        else:
            presigned_url = presigned_response
            
        if not presigned_url:
            print(f"❌ No URL in presigned response: {presigned_response}")
            return None
            
        print(f"✅ Presigned URL obtained")
        print(f"🔗 URL (first 100 chars): {presigned_url[:100]}...")
    except Exception as e:
        print(f"❌ Failed to get presigned URL: {e}")
        return None
    
    # Step 5: Download the file
    print(f"⬇️  Downloading file...")
    try:
        response = requests.get(presigned_url, stream=True)
        response.raise_for_status()
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save file
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    # Show progress
                    if size > 0:
                        progress = (downloaded / size) * 100
                        print(f"\rProgress: {progress:.1f}%", end="")
        
        print(f"\n✅ Successfully downloaded to: {output_path}")
        
        # Step 6: Verify download (optional)
        if size > 0:
            actual_size = os.path.getsize(output_path)
            if actual_size != size:
                print(f"⚠️  Warning: Size mismatch. Expected {size}, got {actual_size}")
            else:
                print(f"✅ Size verified: {size} bytes")
        
        # Verify hash if MD5 is available
        if "md5" in hashes:
            import hashlib
            print(f"🔍 Verifying MD5 hash...")
            md5 = hashlib.md5()
            with open(output_path, 'rb') as f:
                while chunk := f.read(8192):
                    md5.update(chunk)
            actual_md5 = md5.hexdigest()
            expected_md5 = hashes["md5"]
            
            if actual_md5 == expected_md5:
                print(f"✅ MD5 verified: {actual_md5}")
            else:
                print(f"❌ MD5 mismatch!")
                print(f"   Expected: {expected_md5}")
                print(f"   Got:      {actual_md5}")
        
        return output_path
        
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error during download: {e}")
        print(f"   Status code: {e.response.status_code}")
        print(f"   Response: {e.response.text[:200]}")
        return None
    except Exception as e:
        print(f"\n❌ Error during download: {e}")
        return None


def download_multiple_files(guids, output_dir="./downloads"):
    """
    Download multiple files by their GUIDs.
    
    Args:
        guids: List of GUIDs to download
        output_dir: Directory where files will be saved
    """
    print(f"📥 Downloading {len(guids)} files...\n")
    
    successful = []
    failed = []
    
    for i, guid in enumerate(guids, 1):
        print(f"\n{'='*60}")
        print(f"File {i}/{len(guids)}: {guid}")
        print(f"{'='*60}")
        
        result = download_file_by_guid(guid, output_dir)
        
        if result:
            successful.append(guid)
        else:
            failed.append(guid)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Download Summary")
    print(f"{'='*60}")
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    
    if failed:
        print(f"\nFailed GUIDs:")
        for guid in failed:
            print(f"  - {guid}")


def main():
    if len(sys.argv) < 2:
        print(f"Usage:")
        print(f"  Single file:   python {sys.argv[0]} <GUID> [output_dir]")
        print(f"  Multiple files: python {sys.argv[0]} <GUID1> <GUID2> ... [output_dir]")
        print(f"\nExamples:")
        print(f"  python {sys.argv[0]} 0479c9c6-89bc-4717-8952-763ccb555eba")
        print(f"  python {sys.argv[0]} guid1 guid2 guid3 ./my_downloads/")
        sys.exit(1)
    
    # Parse arguments
    guids = []
    output_dir = "./downloads"
    
    for arg in sys.argv[1:]:
        # Check if it's a directory path
        if "/" in arg or arg.startswith("."):
            output_dir = arg
        else:
            guids.append(arg)
    
    if not guids:
        print("❌ No GUIDs provided")
        sys.exit(1)
    
    # Download
    if len(guids) == 1:
        download_file_by_guid(guids[0], output_dir)
    else:
        download_multiple_files(guids, output_dir)


if __name__ == "__main__":
    main()
