# coding=utf-8 ##以utf-8编码储存中文字符
'''
    ipaparser.py:
        serves as a tool for ipa file layout parsing
    usage:
        ipaparser.py -c comparedipaurl ipaurl
        -c      用于对比的旧版本
        -h      帮助文档
'''
import sys
import getopt
import zipfile
import os
import os.path
from os.path import join, getsize
import urllib
import platform
import time
import shutil

#     type:    0       1       2       3       4       5       6       7
# typename: 执行文件    文档    图片    媒体文件  bundle  文件夹   XIB     普通文件
FILEITEMTYPES = ['执行文件','文档','图片','媒体文件','bundle','文件夹','XIB','普通文件']
FILEITEMSUF =  [[],
                ["txt","key","html","plist","strings","xml","js","dat","mobileprovision","conf","json","zip","cer","lic","model","y2a"],
                ["png","jpg","gif","car"],
                ["caf","mp3"],
                ["bundle"],
                [],
                ["nib","storyboardc"],
                []];
FILESUFTYPEMAP = {}
output = ''

class OutputSerializer:
    outputfilehandler = ''
    def __init__(self,outputfile):
        self.outputfilehandler = open(outputfile,'w',0)
    def write(self,content):
        self.outputfilehandler.write(content)

class FileCompareModel:
    name = ''
    sizeChange = 0

class FileItemModel:       #文件抽象类
    type = 0
    size = 0
    path = ''
    recursive = False
    appdir = ''
    appname = ''
    name = ''
    subitems = ''
    itemmap = ''

    def __init__(self,path,recur,appdir,appname):
        self.path = path
        self.name = os.path.basename(path)
        self.recursive = recur
        self.appdir = appdir
        self.appname = appname
        self.type = self.getItemType()
        self.subitems = {}
        self.itemmap = {}
        if recur == True:
            for item in os.listdir(path):
                fileitem = FileItemModel(join(path,item),False,appdir,appname)
                self.itemmap[fileitem.name] = fileitem
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
            if self.path == join(self.appdir,self.appname):
                return 0
            return 7
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

def binarySize(size):
    if abs(size) < 1024:
        return '%5.0f'%float(size) +'B'
    elif abs(size) < 1024*1024:
        return '%5.1f'%(float(size)/1024) + 'KB'
    else:
        return '%5.1f'%(float(size)/(1024*1024)) + 'MB'

def getItemSize(path):      #获取文件或文件夹大小
    if not os.path.isfile(path):
        size = 0
        for (dirpath,dirnames,filenames) in os.walk(path):
            for file in filenames:
                size += getsize(join(dirpath,file))
        return size
    else:
        return getsize(path)

def getFileModelForIPA(ipapath):
    zip = zipfile.ZipFile(ipapath)
    basename = os.path.basename(ipapath)
    parts = os.path.splitext(basename)
    basename = parts[0]
    extractdir = join(os.path.dirname(ipapath),basename)
    zip.extractall(extractdir)
    appdir = ''
    appname = ''
    #print 'ipa(%s) size:' % ipapath,getsize(ipapath)
    exepath = ''
    for (dirpath,dirnames,filenames) in os.walk(extractdir):
        for dir in dirnames:
            if dir.endswith('.app'):
                appdir = join(dirpath,dir)
                appname = os.path.splitext(dir)[0]
                exepath = join(appdir,appname)
                exists = 'not'
                if os.path.isfile(exepath):
                    exists = 'does'
                #print 'found app:',dir,'exec name:',appname,'(',exists,'exists)'
                break
        if len(appdir) > 1:
            break
    ipaFile = FileItemModel(appdir,True,appdir,appname)
    #print 'sum :',ipaFile.itemSize()
    return ipaFile

def itemSort(model):
    return model.sizeChange

def compareIPAModel(newIPAPath,oldIPAPath):
    global output
    output.write('ipa文件增加：%s<br/>' % binarySize(getsize(newIPAPath)-getsize(oldIPAPath)))
    newIPA = getFileModelForIPA(newIPAPath)
    oldIPA = getFileModelForIPA(oldIPAPath)
    output.write('执行文件增加：%s<br/>' % binarySize(getsize(join(newIPA.appdir,newIPA.appname))-getsize(join(oldIPA.appdir,oldIPA.appname))))
    output.write('app增加：%s\n<br/>' % binarySize(newIPA.itemSize()-oldIPA.itemSize()))

    newmap = newIPA.itemmap.copy()
    oldmap = oldIPA.itemmap.copy()
    newappears = {}
    increase = {}
    decrease = {}
    deleted = {}
    newsize = incsize = decsize = delsize = 0
    for key in newmap.keys():
        if not oldmap.has_key(key):
            compare = FileCompareModel()
            compare.name = newmap[key].name
            compare.sizeChange = newmap[key].itemSize()
            newappears[key] = compare
            newsize += compare.sizeChange
        elif oldmap[key].itemSize() > newmap[key].itemSize():
            compare = FileCompareModel()
            compare.name = oldmap[key].name
            compare.sizeChange = oldmap[key].itemSize() - newmap[key].itemSize()
            decrease[key] = compare
            decsize += compare.sizeChange
            oldmap.pop(key)
        elif oldmap[key].itemSize() < newmap[key].itemSize():
            compare = FileCompareModel()
            compare.name = oldmap[key].name
            compare.sizeChange = newmap[key].itemSize() - oldmap[key].itemSize()
            increase[key] = compare
            incsize += compare.sizeChange
            oldmap.pop(key)
        else:
            oldmap.pop(key)
    for key in oldmap.keys():
        compare = FileCompareModel()
        compare.name = oldmap[key].name
        compare.sizeChange = oldmap[key].itemSize()
        deleted[key] = compare
        delsize += compare.sizeChange
        
    output.write('对比结果如下：<br/>')
    for i,item in enumerate(FILEITEMTYPES):
        output.write('%-10s\t增加:%s<br/>' % (item,binarySize(newIPA.itemSizeForType(i)-oldIPA.itemSizeForType(i))))
    newlist = newappears.values()
    inclist = increase.values()
    declist = decrease.values()
    dellist = deleted.values()
    newlist.sort(key=itemSort,reverse=True)
    declist.sort(key=itemSort,reverse=True)
    inclist.sort(key=itemSort,reverse=True)
    dellist.sort(key=itemSort,reverse=True)
    result = [('新增',newlist,newsize),('增加',inclist,incsize),('减少',declist,decsize),('删除',dellist,delsize)]
    for i,tup in enumerate(result):
        if len(tup[1]) > 0:
            output.write('\n%-20s %20d项:%s<br/>' % (tup[0],len(tup[1]),binarySize(tup[2])))
            for i,item in enumerate(tup[1]):
                if item.sizeChange > 1024:
                    output.write('%-40s:%s<br/>' % (item.name,binarySize(item.sizeChange)))

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hc:i:o:", ["help"])
        except getopt.error, msg:
            raise Usage(msg)

        newurl = ''
        oldurl = ''

        #输出初始化
        global output
	
        globaldir = '/Library/WebServer/Documents/'
        if platform.platform().find('Windows') > -1:
            globaldir = 'G:/ios/'
        globaldir += str(time.time()) + '/'
	
        if not os.path.exists(globaldir):   #make tmp dir
            os.makedirs(globaldir)
	
        newpath = globaldir + 'entmobile_new.ipa'
        oldpath = globaldir + 'entmobile_old.ipa'

        for name,value in opts:
            if name in ('-h','--help'):
                print '''
ipaparser.py:
    serves as a tool for ipa file layout parsing
usage:
    ipaparser.py [-c comparedipaurl] [-i comparedlinkmapurl] ipaurl linkmapurl
    
    -c      用于对比的旧版本
    -i      用于对比的旧版本linkmap
    -h      帮助文档
                    '''
            elif name in ('-c'):
                oldurl = value

        output = OutputSerializer(globaldir + 'ipacompare.txt')
        newurl = args[0]
        #prepare for global map
        for i,list in enumerate(FILEITEMSUF):
            for j,type in enumerate(list):
                #print ':',type,':',len(type)
                FILESUFTYPEMAP[type] = i
        output.write('start download ipa(%s)...<br/>' % newurl)
        urllib.urlretrieve(newurl, newpath)
        output.write('done download ipa(%s)...<br/>' % newurl)
        output.write('startdownload ipa(%s)...<br/>' % oldurl)
        urllib.urlretrieve(oldurl, oldpath)
        output.write('done download ipa(%s)<br/>' % oldurl)

        #ipaFile = getFileModelForIPA(filepath)    #ipa文件抽象
        #print 'exe size:',getsize(exepath)
        #print 'app size:',getItemSize(appdir)
        #print ipaFile.itemSize()
        compareIPAModel(newpath,oldpath)
	    shutil.rmtree(globaldir)

    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

if __name__ == "__main__":
    sys.exit(main())
