#!/usr/bin/python3
""" Script to run when releasing a new version to pypi """
from __future__ import annotations
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

try:
  import requests
  from requests.structures import CaseInsensitiveDict
except Exception:
  pass


def getVersion() -> str:
  """
  Get current version number from git-tag

  Returns:
    string: v0.0.0
  """
  result = subprocess.run(['git','tag'], capture_output=True, check=False)
  versionStr = result.stdout.decode('utf-8').strip()
  versionList= [i[1:].replace('b','.') for i in versionStr.split('\n')]
  if versionList == ['']:  #default
    return 'v0.0.1'
  versionList.sort(key=lambda s: list(map(int, s.split('.'))))
  lastVersion = versionList[-1]
  if lastVersion.count('.')==3:
    lastVersion = '.'.join(lastVersion.split('.')[:3]) + f'b{lastVersion.split(".")[-1]}'
  return f'v{lastVersion}'


def prevVersionsFromPypi(k:int=15) -> None:
  """ Get and print the information of the last k versions on pypi

  Args:
    k (int): number of information
  """
  url = 'https://pypi.org/pypi/wallo/json'
  with urlopen(url) as response:
    data = json.loads(response.read())
  releases = list(data['releases'].keys())
  uploadTimes = [i[0]['upload_time'] for i in data['releases'].values()]
  releases = [x for _, x in sorted(zip(uploadTimes, releases))]
  uploadTimes = sorted(uploadTimes)
  print('Version information from pypi')
  k = min(k, len(releases)+1)
  for i in range(1, k):
    print(f'  {releases[-i]:8s} was released {(datetime.datetime.now()-datetime.datetime.strptime(uploadTimes[-i],"%Y-%m-%dT%H:%M:%S")).days:3d} days ago')
  return


def newVersion(level:int=2) -> None:
  """
  Create a new version

  Args:
    level (int): which number of the version to increase 0=mayor,1=minor,2=sub
  """
  print('Create new version...')
  prevVersionsFromPypi()
  #get old version number
  versionList = [int(i) for i in getVersion()[1:].replace('b','.').split('.')]
  #create new version number
  versionList[level] += 1
  for i in range(level+1,3):
    versionList[i] = 0
  version = '.'.join([str(i) for i in versionList])
  reply = input(f'Create version (2.5, 3.1.4b1): [{version}]: ')
  version = version if not reply or len(reply.split('.'))<2 else reply
  print(f'======== Version {version} =======')
  #git commands and update python files
  os.system('git pull')
  filesToUpdate = {'wallo/__init__.py':'__version__ = ',
                   #'docs/source/conf.py':'version = ',
                   }
  for path,text in filesToUpdate.items():
    with open(path, encoding='utf-8') as fIn:
      fileOld = fIn.readlines()
    fileNew = []
    for line in fileOld:
      line = line[:-1]  #only remove last char, keeping front part
      if line.startswith(text):
        line = f"{text}'{version}'"
      fileNew.append(line)
    with open(path,'w', encoding='utf-8') as fOut:
      fOut.write('\n'.join(fileNew)+'\n')
  return
  os.system('git commit -a -m "update version numbers"')
  os.system(f'git tag -a v{version} -m "Version {version}; see CHANGELOG for details"')
  #create CHANGELOG / Contributor-list
  with open(Path.home()/'.ssh'/'github.token', encoding='utf-8') as fIn:
    token = fIn.read().strip()
  os.system(f'github_changelog_generator -u PASTA-ELN -p pasta-eln -t {token}')
  addition = input('\n\nWhat do you want to add to the push message (do not use \' or \")? ')
  os.system(f'git commit -a -m "updated changelog; {addition}"')
  #push and publish
  print('\n\nWill bypass rule violation\n\n')
  os.system('git push')
  os.system(f'git push origin v{version}')
  return


def runSourceVerification() -> None:
  """ Verify code with a number of tools:
  Order: first those that change code automatically, then those that require manual inspection
  - pre-commit (which has a number of submodules included)
  - isort
  - pylint
  - mypy
  """
  tools = {'pre-commit': 'pre-commit run --all-files',
           'pylint'    : 'pylint wallo/',
           'mypy'      : 'mypy --no-warn-unused-ignores wallo/',
           }
  for label, cmd in tools.items():
    print(f'------------------ start {label} -----------------')
    os.system(cmd)
    print(f'---------------- end {label} ---------------')
  return


if __name__=='__main__':
  #run tests and create default files
  runSourceVerification()
  versionLevel = 2 if len(sys.argv)==1 else int(sys.argv[1])
  #test if on main branch
  resultMain = subprocess.run(['git','status'], capture_output=True, check=False)
  if resultMain.stdout.decode('utf-8').strip().startswith('On branch main\n'):
    #do update
    if input('Continue: only "y" continues. ') == 'y':
      newVersion(versionLevel)
    else:
      print('You have to be on main branch to continue.')
