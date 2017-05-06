# -*- coding: utf-8 -*-
# author: Li Ding
#


"""
changlog
    0.0.1.20170501: simple translation, one page html
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
import copy

import requests
import requests_cache


__author__ = "Li Ding"
__version__ = "0.0.1.20170501"
__contexts__ = [os.path.basename(__file__), __version__]


from cnstool import excelWrite, stat, getValueList

####################################################
def ensureDir(filename):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def task_one_html(args):
    logging.info(args)

    # download jsonldSchema
    filename = os.path.join(os.path.dirname(__file__),'../local/cache')
    requests_cache.install_cache(filename)

    # generate html
    gen = Schema2html(args.version, args.site)
    gen.downloadDocs()
    gen.downloadSpecial()
    gen.initData()
    gen.run()

def getUsageStr(usageId):
    if (usageId == '1') :
        return "Between 10 and 100 domains"
    elif (usageId == '2'):
        return "Between 100 and 1000 domains"
    elif (usageId == '3'):
        return "Between 1000 and 10,000 domains"
    elif (usageId == '4'):
        return "Between 10,000 and 50,000 domains"
    elif (usageId == '5'):
        return "Between 50,000 and 100,000 domains"
    elif (usageId == '7'):
        return "Between 100,000 and 250,000 domains"
    elif (usageId == '8'):
        return "Between 250,000 and 500,000 domains"
    elif (usageId == '9'):
        return "Between 500,000 and 1,000,000 domains"
    elif (usageId == '10'):
        return "Over 1,000,000 domains"
    else:
        return ""

PLIST_BASIC = ["@id","rdfs:label","rdfs:comment", "_supersede", "_usage", "_layer","_examples","_instances"]
PLIST_REF = ["@id","rdfs:label"]
PLIST_DOMAIN_RANGE = ["http://schema.org/rangeIncludes","http://schema.org/domainIncludes"]
INVERSE_DOMAIN_RANGE ={
"http://schema.org/domainIncludes":"isDomainOf",
"http://schema.org/rangeIncludes":"isRangeOf",
}
PLIST_OBJ = ["http://schema.org/inverseOf", "http://schema.org/supersededBy"]
PLIST_PROP = PLIST_BASIC + PLIST_DOMAIN_RANGE + INVERSE_DOMAIN_RANGE.values() + PLIST_OBJ

def appendSafe(obj, p, v):
    vlist = obj.get(p,[])
    if vlist:
        vlist.append(v)
    else:
        obj[p] = [v]

def getExampleUrls():
    url = "https://github.com/schemaorg/schemaorg/tree/master/data"
    r = requests.get(url)
    logging.info(r.content)
    filenames = re.findall(r"data/[\w\-]*examples.txt", r.content)

    urlBase = "https://github.com/schemaorg/schemaorg/raw/master"
    return [ urlBase+"/"+x for x in filenames]



def loadExample(lines):
    examples = []
    for line in lines:
        #line = line
        if not line.strip():
            continue

        if line.startswith("TYPES:"):
            types = [x.strip() for x in re.split("[\s,]+",line[6:]) if x.strip() and not x.startswith("#")]
            state = "TYPES"
            example = collections.defaultdict(list)
            example[state] = types
            examples.append(example)
        elif line in ["PRE-MARKUP:", "MICRODATA:", "RDFA:","JSON:"]:
            state = line[:-1]
        else:
            example[state].append(line.decode("utf-8"))

    for example in examples:
        for p in ["PRE-MARKUP", "MICRODATA", "RDFA","JSON"]:
            example[p] = u"\n".join(example[p])

        p = "PRE-MARKUP"
        example[p] = re.sub(ur"&amp;", "&", example[p])

    logging.info(len(examples))
    return examples

def diffPage2(html, url, debug=False):
    r = requests.get(url)

    url2 = url.replace("http://","https://")
    r2 = requests.get(url2)

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.content, 'html.parser')
    soupRef = BeautifulSoup(r2.content, 'html.parser')

    import difflib
    text = soup.text
    textRef = soupRef.text

    words = sorted(list(set(re.split(r"[\W]+", text))))
    wordsRef = sorted(list(set(re.split(r"[\W]+", textRef))))

    s = difflib.SequenceMatcher(None, words, wordsRef)
    ratio = s.ratio()
    if ratio < 0.95:
        print url, url2


def diffPage(html, url, debug=False):
    url = url.replace("http://","https://")
    r = requests.get(url)
    htmlRef = r.content

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    soupRef = BeautifulSoup(htmlRef, 'html.parser')

    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.extract()    # rip it out

    # kill all script and style elements
    for script in soupRef(["script", "style"]):
        script.extract()    # rip it out

    import difflib
    text = soup.text
    textRef = soupRef.text

    words = sorted(list(set(re.split(r"[\W]+", text))))
    wordsRef = sorted(list(set(re.split(r"[\W]+", textRef))))

    if debug:
        for line in difflib.context_diff(wordsRef, words):
            print line

    #s = difflib.SequenceMatcher(None, text, textRef)
    #s = difflib.SequenceMatcher(None, list(soup.stripped_strings), list(soupRef.stripped_strings))
    s = difflib.SequenceMatcher(None, words, wordsRef)
    ratio = s.ratio()
    if url in [
    #     "http://schema.org/organizer",
    #     "http://schema.org/broadcastDisplayName",
    #     "http://schema.org/WebSite",
    #     "http://schema.org/HotelRoom",
    #     "http://schema.org/partOfInvoice",
    #     "http://schema.org/UseAction",
    #     "http://schema.org/currency",
    #     "http://schema.org/PlanAction",
    #     "http://schema.org/MovieTheater",
    #     "http://schema.org/PerformanceRole",
    #     "http://schema.org/PaymentComplete",
    #     "http://schema.org/ownedThrough",
    #     "http://schema.org/VideoGameClip",
    #     "http://schema.org/Report",
    #     "http://schema.org/keywords",
    #     "http://schema.org/amount",
    #     "http://schema.org/claimReviewed",
    #     "http://schema.org/programName",
    #     "http://schema.org/UserInteraction",
    #     "http://schema.org/UnRegisterAction",
    #     "http://schema.org/TrainStation",
    #     "http://schema.org/SportsTeam",
    #     "http://schema.org/UserLikes",
    #     "http://schema.org/ExerciseAction",
    #     "http://schema.org/DataType",
    #     "http://schema.org/Episode",
    #     "http://schema.org/FindAction",
    #     "http://schema.org/FollowAction",
    #     "http://schema.org/FailedActionStatus",
    #     "http://schema.org/FoodEstablishment",
    #     "http://schema.org/vehicleInteriorColor",
    #     "http://schema.org/FoodEvent",
    #     "http://schema.org/False",
    #
    #     "http://schema.org/Game",
    #     "http://schema.org/GameServer",
    #     "http://schema.org/GenderType",
    #     "http://schema.org/GovernmentService",
    #     "http://schema.org/Hostel",
    #     "http://schema.org/InformAction",
    #     "http://schema.org/InsertAction",
    #     "http://schema.org/InteractAction",
    #     "http://schema.org/ItemListOrderType",
    #     "http://schema.org/JobPosting",
    #     "http://schema.org/Language",
    #     "http://schema.org/MedicalOrganization",
    #     "http://schema.org/Menu",
    #     "http://schema.org/Message",
    #     "http://schema.org/Motel",
    #     "http://schema.org/MoveAction",
    #     "http://schema.org/OrganizationRole",
    #     "http://schema.org/PaymentStatusType",
    #     "http://schema.org/PeopleAudience",
    #     "http://schema.org/Permit",
    #     "http://schema.org/ProfilePage",
    #     "http://schema.org/PublicationEvent",
    #     "http://schema.org/QAPage",
    #     "http://schema.org/ReactAction",
    #     "http://schema.org/RentalCarReservation",
    #     "http://schema.org/ReservationStatusType",
    #     "http://schema.org/ReturnAction",
	# "http://schema.org/RsvpAction",
	# "http://schema.org/RsvpResponseYes",
	# "http://schema.org/SearchAction",
	# "http://schema.org/Series",
	# "http://schema.org/ShareAction",
	# "http://schema.org/SingleFamilyResidence",
	# "http://schema.org/SocialEvent",
	# "http://schema.org/SomeProducts",
	# "http://schema.org/SportsEvent",
	# "http://schema.org/TVClip",
	# "http://schema.org/TVEpisode",
	# "http://schema.org/TVSeries",
	# "http://schema.org/TaxiReservation",
	# "http://schema.org/TheaterEvent",
	# "http://schema.org/TipAction",
	# "http://schema.org/TouristAttraction",
	# "http://schema.org/TrackAction",
	# "http://schema.org/TrainReservation",
	# "http://schema.org/True",
	# "http://schema.org/UpdateAction",
	# "http://schema.org/UserComments",
	# "http://schema.org/UserPlays",
	# "http://schema.org/VideoGameSeries",
	# "http://schema.org/WantAction",
	# "http://schema.org/WriteAction",
	# "http://schema.org/artMedium",
	# "http://schema.org/billingIncrement",
	# "http://schema.org/broadcastOfEvent",
	# "http://schema.org/character",
	# "http://schema.org/currenciesAccepted",
	# "http://schema.org/dateDeleted",
	# "http://schema.org/encoding",
	# "http://schema.org/gtin8",
	# "http://schema.org/honorificSuffix",
	# "http://schema.org/instructor",
	# "http://schema.org/iswcCode",
	# "http://schema.org/itemOffered",
	# "http://schema.org/jobTitle",
	# "http://schema.org/knownVehicleDamages",
	# "http://schema.org/playMode",
	# "http://schema.org/provider",
	# "http://schema.org/query",
	# "http://schema.org/recipient",
    #
    #     "http://schema.org/Researcher",
    #     "http://schema.org/MultiPlayer",
    #     "http://schema.org/InStoreOnly",
    #
    #     "http://schema.org/UnitPriceSpecification",
    #     "http://schema.org/FilmAction"
        ]:
        assert ratio > 0, url
    else:
        if ratio > 0.9:
            pass
        else:
            #logging.info( ratio )
            #logging.error( os.path.basename(url) )
            print( '\t"{}",'.format(url) )

SITE_CNSCHEMA = "cnschema.ruyi.ai"

def cleanAbsoluteUrl(content):
    ret = content
    ret = re.sub("https?://schema.org/docs","/docs", ret)
    return ret

class Schema2html():

    def __init__(self, version, site):
        self.version = version
        self.site = site
        self.dirOutput = os.path.join(os.path.dirname(__file__), "../data/releases/{}/").format(self.version)
        self.mapNameExample = collections.defaultdict(list)

    def downloadSpecial(self):
        url = "http://code.jquery.com/jquery-1.5.1.min.js"
        r = requests.get(url)
        filename = os.path.join(self.dirOutput, "{}/docs".format(self.site), os.path.basename(url))
        ensureDir(filename)
        with codecs.open(filename,'wb') as f:
            f.write(r.content)

        url = "https://github.com/schemaorg/schemaorg/tree/master/docs/favicon.ico"
        r = requests.get(url)
        filename = os.path.join(self.dirOutput, "{}".format(self.site), os.path.basename(url))
        with codecs.open(filename,'wb') as f:
            f.write(r.content)

        url = "https://schema.org/docs/full.html"
        r = requests.get(url)
        filename = os.path.join(self.dirOutput, "{}/docs".format(self.site), os.path.basename(url))
        with codecs.open(filename,'wb') as f:
            content = r.content
            content = cleanAbsoluteUrl(content)
            f.write(content)

        url = "https://schema.org/"
        r = requests.get(url)
        filename = os.path.join(self.dirOutput, "{}/index.htm".format(self.site))
        with codecs.open(filename,'wb') as f:
            content = r.content
            content = cleanAbsoluteUrl(content)
            f.write(content)


    def downloadDocs(self):

        url = "https://github.com/schemaorg/schemaorg/tree/master/docs"
        r = requests.get(url)
        logging.info(r.content)
        filenames = re.findall(r"(docs/[^\"]+\.(txt|owl|html|css|js|jsonld))", r.content)


        urlBase = "https://github.com/schemaorg/schemaorg/raw/master"
        for fx in filenames:
            filename = fx[0]

            url = urlBase + "/" + filename
            logging.info(url)
            r = requests.get(url)

                #logging.info(filename)
            filename = os.path.join(self.dirOutput, "{}/".format(self.site), filename)
            with codecs.open(filename,'wb') as f:
                content = r.content
                #if not "action" in filename:
                #    continue

                if filename.endswith("html") and self.site!= "schema.org":
                    content = re.sub(r"//ajax.googleapis.com/ajax/libs/jquery/1.5.1/jquery.min.js", "jquery-1.5.1.min.js", content)
                    #content = re.sub(ur"<script.*google.*</script>","", content)

                    SEPEARTOR = "&&&&_____"
                    content = re.sub("\n+",SEPEARTOR, content)
                    content = re.sub(ur"<script[^>]*google.[^<]*</script>","", content)
                    content = re.sub(ur"<script[^>]+>[^<]*google.[^<]*</script>","", content)
                    content = cleanAbsoluteUrl(content)
                    content = re.sub(SEPEARTOR,"\n", content)
                    #logging.info(content[:3000])
                f.write( content )
        #exit()

    def copyData(self, v, plist=PLIST_BASIC, simplify=False):
        ret = {}
        for p in plist:
            if not p in v:
                continue

            if simplify:
                pX = os.path.basename(p)
            else:
                pX = p

            if p in PLIST_DOMAIN_RANGE:
                ret[pX] = []
                for rX in getValueList(v, p):
                    r = self.mapIdNode.get(rX["@id"])
                    ret[pX].append(self.copyData(r, PLIST_REF))
                if ret[pX]:
                    ret[pX][-1]["_last"] = True
            elif p in PLIST_OBJ:
                r = self.mapIdNode.get(v[p]["@id"])
                ret[pX] = self.copyData(r, PLIST_REF)
            else:
                ret[pX] = v[p]


        #logging.info(ret.keys())
        return ret




    def initData(self):
        urlBase = "https://github.com/schemaorg/schemaorg/raw/sdo-callisto"

        #examples
        self.mapNameExample = collections.defaultdict(list)

        urls = getExampleUrls()
        for url in urls:
            logging.info(url)
            examples = loadExample(re.split("\n",requests.get(url).content))
            for example in examples:
                example["_source"] = url
                #logging.info(example)
                for xtype in example["TYPES"]:
                    x = copy.deepcopy(example)
                    x["_index"] = len(self.mapNameExample[xtype])+1
                    self.mapNameExample[xtype].append(x)

        #logging.info(self.mapNameExample["MusicPlaylist"])
        #exit()

        # the word count
        self.mapNameCount = {}
        filename = "2015-04-vocab_counts.txt"
        url = '{}/data/{}'.format(urlBase,  filename)
        r = requests.get(url)

        for idx, line in enumerate(re.split("\n",r.content)):
            #line =line.strip()
            if not line:
                continue
            temp = re.split("\t",line)
            if len(temp) != 2:
                logging.warn("bad input at line {}, [{}]".format(idx, line))
                continue
            name, usageId = temp
            self.mapNameCount[name] = usageId

        # the main json-ld
        self.mapIdNode = {}
        filename = "schema.jsonld"
        version = self.version
        url = '{}/data/releases/{}/{}'.format(urlBase,version, filename)
        #logging.info(url)
        r = requests.get(url)
        self.jsonldSchema = json.loads(r.content)
        logging.info(len(self.jsonldSchema))

        for node in self.jsonldSchema["@graph"]:
            if "schema.org" not in node["@id"]:
                logging.debug(node["@id"])
                # node.get("@type")
                pass

            type_list = node.get("@type",[])
            if not type(type_list) == list:
                type_list = [type_list]
            node["xtype"] = ','.join(type_list)


        #first pass
        for node in self.jsonldSchema["@graph"]:
            xid = node["@id"]
            self.mapIdNode[xid] = node

            #group
            xtypeList = getValueList(node, "@type")
            if "rdfs:Class" in xtypeList:
                node["_group"] = "type"
            elif "rdf:Property" in xtypeList:
                node["_group"] = "property"
            else:
                node["_group"] = "other"

            node["_layer"] = "core"

            #nameCount
            usageId = self.mapNameCount.get(node.get("rdfs:label"))
            node["_usage"] = getUsageStr(usageId)

            examples = self.mapNameExample.get(node.get("rdfs:label"))
            if examples:
                node["_examples"] = examples
                #logging.info(examples)
            #exit()
        #stat(self.jsonldSchema["@graph"], ["@id","xtype"],["xtype"])
        #exit(0)




    def genIndex(self):
        #second pass
        for node in self.jsonldSchema["@graph"]:
            xid = node["@id"]

            # instances
            for xtype in getValueList(node, "@type"):
                clsObj = self.mapIdNode.get(xtype)
                if clsObj:
                    appendSafe(clsObj, "_instances", self.copyData(node, PLIST_REF))
                    clsObj["_instances"] = sorted(clsObj["_instances"], key=lambda x:x["rdfs:label"])
            # subclass relation
            for p in ["rdfs:subClassOf", "rdfs:subPropertyOf"]:
                for v in getValueList(node, p):
                    superId = v["@id"]
                    if superId not in self.mapIdNode:
                        continue

                    superNode = self.mapIdNode[superId]
                    appendSafe(node, "_super", superId)
                    appendSafe(superNode, "_sub", xid)

            #domain range
            if node["_group"]  == "property":
                for p in PLIST_DOMAIN_RANGE:
                    for xdomainObj in getValueList(node, p):
                        refxid = xdomainObj["@id"]
                        pX = INVERSE_DOMAIN_RANGE[p]
                        appendSafe(self.mapIdNode[refxid], pX, node)
                        self.mapIdNode[refxid][pX]= sorted(self.mapIdNode[refxid][pX], key=lambda x:x["rdfs:label"])

            # http://schema.org/supersededBy
            p = "http://schema.org/supersededBy"
            if p in node:
                superId = node[p]["@id"]
                superNode = self.mapIdNode[superId]
                superNode["_supersede"] = self.copyData(node, PLIST_REF)
                #logging.info(superNode)
                #exit()


        #stat for class/type
        filename = os.path.join(self.dirOutput, "misc/class.xls")
        ensureDir(filename)
        items = [x for x in self.mapIdNode.values() if x["_group"] == "type"]
        items = sorted(items, key= lambda x: x["@id"])
        excelWrite(items, ["@id","rdfs:label","rdfs:comment"],filename )

        #stat for property
        filename = os.path.join(self.dirOutput, "misc/property.xls")
        items = [x for x in self.mapIdNode.values() if x["_group"] == "property"]
        items = sorted(items, key= lambda x: x["@id"])
        excelWrite(items, ["@id","rfds:label","rdfs:comment"],filename )

        class_hierarchy = self.genClassHierachy(["http://schema.org/Thing"])
        filename = os.path.join(self.dirOutput, "misc/taxonomy.json")
        with open(filename, 'w') as f:
            f.write(json.dumps(class_hierarchy[0], indent=4, sort_keys=True))

        self.genTermPage()

    def genClassHierachy(self, roots):
        output = []
        #logging.info(roots)
        for root in roots:
            node = self.mapIdNode[root]
            item = {}
            item["name"] = node["rdfs:label"]
            subclasses = node.get("_sub",[])
            if subclasses:
                item["children"] = self.genClassHierachy(subclasses)
            output.append(item)
        return output


    def genTermPage(self):
        def genPath(p, node, path, result):
            if p in node:
                for v in node[p]:
                    nextNode = self.mapIdNode[v]
                    genPath(p, nextNode, path + [nextNode], result)
            else:
                temp = []
                for node in reversed(path):
                    temp.append(self.copyData(node, PLIST_REF))
                temp[-1]["_lastone"] = True
                result.append({"_path":temp})


        filters = [
        #    "http://schema.org/track",
        #    "http://schema.org/MusicPlaylist"
        #    "http://schema.org/LiveAlbum"
        #    "http://schema.org/Offer"
        #"http://schema.org/identifier"
        #"http://schema.org/claimReviewed"
    #    "http://schema.org/DataType"
#    "http://schema.org/FoodEstablishment",
#    "http://schema.org/foodEstablishment",
#"http://schema.org/referenceQuantity"
#"http://schema.org/gtin8"
        ]
        for xid in sorted(self.mapIdNode):
            node = self.mapIdNode[xid]

            if filters and not xid in filters:
                continue

            if "#" in xid:
                logging.warn("skip {}".format(xid))
                continue

            entry = self.copyData(node, PLIST_PROP, simplify=True)
            filename = os.path.join(os.path.dirname(__file__), "../templates/page.mustache")
            with codecs.open (filename, encoding="utf-8") as f:
                templatePage = f.read()

            entry["_node_label"] = entry["rdfs:label"]

            entry["_group_{}".format(node["_group"])] = True

            #source
            p = "http://purl.org/dc/terms/source"
            sourceList = getValueList(node, p)
            for sourceRef in sourceList:
                if not type(sourceRef) == dict:
                    logging.error(sourceList)
                    continue

                #logging.info(node[p])
                source = self.mapIdNode.get(sourceRef["@id"])
                if source:
                    temp = source
                    appendSafe(entry, "_sourceAck", temp)
                else:
                    temp = {}
                    temp["@id"] = sourceRef["@id"]
                    temp["rdfs:label"] = sourceRef["@id"]
                    temp["rdfs:comment"] = '<a href="{}">{}</a>'.format(sourceRef["@id"],sourceRef["@id"])
                    appendSafe(entry, "_source", temp)

            if node["_group"] == "property":
                result = []
                genPath("_super", node, [node], result)

                rootPath = [ self.copyData(self.mapIdNode["http://schema.org/Thing"], PLIST_REF),
                                    {"rdfs:label":"Property", "@id":"http://meta.schema.org/Property"}]
                entry["_paths"] = []
                for onePath in result:
                    temp = []
                    temp.extend(rootPath)
                    temp.extend(onePath["_path"])
                    temp[-1]["_lastone"] = True
                    entry["_paths"].append({"_path":temp})

            if node["_group"] == "other":
                result = []
                typeNode = self.mapIdNode.get(node["@type"])
                genPath("_super", typeNode, [typeNode], result)
                entry["_paths"] = result
                entry["_is_instance"] = True

            if node["_group"] == "type":
                #path
                result = []
                genPath("_super", node, [node], result)
                #logging.info(result)
                entry["_paths"] = result

                #domain
                p = "http://schema.org/domainIncludes"
                p = "isDomainOf"
                pX = os.path.basename(p)
                entry["_pTree"]=[]
                seedList = [xid]
                while seedList:
                    newSeedList = []
                    for seedId in seedList:
                        seed = self.mapIdNode.get(seedId)

                        treeItem = self.copyData(seed)
                        treeItem["_properties"] = []

                        for v in sorted(seed.get(p,[]), key=lambda x:x["@id"]):
                            if "http://schema.org/supersededBy" in v:
                                continue


                            prop = self.copyData(v, plist=PLIST_PROP, simplify=True)

                            # if v["@id"] == "http://schema.org/offeredBy":
                            #     logging.info(v.keys())
                            #     logging.info(prop.keys())
                            #     exit()

                            #logging.info(prop)
                            treeItem["_properties"].append(prop)
                            #break #TODO

                        if treeItem["_properties"]:
                            entry["_pTree"].append(treeItem)

                        newSeedList.extend( seed.get("_super",[]) )
                        #logging.info(v)
                    seedList = newSeedList
                if entry["_pTree"]:
                    entry["_pTree"][-1]["_last"]=True

                #range
                p = "http://schema.org/rangeIncludes"
                p = "isRangeOf"
                pX = "_pRange"
                if node.get(p,[]):
                    entry[pX]=[]
                    for v in sorted(node.get(p,[]), key= lambda x:x["@id"]):
                        prop = self.copyData(v,plist=PLIST_PROP, simplify=True)
                        entry[pX].append(prop)


            #super and sub
            for p in ["_sub", "_super"]:
                if node.get(p, []):
                    entry[p] = []
                    for v in node.get(p, []):
                        relNode = self.mapIdNode.get(v)
                        entry[p].append(self.copyData(relNode, PLIST_REF))

            entry["_sitename"] = "schema.org" # self.site

            entry["_version"] = self.version
            entry["_url_root"] = "."
            entry["_url_schema"] = "http://{}".format(self.site) # "http://schema.org"

            #entry["_examples"] = []
            for k, v in entry.items():
                if type(v) == list  and v and type(v[0]) in [dict,collections.defaultdict]:
                    v[-1]["_last"] = True
                #logging.info(k)
                #logging.info(type(v))
                #logging.info(type(v[0]))
            #exit()

            #logging.info(node["@id"])
            #logging.info( json.dumps(entry,  indent=4, sort_keys=True) )
            #logging.info(node["@id"])
            import pystache
            html = pystache.render(templatePage, entry)
            filename = os.path.join(self.dirOutput,"{}/{}.html".format(self.site, node["rdfs:label"]))
            ensureDir(filename)
            with codecs.open(filename, "w", encoding="utf-8") as f:
                f.write(html)
            #print html
            diffPage2(html, node["@id"])
            #print filename
        pass

    def genPropertyCard(self):
        # property card
        pass

    def run(self):
        self.genIndex()
        #self.genClassCard()
        #self.genPropertyCard()


####################################################
def main():
    #  http://stackoverflow.com/questions/3217673/why-use-argparse-rather-than-optparse
    #  As of 2.7, optparse is deprecated, and will hopefully go away in the future
    parser = argparse.ArgumentParser(description="libcore")
    parser.add_argument('option', help='option')
    parser.add_argument('--version', help='schema.org version')
    parser.add_argument('--site', help='schema.org site')
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
    python scripts/schemaorg2html.py task_one_html --version=3.2 --site=cnschema.org
    python scripts/schemaorg2html.py task_one_html --version=3.2 --site=schema.org
"""
