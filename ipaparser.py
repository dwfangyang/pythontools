# coding=utf-8 ##以utf-8编码储存中文字符
'''
    ipaparser.py:
        serves as a tool for ipa file layout parsing
    usage:
    
'''
import sys
import getopt
import zipfile
import os
import os.path
from os.path import join, getsize

#     type:    0       1       2       3       4       5       6
# typename:普通文件     文档    图片    媒体文件  bundle  文件夹   XIB
FILEITEMTYPES = ['普通文件','文档','图片','媒体文件','bundle','文件夹','XIB']
FILEITEMSUF =  [[],
                ["txt","key","html","plist","strings","xml","js","dat","mobileprovision","conf","json","zip","cer","lic","model","y2a"],
                ["png","jpg","gif","car"],
                ["caf","mp3"],
                ["bundle"],
                [],
                ["nib","storyboardc"]];
FILESUFTYPEMAP = {}

def getItemSize(path):      #获取文件或文件夹大小
    if not os.path.isfile(path):
        size = 0
        for (dirpath,dirnames,filenames) in os.walk(path):
            for file in filenames:
                size += getsize(join(dirpath,file))
        return size
    else:
        return getsize(path)

class FileItemModel:       #文件项表示类
    type = 0
    size = 0
    path = ''
    recursive = False
    subitems = {}

    def __init__(self,path,recur):
        self.path = path
        self.recursive = recur
        self.type = self.getItemType()
        if recur == True:
            for item in os.listdir(path):
                fileitem = FileItemModel(join(path,item),False)
                if self.subitems.has_key(fileitem.type):
                    self.subitems[fileitem.type].append(fileitem)
                else:
                    self.subitems[fileitem.type] = [fileitem]
    
    def itemSize(self):
        if self.size != 0:
            return self.size
        if self.recursive == False:
            self.size = getItemSize(self.path)
        else:
            for i,typeitems in enumerate(self.subitems.values()):
                for j,item in enumerate(typeitems):
                    self.size += item.itemSize()
                #print self.subitems.keys()[i],item.itemSize()
        return self.size

    def getItemType(self):
        parts = os.path.splitext(self.path)
        ext = ''
        if len(parts) > 1:
            ext = parts[1][1:len(parts[1])]
        #print ':',ext,':',len(ext),':',FILESUFTYPEMAP.has_key('nib')
        if FILESUFTYPEMAP.has_key(ext):
            return FILESUFTYPEMAP[ext]
        elif not os.path.isfile(self.path):
            return 5
        else:
            return 0
    def itemSizeForType(self,type):
        size = 0
        if not self.subitems.has_key(type):
            return 0
        if len(self.subitems[type]) <= 0:
            return 0
                #print self.subitems[type]
        for i,item in enumerate(self.subitems[type]):
            size += item.itemSize()
#print size
        return size

def main(argv=None):
    filepath = '/Users/fangyang/Downloads/entmobile.ipa'
    zip = zipfile.ZipFile(filepath)
    extractdir = '/Users/fangyang/Downloads/entmobile'
    zip.extractall(extractdir)
    appdir = ''
    appname = ''
    for (dirpath,dirnames,filenames) in os.walk(extractdir):
        for dir in dirnames:
            if dir.endswith('.app'):
                appdir = join(dirpath,dir)
                appname = os.path.splitext(dir)[0]
                exepath = join(appdir,appname)
                exists = 'not'
                if os.path.isfile(exepath):
                    exists = 'does'
                print 'found app:',dir,'exec name:',appname,'(',exists,'exists)'
                break
        if len(appdir) > 1:
            break

    print 'begin preparation of global data'
    for i,list in enumerate(FILEITEMSUF):
        for j,type in enumerate(list):
            #print ':',type,':',len(type)
            FILESUFTYPEMAP[type] = i
    print 'done preparation of global data'

    ipaFile = FileItemModel(appdir,True)    #ipa文件抽象

#print ipaFile.subitems
    for i,type in enumerate(FILEITEMTYPES):
        print type,':',ipaFile.itemSizeForType(i)
    print 'ipa size:',getsize(filepath)
    print 'exe size:',getsize(exepath)
    print 'app size:',getItemSize(appdir)
    print ipaFile.itemSize()

if __name__ == "__main__":
    sys.exit(main())
