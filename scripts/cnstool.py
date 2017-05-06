# -*- coding: utf-8 -*-
# author: Li Ding
#


# base packages
import os
import sys
import json
import logging
import codecs
import hashlib
import datetime
import logging
import time
import argparse
import urlparse
import re
import collections

def stat(items, unique_fields, value_fields=[]):
    counter = collections.Counter()
    unique_counter = collections.defaultdict(list)

    for item in items:
        counter["all"] +=1
        for field in unique_fields:
            if item.get(field):
                unique_counter[field].append(item[field])
        for field in value_fields:
            value = item.get(field)
            if value:
                counter[u"{}_{}".format(field,value)] +=1

    for field in unique_fields:
        counter[u"{}_unique".format(field)] = len(set(unique_counter[field]))
        counter[u"{}_nonempty".format(field)] = len(unique_counter[field])

    logging.info( json.dumps(counter, ensure_ascii=False, indent=4, sort_keys=True) )


def excelWrite(items, keys, filename, page_size=60000):
    import xlwt
    wb = xlwt.Workbook()
    rowindex =0
    sheetindex=0
    for item in items:
        if rowindex % page_size ==0:
            sheetname = "%02d" % sheetindex
            ws = wb.add_sheet(sheetname)
            rowindex = 0
            sheetindex +=1

            colindex =0
            for key in keys:
                ws.write(rowindex, colindex, key)
                colindex+=1
            rowindex +=1

        colindex =0
        for key in keys:
            v = item.get(key,"")
            if type(v) == list:
                v = ','.join(v)
            if type(v) == set:
                v = ','.join(v)
            ws.write(rowindex, colindex, v)
            colindex+=1
        rowindex +=1

    logging.debug(filename)
    wb.save(filename)

def test_excelWrite(filename):
    input_data = [{
        "name":u"张三",
        u"年龄":18
    },
    {
        "name":u"李四",
        "notes":u"this is li si",
        u"年龄":18
    }]
    excelWrite(input_data, ["name", u"年龄", "notes"], filename)

####################################
# 2017-01-21  selected

def excelRead(filename, non_empty_col=0, file_contents=None):
    # http://www.lexicon.net/sjmachin/xlrd.html
    import xlrd

    counter = collections.Counter()
    if file_contents:
        workbook = xlrd.open_workbook(file_contents=file_contents)
    else:
        workbook = xlrd.open_workbook(filename)

    start_row = 0
    ret = collections.defaultdict(list)
    fields = {}
    for name in workbook.sheet_names():
        sh = workbook.sheet_by_name(name)
        headers = []
        for col in range(len(sh.row(start_row))):
            headers.append(sh.cell(start_row,col).value)

        logging.info( u"sheet={} header={} rows={}".format( name, json.dumps(headers,ensure_ascii=False) , sh.nrows) )

        fields[name]= headers

        for row in range(start_row+1, sh.nrows):
            item={}
            rowdata = sh.row(row)
            if len(rowdata)< len(headers):
                msg = "skip mismatched row {}".format(json.dumps(rowdata, ensure_ascii=False))
                logging.warning(msg)
                continue

            for col in range(len(headers)):
                value = sh.cell(row,col).value
                if type(value) in [unicode, basestring]:
                    value = value.strip()
                item[headers[col]]= value

            if non_empty_col>=0 and not item[headers[non_empty_col]]:
                logging.debug("skip empty cell")
                continue

            ret[name].append(item)
        logging.info( u"loaded {} {} (non_empty_col={})".format( filename, len(ret[name]) , non_empty_col))
    return {'data':ret,'fields':fields}

def test_excelRead(filename):
    output_data =excelRead(filename)
    logging.info(json.dumps(output_data,ensure_ascii=False,indent=4))


def getValueList( node, p):
    v = node.get(p,[])
    if type(v) == list:
        return v
    else:
        return [v]
