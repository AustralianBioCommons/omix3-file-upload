import sys
from gen3.index import Gen3Index
from gen3.auth import Gen3Auth

if len(sys.argv) != 2:
    print("Usage: python get_records1.py <DID>")
    sys.exit(1)

did = sys.argv[1]

auth = Gen3Auth("https://omix3.test.biocommons.org.au", refresh_file="/Users/nalava/Downloads/credentials8.json")
index = Gen3Index("https://omix3.test.biocommons.org.au", auth)

record = index.get_record(did)
print(record)

