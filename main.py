import glob
import json
import os
import shutil

import requests

import Util

# Init
working_path = Util.get_current_directory()
cache_path = os.path.join(working_path, 'build', 'downloadCache')
output_path = os.path.join(working_path, 'build', 'output')
template_path = os.path.join(working_path, 'template')
lwjgl_version = ''  # Stub value

for folder in [cache_path, output_path, template_path]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Clean cache folder
for cleaningDir in [cache_path, output_path]:
    for item in os.listdir(cleaningDir):
        path = os.path.join(cleaningDir, item)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

# Download installer artifact
installerURL = 'https://nightly.link/CleanroomMC/Cleanroom/workflows/BuildTest/main/installer.zip'
response = requests.get(installerURL)
open(os.path.join(cache_path, 'installer.zip'), 'wb').write(response.content)

# Prepare installer and template
Util.extractArchive(cache_path, 'installer', cache_path)
Util.extractArchive(cache_path, 'cleanroom', os.path.join(cache_path, 'installer'))
Util.extractArchive(template_path, 'template', output_path)

# Read cleanroom version
cleanroom_version = Util.findFileName(cache_path, 'cleanroom').split('-')[1]

# Create libraries folder and copy required
os.mkdir(os.path.join(output_path, 'libraries'))
shutil.copyfile(
    glob.glob(os.path.join(cache_path, 'installer', '**', 'cleanroom*.jar'), recursive=True)[0],
    os.path.join(output_path, 'libraries', 'cleanroom-{version}-universal.jar'.format(version=cleanroom_version)))

# Create patches file for Cleanroom
cleanroom_patches_output_path = os.path.join(output_path, 'patches', 'com.cleanroommc.json')
installer_patches_path = os.path.join(cache_path, 'installer', 'version.json')

with (open(installer_patches_path, 'r') as __in,
      open(cleanroom_patches_output_path, 'r') as __out):
    data = json.load(__in)['libraries']
    out_json = json.load(__out)

    for kd in data:
        sub_kd = {'name': kd['name']}
        if 'com.cleanroommc:cleanroom' not in kd['name']:
            sub_kd.update({'downloads': {'artifact': {
                'sha1': kd['downloads']['artifact']['sha1'],
                'size': kd['downloads']['artifact']['size'],
                'url': kd['downloads']['artifact']['url']
            }}})
        else:
            sub_kd['name'] += '-universal'
            sub_kd['MMC-hint'] = 'local'
        if 'org.lwjgl3:lwjgl3:' in kd['name']:
            lwjgl_version = str(kd['name']).split(':')[2]
        out_json['libraries'].append(sub_kd)

    out_json['version'] = cleanroom_version
with open(cleanroom_patches_output_path, "w") as __out:
    json.dump(out_json, __out, indent=4)

# Patch mmc-pack.json
mmc_pack_path = os.path.join(output_path, 'mmc-pack.json')

with open(mmc_pack_path) as mmc_pack:
    data = json.load(mmc_pack)
    for item in data['components']:
        if 'LWJGL' in item['cachedName']:
            item['version'] = lwjgl_version
            item['cachedVersion'] = lwjgl_version
        if 'Minecraft' in item['cachedName']:
            item['cachedRequires'][0]['suggests'] = lwjgl_version
        if 'Cleanroom' in item['cachedName']:
            item['version'] = cleanroom_version
            item['cachedVersion'] = cleanroom_version

with open(mmc_pack_path, 'w') as __out:
    json.dump(data, __out, indent=4)

# Pack everything to a single archive
shutil.make_archive(os.path.join(working_path, 'build', 'CleanroomMMC'), 'zip', output_path)
