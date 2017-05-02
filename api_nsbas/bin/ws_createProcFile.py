#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Webservice ws_createProcFile , ex WS2
#
"""Fonction :
Créer, dans le dossier de travail, le répertoire de chaque sous-fauchée où le fichier nsbas.proc est généré.

Ce code est inspiré de https://blog.miguelgrinberg.com/post/designing-a-restful-api-with-python-and-flask
Pour en savoir plus : http://flask.pocoo.org/docs/0.12/quickstart/

Utilisation des arguments :
request.json est un hypercube associatif qui reprend la structure du json envoye.
request.values est un tableau associatif qui reprend les variables transmises en mode key-value pair (?toto=156&mode=sync)
"""

import logging
# cet import os et subproces est-il bien utile ? Ne sert-il pas qu'en local ?
import os, subprocess

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
wsName = 'ws_createProcFile'
wsVersion = config['apiVersion']
wsPortNumber = int(config['ws_createProcFile_PN'])

app = Flask(__name__, static_url_path = "")
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
    return jsonify( { "id": "02", "label": "ForM@Ter - NSBAS API", "type": "WPS", "url": ""+ url_for("get_capabilities", _external=True) +"", "contact": "contact@poleterresolide.fr" })

@app.route('/v' + wsVersion + '/services/'+wsName, methods = ['GET'])
@auth.login_required
def describe_process():
    return jsonify( {
        "id": ""+wsName+"",
        "label": "ForM@Ter/Etalab ws_createProcFile webservice",
        "description": "Creates on the cluster subwath directories and .proc parameters files",
        "inputs":  [
              [{"processToken" : "<token>"},
                              {"subSwath" : "<subswathnb>"},
                              { "type": "Feature",
                                "bbox": [ "<long min>"  ,  "<lat min>"  ,
                                          "<long max>"  ,  "<lat max>" ]
                              }]
                             ],
                  "outputs": [ { "jobId" : "<jobId>", "processToken" : "<token>" } ]
                    }
                  )

@app.route('/v' + wsVersion + '/services/'+wsName+'/<int:job_id>/<process_token>', methods = ['GET'])
@auth.login_required
def get_status(job_id,process_token):
    statusJson = lws_nsbas.getJobStatus(job_id,process_token)
    return jsonify(statusJson)

@app.route('/v' + wsVersion + '/services/'+wsName, methods = ['POST'])
@auth.login_required
def execute():

    logging.critical("getting: token %s", str(request.json[0]['processToken']))
    logging.critical("getting: swath %s", str(request.json[1]['subSwath']))
    process_token = request.json[0]['processToken']
    str_swath = str(request.json[1]['subSwath'])
    token_dir = config['clstrDataDir'] + '/' + process_token
    # En mode synchrone, le webservice donne illico sa réponse GetResult
    try:
        ssh_client = lws_connect.connect_with_sshconfig(config, ssh_config_file)
    except Exception as excpt:
        logging.critical("unable to log on %s, ABORTING", config["clstrHostName"])
        raise excpt
    if ssh_client is None:
        logging.critical("unable to log on %s, ABORTING", config["clstrHostName"])
        raise ValueError("unable to log on %s, ABORTING", config["clstrHostName"])
    logging.info("connection OK")
    # command is not expensive -> we can run it on frontal
    dem_dir = token_dir + '/DEM'
    slc_dir = token_dir + '/SLC'
    command = " ".join(["cd", token_dir, ";", "nsb_mkworkdir.py -s s1 -d", dem_dir, "SLC", "iw" + str_swath])
    logging.critical("command = %s", command)
    ret = None
    try:
        ret = lws_connect.run_on_frontal(ssh_client, command)
    except Exception as excpt:
        logging.critical("ERROR: " + str(ret) + "--" + str(excpt))
        resultJson = {"job_id" : "NaN", "processToken": process_token}
        ssh_client.close()
        return jsonify(resultJson), 500
    ssh_client.close()
    resultJson = { "job_id" : "NaN", "processToken": process_token }
    return jsonify(resultJson), 200

@app.route('/v' + wsVersion + '/services/'+wsName+'/<int:job_id>/<process_token>/outputs', methods = ['GET'])
#@auth.login_required
def get_result(job_id,process_token):
    # Lorsqu'il est interrogé uniquement à fin de suivi,
    # le webservice a besoin du job Id et, par sécurité,
    # du jeton de suivi du processus de calcul pour répondre
    # On les trouve dans les paramètres de l'url
    resultJson = { "job_id" : job_id , "processToken": process_token }
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
