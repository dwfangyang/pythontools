# coding=utf-8 ##以utf-8编码储存中文字符

import urllib
import sys
import shutil
import getopt
import platform
import time
import os
#reload(sys)
#sys.setdefaultencoding('utf-8')
dataOffset = 0  #data segment start address

class SymbolModel:
    file = ''
    size = 0
    codeSize = 0

def binarySize(size):
    if size < 1024:
        return '%5.0f'%float(size) +'B'
    elif size < 1024*1024:
        return '%5.1f'%(float(size)/1024) + 'KB'
    else:
        return '%5.1f'%(float(size)/(1024*1024)) + 'MB'

def getSymbolmap(content):
    partition = 0 #part num in linkmap, typically objects:1 sections:2 symbols:3 <<dead>>:4
    models = {};
    for line in content:
        if line.find('# Object files:') > -1:
            partition = 1
            continue
        if line.find('# Sections:') > -1:
            partition = 2
            continue
        if line.find('# Symbols:') > -1:
            partition = 3
            continue
        if line.find('# Dead') > -1:
            break
        if partition == 1:
            index = line.find(']')
            if index > -1:
                model = SymbolModel()
                model.file = line[index+2:len(line)-1]
                models[line[0:index+1]] = model
                #print model.file
        elif partition == 2:
            global dataOffset
            map = line[0:len(line)-1].split('\t')
            if map[2] == '__DATA' and dataOffset <= 0:
                dataOffset = long(map[0],16)
                #print '__DATA offset:',dataOffset
        elif partition == 3:
            map = line[0:len(line)-1].split('\t')
            if len(map) >= 3:
                key = map[2];
                lparent = key.find('[')
                rparent = key.find(']')
                if lparent > -1 and rparent > -1:
                    key = key[lparent:rparent+1]
                    #print key
                    if models.has_key(key):
                        models[key].size += long(map[1],16)
                        #print models[key].size
                        offset = int(map[0],16)
                        if offset < dataOffset:
                            models[key].codeSize += long(map[1],16)
            elif len(line) > 1:
                print 'symbols split wrong:',line,'line end'
    return models

def getGroupedSymbolmap(symbolmaps):
    models = {}
    for model in symbolmaps.itervalues():
        name = getGroupedFilename(model.file)
        if models.has_key(name):
            models[name].codeSize += model.codeSize
            models[name].size += model.size
        else:
            m = SymbolModel()
            m.file = name
            m.codeSize = model.codeSize
            m.size = model.size
            models[name] = m
    return models

def getGroupedFilename(filename):
    fragments = filename.split('/')
    name = fragments[len(fragments)-1]
    lparent = name.find('(')
    rparent = name.find(')')
    if lparent > -1 and rparent > -1:
        name = name[0:lparent]
    return name

def symbolSort(model):
    return model.size

def sortSymbols(symbolmodels):
    values = symbolmodels.values()
    values.sort(key=symbolSort,reverse=True)
    return values

def writeSymbolsLayout(filehandle,symbolModels):
    name = ('目标文件名','总数据大小','代码段大小')
    filehandle.write('%-40s\t%-30s\t%-20s\n' % name )#('%-38s\t%-20s\t%-20s' % (name,name,name)) # ,
    for i,model in enumerate(symbolModels):
        filehandle.write('%-40s\t%-20s\t%-20s\n' % (model.file,binarySize(model.size),binarySize(model.codeSize)))

def writeComparation(newModelMap,oldModelMap,filehandle):
    newmap = newModelMap.copy()
    oldmap = oldModelMap.copy()
    newappears = {}
    increase = {}
    decrease = {}
    deleted = {}
    newsize = incsize = decsize = delsize = 0
    newcodesize = inccodesize = deccodesize = delcodesize = 0
    for key in newmap.keys():
        if not oldmap.has_key(key):
            newappears[key] = newmap[key]
            newsize += newmap[key].size
            newcodesize += newmap[key].codeSize
        elif oldmap[key].size > newmap[key].size:
            model = SymbolModel()
            model.file = oldmap[key].file
            model.size = oldmap[key].size-newmap[key].size
            model.codeSize = oldmap[key].codeSize - newmap[key].codeSize
            decrease[key] = model
            oldmap.pop(key)
            decsize += model.size
            deccodesize += model.codeSize
        elif oldmap[key].size < newmap[key].size:
            model = SymbolModel()
            model.file = oldmap[key].file
            model.size = newmap[key].size-oldmap[key].size
            model.codeSize = newmap[key].codeSize - oldmap[key].codeSize
            increase[key] = model
            oldmap.pop(key)
            incsize += model.size
            inccodesize += model.codeSize
        else:
            oldmap.pop(key)
    for key in oldmap.keys():
        deleted[key] = oldmap[key]
        delsize += oldmap[key].size
        delcodesize += oldmap[key].codeSize

    filehandle.write('对比结果如下：\n')
    newlist = newappears.values()
    inclist = increase.values()
    declist = decrease.values()
    dellist = deleted.values()
    newlist.sort(key=symbolSort,reverse=True)
    declist.sort(key=symbolSort,reverse=True)
    inclist.sort(key=symbolSort,reverse=True)
    dellist.sort(key=symbolSort,reverse=True)
    if len(newappears) > 0:
        filehandle.write('新增部分：%-20s,代码：%-20s(%d项)\n' % (binarySize(newsize),binarySize(newcodesize),len(newappears)))
        for i,model in enumerate(newlist):
            filehandle.write('%-40s\t%-20s\t%-20s\n' % (model.file,binarySize(model.size),binarySize(model.codeSize)))
    if len(increase) > 0:
        filehandle.write('\n增加部分：%-20s,代码：%-20s(%d项)\n' % (binarySize(incsize),binarySize(inccodesize),len(increase)))
        for i,model in enumerate(inclist):
            filehandle.write('%-40s\t%-20s\t%-20s\n' % (model.file,binarySize(model.size),binarySize(model.codeSize)))
    if len(decrease) > 0:
        filehandle.write('\n减少部分：%-20s,代码：%-20s(%d项)\n' % (binarySize(decsize),binarySize(deccodesize),len(decrease)))
        for i,model in enumerate(declist):
            filehandle.write('%-40s\t%-20s\t%-20s\n' % (model.file,binarySize(model.size),binarySize(model.codeSize)))
    if len(deleted) > 0:
        filehandle.write('\n删除部分：%-20s,代码：%-20s(%d项)\n\n' % (binarySize(delsize),binarySize(delcodesize),len(deleted)))
        for i,model in enumerate(dellist):
            filehandle.write('%-40s\t%-20s\t%-20s\n' % (model.file,binarySize(model.size),binarySize(model.codeSize)))

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hc:", ["help"])
        except getopt.error, msg:
            raise Usage(msg)

        newurl = ''
        oldurl = ''

        for name,value in opts:
            if name in ('-h','--help'):
                print '''
linkmaper.py:
serves as a tool for executable layout parsing with linkmapfile
usage:
linkmaper.py [-c comparedlinkmapurl] linkmapurl

-c      用于对比的旧版本
-h      帮助文档
                    '''
            elif name in ('-c'):
                oldurl = value

        globaldir = '/Library/WebServer/Documents/'
        if platform.platform().find('Windows') > -1:
            globaldir = 'E:/wamp64/tmp/'

        outputfile = open(globaldir+'result.txt','w')   #outputfile

        globaldir += str(time.time()) + '/'

        if not os.path.exists(globaldir):   #make tmp dir
            os.makedirs(globaldir)

        newurl = args[0]

        newpath = globaldir + 'linkmap.txt'
        oldpath = globaldir + 'linkmap_compared.txt'

        #download linkmap files
        #outputfile.write('start download:'+newurl)
        urllib.urlretrieve(newurl, newpath)
        #outputfile.write('start download:'+oldurl)
        urllib.urlretrieve(oldurl, oldpath)

        oldfilelinkmap = open(oldpath)
        oldmodelmap = getSymbolmap(oldfilelinkmap.readlines())
        oldmodelmap = getGroupedSymbolmap(oldmodelmap)
        sortedOldSymbols = sortSymbols(oldmodelmap)
        oldfilelinkmap.close()
        
        filelinkmap = open(newpath)
        newmodelmap = getSymbolmap(filelinkmap.readlines())
        newmodelmap = getGroupedSymbolmap(newmodelmap)
        sortedNewSymbols = sortSymbols(newmodelmap)
        filelinkmap.close()

        writeComparation(newmodelmap,oldmodelmap,outputfile)
        outputfile.write('\n新linkmap分布如下：\n')
        writeSymbolsLayout(outputfile,sortedNewSymbols)
        outputfile.write('\n旧linkmap分布如下：\n')
        writeSymbolsLayout(outputfile,sortedOldSymbols)

        #clean tmp files
        print 'about to delete: '+globaldir
        shutil.rmtree(globaldir)
        outputfile.close()
	
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

if __name__ == '__main__':
    sys.exit(main())
