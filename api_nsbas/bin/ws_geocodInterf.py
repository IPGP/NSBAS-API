#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Webservice ws_atmoCorr.py
#
"""Fonctions : 
- Géocoder les résultats, passer de la géométrie radar à la géométrie terrain à la demande de l'utilisateur.
- Générer une version jpeg de chaque interférogramme du processus courant en plein résolution et une vignette jpeg de taille max 300x300 pixels.

Ce code est inspiré de https://blog.miguelgrinberg.com/post/designing-a-restful-api-with-python-and-flask
Pour en savoir plus : http://flask.pocoo.org/docs/0.12/quickstart/

Utilisation des arguments : 
request.json est un hypercube associatif qui reprend la structure du json envoye.
request.values est un tableau associatif qui reprend les variables transmises en mode key-value pair (?toto=156&mode=sync)

Note PHA 20170418 : Code dérivé du modèle synchrone ws_createProcFile en vue du codage final
"""

import os
import logging
from flask import Flask, jsonify, abort, request, make_response, url_for
from flask_httpauth import HTTPBasicAuth
import paramiko

# Le module (bibliotheque) specifique des webservices NSBAS
# Doit etre dans le PYTHON PATH
import lib_ws.ws_nsbas as lws_nsbas
import lib_ws.ws_connect as lws_connect

# Incluons un fichier de parametres communs a tous les webservices
import parametres
config = parametres.configdic
remote_prefix = config["clstrBaseDir"]
remote_data_prefix = config["clstrDataDir"]
ssh_config_file = os.environ["HOME"] + "/" + ".ssh/config"

# Preparons la connexion ssh via Paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Autorisons les requetes provenant de domaines distincts du domaine qui heberge le webservice
# A restreindre dès que l'hébergement du frontal sera connu
from flask_cors import CORS, cross_origin
app = Flask(__name__, static_url_path = "")
cors = CORS(app, resources={r"*": {"origins": "null", "supports_credentials": True}})
logging.getLogger('flask_cors').lev = logging.DEBUG

# Parametres specifiques a ce webservice
wsName = 'ws_geocodInterf'
wsVersion = config['apiVersion']
wsPortNumber = int(config[wsName + '_PN'])

#app = Flask(__name__, static_url_path = "")
auth = HTTPBasicAuth()

@auth.get_password
def get_password(username):
    if username == config['httpUserName']:
        return config['httpPassWord']
    return None

@auth.error_handler
def unauthorized():
    return make_response(jsonify( { 'error': 'Unauthorized access' } ), 403)
    # return 403 instead of 401 to prevent browsers from displaying the default auth dialog

@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify( { 'error': 'Bad request' } ), 400)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Not found' } ), 404)

@app.route('/v' + wsVersion + '/services', methods = ['GET'])
@auth.login_required
def get_capabilities():
    return jsonify( { "id": "03", "label": "ForM@Ter - NSBAS API", "type": "WPS", "url": ""+ url_for("get_capabilities", _external=True) +"", "contact": "contact@poleterresolide.fr" })


@app.route('/v' + wsVersion + '/services/'+wsName, methods = ['GET'])
@auth.login_required
def describe_process():
    return jsonify( {
     "id": ""+wsName+"",
     "label": "ForM@Ter/Etalab ws_geocodInterf webservice",
     "description": "Geocodes interferograms, converts them to jpeg and generates thumbnails.",
     "inputs":  [
          {"processToken" : "<token>",
                           "subSwath" : "<subswathnb>"}
                         ],
              "outputs": [
                          {"job_id" : "<jobId>",
                           "processToken" : "<token>",
                           "resNames" :[
                                       {"resName" : "<resName1>" , "resURI" : "<resURI1>"},
                                       {"resName" : "<resName2>" , "resURI" : "<resURI2>"},
                                        {"<etc...>" : "<etc...>" , "<etc...>" : "<etc...>"}
                                       ]
                          }
                ]
               }
)

@app.route('/v' + wsVersion + '/services/'+wsName+'/<int:job_id>/<process_token>', methods = ['GET'])
@auth.login_required
def get_status(job_id, process_token):
    """ returns the status of the given process id and process token
    :param job_id: the job id
    :type job_id: int?
    :param process_token: the token being queried
    :type process_token: str (uuid)
    :return: the status of the task
    :type: str (containing a json)
    """
    ssh_client = None
    try:
        ssh_client = lws_connect.connect_with_sshconfig(config, ssh_config_file)
    except Exception as excpt:
        logging.critical("unable to log on %s, ABORTING", config["clstrHostName"])
        raise excpt
    if ssh_client is None:
        logging.critical("unable to log on %s, ABORTING", config["clstrHostName"])
        raise ValueError("unable to log on %s, ABORTING", config["clstrHostName"])
    logging.info("get_status for token %s", process_token)
    status_json = lws_connect.get_job_status(ssh_client, process_token, job_id)
    ssh_client.close()
    return jsonify(status_json)

@app.route('/v' + wsVersion + '/services/'+wsName, methods = ['POST'])
@auth.login_required
def execute():
    """ L'execute synchrone renvoit le resultat et la reponse http 200 : OK
     L'execute asynchrone doit renvoyer la reponse du GetStatus et la reponse http 201 ou celle du GetResult et la reponse http 200, selon

     L'execute du webservice ws_coregListInterf doit
    """
    if request.values['mode'] == "async" :
        # TODO : estimer dynamiquement walltime
        process_token = request.json[0]['processToken']
        subswath = request.json[1]['subSwath']
        logging.critical("getting: token %s swath %s", str(process_token), str(subswath))
        token_dir = remote_data_prefix + '/' + process_token
        working_dir = token_dir + '/iw' + subswath
        log_dir = token_dir + '/LOG'
        process_ressources = {"nodes" : 1, "cores" : 4, "walltime" : "00:30:00",
                "workdir": working_dir, "logdir" : log_dir}
        ret = "Error"
        error = "OK"
        job_id = -1
        try:
            ssh_client = lws_connect.connect_with_sshconfig(config, ssh_config_file)
        except Exception as excpt:
            logging.critical("unable to log on %s, ABORTING", config["clstrHostName"])
            raise excpt
        if ssh_client is None:
            logging.critical("unable to log on %s, ABORTING", config["clstrHostName"])
            raise ValueError("unable to log on %s, ABORTING", config["clstrHostName"])
        logging.info("connection OK")
#        command = " ".join(['nsb_make_geomaptrans.py', 'nsbas.proc', '4'])
        publishDir = "".join("/", config["apiVersion"],"/services/ws_dnldResult/" , process_token)
        command = " ".join(['wsc_geocod-publishInter.sh', config["thumbnailsWidth"] , publishDir])
        
        try:
            logging.critical("launching command: %s", command)
            job_id = lws_connect.run_on_cluster_node(ssh_client, command, str(process_token),
                                                  process_ressources)
            logging.critical("returned from submission %s", job_id)
        except Exception as excpt:
            error = error + "fail to run command on server: {}".format(excpt)
            logging.error(error)

        # Des lors qu'il est lance, le webservice donne son jeton via son GetStatus, sans attendre d'avoir terminé
        status_json = lws_connect.get_job_status(ssh_client, process_token, job_id)
        logging.critical("response=%s", status_json)
        ssh_client.close()
        return jsonify(status_json), 201   
    else :
        # En mode synchrone, le webservice donne illico sa réponse GetResult
        resultJson = { "job_id" : "NaN" , "processToken": request.json[0]['processToken'] }
        return jsonify(resultJson), 200

@app.route('/v' + wsVersion + '/services/'+wsName+'/<int:job_id>/<process_token>/outputs', methods = ['GET'])
#@auth.login_required
def get_result(job_id,process_token):
   """ returns the status of the given process id and process token
    :param job_id: the job id
    :type job_id: int?
    :param process_token: the token being queried
    :type process_token: str (uuid)
    :return: the results of the task
    :type: str (containing a json)
    """
    ssh_client = None
    try:
        ssh_client = lws_connect.connect_with_sshconfig(config, ssh_config_file)
    except Exception as excpt:
        logging.critical("unable to log on %s, ABORTING", config["clstrHostName"])
        raise excpt
    if ssh_client is None:
        logging.critical("unable to log on %s, ABORTING", config["clstrHostName"])
        raise ValueError("unable to log on %s, ABORTING", config["clstrHostName"])
    logging.info("get_status for token %s", process_token)
    status_json = lws_connect.get_job_status(ssh_client, process_token, job_id)
    
    """Lorsqu'il est interrogé uniquement à fin de suivi, 
    le webservice a besoin du job Id et, par sécurité,
    du jeton de suivi du processus de calcul 
    pour répondre un simple message d'attente
    """
    resultJson = { "job_id" : job_id , "processToken": process_token }
    
    """Lorsque le process est terminé, le web-service renvoit les url de ses produits
    """
    statusTab=json.loads(status_json)
    if statusTab['Status']=="Terminated":
        """Lisons le contenu du repertoire de publication
        """
        publishDir = "".join(config["clstrIrodsDir"],"/", config["apiVersion"],"/services/ws_dnldResult/" , process_token)
        command = "ils "+publishDir
        logging.critical("list of results: command=%s", command)
        ret = run_on_frontal(ssh_client, command)
               
        """ Elaborons la liste json des produits
        """
        resultJson={ "job_id" : job_id ,\
                     "processToken": process_token ,\
                     "resNames" :[{"resName" : "unw interferogram" , "resURI" : "<resURI1>"},\
                                  {"resName" : "jpeg high resolution interferogram" , "resURI" : "<resURI2>"},\
                                  {"resName" : "jpeg low resolution interferogram" , "resURI" : "<resURI3>"}
                                ]
                    }
        
    ssh_client.close()
    return jsonify(resultJson), 200

@app.route('/v' + wsVersion + '/services/'+wsName+'/<int:job_id>', methods = ['DELETE'])
@auth.login_required
def dismiss(job_id):
# Directive prevue mais non mise en place. Informons l'interlocuteur par le code 501 : NOT IMPLEMENTED
    return jsonify( { 'job_id' : job_id , 'result': False } ), 501


if __name__ == '__main__':
    app.secret_key = os.urandom(12)
    print "hostname=", config['wsHostName'], "port=", wsPortNumber
    app.run(debug=config['debugMode'], host=config['wsHostName'], port=wsPortNumber)
