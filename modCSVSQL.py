path = 'C:\\Users\\alpro\\Downloads'

def loadTable(filename):
    f = open(path + '\\' + filename,'r')
    strdata = cleanAndStructure(f.read())
    f.close()
    return strdata

def cleanAndStructure(data):
    tabledict = {}
    entrydelim = ','
    recorddelim = '\n'
    headersflag = True
    data = data.strip(recorddelim)
    for line in data.split(recorddelim):
        if headersflag:
            headerslist = cleanQuotes(line.split(entrydelim),entrydelim)
            for header in headerslist:
                tabledict[header] = []
            headersflag = False
        else:
            recordlist = cleanQuotes(line.split(entrydelim),entrydelim)
            i = 0
            while i < len(headerslist):
                tabledict[headerslist[i]].append(recordlist[i])
                i += 1
    return tabledict

def cleanQuotes(linelist,delim):
    i = 0
    while i < len(linelist):
        if linelist[i].startswith('"'):
            a = linelist.pop(i)
            linelist[i] = a.lstrip('"') + delim + linelist[i].rstrip('"')
        i +=1
    return linelist

def saveTable(arr2d,filename):
    f = open(path + '\\' + filename,'w')
    arrstr = table2string(arr2d)
    f.write(arrstr)
    f.close()

def table2string(table):
    entrydelim = ','
    recorddelim = '\n'
    tablestr = ''
    headerslist = table.keys()
    for header in headerslist:
        tablestr += escapeDelimAddDelim(header,entrydelim)
    tablestr = tablestr.strip(entrydelim) + recorddelim
    i = 0
    while i < len(table[header]):
        for header in headerslist:
            tablestr += escapeDelimAddDelim(table[header][i],entrydelim)
        tablestr = tablestr.strip(entrydelim) + recorddelim
        i += 1

    return tablestr.strip(recorddelim)

def escapeDelimAddDelim(string,delim):
    if delim in string:
        return '"' + string + '"' + delim
    else:
        return string + delim

def lookup(returnheader,table,critheader,critval):
    return table[returnheader][table[critheader].index(critval)]

def appendRecords(table,records):
    if isinstance(records,dict):
        for header in table.keys():
            if header in records.keys():
                if isinstance(records[header],list):
                    table[header].extend(records[header])
                else:
                    table[header].append(records[header])
    else:
        i = 0
        for data in table.values():
            if i < len(records):
                if isinstance(records[i],list):
                    data.extend(records[i])
                else:
                    data.append(records[i])
            i += 1

fname = 'tblTestHeaders.csv'
tblA = loadTable(fname)
print(tblA.keys())
print(tblA)
print(table2string(tblA))
# saveTable(tblA,fname)
# print(tblA)
print(lookup('Value',tblA,'Name','nameD'))
appendRecords(tblA,[['7','8'],['nameG','nameH'],['valG','valH']])
print(tblA)
appendRecords(tblA,{'ID':['9','10'],'Value':['valI','valJ'],'Name':['nameI','nameJ']})
print(tblA)