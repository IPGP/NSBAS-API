#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Webservice ws_dnldResult, ex WS8
#
# Fonctions : 
# - Fournir à l'application cliente le fichier qu'elle demande à destination de l'utilisateur.
# ATTENTION : ce script sera probablement remplacé par un autre dispositif. Ne pas consommer de temps dessus.
#
# Ce code est inspiré de https://blog.miguelgrinberg.com/post/designing-a-restful-api-with-python-and-flask
# Pour en savoir plus : http://flask.pocoo.org/docs/0.12/quickstart/
#
# Utilisation des arguments : 
# request.json est un hypercube associatif qui reprend la structure du json envoye.
# request.values est un tableau associatif qui reprend les variables transmises en mode key-value pair (?toto=156&mode=sync)
#
# Tests :
# Tester 
# 
# GetResult : curl -i -umiguel:python -X GET http://gravi155.step.univ-paris-diderot.fr:5030/v1.0/services/ws_dnldResult/67b373c6-4c6f-443b-8cb0-0986d7c76598/outputs/5697
# GetCapabilities : curl -i -umiguel:python -X GET http://gravi155.step.univ-paris-diderot.fr:5030/v1.0/services
# DescribeProcess : curl -i -umiguel:python -X GET http://gravi155.step.univ-paris-diderot.fr:5030/v1.0/services/ws_dnldResult
#
# ATTENTION : ce web-service est en voie de remplacement


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

# Preparons la connexion ssh via Paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Autorisons les requetes provenant de domaines distincts du domaine qui heberge le webservice
from flask_cors import CORS, cross_origin
app = Flask(__name__, static_url_path = "")
cors = CORS(app, resources={r"*": {"origins": "*"}})

# Parametres specifiques a ce webservice
wsName = 'ws_dnldResult'
wsVersion = '1.0'
wsPortNumber = 5030

app = Flask(__name__, static_url_path = "")
auth = HTTPBasicAuth()

@auth.get_password
def get_password(username):
    if username == httpUserName:
        return httpPassWord
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
    return jsonify( { "id": "08", "label": "ForM@Ter - NSBAS API", "type": "WPS", "url": ""+ url_for("get_capabilities", _external=True) +"", "contact": "contact@poleterresolide.fr" })

@app.route('/v' + wsVersion + '/services/'+wsName, methods = ['GET'])
@auth.login_required
def describe_process():
    return jsonify( {
		  "id": ""+wsName+"",
		  "label": "ForM@Ter/Etalab ws_dnldResult webservice",
		  "description": "Provides the file it is asked for, designated by its unique identifier.",
		  "inputs":  [ "http://<hostname>/v1.0/services/ws_dnldResult/<processToken>/outputs/<resName>" ], 
                  "outputs": [ "<Downloaded file>"] 
                    }
		  )


@app.route('/v' + wsVersion + '/services/'+wsName+'/<process_token>/outputs/<int:res_name>', methods = ['GET'])
@auth.login_required
def get_result(process_token,res_name):
# Le GetResult du webservice dnldResult doit fournir le fichier demandé
# Avec le bon nom, la bonne taille, le bon type mime et la bonne date de création
# Pour l'instant, on ne retourne rien : 501
    return jsonify( { 'job_id' : process_token , 'result': False } ), 501

@app.route('/v' + wsVersion + '/services/'+wsName+'/<int:job_id>', methods = ['DELETE'])
@auth.login_required
def dismiss(job_id):
# Directive prevue mais non mise en place. Informons l'interlocuteur par le code 501 : NOT IMPLEMENTED
    return jsonify( { 'job_id' : job_id , 'result': False } ), 501

    
if __name__ == '__main__':
    app.secret_key = os.urandom(12)
    print "hostname=", config['wsHostName'], "port=", wsPortNumber
    app.run(debug=config['debugMode'], host=config['wsHostName'], port=wsPortNumber)
