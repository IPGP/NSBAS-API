#!/usr/bin/python

"""
file containing different config dictionnaries (describing hostname, usernames, pwd)
to be used on the API/webservices platform side.
Switch from one to another by commenting/uncommenting definitions
"""
# Example
configdic = {'httpUserName' : 'http authentication user name',\
 'httpPassWord' : 'http authentication password',\
 'wsHostName' : 'Web services platform host name',\
 'clstrHostName' : 'Computing cluster hostname seen from the API platform',\
  'clstrUserName' : 'User name to be used on the cluster',\
 'clstrBaseDir' : 'Path of the ws_cluster directory on the cluster', \
 'clstrDataDir' : 'Path of the ws_cluster director where to hold the data', \
 'apiVersion' : '1.0', \
 'mpiCmd' : 'mpiexec', \
 'ws_dnldSar2Clstr_PN' : '1111', \
 'ws_dnldDem2Clstr_PN' : '2222', \
 'ws_createProcFile_PN' : '3333', \
 'ws_coregListInterf_PN' : '4444', \
 'ws_compInterf_PN' : '5555', \
 'ws_atmoCorr_PN' : '6666', \
 'ws_filtrunwrInterf_PN' : '7777', \
 'ws_geocodInterf_PN' : '8888', \
 'debugMode' : 'true or false, depending'}


