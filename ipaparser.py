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
import urlparse
#from script.sendemail.send_email import Email
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
sizelimit = 1024

class OutputSerializer:
    outputfilehandler = ''
    emailFileHandler = ''
    def __init__(self,outputfile,emailfile):
        self.outputfilehandler = open(outputfile,'w',0)
        self.emailFileHandler = open(emailfile,'w')
    def write(self,content):
        self.outputfilehandler.write(content+'\n')
    def writeHtml(self,content):
        self.emailFileHandler.write(content)
    def closeOutput(self):
        self.outputfilehandler.close()
        self.emailFileHandler.close();

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
        if self.recursive == True and os.path.isdir(self.path):
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
        result = []
        if newsize:
            result.append(('新增',newlist,newsize))
        if incsize:
            result.append(('增加',inclist,incsize))
        if decsize:
            result.append(('减少',declist,decsize))
        if delsize:
            result.append(('删除',dellist,delsize))
        return result

def binarySize(size):
    str = ''
    if abs(size) < 1024:
        str = '%5.0f'%float(abs(size)) +'B'
    elif abs(size) < 1024*1024:
        str = '%5.1f'%(float(abs(size))/1024) + 'KB'
    else:
        str = '%5.1f'%(float(abs(size))/(1024*1024)) + 'MB'
    change = '增加'
    if abs(size) > size:
        change = '减少'
    elif size == 0:
        str = ''
        change = '-'
    return (change,str)

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

#@params
#   @recursive indicate depth of invocation,namely True for depth 1, False for depth 2, and comparation's max depth is 2
def writeComparation(resultTuple,newFileModel,oldFileModel,recursive,delimiter):
    global output
    global sizelimit
    for i,tup in enumerate(resultTuple):
        if recursive:
            output.writeHtml('<h5>%s %20d项: %s</h5>' % (tup[0],len(tup[1]),binarySize(tup[2])[1]))
            output.writeHtml('<table border="1">')
        else:
            output.writeHtml('%s %20d项: %s' % (tup[0],len(tup[1]),binarySize(tup[2])[1]))
            output.writeHtml('<table width="100%">')
        output.write('\n%s%-20s %20d项: %s' % (delimiter,tup[0],len(tup[1]),binarySize(tup[2])[1]))
        for i,item in enumerate(tup[1]):
            if item.sizeChange > sizelimit:
                hasRecursiveComparation = (recursive and newFileModel.itemmap.has_key(item.name) and oldFileModel.itemmap.has_key(item.name))
                if hasRecursiveComparation:
                    compareitem = newFileModel.itemmap[item.name]
                    if compareitem.type != 4 and compareitem.type != 5:
                        hasRecursiveComparation = False
                if hasRecursiveComparation:
                    output.writeHtml('<tr><td rowspan="2">%s</td><td align="right">%s</td></tr>' % (item.name,binarySize(item.sizeChange)[1]))
                else:
                    output.writeHtml('<tr><td>%s</td><td align="right">%s</td></tr>' % (item.name,binarySize(item.sizeChange)[1]))
                output.write('%s %-40s: %s' % (delimiter,item.name,binarySize(item.sizeChange)[1]))
                if hasRecursiveComparation: #increase or decrease item
                    output.writeHtml('<tr><td>')
                    newOrigItem = newFileModel.itemmap[item.name]
                    oldOrigItem = oldFileModel.itemmap[item.name]
                    writeComparation(newOrigItem.getComparationWith(oldOrigItem),newOrigItem,oldOrigItem,False,'\t')
                    output.writeHtml('</td></tr>')
        output.writeHtml('</table>')

def writeHTMLSummary(summary):
    global output
    output.writeHtml('<table><tr><td valign="top">')
    output.writeHtml('<h3 style="color:red">安装包总变化</h3>')
    output.writeHtml('<table border="1">')
    output.writeHtml('<tr><th></th><th>新包</th><th>旧包</th><th>变化</th></tr>')
    for i,item in enumerate(summary):
        change = binarySize(item[1]-item[2])
        output.writeHtml('<tr><td style="color:red">%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' %(item[0],binarySize(item[1])[1],binarySize(item[2])[1],change[0]+change[1]))
    output.writeHtml('</table>')
    output.writeHtml('</td>')

def writeHTMLSubSummary(subsummary):
    global output
    output.writeHtml('<td valign="top">')
    output.writeHtml('<h3 style="color:red">各类型文件变化</h3>')
    output.writeHtml('<table border="1">')
    output.writeHtml('<tr><th>文件类型</th><th>新包</th><th>旧包</th><th>变化</th></tr>')
    for i,item in enumerate(subsummary):
        change = binarySize(item[1]-item[2])
        output.writeHtml('<tr><td style="color:red">%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (item[0],binarySize(item[1])[1],binarySize(item[2])[1],change[0]+change[1]))
    output.writeHtml('</table>')
    output.writeHtml('</td></tr></table>')

def isLocalUrl(url):
    if len(urlparse.urlsplit(url.lstrip())[0]) > 0:
        return False
    return True

def compareIPAModel(newIPA,oldIPA):
    global output

    result = newIPA.getComparationWith(oldIPA)

    subsummary = []
    for i,item in enumerate(FILEITEMTYPES):
        itemsummary = (item,newIPA.itemSizeForType(i),oldIPA.itemSizeForType(i))
        subsummary.append(itemsummary)
        tuple = binarySize(itemsummary[1]-itemsummary[2])
        output.write('%-10s\t%s:%s' % (item,tuple[0],tuple[1]))

    writeHTMLSubSummary(subsummary)
    output.writeHtml('<h3 style="color:red">文件增减明细</h3>')
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

        output = OutputSerializer(outputfile,globaldir+'compareresult.html')
        newurl = args[0]
        if len(args) > 1:
            newlinkmapurl = args[1]
        #prepare for global map
        for i,list in enumerate(FILEITEMSUF):
            for j,type in enumerate(list):
                #print ':',type,':',len(type)
                FILESUFTYPEMAP[type] = i

        #if len(urlparse.urlsplit(newurl.lstrip())[0])
        if not isLocalUrl(newurl):
            # newurl is remote resource
            urllib.urlretrieve(newurl, newpath)
        else:
            shutil.copyfile(newurl,newpath)
            if not os.path.isabs(newurl):
                newurl = os.path.abspath(newurl)
        if not isLocalUrl(oldurl):
            #oldurl is remote resource
            urllib.urlretrieve(oldurl, oldpath)
        else:
            shutil.copyfile(oldurl,oldpath)
            if not os.path.isabs(oldurl):
                oldurl = os.path.abspath(oldurl)

        output.write('新ipa(%s) 相比于 旧ipa(%s) 大小变化如下' % (newurl,oldurl))
        output.writeHtml('<h3 style="color:red">新ipa(%s) 相比于 旧ipa(%s) 大小变化如下</h3>' % (newurl,oldurl))
        newIPA = getFileModelForIPA(newpath)
        oldIPA = getFileModelForIPA(oldpath)
        summary = [('ipa文件',getsize(newpath),getsize(oldpath)),('执行文件',getsize(join(newIPA.appdir,newIPA.appname)),getsize(join(oldIPA.appdir,oldIPA.appname))),('app',newIPA.itemSize(),oldIPA.itemSize())]
        for i,item in enumerate(summary):
            tuple = binarySize(item[1]-item[2])
            output.write('%s: %s %s' % (item[0],tuple[0],tuple[1]))
        writeHTMLSummary(summary)

        output.write('\n\n对比结果如下：')

        compareIPAModel(newIPA,oldIPA)
        if len(newlinkmapurl):
            tuple = getLinkmapComparation(newlinkmapurl,oldlinkmapurl,False)
            linkmapcomparation = open(tuple[0]+tuple[1])
            linkmaphtmlcomparation = open(tuple[0]+tuple[2])
            for line in linkmapcomparation:
                output.write(line)
            for line in linkmaphtmlcomparation:
                output.writeHtml(line)
            linkmapcomparation.close()
            linkmaphtmlcomparation.close()
            shutil.rmtree(tuple[0])
        output.closeOutput()

        if len(emailaddr) > 0:
            emailhandler = Email('yy-pgone@yy.com','Guozhi1221')
            comparationfile = open(globaldir+'compareresult.html')
            emailcontent = ''
            for line in comparationfile:
                emailcontent += line
            emailcontent += '<div style="color:red">注：更详细内容在附件中</div>'
            comparationfile.close()
            emailhandler.sendmail('ipa compare result',emailaddr,['fangyang@yy.com'],[outputfile],emailcontent)
		
#shutil.rmtree(globaldir)

    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

if __name__ == "__main__":
    sys.exit(main())
