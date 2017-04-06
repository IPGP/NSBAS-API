# NSBAS-API
Sources of the NSBAS WPS API
This API is to give web workflows platforms access to Isterre NSBAS software as a service.
It is based on the Open Geospatial Consortium WPS standard.

INSTALLATION

This stuf is to install on both a computing cluster and an API hosting machine.

On the cluster :
- Copy, in a user home directory, the ws_cluster directory (not only its content)
- To let scripts find libraries and parameters, append the ws_cluster directory to $PYTHONPATH environment variable in /etc/environment : 
  - cd to ws_cluster directory
  - type pwd
  - append the local path to PYTHONPATH environment variable
  Example : PYTHONPATH="/other/path/:/home/myplace/ws_cluster/"

On the API hosting machine (VM) :
- Copy the api_nsbas directory
- Rename the api_nsbas/parametres.template.py as api_nsbas/file parametres.py
- To let web-services find libraries and parameters, append the api_nsbas directory to $PYTHONPATH environment variable in /etc/environment : 
  - cd to api_nsbas directory
  - type pwd
  - append the local path to PYTHONPATH environment variable
  Example : PYTHONPATH="$PYTHONPATH:/home/myplace/api_nsbas/"
  - make sure a .profile exists to apply it to the next shells
- To allow ssh connections to the cluster, write your ssh key into ~/ssh/config 
