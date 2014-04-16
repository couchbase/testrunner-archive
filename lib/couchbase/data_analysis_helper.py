from remote.remote_util import RemoteMachineShellConnection
from lib.mc_bin_client import MemcachedClient
# constants used in this file only
DELETED_ITEMS_FAILURE_ANALYSIS_FORMAT="\n1) Failure :: Deleted Items :: Expected {0}, Actual {1}"
DELETED_ITEMS_SUCCESS_ANALYSIS_FORMAT="\n1) Success :: Deleted Items "
ADDED_ITEMS_FAILURE_ANALYSIS_FORMAT="\n2) Failure :: Added Items :: Expected {0}, Actual {1}"
ADDED_ITEMS_SUCCESS_ANALYSIS_FORMAT="\n2) Success :: Added Items "
UPDATED_ITEMS_FAILURE_ANALYSIS_FORMAT="\n3) Failure :: Updated Items :: Expected {0}, Actual {1}"
UPDATED_ITEMS_SUCCESS_ANALYSIS_FORMAT="\n3) Success :: Updated Items"
ADD_ITEMS="addedItems"
DELETED_ITEMS="deletedItems"
UPDATED_ITEMS="updatedItems"
LOGICAL_RESULT="logicalresult"
RESULT="result"

class DataAnalysisResultAnalyzer:
    """ Class containing methods to help analyze results for data analysis """

    def analyze_all_result(self,result,deletedItems = False ,addedItems = False,updatedItems = False):
        """
            Method to Generate & analyze result AND output the logical and analysis result
            This works on a bucket level only since we have already taken a union for all nodes
        """
        output=""
        summary=""
        logic=True
        for bucket in result.keys():
            summary+="\n ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
            output+="\n ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
            output+="\n Analyzing for Bucket {0}".format(bucket)
            summary+="\n Analyzing for Bucket {0}".format(bucket)
            logicalresult=result[bucket][LOGICAL_RESULT]
            analysis=result[bucket][RESULT]
            l, o, s = self.analyze_result(analysis,logicalresult, \
                DELETED_ITEMS,deletedItems,DELETED_ITEMS_SUCCESS_ANALYSIS_FORMAT,DELETED_ITEMS_FAILURE_ANALYSIS_FORMAT)
            output+=o
            summary+=s
            logic=l and logic
            l, o, s = self.analyze_result(analysis,logicalresult, \
                ADD_ITEMS,addedItems,ADDED_ITEMS_SUCCESS_ANALYSIS_FORMAT,ADDED_ITEMS_FAILURE_ANALYSIS_FORMAT)
            output+=o
            summary+=s
            logic=l and logic
            l, o, s = self.analyze_result(analysis,logicalresult, \
                UPDATED_ITEMS,updatedItems,UPDATED_ITEMS_SUCCESS_ANALYSIS_FORMAT,UPDATED_ITEMS_FAILURE_ANALYSIS_FORMAT)
            output+=o
            summary+=s
            logic=l and logic
        return logic,summary,output

    def analyze_per_node_result(self,result,deletedItems = False,addedItems = False,updatedItems = False):
        """
            Method to Generate & analyze result AND output the logical and analysis result
            This works on a bucket, node level only
        """
        output=""
        summary=""
        logic=True
        for bucket in result.keys():
            output+="\n ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
            summary+="\n ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
            output+="\n Analyzing for Bucket {0}".format(bucket)
            summary+="\n Analyzing for Bucket {0}".format(bucket)
            for node in result[bucket].keys():
                output+="\n ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                output+="\n Analyzing for Bucket {0}, node {1}".format(bucket,node)
                summary+="\n Analyzing for Bucket {0}, node {1}".format(bucket,node)
                logicalresult=result[bucket][node][LOGICAL_RESULT]
                analysis=result[bucket][node][RESULT]
                l, o, s = self.analyze_result(analysis,logicalresult, \
                    DELETED_ITEMS,deletedItems,DELETED_ITEMS_SUCCESS_ANALYSIS_FORMAT,DELETED_ITEMS_FAILURE_ANALYSIS_FORMAT)
                output+=o
                summary+=s
                logic=l and logic
                l, o, s = self.analyze_result(analysis,logicalresult, \
                    ADD_ITEMS,addedItems,ADDED_ITEMS_SUCCESS_ANALYSIS_FORMAT,ADDED_ITEMS_FAILURE_ANALYSIS_FORMAT)
                output+=o
                summary+=s
                logic=l and logic
                l, o, s = self.analyze_result(analysis,logicalresult, \
                    UPDATED_ITEMS,updatedItems,UPDATED_ITEMS_SUCCESS_ANALYSIS_FORMAT,UPDATED_ITEMS_FAILURE_ANALYSIS_FORMAT)
                output+=o
                summary+=s
                logic=l and logic
        return logic,summary,output

    def analyze_result(self,analysis,logicalresult,type,actual,successoutputformat,failureoutputformat):
        """ Helper for analyzing result """
        output=""
        summary=""
        logic=False
        lresult=logicalresult[type]
        result=analysis[type]
        if lresult == actual:
                logic=True
                summary+=successoutputformat
                output+=successoutputformat
        else:
            summary+=failureoutputformat.format(actual,lresult)
            output+=failureoutputformat.format(actual,lresult)
        if result != None and type == UPDATED_ITEMS:
            for key in result.keys():
                output+="\n {0}".format(result)
        else:
            for values in result:
                output+="\n {0}".format(values)
        return logic,output,summary

class DataAnalyzer(object):
    """ Class which defines logic for data comparison """

    def compare_all_dataset(self,headerInfo,sourceMap,targetMap,comparisonMap=None):
        """
            Method to compare data sets and given as input of two bucket maps

            Paramters:

            headerInfo: field names of values in input (comma seperated list)
            sourceMap: input 1 used for comparison
            targetMap: input 2 used for comparison
            The input is present in the format {bucket: {vbucket:[{key:value}]}}
            comparisonMap: logical comparison definitions for key, values

            Returns:

            for all buckets get result set as follows
            deletedItems = A-B, addedItems = B-A, updatedItems = Present in A and B, but have different values
            A  =  bucketmap1, B  =  bucketmap2
            The output has two Parts
            1) Logical: deletedItems = (True/False),addedItems = (True/False),updatedItems = (True/False)
                True indicates items present
                False indicates items not present
            2) Result Set: deletedItems,addedItems, updatedItems
               This output is for bucket -> vbucket level
        """
        Result = {}
        for bucket in sourceMap.keys():
            info1 = sourceMap[bucket]
            info2 = targetMap[bucket]
            Result[bucket] = self.compare_data_maps(info1,info2,headerInfo,"key")
        return Result

    def compare_per_node_dataset(self,headerInfo,sourceMap,targetMap,comparisonMap=None):
        """
            Method to compare data sets and given as input of two compare_maps

            Paramters:

            headerInfo: field names of values in input (comma seperated list)
            sourceMap: input 1 used for comparison
            targetMap: input 2 used for comparison
            The input is present in the format {bucket: {vbucket:[{key:value}]}}
            comparisonMap: logical comparison definitions for key, values

            Returns:

            For all buckets get result set as follows:
            deletedItems = A-B, addedItems = B-A, updatedItems = Present in A and B, but have different values
            A  =  bucketmap1, B  =  bucketmap2

            The output has two Parts
            1) Logical: deletedItems = (True/False),addedItems = (True/False),updatedItems = (True/False)
                True indicates items present
                False indicates items not present
            2) Result Set: deletedItems,addedItems, updatedItems
                This output is for bucket -> node -> vbucket level
        """
        Result = {}
        for bucket in sourceMap.keys():
            Result[bucket] = {}
        for bucket in sourceMap.keys():
            for node in sourceMap[bucket].keys():
                info1 = sourceMap[bucket][node]
                info2 = targetMap[bucket][node]
                Result[bucket][node] = self.compare_data_maps(info1,info2,headerInfo,"key")
        return Result

    def compare_stats_dataset(self,bucketmap1,bucketmap2,mainKey,comparisonMap=None):
        """
            Method to compare data sets and given as input of two bucket maps

            Paramters:

            bucketmap1: input 1 used for comparison
            bucketmap2: input 2 used for comparison
            mainKey: key name used in output
            The input is present in the format {bucket: {vbucket:[{key:value}]}}
            comparisonMap: logical comparison definitions for key, values

            Returns:

            for all buckets get result set as follows
            deletedItems = A-B, addedItems = B-A, updatedItems = Present in A and B, but have different values
            A  =  bucketmap1, B  =  bucketmap2
            The output has two Parts
            1) Logical: deletedItems = (True/False),addedItems = (True/False),updatedItems = (True/False)
                True indicates items present
                False indicates items not present
            2) Result Set: deletedItems,addedItems, updatedItems
               This output is for bucket -> vbucket level
        """
        Result = {}
        for bucket in bucketmap1.keys():
            info1 = bucketmap1[bucket]
            info2 = bucketmap2[bucket]
            Result[bucket] = self.compare_maps(info1,info2,mainKey)
        return Result

    def compare_per_node_stats_dataset(self,bucketmap1,bucketmap2,mainKey="key",comparisonMap=None):
        """
            Method to compare data sets and given as input of two compare_maps

            Paramters:

            bucketmap1: input 1 used for comparison
            bucketmap2: input 2 used for comparison
            mainKey: key name used in output
            the input is present in the format {bucket: {node:{vbucket:[{key:value}]}}
            comparisonMap: logical comparison definitions for key, values

            Returns:

            For all buckets get result set as follows:
            deletedItems = A-B, addedItems = B-A, updatedItems = Present in A and B, but have different values
            A  =  bucketmap1, B  =  bucketmap2

            The output has two Parts
            1) Logical: deletedItems = (True/False),addedItems = (True/False),updatedItems = (True/False)
                True indicates items present
                False indicates items not present
            2) Result Set: deletedItems,addedItems, updatedItems
                This output is for bucket -> node -> vbucket level
        """
        Result = {}
        for bucket in bucketmap1.keys():
            map1 = bucketmap1[bucket]
            map2 = bucketmap2[bucket]
            NodeResult = {}
            if map1 !=  None:
                for node in map1.keys():
                    info1 = map1[node]
                    info2 = map2[node]
                    NodeResult[node] = self.compare_maps(info1,info2,mainKey)
            Result[bucket] = NodeResult
        return Result

    def compare_maps(self,info1,info2,mainKey="key",comparisonMap=None):
        """ Method to help comparison of stats datasets """
        updatedItemsMap = {}
        deletedItemsList = list(set(info1.keys()) - set(info2.keys()))
        addedItemsList = list(set(info2.keys()) - set(info1.keys()))
        for key in set(info1.keys()) & set(info2.keys()):
            data1 = info1[key]
            data2 = info2[key]
            isNotEqual = False
            reason = {}
            if len(data1.keys()) == len(data2.keys()):
                for vkey in data1.keys():
                    if comparisonMap != None and vkey in comparisonMap.keys():
                        self.compare_values(data1[vkey],data2[vkey],key,reason,comparisonMap[vkey])
                    elif data1[vkey] !=  data2[vkey]:
                            reason[vkey] = "Expected {0} :: Actual {1}".format(data1[vkey],data2[vkey])
            else:
                reason["number of key mismatch"] = "Key Mismatch :: Expected keys {0} \n Actual keys {1}".format(data1.keys(),data2.keys())
            if len(reason) > 0:
                updatedItemsMap[key] = reason
        comparisonResult = {DELETED_ITEMS:deletedItemsList,ADD_ITEMS:addedItemsList,UPDATED_ITEMS:updatedItemsMap}
        logicalResult = {DELETED_ITEMS:(len(deletedItemsList) > 0),ADD_ITEMS:(len(addedItemsList) > 0),UPDATED_ITEMS:(len(updatedItemsMap) > 0)}
        return {LOGICAL_RESULT:logicalResult,RESULT:comparisonResult}

    def compare_data_maps(self,info1,info2,headerInfo,mainKey,comparisonMap=None):
        """ Method to help comparison of datasets """
        updatedItemsMap = {}
        deletedItemsList = list(set(info1.keys()) - set(info2.keys()))
        addedItemsList = list(set(info2.keys()) - set(info1.keys()))
        for key in set(info1.keys()) & set(info2.keys()):
            data1 = info1[key].split(",")
            data2 = info2[key].split(",")
            reason = {}
            if len(data1) == len(data2):
                for i in range(len(data1)):
                    if comparisonMap != None and headerInfo[i] in comparisonMap.keys():
                        self.compare_values(data1[i],data2[i],headerInfo[i],reason,comparisonMap[headerInfo[i]])
                    elif data1[i] !=  data2[i]:
                        reason[headerInfo[i]] = "Expected {0} :: Actual {1}".format(data1[i],data2[i])
            else:
                reason["number of value mismatch"] = "Number of values mismatch :: Expected values {0} \n Actual values {1}".format(data1,data2)
            if len(reason) > 0:
                updatedItemsMap[key] = reason
        comparisonResult = {DELETED_ITEMS:deletedItemsList,ADD_ITEMS:addedItemsList,UPDATED_ITEMS:updatedItemsMap}
        logicalResult = {DELETED_ITEMS:(len(deletedItemsList) > 0),ADD_ITEMS:(len(addedItemsList) > 0),UPDATED_ITEMS:(len(updatedItemsMap) > 0)}
        return {LOGICAL_RESULT:logicalResult,RESULT:comparisonResult}

    def compare_values(self,val1,val2,key,reason,logic):
        """ Helper method to compare values """
        isFail=True
        type=logic["type"]
        operation=logic["operation"]
        val1=self.convert_value(val1,type)
        val2=self.convert_value(val2,type)
        if operation == "filter":
            return
        elif operation == ">=":
            if val1 >= val2:
                isFail=False
        elif operation == "<=":
            if val1 <= val2:
                isFail=False
        elif operation == ">":
            if val1 > val2:
                isFail=False
        elif operation == "<":
            if val1 < val2:
                isFail=False
        elif operation == "==":
            if val1 == val2:
                isFail=False
        elif operation == "!=":
            if val1 != val2:
                isFail=False
        if isFail:
            reason[key] = "Condition Fail:: {0} {1} {2}".format(data1[i],logic,data2[i])

    def convert_value(val,type):
        """ Helper method to convert to a typical value """
        if val == None:
            return ""
        if type == "int":
            return int(val)
        elif type == "long":
            return long(val)
        elif type == "float":
            return float(val)

class DataCollector(object):
    """ Helper Class to collect stats and data from clusters """

    def collect_data(self,servers,buckets,userId="Administrator",password="password",data_path = None,perNode = True):
        """
            Method to extract all data information from memory or disk using cbtransfer
            The output is organized like { bucket :{ node { document-key : list of values }}}

            Paramters:

            servers: server information
            bucket: bucket information
            userId: user id of cb server
            password: password of cb server
            data_path: data path on servers, if given we will do cbtransfer on files
            perNode: if set we organize data for each bucket per node basis else we take a union

            Returns:

            If perNode flag is set we return data as follows
              {bucket {node { key: value list}}}
            else
              {bucket {key: value list}}
        """
        completeMap = {}
        for bucket in buckets:
            completeMap[bucket.name] = {}
        headerInfo = None
        for server in servers:
            remote_client = RemoteMachineShellConnection(server)
            headerInfo,bucketMap = remote_client.get_data_map_using_cbtransfer(buckets,data_path=data_path,userId=userId,password=password)
            remote_client.disconnect()
            for bucket in bucketMap.keys():
                newMap = self.translateDataFromCSVToMap(0,bucketMap[bucket])
                if perNode:
                    completeMap[bucket][server.ip] = newMap
                else:
                    completeMap[bucket].update(newMap)
        return headerInfo,completeMap

    def collect_vbucket_stats(self,buckets,servers,collect_vbucket = True,collect_vbucket_seqno = True,collect_vbucket_details = True,perNode = True):
        """
            Method to extract the vbuckets stats given by cbstats tool

            Paramters:

            buckets: bucket information
            servers: server information
            collect_vbucket: take vbucket type stats
            collect_vbucket_seqno: take vbucket-seqno type stats
            collect_vbucket_details: take vbucket-details type stats
            perNode: if True collects data per node else takes a union across nodes

            Returns:

            The output can be in two formats

            if we are doing per node data collection
            Vbucket Information :: {bucket { node : [vbucket_seqno {key:value} U vbucket_details {key:value} U vbucket {key:value}]}}

            if we are not doing per node data collection
            Vbucket Information :: {bucket : [vbucket_seqno {key:value} U vbucket_details {key:value} U vbucket {key:value}]}
        """
        bucketMap = {}
        vbucket = []
        vbucket_seqno = []
        vbucket_details = []
        for bucket in buckets:
            bucketMap[bucket.name] = {}
        for bucket in buckets:
            dataMap = {}
            for server in servers:
                map_data = {}
                client = MemcachedClient(host=server.ip, port=11210)
                if collect_vbucket:
                    vbucket=client.stats('vbucket')
                    self.createMapVucket(vbucket,map_data)
                if collect_vbucket_seqno:
                    vbucket_seqno=client.stats('vbucket-seqno')
                    self.createMapVucket(vbucket_seqno,map_data)
                if collect_vbucket_details:
                    vbucket_details=client.stats('vbucket-details')
                    self.createMapVucket(vbucket_details,map_data)
                if perNode:
                    dataMap[server.ip] = map_data
                else:
                    dataMap.update(map_data)
            bucketMap[bucket.name] = dataMap
        return bucketMap

    def collect_failovers_stats(self,buckets,servers,perNode = True):
        """
            Method to extract the failovers stats given by cbstats tool

            Paramters:

            buckets: bucket informaiton
            servers: server information
            perNode: if set collect per node information else all

            Returns:

            Failover stats as follows:
            if not collecting per node :: {bucket : [{key:value}]}
            if collecting per node :: {bucket : {node:[{key:value}]}}
        """
        bucketMap = {}
        for bucket in buckets:
            bucketMap[bucket.name] = {}
        for bucket in buckets:
            dataMap = {}
            for server in servers:
                client = MemcachedClient(host=server.ip, port=11210)
                stats = client.stats('failovers')
                map_data = {}
                for o in stats.keys():
                    tokens = o.split(":")
                    vb = tokens[1]
                    key = tokens[2]
                    value = stats[o].split()
                    if len(tokens)  ==  4:
                        vb = tokens[1]
                        key = tokens[3]
                    if vb in map_data.keys():
                        map_data[vb][key] = value
                    else:
                        m = {}
                        m[key] = value
                        map_data[vb] = m
                if perNode:
                    dataMap[server.ip] = map_data
                else:
                    dataMap.update(map_data)
            bucketMap[bucket.name] = dataMap
            return bucketMap

    def createMapVucket(self,details,map_data):
        """ Helper method for vbucket information data collection """
        for o in details.keys():
            tokens = o.split(":")
            if len(tokens) ==  2:
                vb = tokens[0]
                key = tokens[1]
                value = details[o].strip()
                if vb in map_data.keys():
                    map_data[vb][key] = value
                else:
                    m = {}
                    m[key] = value
                    map_data[vb] = m
            elif len(tokens)  ==  1:
                vb = tokens[0]
                value = details[o].strip()
                if "state" in map_data.keys():
                    map_data[vb]["state"] = value
                else:
                    m = {}
                    m["state"] = value
                    map_data[vb] = m

    def translateDataFromCSVToMap(self,index,dataInCSV):
        """ Helper method to translate cbtransfer per line data into key: value pairs"""
        bucketMap = {}
        for value in dataInCSV:
            values = value.split(",")
            bucketMap[values[index]] = value
        return bucketMap