#!/usr/bin/env python3
"""
Sync Gen3 structured data (Explorer/Guppy) to Discovery metadata (MDS)
"""
import requests
import json
import sys
from gen3.auth import Gen3Auth

# Configuration
BASE_URL = "https://omix3.test.biocommons.org.au"
CREDENTIALS_FILE = "/path/to/the/credentials.json"

def get_auth_token():
    """Get authentication token using Gen3Auth"""
    try:
        print(f"📂 Loading credentials from: {CREDENTIALS_FILE}")
        auth = Gen3Auth(endpoint=BASE_URL, refresh_file=CREDENTIALS_FILE)
        token = auth.get_access_token()
        print("✅ Token generated successfully")
        return token
    except Exception as e:
        print(f"❌ Error loading credentials: {e}")
        sys.exit(1)

def fetch_projects_from_explorer(token):
    """Query structured data via GraphQL - with availability_type!"""
    query = """
    query {
      project(first: 0) {
        project_id
        name
        code
        short_name
        full_name
        project_description
        availability_type
        availability_mechanism
        dbgap_accession_number
        data_access_url
        consent_codes
        state
        released
        _subjects_count
      }
    }
    """
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/api/v0/submission/graphql",
        json={"query": query},
        headers=headers
    )
    
    print(f"Response Status: {response.status_code}")
    
    try:
        response_json = response.json()
        
        # Check for errors
        if "errors" in response_json:
            print(f"GraphQL Errors: {json.dumps(response_json['errors'], indent=2)}")
            sys.exit(1)
        
        # Check if we have data
        if "data" in response_json and response_json["data"]:
            projects = response_json["data"]["project"]
            return projects
        else:
            print(f"No data returned: {response_json}")
            return []
            
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        print(f"Raw response: {response.text}")
        sys.exit(1)

def transform_to_discovery_format(projects):
    """Convert structured data to MDS discovery format"""
    discovery_records = []
    
    for project in projects:
        project_code = project.get("code", project.get("short_name", project.get("name", "unknown")))
        
        # Use availability_type from the project data
        availability_type = project.get("availability_type") or "Not Available"
        
        # Build summary from available fields
        summary_parts = []
        if project.get("project_description"):
            summary_parts.append(project["project_description"])
        else:
            summary_parts.append(f"Dataset: {project.get('full_name') or project.get('name', '')}")
        
        if project.get("_subjects_count", 0) > 0:
            summary_parts.append(f"Contains {project['_subjects_count']} subjects.")
        
        summary = " ".join(summary_parts)
        
        # Build tags
        tags = ["auto-synced", "explorer"]
        if availability_type:
            tags.append(availability_type.lower().replace(" ", "-"))
        if project.get("state"):
            tags.append(project["state"].lower())
        if project.get("consent_codes"):
            tags.extend(project["consent_codes"])
        
        discovery_records.append({
            "guid": f"omix3-{project_code}",
            "data": {
                "_guid_type": "discovery_metadata",
                "gen3_discovery": {
                    "study_title": project.get("full_name") or project.get("name", ""),
                    "name": project_code,
                    "short_name": project.get("short_name"),
                    "summary": summary,
                    "project_id": project["project_id"],
                    "project_description": project.get("project_description"),
                    "_subjects_count": project.get("_subjects_count", 0),
                    "year": "2025",
                    "availability_type": availability_type,
                    "availability_mechanism": project.get("availability_mechanism"),
                    "data_access_url": project.get("data_access_url"),
                    "dbgap_accession": project.get("dbgap_accession_number"),
                    "consent_codes": project.get("consent_codes", []),
                    "state": project.get("state"),
                    "released": project.get("released"),
                    "tags": tags,
                    "link": f"{BASE_URL}/Discovery?study={project_code}",
                    "study_url": f"{BASE_URL}/Explorer?node_type=project&project_id={project['project_id']}"
                },
                "authz": [f"/programs/program1/projects/{project_code}"]
            }
        })
    
    return discovery_records

def update_mds(records, token):
    """Upload to MDS (this will create or update records)"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"\nSending {len(records)} records to MDS...")
    print(f"\nSample record (first one):")
    print(json.dumps(records[0], indent=2))
    
    response = requests.post(
        f"{BASE_URL}/mds/metadata",
        headers=headers,
        json=records
    )
    
    print(f"\nMDS Response Status: {response.status_code}")
    
    if response.status_code == 200:
        print(f"\n✅ Successfully updated {len(records)} discovery records")
        return True
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return False

def main():
    print("=" * 80)
    print("ETL: Explorer/Guppy → Discovery (MDS)")
    print("=" * 80)
    
    # Get authentication token
    print("\n[Step 1/3] Loading credentials...")
    token = get_auth_token()
    
    print("\n[Step 2/3] Fetching projects from Explorer via GraphQL...")
    projects = fetch_projects_from_explorer(token)
    
    if not projects:
        print("\n⚠️  No projects found in Explorer.")
        print("This could mean:")
        print("  - No projects exist")
        print("  - You don't have access to any projects")
        print("  - Guppy index needs to be updated")
        sys.exit(0)
    
    print(f"✅ Found {len(projects)} projects:")
    for p in projects:
        availability = p.get("availability_type", "Not Available")
        subject_count = p.get("_subjects_count", 0)
        print(f"  - {p['project_id']} ({p.get('name', 'N/A')})")
        print(f"    Availability: {availability} | Subjects: {subject_count}")
    
    print("\n" + "=" * 80)
    print("Transforming to discovery format...")
    discovery_records = transform_to_discovery_format(projects)
    print(f"✅ Transformed {len(discovery_records)} records")
    
    # Show what will be updated
    print("\nDiscovery records that will be created/updated:")
    for record in discovery_records:
        guid = record["guid"]
        avail = record["data"]["gen3_discovery"]["availability_type"]
        print(f"  - {guid} (Availability: {avail})")
    
    print("\n[Step 3/3] Updating MDS...")
    success = update_mds(discovery_records, token)
    
    if success:
        print("\n" + "=" * 80)
        print("✅ ETL Complete!")
        print("=" * 80)
        print("\nYour Discovery page has been updated with data from Explorer.")
        print(f"View it at: {BASE_URL}/Discovery")
        print("\nNote: Changes should be visible immediately in the Discovery page.")
    else:
        print("\n❌ ETL Failed. Check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
