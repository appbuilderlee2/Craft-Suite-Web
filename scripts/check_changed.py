"""Skip scheduled publication only when the currently deployed fingerprint agrees."""
import json
import os
from urllib.request import urlopen

publish = True
if os.environ.get('EVENT_NAME') == 'schedule':
    owner, repo = os.environ['REPOSITORY'].split('/')
    url = f'https://{owner}.github.io/{repo}/versions.json'
    try:
        with urlopen(url, timeout=30) as response:
            deployed = json.load(response)
        with open('release-lock.json') as stream:
            planned = json.load(stream)
        publish = deployed.get('fingerprint') != planned['fingerprint']
    except Exception as error:
        print('Cannot compare deployed version; rebuild:', type(error).__name__)
with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
    stream.write(f'publish={str(publish).lower()}\n')
print('Publish:', publish)
