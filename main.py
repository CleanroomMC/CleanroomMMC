import glob
import json
import os
import re
import shutil
import sys

import requests

import Util
import metautil

# Init
print('---> Initialize')
commit_hash = os.getenv('commit_hash')
run_job_url = os.getenv('run_job_url')

working_path = Util.get_current_directory()
cache_path = os.path.join(working_path, 'build', 'downloadCache')
output_path = os.path.join(working_path, 'build', 'output')
template_path = os.path.join(working_path, 'template')
lwjgl_version = ''  # Stub value

for folder in [cache_path, output_path, template_path]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Clean cache folder
print('---> Cleaning cache folder')
for cleaningDir in [cache_path, output_path]:
    for item in os.listdir(cleaningDir):
        path = os.path.join(cleaningDir, item)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

# Get download branch from env
print('---> Get download branch from env')
defaultBranch = 'main'
branch = Util.get_working_branch(defaultBranch)

# Download installer artifact
print('---> Download installer artifact')
installerURL = 'https://nightly.link/CleanroomMC/Cleanroom/' \
               + (f'workflows/BuildTest/{branch}' if not run_job_url
                  else f'actions/runs/{run_job_url.rsplit("/", 1)[-1]}') \
               + '/installer.zip'
print('Installer URL: ' + installerURL)
response = requests.get(installerURL)
if not response.ok:
    print('Response failed. Code: ' + str(response.status_code))
    sys.exit(1)
print('Downloading installer')
open(os.path.join(cache_path, 'installer.zip'), 'wb').write(response.content)

# Prepare installer and template
print('---> Prepare installer and template')
Util.extractArchive(cache_path, 'installer', cache_path)
Util.extractArchive(cache_path, 'cleanroom', os.path.join(cache_path, 'installer'))
Util.extractArchive(template_path, 'template', output_path)

# Read cleanroom version
print('---> Reading Cleanroom version')
cleanroom_version = Util.findFileName(cache_path, 'cleanroom').split('-')[1]
print('Cleanroom version: ' + cleanroom_version)

# Create libraries folder and copy required
print('---> Create libraries folder and copy required files')
os.mkdir(os.path.join(output_path, 'libraries'))
shutil.copyfile(
    glob.glob(os.path.join(cache_path, 'installer', '**', 'cleanroom*.jar'), recursive=True)[0],
    os.path.join(output_path, 'libraries', 'cleanroom-{version}-universal.jar'.format(version=cleanroom_version)))

# Create patch file for Cleanroom
print('---> Create patch file for Cleanroom')
cleanroom_patches_output_path = os.path.join(output_path, 'patches', 'net.minecraftforge.json')
lwjgl_patches_output_path = os.path.join(output_path, 'patches', 'org.lwjgl3.json')
installer_patches_path = os.path.join(cache_path, 'installer', 'version.json')

with (open(installer_patches_path, 'r') as __in,
      open(cleanroom_patches_output_path, 'r') as cleanroom_patches_out,
      open(lwjgl_patches_output_path, 'r') as lwjgl_patches_out):
    print('Parsing template patch file')
    data = json.load(__in)['libraries']
    cleanroom_patches_json = json.load(cleanroom_patches_out)
    lwjgl_patches_json = json.load(lwjgl_patches_out)

    for kd in data:
        if 'org.lwjgl3:lwjgl3:' in kd['name']:
            if not lwjgl_version:
                lwjgl_version = str(kd['name']).split(':')[2]
            lwjgl_patches_json['libraries'].append(kd)
        else:
            if 'com.cleanroommc:cleanroom' in kd['name']:
                dep = metautil.DependencyBuilder()
                dep.set_name(f"{kd['name']}-universal")
                dep.set_mmc_hint('local')
                cleanroom_patches_json['libraries'].append(dep.build())
            else:
                cleanroom_patches_json['libraries'].append(kd)

    cleanroom_patches_json['version'] = cleanroom_version
with (open(cleanroom_patches_output_path, "w") as __cleanroom_out,
      open(lwjgl_patches_output_path, 'r') as __lwjgl_out):
    json.dump(cleanroom_patches_json, __cleanroom_out, indent=4)
    json.dump(lwjgl_patches_json, __lwjgl_out, indent=4)
    print('Patch file created')

# Patch mmc-pack.json
print('---> Patching mmc-pack.json')
mmc_pack_path = os.path.join(output_path, 'mmc-pack.json')

with open(mmc_pack_path) as mmc_pack:
    print('Parsing mmc-pack.json')
    data = json.load(mmc_pack)
    for item in data['components']:
        if 'org.lwjgl' in item['uid']:
            item['version'] = lwjgl_version
            item['cachedVersion'] = lwjgl_version
        if 'net.minecraft' == item['uid']:
            item['cachedRequires'][0]['suggests'] = lwjgl_version
        if 'net.minecraftforge' == item['uid']:
            item['version'] = cleanroom_version
            item['cachedVersion'] = cleanroom_version
with open(mmc_pack_path, 'w') as __out:
    json.dump(data, __out, indent=4)
    print('Patched mmc-pack.json')

# Create notes for instance if build callouts from CI
if commit_hash and run_job_url:
    print('---> Adding notes to instance.cfg')
    instance_cfg_path = os.path.join(output_path, 'instance.cfg')
    with open(instance_cfg_path, 'r') as instance_cfg:
        content = instance_cfg.read()
        content = re.sub(
            r"notes=.*",
            rf"notes=This instance is built using Github Action.\\nUsing installer artifact from commit: {commit_hash}\\nAction URL: {run_job_url}",
            content)
    with open(instance_cfg_path, 'w') as __out:
        __out.write(content)
    print('---> Added notes to mmc-pack.json')

# Pack everything to a single archive
print('---> Archiving instance')
print('Saved in: ' + shutil.make_archive(os.path.join(working_path, 'build', 'CleanroomMMC'), 'zip', output_path))
