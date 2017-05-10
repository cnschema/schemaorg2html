# -*- coding: utf-8 -*-
# author: Li Ding
#


"""
changlog
    0.0.1.20170501: task_init_en2zh_mapping init chinese mapping form 2014 translation work
"""

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

import requests
import requests_cache
import wikipedia

__author__ = "Li Ding"
__version__ = "0.0.1.20170501"
__contexts__ = [os.path.basename(__file__), __version__]


from cnstool import excelWrite, stat, getValueList

def task_wikify(args):
    return wikify(args.phrase)

MAX_RESULT = 1
def wikify(phrase, description=None):
    ret = {}
    ret.update(wikify1(phrase, description))
    ret.update(wikify3(phrase, description))
    #logging.info(json.dumps(ret,sort_keys=True, indent=4))
    return ret

def wikify1(phrase, description=None):

    #wikification
    """
    {
        searchinfo: - {
        search: "birthday"
        },
        search: - [
        - {
            repository: "",
            id: "P3150",
            concepturi: "http://www.wikidata.org/entity/P3150",
            url: "//www.wikidata.org/wiki/Property:P3150",
            title: "Property:P3150",
            pageid: 28754653,
            datatype: "wikibase-item",
            label: "birthday",
            description: "item for day and month on which the subject was born. Used when full "date of birth" (P569) isn't known.",
            match: - {
            type: "label",
            language: "en",
            text: "birthday"
        }
    },"""
    urlBase = "https://www.wikidata.org/w/api.php?action=wbsearchentities&search={}&format=json&language=en&uselang=en&type=property"
    url = urlBase.format(re.sub("\s+","%20",phrase))
    r = requests.get(url)
    items = json.loads(r.content).get("search",[])
    #logging.info(items)
    ret = {}
    for idx, item in enumerate(items[0:MAX_RESULT]):
        if idx > 0:
            prefix = "wikidata_{}".format(idx+1)
        else:
            prefix = "wikidata"
        ret["{}".format(prefix)] = item["id"]
        ret["{}_label".format(prefix)] = item.get("label","")
        ret["{}_desc".format(prefix)] = item.get("description","")
        ret["{}_url".format(prefix)] = item["concepturi"]
    return ret

def wikify2(phrase, description=None):
    #wikification
    ret = {}
    wikiterm = wikipedia.search(phrase)
    for idx, term in enumerate(wikiterm[0:MAX_RESULT]):
        wikipage = wikipedia.page(term)
        ret["wikipedia_{}_url".format(idx)] = wikipage.url
        ret["wikipedia_{}_desc".format(idx)] = wikipedia.summary(term, sentences=1)

    return ret

def wikify3(phrase, description=None):
    ret = {}
    urlBase = "https://en.wikipedia.org/w/api.php?action=opensearch&format=json&formatversion=2&search={}&namespace=0&limit=10&suggest=true"
    url = urlBase.format(re.sub("\s+","%20",phrase))
    r = requests.get(url)
    jsonData = json.loads(r.content)
    #logging.info(items)
    ret = {}
    for idx, label in enumerate(jsonData[1][0:MAX_RESULT]):
        description = jsonData[2][idx]
        url = jsonData[3][idx]
        #if "refer to:" in description:
        #    continue

        if idx > 0:
            prefix = "wikipedia_{}".format(idx+1)
        else:
            prefix = "wikipedia"
        ret["{}_label".format(prefix)] = label
        ret["{}_desc".format(prefix)] = description
        ret["{}_url".format(prefix)] = url
    return ret

####################################################
def task_init_en2zh_mapping(args):
    # load old version zh-cn translation
    import requests_cache
    requests_cache.install_cache('local/req')

    # converted from https://github.com/schemaorg/schemaorg/tree/master/data/l10n/zh-cn
    # using RDFa tool https://www.w3.org/2012/pyRdfa/Overview.html#distill_by_input+with_options
    filename = os.path.join(os.path.dirname(__file__),'../data/l10n/vocab.zh-cn.2014.jsonld')
    mapIdItemZh = {}
    with open(filename) as f:
        jsonData = json.load(f)
        for item in jsonData["@graph"]:
            xid = item["@id"]
            xtype_list = getValueList(item, "@type")
            item["xtype"] = ','.join(xtype_list)
            newItem = {}
            for p in ["rdfs:label","rdfs:comment"]:
                for v in item.get(p,[]):
                    if type(v) == dict and v["@language"] == "zh-cn":
                        newItem["{}.zh-cn".format(p)] = v["@value"]

            mapIdItemZh[xid] = newItem

    stat(jsonData["@graph"], ["@id","xtype"],["xtype"])

    # current version
    version = "3.2"
    filename = "schema.jsonld"
    xfilename =  "/Users/lidingpku/haizhi/other/schemaorg/data/releases/{}/{}".format(version, filename)

    with open(xfilename) as f:
        jsonldSchema = json.load(f)
#    url = 'https://github.com/schemaorg/schemaorg/raw/sdo-callisto/data/releases/{}/{}'.format(version, filename)
#    logging.info(url)
#    r = requests.get(url)
#    jsonldSchema = json.loads(r.content)

    mapIdItem = {}
    wikikeys = set()
    for idx, item in enumerate(sorted(jsonldSchema["@graph"],key=lambda x:x["@id"])):
        xid = item["@id"]
        logging.info("{}/{} {}".format(idx, len(jsonldSchema["@graph"]), xid))
        xtype_list = getValueList(item, "@type")
        if "rdfs:Class" in xtype_list:
            item["group"] = "type"
        elif  "rdf:Property" in xtype_list:
            item["group"] = "property"
        else:
            #logging.info("skip {}".format(xid))
            item["group"] = "instance"
            continue

        item.update(mapIdItemZh.get(xid,{}))
        item["xtype"] = ','.join(xtype_list)
        mapIdItem[xid] = item

        #if not re.search(".+Action", xid):
        label = item["rdfs:label"]
        label = re.sub("([a-z])([A-Z])","\g<1> \g<2>",label)
        ret = wikify3(label, item['rdfs:comment'])
        if ret:
            item.update(ret)
            wikikeys.update(ret.keys())

        if item["group"] == "property":
            ret = wikify1(label, item['rdfs:comment'])
            if ret:
                item.update(ret)
                wikikeys.update(ret.keys())

        #logging.info(json.dumps(item, indent=4,sort_keys=True))

    filename = os.path.join(os.path.dirname(__file__),'../local/vocab.zh-cn.{}.xls'.format(version))
    items = mapIdItem.values()
    stat(items, ["@id","xtype"]+ list(wikikeys),["xtype"])
    items = sorted(items, key= lambda x: x["@id"])
    keys =  ["group", "@id","rdfs:label","rdfs:comment"]
    #print mapIdItemZh.values()[0].keys()
    keys.extend(mapIdItemZh.values()[0].keys())
    keys.extend( sorted(list(wikikeys)))
    excelWrite(items, keys, filename )


####################################################
def main():
    #  http://stackoverflow.com/questions/3217673/why-use-argparse-rather-than-optparse
    #  As of 2.7, optparse is deprecated, and will hopefully go away in the future
    parser = argparse.ArgumentParser(description="libcore")
    parser.add_argument('option', help='option')
    parser.add_argument('--version', help='schema.org version')
    parser.add_argument('--phrase', help='phrase')
    args = parser.parse_args()

    if args.option.startswith("task_"):
        # http://stackoverflow.com/questions/17734618/dynamic-method-call-in-python-2-7-using-strings-of-method-names
        the_method = getattr(sys.modules[__name__], args.option)
        if the_method:
            the_method(args)
            logging.info("done")
            return

    logging.info("unsupported")

if __name__ == "__main__":
    logging.basicConfig(format='[%(levelname)s][%(asctime)s][%(module)s][%(funcName)s][%(lineno)s] %(message)s', level=logging.INFO)
    logging.getLogger("requests").setLevel(logging.WARNING)

    main()

"""
    python scripts/preprocess.py task_wikify --phrase="birth place"
    python scripts/preprocess.py task_init_en2zh_mapping
"""
