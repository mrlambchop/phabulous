import hashlib
import json
import requests
import time
import pickledb
import sys
import functools
import locale

class Phabulous():
    def __init__( self, cert, username, url, offline=False ):

        self.cert = cert
        self.username = username
        self.phab_url = url

        self.offline = offline

        if self.offline  == False:
            self.conduit = self._openConnection()

        self.phidCache = pickledb.load('phid.db', False)

        #first time init?
        if len(self.phidCache.db) == 0:
            print "First time init - making PHID db"
            self.refreshPHIDs()

    def _openConnection( self ):
        # Format parameters for conduit.connect
        token = int(time.time())
        signature = hashlib.sha1(str(token) + self.cert).hexdigest()
        connect_params = {
            'client': 'Phabulous',
            'clientVersion': 1,
            'clientDescription': 'Phabulous by Automatic',
            'user': self.username,
            'host': self.phab_url,
            'authToken': token,
            'authSignature': signature,
        }

        # Make the request to conduit.connect
        req = requests.post('%s/api/conduit.connect' % self.phab_url, data={
            'params': json.dumps(connect_params),
            'output': 'json',
            '__conduit__': True,
        })

        # Parse out the response (error handling ommitted)
        result = json.loads(req.content)['result']
        conduit = {
            'sessionKey': result['sessionKey'],
            'connectionID': result['connectionID'],
        }

        return conduit

    def _doConduit( self, url, queryParams={} ):
        params = {}
        params['__conduit__'] = self.conduit
        params.update( queryParams ) # merge in the query
        req = requests.post('%s/api/%s' % (self.phab_url, url), data={
            'params': json.dumps(params),
            'output': 'json',
        })
        result = json.loads(req.content)['result']
        if result == None:
            print json.loads(req.content)
        return result


    def getProjectPHID( self, projectName ):
        projPHID = None
        for r in self.phidCache.db:
            if 'PROJ' in r:
                if self.phidCache.get(r)['name'] == projectName:
                    projPHID = r
                    break
        return projPHID

    def getProjectName( self, projectPHID ):
        name = "unknown"
        if self.phidCache.get(projectPHID) != None and self.phidCache.get(projectPHID).has_key('name'):
            name = self.phidCache.get(projectPHID)['name']
        return name

    def getUserPHID( self, userName ):
        userPHID = None
        for r in self.phidCache.db:
            if 'USER' in r:
                if self.phidCache.get(r)['userName'] == userName:
                    userPHID = r
                    break
        return userPHID


    def getUserFromPHID( self, phid ):
        userName = "unknown"
        if None != self.phidCache.get(phid) and self.phidCache.get(phid).has_key( 'userName' ):
            userName = self.phidCache.get(phid)['userName']
        return userName


    ###################
    ## Public APIs
    ###################

    def refreshPHIDs( self, subset=None ):
        params = {}

        if self.offline  == False:
            if subset == None:
                users = True
                projects = True
                maniphest = True
            elif subset == "users":
                users = True
            elif subset == "projects":
                projects = True
            elif subset == "maniphest":
                maniphest = True

            #read all the phils
            if users:
                params['limit'] = 500
                results = self._doConduit( 'user.query', params )
                if results != None:
                    for r in results:
                        self.phidCache.set( r['phid'], r )

            #read all the projects?
            if projects:
                params['limit'] = 500
                results = self._doConduit( 'project.query', params )
                if results != None:
                    for r in results['data'].keys():
                        self.phidCache.set( r, results['data'][r] )

            #read all the tasks
            if maniphest:
                params['limit'] = 10000
                results = self._doConduit( 'maniphest.query', params )
                if results != None:
                    for r in results.keys():
                        self.phidCache.set( r, results[r] )

            #save!
            self.phidCache.dump()
        else:
            print "Can't refresh - offline mode"


    def getProjectTasks( self, projectName ):
        tasks = []
        projPHID = self.getProjectPHID(projectName )
        for r in self.phidCache.db:
            if 'TASK' in r:
                if projPHID in self.phidCache.get(r)['projectPHIDs']:
                    tasks.append( self.phidCache.get(r) )
        return tasks


    def getUserTasks( self, userName ):
        tasks = []
        userPHID = self.getUserPHID(userName )
        print userPHID
        for r in self.phidCache.db:
            if 'TASK' in r:
                if (self.phidCache.get(r)['ownerPHID'] != None) and (userPHID in self.phidCache.get(r)['ownerPHID']):
                    tasks.append( self.phidCache.get(r) )
        return tasks


    def getUsers( self ):
        users = []
        for r in self.phidCache.db:
            if 'USER' in r:
                users.append( self.phidCache.get(r)['userName'] )
        return sorted(users, key=functools.cmp_to_key(locale.strcoll))


    def getProjects( self ):
        projects = []
        for r in self.phidCache.db:
            if 'PROJ' in r:
                projects.append( self.phidCache.get(r)['name'] )
        return sorted(projects, key=functools.cmp_to_key(locale.strcoll))



    def createTask( self, title, projectName, userName, description, priority ):
        params = {}

        projectPHID = self.getProjectPHID( projectName )
        ownerPHID = self.getUserPHID( userName )

        params['title'] = title
        params['description'] = description
        params['priority'] = priority

        if projectPHID != None:
            params['projectPHIDs'] = [ projectPHID ]
        else:
            print "no project specified"
            return None

        if ownerPHID != None:
            params['ownerPHID'] = ownerPHID
        else:
            print "no user name specified"
            return None

        result = self._doConduit( 'maniphest.createtask', params )
        if result != None:
            self.phidCache.set( result['phid'], result )
            self.phidCache.dump()
        return result


    def updateTask( self, phid, status=None, comment=None, priority=None, projects=None, ccUsers=None ):
        params = {}

        params['phid'] = phid

        if status != None:
            params['status'] = status

        if comment != None:
            params['comments'] = comment

        if priority != None:
            params['priority'] = priority

        if ccUsers != None:
            userPHID = []
            for i in ccUsers:
                userPHID.append( self.getUserPHID( i ) )
            params['ccPHIDs'] = userPHID

        if projects != None:
            projectPHID = []
            for i in projects:
                projectPHID.append( self.getProjectPHID( i ) )
            params['projectPHIDs'] = projectPHID

        result = self._doConduit( 'maniphest.update', params )
        if result != None:
            self.phidCache.set( phid, result )
            self.phidCache.dump()
        return result
