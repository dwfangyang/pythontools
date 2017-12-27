# coding=utf-8 ##以utf-8编码储存中文字符

import zipfile
import os
import os.path
from os.path import join, getsize

#     type:    0       1       2       3       4       5       6
# typename:普通文件     文档    图片    媒体文件  bundle  文件夹   XIB

class FileItemModel:
    type = 0
    size = 0
    path = ''
    recursive = False
    subitems = {}

    def __init__(self,path,recur):
        self.path = path
        self.recursive = recur
    
    def itemSize():
        if recursive == False:
            return getItemSize(path)
        return 0

def getItemSize(path):
    if not os.path.isfile(path):
        size = 0
        for (dirpath,dirnames,filenames) in os.walk(path):
            for file in filenames:
                size += getsize(join(dirpath,file))
        return size
    else:
        return getsize(path)

filepath = '/Users/fangyang/Downloads/entmobile.ipa'
zip = zipfile.ZipFile(filepath)
extractdir = '/Users/fangyang/Downloads/entmobile'
zip.extractall(extractdir)
appdir = ''
appname = ''
for (dirpath,dirnames,filenames) in os.walk(extractdir):
    for dir in dirnames:
        if dir.endswith('.app'):
            appdir = dirpath+'/'+dir
            appname = os.path.splitext(dir)[0]
            exepath = appdir+'/'+appname
            exists = 'not'
            if os.path.isfile(exepath):
                exists = 'does'
            print 'found app:',dir,'exec name:',appname,'(',exists,'exists)'
            break
    if len(appdir) > 1:
        break

print 'exe size:',getsize(exepath)
print 'app size:',getItemSize(appdir)
