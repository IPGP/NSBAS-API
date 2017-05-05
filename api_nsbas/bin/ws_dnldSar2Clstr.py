#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Webservice ws_dnldSar2Clstr , ex WS0
#
"""Fonction :
Ce webservice a plusieurs fonctions :
 - Telecharger les donnees a traiter sur le cluster apres selection des differents
   parametre depuis l'interface. (collection, polarisation, sens de l'orbite, date, zone).
- Fournir a l'application interlocutrice un jeton qui lui permette de designer aux autres
   webservices l'instance de processus en cours.

Note : GetStatus et GetResult attendent de l'application cliente le jobId et le processToken
Il est convenu, de ne pas remettre en question les specs
Ce code est inspire de
https://blog.miguelgrinberg.com/post/designing-a-restful-api-with-python-and-flask
Pour en savoir plus : http://flask.pocoo.org/docs/0.12/quickstart/

 Utilisation des arguments :
 request.json est un hypercube associatif qui reprend la structure du json envoye.
 request.values est un tableau associatif qui reprend les variables transmises en
 mode key-value pair (?toto=156&mode=sync)
"""

import os
import sys
import logging
from flask import Flask, jsonify, abort, request, make_response, url_for
from flask_httpauth import HTTPBasicAuth
import paramiko, uuid


# Le module (bibliotheque) specifique des webservices NSBAS
# Doit etre dans le PYTHON PATH
import lib_ws.ws_nsbas as lws_nsbas
import lib_ws.ws_connect as lws_connect

# Incluons un fichier de parametres communs a tous les webservices
import parametres
config = parametres.configdic
remote_prefix = config["clstrBaseDir"]
ssh_config_file = os.environ["HOME"] + "/" + ".ssh/config"

# Preparons la connexion ssh via Paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Autorisons les requetes provenant de domaines distincts du domaine qui heberge le webservice
# A restreindre dès que l'hébergement du frontal sera connu
from flask_cors import CORS, cross_origin
app = Flask(__name__, static_url_path = "")
cors = CORS(app, resources={r"*": {"origins": "*"}})

# Parametres specifiques a ce webservice
wsName = 'ws_dnldSar2Clstr'
# what about: wsName= __file__[:-3] ?

# Incluons un fichier de parametres communs a tous les webservices
import parametres

config = parametres.configdic
wsVersion = config['apiVersion']
wsPortNumber = int(config['ws_dnldSar2Clstr_PN'])
remote_prefix = config["clstrBaseDir"]
remote_data_prefix = config["clstrDataDir"]
ssh_config_file = os.environ["HOME"] + "/" + ".ssh/config"

app = Flask(__name__, static_url_path = "")
auth = HTTPBasicAuth()

@auth.get_password
def get_password(username):
    """ return the password of the given username if any
    :param username: a username
    :type username: str
    :return: the password or None if unknown username
    :rtype: str
    """
    if username == config['httpUserName']:
        return config['httpPassWord']
    return None

@auth.error_handler
def unauthorized():
    """ return a string mentionning access is refused"""
    return make_response(jsonify({'error': 'Unauthorized access'}), 403)
    # return 403 instead of 401 to prevent browsers from displaying the default auth dialog

@app.errorhandler(400)
def not_found(error):
    """ build a anwser corresponding to the error string (handling 400 error)
    :param error: the error string
    :type error: str
    :return: the formated error
    :rtype: str
    """
    return make_response(jsonify({'error': 'Bad request: {}'.format(error)}), 400)

@app.errorhandler(404)
def not_found(error):
    """ build a anwser corresponding to the error string (handling 404 error)
    :param error: the error string
    :type error: str
    :return: the formated error
    :rtype: str
    """
    return make_response(jsonify({'error': 'Not found: {}'.format(error)}), 404)

@app.route('/v' + wsVersion + '/services', methods = ['GET'])
@auth.login_required
def get_capabilities():
    """ implements the get_capabilities """
    return jsonify( { "id": "00", "label": "ForM@Ter - NSBAS API", "type": "WPS", "url": ""+ url_for("get_capabilities", _external=True) +"", "contact": "contact@poleterresolide.fr" })

@app.route('/v' + wsVersion + '/services/'+wsName, methods = ['GET'])
@auth.login_required
def describe_process():
    """ return a formated strings representing the process """
    return jsonify({"id": ""+wsName+"",\
                    "label": "ForM@Ter/Etalab ws_dnldSar2Clstr webservice",
                    "description": "Downloads SAR data to the computing cluster. Produces a token to drive and survey the computing process",
                    "inputs": [
                        {"pepsDataIds" :
                             [{"id":"<pepsId1>"} , {"id":"<pepsId2>"} , {"id":"<pepsId3>"} , {"id":"..."}]
                             }
                            ],
                  "outputs":[{"jobId" : "<jobId>", "processToken" : "<token>" }]
                    }
    )

@app.route('/v' + wsVersion + '/services/'+wsName+'/<int:job_id>/<process_token>', methods = ['GET'])
@auth.login_required
def get_status(job_id,process_token):
    """ returns the status of the given process id and process token
    :param job_id: the job id
    :type job_id: int?
    :param process_token: the token being queried
    :type process_token: str (uuid)
    :return: the status of the task
    :rtype: str (containing a json)
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
    status_json = lws_connect.get_job_status(ssh_client, job_id)
    ssh_client.close()
    return jsonify(status_json)

@app.route('/v' + wsVersion + '/services/'+wsName, methods = ['POST'])
@auth.login_required
def execute():
    """
 L'execute synchrone renvoit le resultat et la reponse http 200 : OK
 L'execute asynchrone doit renvoyer la reponse du GetStatus et la reponse http 201
 ou celle du GetResult et la reponse http 200, selon
 L'execute du webservice ws_dnldSar2Clstr doit
 - prendre en arguments, dans les data de la requete http, un json listant les ids des images Peps a telecharger,
 ex : [{"pepsDataIds" :[{"id":"56987456"} ,
                       {"id":"287946133"} ,
                       {"id":"4789654123"} ,
                       {"id":"852147963"}]}]
 afin que request.json produise un tableau du style request.json['ids'][0]['id']
 - donner en sortie un ticket permettant d'interroger le getstatus pour savoir ou
   en est le telechargement. Ce ticket pourrait etre un jobid.
"""
    # Creons le jeton du processus dans le style "d9dc5248-e741-4ef0-a54fee1a0"
    processToken = str(uuid.uuid4())
    ids = [numid['id'] for numid in request.json[0]['pepsDataIds']]

    if request.values['mode'] == "async":
        print ids
        job_id = 0
        error = ""
        ssh_client = None
        token_dir = config['clstrDataDir'] + '/' + processToken
        log_dir = "{}/LOG".format(token_dir)
        process_ressources = {"nodes" : 1, "cores" : 1, "walltime" : "00:50:00",
                "workdir": token_dir, "logdir" : log_dir}
        ret = "Error"
        try:
            ssh_client = lws_connect.connect_with_sshconfig(config, ssh_config_file)
        except Exception as excpt:
            logging.critical("unable to log on %s, ABORTING", config["clstrHostName"])
            raise excpt
        if ssh_client is None:
            logging.critical("unable to log on %s, ABORTING", config["clstrHostName"])
            raise ValueError("unable to log on %s, ABORTING", config["clstrHostName"])
        logging.info("connection OK, managing %d images", len(ids))
        command = " ".join([remote_prefix + "/bin/wsc_downloadPepsData.py", \
                            "-v", "4",\
                            "-token", str(processToken), \
                            "-wd", remote_data_prefix + "/" + str(processToken) + "/SLC"] + ids)
        try:
            logging.critical("launching command: %s", command)
            job_id = lws_connect.run_on_cluster_node(ssh_client, command, str(processToken),
                                                  process_ressources)
            logging.critical("returned from submission %s", job_id)
        except Exception as excpt:
            error = error + "fail to run command on server: {}".format(excpt)
            logging.error(error)
        ssh_client.close()
        # Des lors qu'il est lance, le webservice donne son jeton via son GetStatus, sans attendre d'avoir terminé
        statusJson = lws_nsbas.getJobStatus(job_id, processToken, error)
        return jsonify(statusJson), 201
    else :
        # En mode synchrone, le webservice donne illico sa réponse GetResult
        resultJson = {"job_id" : job_id , "processToken": processToken}
        return jsonify(resultJson), 200

@app.route('/v' + wsVersion + '/services/'+wsName+'/<int:job_id>/<process_token>/outputs', methods = ['GET'])
#@auth.login_required
def get_result(job_id, process_token):
    """
    Lorsqu'il est interrogé uniquement à fin de suivi,
    le webservice a besoin du job Id et, par sécurité,
    du jeton de suivi du processus de calcul pour répondre
    On les trouve dans les paramètres de l'url
    """
    resultJson = {"job_id" : job_id , "processToken": process_token}
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

