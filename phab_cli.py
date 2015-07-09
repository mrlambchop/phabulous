#!/usr/bin/env python

from __future__ import unicode_literals
from prompt_toolkit.shortcuts import get_input
from prompt_toolkit.key_binding.manager import KeyBindingManager
from prompt_toolkit.keys import Keys
from termcolor import colored
import datetime
import pickledb
import argparse

import phabulous

################################################
# Input helper funcs
################################################

def getText( prompt ):
    text = get_input(prompt + '> ', key_bindings_registry=key_bindings_manager.registry)
    if len(text) == 0:
        text = None
    return text

def validText( text ):
    if None != text and len(text):
        return True
    else:
        return False

################################################
# Horrible init code
################################################

print "Phabulous: v0.1"

#command line args
parser = argparse.ArgumentParser(description='Phabulous Command Line Interface')
parser.add_argument('-r', '--reset', help='reset the phab credentials', action='store_true')
args = parser.parse_args()

# We start with a `KeyBindingManager` instance, because this will already
# nicely load all the default key bindings.
key_bindings_manager = KeyBindingManager()

#Prompt settings
promptSettings = pickledb.load('prompt.db', False)

#reset params?
if None != args.reset and args.reset:
    promptSettings.rem("username")
    promptSettings.rem("url")
    promptSettings.rem("cert")

#fill in the basic credentials (if needed)
if None == promptSettings.get("username"):
    userName = getText("enter phab username")
    if( validText( userName ) ):
        promptSettings.set( "username", userName )

if None == promptSettings.get("url"):
    print "Please enter the phabricator URL (something like https://phabricator.automatic.co or https://secure.phabricator.com)"
    url = getText("phab url")
    if( validText( url ) ):
        promptSettings.set( "url", url )

if None == promptSettings.get("cert"):
    print "Please paste in the phabrictor cert (from here: ", promptSettings.get( "url" ) + "/settings/panel/conduit/"
    cert = getText("enter phab cert")
    if( validText( cert ) ):
        promptSettings.set( "cert", cert )

######
#defaults for "friends" and "projects"
######
if None == promptSettings.get("projects"):
    promptSettings.set( "projects" , [ "Phabulous" ] )

if None == promptSettings.get("taskFilter"):
    promptSettings.set( "taskFilter", "P1,P2,P3"  )


if None == promptSettings.get("friends"):
    promptSettings.set( "friends", [ promptSettings.get("username") ] )

if None == promptSettings.get("group"):
    promptSettings.set( "group", [ ["Phab+Nick", "Phabulous", promptSettings.get("username") ] ] )

#init phabulous!
phab = phabulous.Phabulous( promptSettings.get("cert"), promptSettings.get("username"), promptSettings.get("url") )

################################################
# Horrible init code
################################################

def getPrettyColumnFormat(mylist, cols):

    listToDisplay = []

    def cap(s, l):
        return s if len(s)<=l else s[0:l-3]+'...'

    for i,item in enumerate(mylist):
        listToDisplay.append( str(i+1) + ": " + cap(item, 25) )

    maxwidth = max(map(lambda x: len(x), listToDisplay))
    justifyList = map(lambda x: x.ljust(maxwidth), listToDisplay)
    lines = (' '.join(justifyList[i:i+cols])
             for i in xrange(0,len(justifyList),cols))
    print "\n".join(lines)

################################################
# Functions used to add data to a list
################################################

def getProject( prompt ):
    return getChoice( prompt, phab.getProjects() )


def getUser( prompt ):
    return getChoice( prompt, phab.getUsers() )

def getGroup( prompt ):
    groupName = getText("group name")
    if None != groupName and len(groupName):
        proj = getChoice( prompt, phab.getProjects()  )
        if validText(proj):
            user = getChoice( prompt, phab.getUsers() )
            if None != user and len(user):
                return [ groupName, proj, user ]
    return None

def getChoice( prompt, choices, responses=None ):
    while True:
        #print choices
        getPrettyColumnFormat( choices , 3 )
        # for i in range( 0, len(choices)):
        #     print('  ' + str(i+1) + ':  ' + choices[i])

        text = get_input(prompt + '> ', key_bindings_registry=key_bindings_manager.registry)

        if len(text) and text.isdigit():
            i = int( text )
            if i >= 1 and i <= (len(choices) + 1):
                if responses != None:
                    return responses[i-1]
                else:
                    return choices[i-1]
            else:
                print("invalid option!")
        elif len(text) == 0:
            return None


def getPhabOption( prompt, dbKey, getFunc ):
    while True:
        store = False

        values = promptSettings.get( dbKey )

        #this is a little hacky. if its a list,
        printValues = []

        if len(values):
            if type(values[0]) == list:
                for l in values:
                    printValues.append( l[0] )
            else:
                printValues = values

        for i in range( 0, len(printValues)):
            print('  ' + str(i+1) + ':  ' + printValues[i])

        print('  a: add ' + prompt + '    r: remove ' + prompt  )
        text = get_input('select ' + prompt + '> ', key_bindings_registry=key_bindings_manager.registry)

        if len(text) and text.isdigit():
            i = int( text )
            if i >= 1 and i <= (len(values) + 1):
                return values[i-1]
            else:
                print("invalid option!")
        elif len(text) == 0:
            return None
        elif text == "a" or text == "add":
            newValue = getFunc( prompt )
            if None != newValue:
                values.append( newValue )
                store = True
        elif text == "r" or text == "remove":
            oldValue = getText( prompt + " to remove" )
            if None != oldValue and len(oldValue) and oldValue.isdigit():
                i = int( oldValue )
                if i >= 1 and i <= (len(values) + 1):
                    values.remove( values[i-1] )
                    store = True

        if store:
            promptSettings.set( dbKey, values )
            promptSettings.dump()


def getNewStatus():
    choices = [ "resolved", "reopen", "invalid", "won\'tfix" ]
    return getChoice( "select status", choices )


def getNewPriority():
    choices = [ "P1", "P2", "P3" ]
    responses = [ 75, 50, 25 ]
    return getChoice( "select priority", choices, responses )




def taskView( task ):
    # Read input.
    while True:
        newTask = None

        userName = phab.getUserFromPHID( task['authorPHID'] )
        assignedUser = phab.getUserFromPHID( task['ownerPHID'] )

        projectNames = []
        for n in task['projectPHIDs']:
            projectNames.append( phab.getProjectName( n ) )

        #make project names readable
        projectNamesStr = ""
        for i, p in enumerate(projectNames):
            if i != 0:
                projectNamesStr += ", "
            projectNamesStr += p

        ccUsers = []
        for n in task['ccPHIDs']:
            ccUsers.append( phab.getUserFromPHID( n ) )

        #make CC names readable
        ccNamesStr = ""
        for i, p in enumerate(ccUsers):
            if i != 0:
                ccNamesStr += ", "
            ccNamesStr += p

        print('  ' + task['objectName'])
        print('     Title:       ' + task['title'])
        print('     Status  :    ' + colored(task['status'], 'red') )
        print('     Priority:    ' + colored(task['priority'], 'green') )
        print('     User:        ' + colored(userName, 'blue') )
        print('     Assign:      ' + colored(assignedUser, 'blue') )
        print('     CC:          ' + colored(ccNamesStr, 'blue') )
        print('     Projects:    ' + colored(projectNamesStr, 'cyan') )
        utc = float(task['dateCreated'].encode("utf8","ignore"))
        print('     Created:     ' + datetime.datetime.utcfromtimestamp( utc ).strftime('%A %d. %B %Y') )
        print('     PHID:        ' + task['phid'])
        desc = task['description']
        descLines = desc.split('\n')
        descPretty = ""
        extension = ""
        i = 0
        for l in descLines:
            if len(l):
                if len(l) > 160:
                    descPretty += extension + l[:160] + '\n'
                    descPretty += extension + l[160:] + '\n'
                else:
                    descPretty += extension + l + '\n'
            if i >= 5:
                break
            extension = '                  '

        print('     Description:' ),
        print( descPretty )
        print('  1: status    2: comment   3: priority  4. add project   5. remove project   6. cc user')
        text = get_input('select task> ', key_bindings_registry=key_bindings_manager.registry)

        if len(text) == 0:
            break

        if text == "1" or text == "s" or text == "status":
            newStatus = getNewStatus()

            if newStatus != None:
                newTask = phab.updateTask( task['phid'], status=newStatus )

        if text == "2" or text == "comment" or text == "c":
            newComment = getText( 'comment' )

            if len(newComment):
                newTask = phab.updateTask( task['phid'], comment=newComment )

        if text == "3" or text == "p" or text == "priority":
            newPriority = getNewPriority()

            if newPriority != None:
                newTask = phab.updateTask( task['phid'], priority=newPriority )

        if text == "4" or text == "a" or text == "add":
            newProject = getPhabOption( "project", "projects", getProject )

            if newProject != None:
                projectNames.append( newProject )
                newTask = phab.updateTask( task['phid'], projects=projectNames )

        if text == "5" or text == "r" or text == "remove":
            removeProject = getPhabOption( "project", "projects", getProject )

            if removeProject != None:
                projectNames.remove( removeProject )
                newTask = phab.updateTask( task['phid'], projects=projectNames )

        if text == "6" or text == "u" or text == "user":
            ccUser = getPhabOption( "add user", "friends", getUser )

            if ccUser != None:
                ccUsers.append( ccUser )
                newTask = phab.updateTask( task['phid'], ccUsers=ccUsers )

        #if the task updated, refresh it now
        if newTask != None:
            task = newTask



def createTaskView( projectName=None, userName=None ):
    if projectName == None:
        projectName = getPhabOption( "project", "projects", getProject )
        if None == projectName:
            return

    if userName == None:
        userName = getPhabOption( "add user", "friends", getUser )
        if None == userName:
            return

    title = getText("title")
    if None == title:
        return

    description = getText("Description")
    priority = getNewPriority()
    if None == priority:
        return

    #ok, lets create a task!
    phab.createTask( projectName=projectName, userName=userName, title=title, description=description, priority=priority )



def taskListView( projectName=None, userName=None, optionalTaskListName=None ):
    # Read input.
    while True:
        if projectName == None and userName == None:
            print "invalid function call!"
            return

        tasks = []

        if projectName != None and userName != None:
            if None == optionalTaskListName:
                print "Group: ", projectName, "/", userName
            else:
                print "Group: ", optionalTaskListName

            #get both lists and filter them
            projTasks = phab.getProjectTasks(projectName)
            userPHID = phab.getUserPHID( userName )

            for t in projTasks:
                if t['ownerPHID'] == userPHID:
                    tasks.append( t )
        else:
            if projectName != None:
                print "Project: ", projectName
                tasks = phab.getProjectTasks(projectName)

            if userName != None:
                print "User: ", userName
                tasks = phab.getUserTasks(userName)

        displayedTasks = []
        global promptSettings
        priorityFilters = promptSettings.get("taskFilter").split(',')

        #create a dict of the priorities
        priorities = [ "P1", "P2", "P3" ]
        taskPriorities = {}

        for k in tasks:
            if k['statusName'] == 'Open' and k['priority'] in priorityFilters:
                if taskPriorities.has_key( k['priority'] ):
                    taskPriorities[ k['priority'] ].append( k )
                else:
                    taskPriorities[ k['priority'] ] = [ k ]

        #print the tasks in priority grouping
        for priority in priorities:
            if taskPriorities.has_key( priority ):
                for task in taskPriorities[priority]:
                    ownerUserName = phab.getUserFromPHID( task['ownerPHID'] )
                    authorUserName = phab.getUserFromPHID( task['authorPHID'] )
                    print len(displayedTasks) + 1, "  ", task['objectName'], "\t", task['title'], colored(task['priority'], 'green'), colored(ownerUserName, 'blue'), '/', colored(authorUserName, 'blue')
                    displayedTasks.append( task )

        print('     f: filter (%s)   c: create    q: quit' % (promptSettings.get("taskFilter")) )
        text = get_input('select task> ', key_bindings_registry=key_bindings_manager.registry)

        if text == "q" or text == "quit":
            break

        if text == "c" or text == "create":
            createTaskView( projectName=projectName, userName=userName )

        if text == "f" or text == "filter":
            newFilter = getText( 'filter' )
            if None != newFilter:
                promptSettings.set("taskFilter", newFilter )
                promptSettings.dump()

        if len(text) and text.isdigit():
            i = int( text )
            if i >= 1 and i <= (len(displayedTasks) + 1):
                taskView( displayedTasks[i-1] )
            else:
                print("invalid option!")


################################################
# Views
################################################

def projectView():
    while True:
        project = getPhabOption( "project", "projects", getProject )

        if not validText( project ):
            break

        if project != None:
            taskListView( projectName=project )


def groupView():
    while True:
        group = getPhabOption( "group", "group", getGroup )

        if not validText( group ):
            break

        if group != None:
            taskListView( projectName=group[1], userName=group[2], optionalTaskListName=group[0] )


def userView():
    while True:
        username = getPhabOption( "user", "friends", getUser )

        if not validText( username ):
            break

        if username != None:
            taskListView(userName=username)


def mainView():
    # @key_bindings_manager.registry.add_binding('u',)
    # def _(event):
    #     event.cli.current_buffer.insert_text('z')

    # menu = Menu()
    # menu.add( "project view", projectView )
    # menu.add( "user view", userView )
    # menu.add( "group view", groupView )
    # menu.add( "refresh", None )
    # menu.run()

    # Read input.
    while True:
        print('*** Commands ***')
        print('   1: projects    2: users     3: groups')
        print('   4: refresh     5: quit')
        text = get_input('What now> ', key_bindings_registry=key_bindings_manager.registry)

        if text == "project" or text == "p" or text == "1":
            projectView()

        if text == "user" or text == "u" or text == "2":
            userView()

        if text == "group" or text == "g" or text == "3":
            groupView()

        if text == "refresh" or text == "r" or text == "4":
            print "Refreshing all PHIDs.."
            phab.refreshPHIDs()

        if text == "quit" or text == "q" or text == "5":
            break

    promptSettings.dump()

if __name__ == '__main__':
    mainView()
