import json
import os
import sys
import zipfile
import urllib.parse

def get_current_directory():
    list = sys.path[0].split(os.sep)
    return_str = ''
    for element in list:
        return_str += element + os.sep
    return return_str.rstrip(os.sep)


def getWorkingBranch(default):
    env = os.getenv('cleanroomDownloadBranch')
    if not env:
        print('No branch was found. Use default branch: ' + default)
        env = default
    else:
        print('Download branch: ' + env)
    return urllib.parse.quote(env, safe='')


# function to add to JSON
def write_json(filepath, new_data):
    with open(filepath, 'r+') as file:
        # First we load existing data into a dict.
        file_data = json.load(file)
        # Join new_data with file_data
        file_data.update(new_data)
        # Sets file's current position at offset.
        file.seek(0)
        # convert back to json.
        json.dump(file_data, file, indent=4)


# function to extract archive with relevant path and name pattern
def extractArchive(relevant_path, name_pattern, extract_path):
    file_name = findFileName(relevant_path, name_pattern)

    with MyZipFile(os.path.join(relevant_path, file_name)) as z:
        z.extractall(extract_path)


# function to find file via pattern
def findFileName(relevant_path, name_pattern):
    return [fn for fn in os.listdir(relevant_path)
            if any(fn.startswith(ext) for ext in name_pattern)][0]


class MyZipFile(zipfile.ZipFile):

    def extract(self, member, path=None, pwd=None):
        if not isinstance(member, zipfile.ZipInfo):
            member = self.getinfo(member)

        if path is None:
            path = os.getcwd()

        ret_val = self._extract_member(member, path, pwd)
        attr = member.external_attr >> 16
        if attr != 0:
            os.chmod(ret_val, attr)
        return ret_val

    def extractall(self, path=None, members=None, pwd=None):
        if members is None:
            members = self.namelist()

        if path is None:
            path = os.getcwd()
        else:
            path = os.fspath(path)

        for zipinfo in members:
            self.extract(zipinfo, path, pwd)
