
import sys
import urllib2
import urllib
import httplib2
import json
import string
import time
from optparse import OptionParser
import traceback

from couchbase import Couchbase
from couchbase.bucket import Bucket
from couchbase.exceptions import CouchbaseError
from couchbase.n1ql import N1QLQuery


# takes an ini template as input, standard out is populated with the server pool
# need a descriptor as a parameter

# need a timeout param

POLL_INTERVAL = 120
SERVER_MANAGER = '172.23.105.177:8081'
TEST_SUITE_DB = '172.23.105.177'


def getNumberOfServers( iniFile):
    f = open(iniFile)
    contents = f.read()
    f.close()
    return contents.count('dynamic')


def main():

    usage = '%prog -s suitefile -v version -o OS'
    parser = OptionParser(usage)
    parser.add_option('-v','--version', dest='version')
    parser.add_option('-r','--run', dest='run')
    parser.add_option('-o','--os', dest='os')
    parser.add_option('-n','--noLaunch', action="store_true", dest='noLaunch', default=False)
    parser.add_option('-c','--component', dest='component', default=None)
    parser.add_option('-p','--poolId', dest='poolId', default='12hour')
    parser.add_option('-t','--test', dest='test', default=False, action='store_true')
    parser.add_option('-s','--subcomponent', dest='subcomponent', default=None)
    parser.add_option('-e','--extraParameters', dest='extraParameters', default=None)


    options, args = parser.parse_args()



    print 'the run is', options.run
    print 'the  version is', options.version
    releaseVersion = float( '.'.join( options.version.split('.')[:2]) )
    print 'release version is', releaseVersion

    print 'nolaunch', options.noLaunch
    print 'os', options.os

    print 'subcomponent is', options.subcomponent




    #f = open(options.suiteFile)
    #data = f.readlines()

    testsToLaunch = []

    #for d in data:
     #  fields = d.split()
     #  testsToLaunch.append( {'descriptor':fields[0],'confFile':fields[1],'iniFile':fields[2],
     #                         'serverCount':int(fields[3]), 'timeLimit':int(fields[4]),
     #                          'parameters':fields[5]})


    cb = Bucket('couchbase://' + TEST_SUITE_DB + '/QE-Test-Suites')

    if options.component is None or options.component == 'None':
        queryString = "select * from `QE-Test-Suites` where '" + options.run + "' in partOf order by component"
    else:
        if options.subcomponent is None or options.subcomponent == 'None':
            splitComponents = options.component.split(',')
            componentString = ''
            for i in range( len(splitComponents) ):
                componentString = componentString + "'" + splitComponents[i] + "'"
                if i < len(splitComponents) - 1:
                    componentString = componentString + ','


            queryString = "select * from `QE-Test-Suites` where \"{0}\" in partOf and component in [{1}] order by component;".format(options.run, componentString)

        else:
            # have a subcomponent, assume only 1 component
            queryString = "select * from `QE-Test-Suites` where \"{0}\" in partOf and component in ['{1}'] and subcomponent ='{2}';".\
                format(options.run, options.component, options.subcomponent)


    print 'the query is', queryString #.format(options.run, componentString)
    query = N1QLQuery(queryString )
    results = cb.n1ql_query( queryString )


    for row in results:
        try:
            data = row['QE-Test-Suites']
            print 'row', data

            # check any os specific
            if 'os' not in data or (data['os'] == options.os) or \
                (data['os'] == 'linux' and options.os in set(['centos','ubuntu']) ):

                # and also check for which release it is implemented in
                if 'implementedIn' not in data or releaseVersion >= float(data['implementedIn']):
                    if 'jenkins' in data:
                        # then this is sort of a special case, launch the old style Jenkins job
                        # not implemented yet
                        print 'Old style Jenkins', data['jenkins']
                    else:
                        if 'initNodes' in data:
                            initNodes = data['initNodes'].lower() == 'true'
                        else:
                            initNodes = True
                        if 'installParameters' in data:
                            installParameters = data['installParameters']
                        else:
                            installParameters = 'None'


                        testsToLaunch.append( {'component':data['component'], 'subcomponent':data['subcomponent'],
                                    'confFile':data['confFile'], 'iniFile':data['config'],
                                    'serverCount':getNumberOfServers(data['config']), 'timeLimit':data['timeOut'],
                                    'parameters':data['parameters'], 'initNodes':initNodes,
                                    'installParameters':installParameters})
                else:
                    print data['component'], data['subcomponent'], ' is not supported in this release'
            else:
                print 'OS does not apply to', data['component'], data['subcomponent']

        except Exception as e:
            print 'exception in querying tests, possible bad record'
            print traceback.format_exc()
            print data

    print 'tests to launch:'
    for i in testsToLaunch: print i['component'], i['subcomponent']
    print '\n\n'



    launchStringBase = 'http://qa.sc.couchbase.com/job/test_suite_executor'
    if options.test:
        launchStringBase = launchStringBase + '-test'

    launchString = launchStringBase + '/buildWithParameters?token=test_dispatcher&' + \
                        'version_number={0}&confFile={1}&descriptor={2}&component={3}&subcomponent={4}&' + \
                         'iniFile={5}&servers={6}&parameters={7}&os={8}&initNodes={9}&installParameters={10}'

    summary = []

    while len(testsToLaunch) > 0:
        try:
            response, content = httplib2.Http(timeout=60).request('http://' + SERVER_MANAGER +
                           '/getavailablecount/{0}?poolId={1}'.format(options.os,options.poolId), 'GET')
            if response.status != 200:
               print time.asctime( time.localtime(time.time()) ), 'invalid server response', content
               time.sleep(POLL_INTERVAL)
            elif int(content) == 0:
                print time.asctime( time.localtime(time.time()) ), 'no VMs'
                time.sleep(POLL_INTERVAL)
            else:
                #see if we can match a test
                serverCount = int(content)
                print time.asctime( time.localtime(time.time()) ), 'there are', serverCount, ' servers available'

                haveTestToLaunch = False
                i = 0
                while not haveTestToLaunch and i < len(testsToLaunch):
                    #print 'i', i, 'ttl sc', testsToLaunch[i]['serverCount']
                    if testsToLaunch[i]['serverCount'] <= serverCount:
                        haveTestToLaunch = True
                    else:
                        i = i + 1

                if haveTestToLaunch:
                    descriptor = urllib.quote(testsToLaunch[i]['component'] + '-' + testsToLaunch[i]['subcomponent'] +
                                    '-' + time.strftime('%b-%d-%X') + '-' + options.version )
                    # get the VMs, they should be there

                    getVMURL = 'http://' + SERVER_MANAGER + \
                            '/getservers/{0}?count={1}&expiresin={2}&os={3}&poolId={4}'. \
                       format(descriptor, testsToLaunch[i]['serverCount'],testsToLaunch[i]['timeLimit'], \
                              options.os, options.poolId)
                    print 'getVMURL', getVMURL

                    response, content = httplib2.Http(timeout=60).request(getVMURL, 'GET')


                    print 'response.status', response.status

                    if response.status == 499:
                        time.sleep(POLL_INTERVAL) # some error checking here at some point
                    else:
                        r2 = json.loads(content)

                        # figure out the parameters, there are test suite specific, and added at dispatch time
                        if options.extraParameters is None or options.extraParameters == 'None':
                            parameters = testsToLaunch[i]['parameters']
                        else:
                            if testsToLaunch[i]['parameters'] == 'None':
                                parameters = options.extraParameters
                            else:
                                parameters = testsToLaunch[i]['parameters'] + ',' + options.extraParameters


                        url = launchString.format(options.version, testsToLaunch[i]['confFile'],
                                    descriptor, testsToLaunch[i]['component'], testsToLaunch[i]['subcomponent'],
                                    testsToLaunch[i]['iniFile'], urllib.quote(json.dumps(r2).replace(' ','')),
                                    urllib.quote( parameters ), options.os, testsToLaunch[i]['initNodes'],
                                    testsToLaunch[i]['installParameters'])

                        #print 'launching', url
                        print time.asctime( time.localtime(time.time()) ), 'launching ', descriptor


                        if options.noLaunch:
                            print 'would launch', url
                            # free the VMs
                            time.sleep(3)
                            response, content = httplib2.Http(timeout=60).\
                                request('http://' + SERVER_MANAGER + '/releaseservers/' + descriptor, 'GET')
                        else:
                            response, content = httplib2.Http(timeout=60).request(url, 'GET')

                        testsToLaunch.pop(i)
                        summary.append( {'test':descriptor, 'time':time.asctime( time.localtime(time.time()) ) } )
                        time.sleep(60)     # don't do too much at once
                else:
                    print 'not enough VMs at this time'
                    time.sleep(POLL_INTERVAL)
            #endif checking for servers

        except Exception as e:
            print 'have an exception'
            print traceback.format_exc()
            time.sleep(POLL_INTERVAL)
    #endwhile



    print '\n\n\ndone, everything is launched'
    for i in summary:
        print i['test'], 'was launched at', i['time']
    return





if __name__ == "__main__":
    main()

