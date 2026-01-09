#!/usr/bin/env python3
"""
Update availability_type for a Gen3 project using create_project (which updates if exists)
"""
import json
import sys
import argparse
from pathlib import Path
from gen3.auth import Gen3Auth
from gen3.submission import Gen3Submission
import requests

# Configuration
BASE_URL = "https://omix3.test.biocommons.org.au"

def get_project_from_graphql(program, project, token):
    """Get project info via GraphQL"""
    query = """
    query($project_id: [String]) {
      project(project_id: $project_id) {
        project_id
        code
        name
        dbgap_accession_number
        availability_type
        availability_mechanism
        state
      }
    }
    """
    
    variables = {"project_id": [f"{program}-{project}"]}
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v0/submission/graphql",
            json={"query": query, "variables": variables},
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data and data["data"]["project"]:
                return data["data"]["project"][0]
        return None
    except:
        return None

def update_availability_type(program, project, availability_type, credentials_file):
    """
    Update the availability_type for a project
    
    Args:
        program: Program name (e.g., "program1")
        project: Project code (e.g., "synthetic_dataset_3")
        availability_type: New value (e.g., "Restricted", "Open", "Controlled")
        credentials_file: Path to credentials file
    """
    
    # Generate auth
    try:
        print(f"📂 Loading credentials from: {credentials_file}")
        auth = Gen3Auth(endpoint=BASE_URL, refresh_file=credentials_file)
        token = auth.get_access_token()
        print("✅ Token generated successfully\n")
    except Exception as e:
        print(f"❌ Error loading credentials: {e}")
        sys.exit(1)
    
    print("=" * 70)
    print(f"Updating: {program}-{project}")
    print("=" * 70)
    
    # Step 1: Get current project info via GraphQL
    print("\n[Step 1/4] Fetching current project info...")
    current_project = get_project_from_graphql(program, project, token)
    
    if not current_project:
        print("❌ Could not fetch project info")
        print("   Make sure the project exists and you have access")
        return False
    
    print(f"✅ Current project info retrieved")
    print(f"   Current availability_type: {current_project.get('availability_type', 'None')}")
    
    # Step 2: Prepare updated project data
    print(f"\n[Step 2/4] Preparing update to: {availability_type}")
    
    # Build minimal project update object
    project_data = {
        "code": project,
        "dbgap_accession_number": current_project.get('dbgap_accession_number', project),
        "availability_type": availability_type
    }
    
    # Add name if it exists
    if current_project.get('name'):
        project_data['name'] = current_project['name']
    
    print(f"Project data to submit:")
    print(json.dumps(project_data, indent=2))
    
    # Step 3: Use Gen3Submission.create_project (which updates if exists)
    print(f"\n[Step 3/4] Submitting via Gen3Submission.create_project()...")
    
    try:
        sub = Gen3Submission(auth)
        
        # create_project actually does an upsert (create or update)
        response = sub.create_project(program, project_data)
        
        print(f"\n✅ Response received:")
        print(json.dumps(response, indent=2))
        
        # Check if successful
        success = False
        if isinstance(response, dict):
            if response.get('code') in [200, 201]:
                success = True
            elif 'entities' in response:
                # Check if any entities were created/updated
                if response.get('created_entity_count', 0) > 0 or response.get('updated_entity_count', 0) > 0:
                    success = True
        
        if success:
            print(f"\n✅ Project update submitted successfully!")
        else:
            print(f"\n⚠️  Response received but status unclear")
            
    except Exception as e:
        error_str = str(e)
        print(f"Response: {error_str}")
        
        # Sometimes updates work even if they throw an error
        # Check if the error mentions the project already exists
        if "already exists" in error_str.lower() or "duplicate" in error_str.lower():
            print("⚠️  Project already exists - this might actually mean the update worked")
        else:
            print(f"❌ Error during submission: {e}")
    
    # Step 4: Always verify regardless of response
    print("\n[Step 4/4] Verifying update...")
    print("=" * 70)
    
    # Wait a moment for the update to propagate
    import time
    time.sleep(1)
    
    updated_project = get_project_from_graphql(program, project, token)
    if updated_project:
        current_type = updated_project.get('availability_type')
        print(f"Current availability_type: {current_type}")
        
        if current_type == availability_type:
            print("✅ Verification successful! Update was applied!")
            
            print("\n" + "=" * 70)
            print("⚠️  NOTE: Guppy/Explorer may need re-indexing")
            print("=" * 70)
            print("The update is saved in Sheepdog (submission system).")
            print("To see it in the web interface, the ETL job must run.")
            print("Contact your Gen3 admin to trigger re-indexing if needed.")
            print("=" * 70)
            
            return True
        else:
            print(f"❌ Verification failed: Expected '{availability_type}', but got '{current_type}'")
            return False
    else:
        print("❌ Could not verify - unable to fetch updated project")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Update availability_type for a Gen3 project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update synthetic_dataset_3 to Restricted
  python update_availability.py -p program1 -j synthetic_dataset_3 -a Restricted -c credentials.json
  
  # Update to Open
  python update_availability.py -p program1 -j synthetic_dataset_2 -a Open -c credentials.json
  
  # Update to Controlled
  python update_availability.py -p program1 -j my_project -a Controlled -c credentials.json

Availability Types:
  - Open: Publicly accessible
  - Restricted: Requires data access request
  - Controlled: Strict access control
        """
    )
    
    parser.add_argument(
        "-p", "--program",
        required=True,
        help="Program name (e.g., program1)"
    )
    
    parser.add_argument(
        "-j", "--project",
        required=True,
        help="Project code (e.g., synthetic_dataset_3)"
    )
    
    parser.add_argument(
        "-a", "--availability",
        required=True,
        choices=["Open", "Restricted", "Controlled"],
        help="Availability type: Open, Restricted, or Controlled"
    )
    
    parser.add_argument(
        "-c", "--credentials",
        required=True,
        help="Path to Gen3 credentials file"
    )
    
    args = parser.parse_args()
    
    # Check credentials file exists
    if not Path(args.credentials).exists():
        print(f"❌ Credentials file not found: {args.credentials}")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("Gen3 Project Availability Type Updater")
    print("=" * 70 + "\n")
    
    # Update the project
    success = update_availability_type(
        program=args.program,
        project=args.project,
        availability_type=args.availability,
        credentials_file=args.credentials
    )
    
    if success:
        print("\n✅ Update completed successfully!\n")
        sys.exit(0)
    else:
        print("\n❌ Update failed!\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
