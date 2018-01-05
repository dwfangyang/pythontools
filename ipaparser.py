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
from script.sendemail.send_email import Email
from linkmaper import getLinkmapComparation

#     type:    0       1       2       3       4       5       6       7
# typename: 执行文件    文档    图片    媒体文件  bundle  文件夹   XIB     普通文件
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
    def closeOutput(self):
        self.outputfilehandler.close()

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
        self.parseSubitems()
    
    def parseSubitems(self):
        if self.recursive == True and not os.path.isfile(self.path):
            for item in os.listdir(self.path):
                fileitem = FileItemModel(join(self.path,item),False,self.appdir,self.appname)
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
    def getComparationWith(self,oldFileModel):
        if not self.recursive:
            self.recursive = True
            self.parseSubitems()
        if not oldFileModel.recursive:
            oldFileModel.recursive = True
            oldFileModel.parseSubitems()
        
        newmap = self.itemmap.copy()
        oldmap = oldFileModel.itemmap.copy()
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
        newlist = newappears.values()
        inclist = increase.values()
        declist = decrease.values()
        dellist = deleted.values()
        newlist.sort(key=itemSort,reverse=True)
        declist.sort(key=itemSort,reverse=True)
        inclist.sort(key=itemSort,reverse=True)
        dellist.sort(key=itemSort,reverse=True)
        return [('新增',newlist,newsize),('增加',inclist,incsize),('减少',declist,decsize),('删除',dellist,delsize)]

def binarySize(size):
    str = ''
    if abs(size) < 1024:
        str = '%5.0f'%float(abs(size)) +'B'
    elif abs(size) < 1024*1024:
        str = '%5.1f'%(float(abs(size))/1024) + 'KB'
    else:
        str = '%5.1f'%(float(abs(size))/(1024*1024)) + 'MB'
    return ('增加' if abs(size) == size else '减少',str)

def getItemSize(path):      #获取文件或文件夹大小
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

def writeComparation(resultTuple,newFileModel,oldFileModel,recursive,delimiter):
    global output
    for i,tup in enumerate(resultTuple):
        if len(tup[1]) > 0:
            output.write('\n%s%-20s %20d项:%s\n' % (delimiter,tup[0],len(tup[1]),binarySize(tup[2])[1]))
            for i,item in enumerate(tup[1]):
                if item.sizeChange > 1024:
                    output.write('%s%-40s:%s\n' % (delimiter,item.name,binarySize(item.sizeChange)[1]))
                    if recursive and newFileModel.itemmap.has_key(item.name) and oldFileModel.itemmap.has_key(item.name):
                        newOrigItem = newFileModel.itemmap[item.name]
                        oldOrigItem = oldFileModel.itemmap[item.name]
                        writeComparation(newOrigItem.getComparationWith(oldOrigItem),newOrigItem,oldOrigItem,False,'\t')

def compareIPAModel(newIPA,oldIPA):
    global output

    result = newIPA.getComparationWith(oldIPA)

    for i,item in enumerate(FILEITEMTYPES):
        tuple = binarySize(newIPA.itemSizeForType(i)-oldIPA.itemSizeForType(i))
        output.write('%-10s\t%s:%s\n' % (item,tuple[0],tuple[1]))
#    for i,tup in enumerate(result):
#        if len(tup[1]) > 0:
#            output.write('\n%-20s %20d项:%s\n' % (tup[0],len(tup[1]),binarySize(tup[2])))
#            for i,item in enumerate(tup[1]):
#                if item.sizeChange > 1024:
#                    output.write('%-40s:%s\n' % (item.name,binarySize(item.sizeChange)))
    writeComparation(result,newIPA,oldIPA,True,'')

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hc:i:e:", ["help"])
        except getopt.error, msg:
            raise Usage(msg)

        newurl = ''
        oldurl = ''
        newlinkmapurl = ''
        oldlinkmapurl = ''

        #输出初始化
        global output
        outputfile = ''
	
        globaldir = '/Library/WebServer/Documents/'
        if platform.platform().find('Windows') > -1:
	        globaldir = 'E:/wamp64/tmp/'
        globaldir += str(time.time()) + '/'
	
        if not os.path.exists(globaldir):   #make tmp dir
	        os.makedirs(globaldir)
	
        newpath = globaldir + 'entmobile_new.ipa'
        oldpath = globaldir + 'entmobile_old.ipa'
        outputfile = globaldir + 'ipacompare.txt'

        emailaddr = []
        usagemsg = '''
ipaparser.py:
    serves as a tool for ipa file layout parsing
usage:
    ipaparser.py [-c comparedipaurl] [-i comparedlinkmapurl] [-e email] ipaurl linkmapurl

    -c      用于对比的旧版本
    -i      用于对比的旧版本linkmap
    -e      用于输入希望接收结果的邮箱
    -h      帮助文档
                    '''
        for name,value in opts:
            if name in ('-h','--help'):
                raise Usage(usagemsg)
            elif name in ('-c'):
                oldurl = value
            elif name in ('-e'):
                emailaddr = value.split(';')
            elif name in ('-i'):
                oldlinkmapurl = value
        if len(args) <= 0:
            raise Usage(usagemsg)

        output = OutputSerializer(outputfile)
        newurl = args[0]
        if len(args) > 1:
            newlinkmapurl = args[1]
        #prepare for global map
        for i,list in enumerate(FILEITEMSUF):
            for j,type in enumerate(list):
                #print ':',type,':',len(type)
                FILESUFTYPEMAP[type] = i
#output.write('start download ipa(%s)...\n' % newurl)
        urllib.urlretrieve(newurl, newpath)
#output.write('done download ipa(%s)...\n' % newurl)
#output.write('startdownload ipa(%s)...\n' % oldurl)
        urllib.urlretrieve(oldurl, oldpath)
#output.write('done download ipa(%s)\n' % oldurl)

        #ipaFile = getFileModelForIPA(filepath)    #ipa文件抽象
        #print 'exe size:',getsize(exepath)
        #print 'app size:',getItemSize(appdir)
        #print ipaFile.itemSize()
        output.write('新ipa(%s) 相比于 旧ipa(%s) 大小变化如下:\n' % (newurl,oldurl))
        tuple = binarySize(getsize(newpath)-getsize(oldpath))
        output.write('ipa文件%s：%s\n' % (tuple[0],tuple[1]))
        newIPA = getFileModelForIPA(newpath)
        oldIPA = getFileModelForIPA(oldpath)
        tuple = binarySize(getsize(join(newIPA.appdir,newIPA.appname))-getsize(join(oldIPA.appdir,oldIPA.appname)))
        output.write('执行文件%s：%s\n' % (tuple[0],tuple[1]))
        tuple = binarySize(newIPA.itemSize()-oldIPA.itemSize())
        output.write('app%s：%s\n\n' % (tuple[0],tuple[1]))
        output.write('对比结果如下：\n')
        compareIPAModel(newIPA,oldIPA)
        if len(newlinkmapurl):
            tuple = getLinkmapComparation(newlinkmapurl,oldlinkmapurl,False)
            linkmapcomparation = open(tuple[0]+tuple[1])
            output.write('\n\n执行文件对比如下:\n')
            for line in linkmapcomparation:
                output.write(line)
            linkmapcomparation.close()
            shutil.rmtree(tuple[0])
        output.closeOutput()

        if len(emailaddr) > 0:
            emailhandler = Email('yy-pgone@yy.com','Guozhi1221')
            emailhandler.sendmail('ipa compare result',emailaddr,[],[outputfile],'ipa test')
		
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
