#!flask/bin/python
# -*- coding: utf-8 -*-
# Webservice ws_dnldDem2Clstr , ex WS1
# Version PHA du 8/3/2017
#
# Fonction :
# Obtenir sur le cluster de calcul un modèle numérique de terrain (MNT ou DEM) à 30m qui couvre l'ensemble de l'image radar (ensemble des 3 sous-fauchées).
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
# Execute avec curl -i -umiguel:python -H "Content-Type: application/json" -X POST -d '[{"processToken" : "f5e6f9g8t5232n5d5d6s56"},{ "type": "Feature","bbox": [ 2.8784608840942383 , 42.694144332492674 , 2.8876025772094727 , 42.69814795493774] }]' http://gravi155.step.univ-paris-diderot.fr:5023/v1.0/services/ws_dnldDem2Clstr?mode=async
#
# GetResult : curl -i -umiguel:python -X GET http://gravi155.step.univ-paris-diderot.fr:5023/v1.0/services/ws_dnldDem2Clstr/5698/67b373c6-4c6f-443b-8cb0-0986d7c76598/outputs
# GetStatus : curl -i -umiguel:python -X GET http://gravi155.step.univ-paris-diderot.fr:5023/v1.0/services/ws_dnldDem2Clstr/5698/67b373c6-4c6f-443b-8cb0-0986d7c76598
# GetCapabilities : curl -i -umiguel:python -X GET http://gravi155.step.univ-paris-diderot.fr:5023/v1.0/services
# DescribeProcess : curl -i -umiguel:python -X GET http://gravi155.step.univ-paris-diderot.fr:5023/v1.0/services/ws_dnldDem2Clstr
#
#
# Backlog :
#
# Comment détermine-t-on le DEM à télécharger ?
# Donner des valeurs aux repertoires sourceDir et workingDir utilisés par les commandes
# Si le workindir n'est pas le meme pour tous les telechargements, integrer le choix du nom du workingdir et sa creation
# Variabiliser et sortir les chemins en dur
# Faire en sorte de fermer la connexion ssh sans tuer les process
# Gerer le cas ou le GetResult est demande avant que le process soit termine: renvoyer le GetStatus
# Comment faire le lien entre jeton du processus et jobId ?
#    - Déposer sur le cluster, a cote des fichiers telecharges, un fichier nomme comme le jobId et contenant le jeton ?
#    - Mettre les fichiers dans un repertoire dont le nom contienne le jobId et le jeton ?
# Tester l'Execute face à un serveur de calcul disposant des scripts python requis pour faire ce que ce webservice lui demande
#
# Dernières modifications:
#

import os
from flask import Flask, jsonify, abort, request, make_response, url_for
from flask_httpauth import HTTPBasicAuth
import paramiko
import logging

# Le module (bibliotheque) specifique des webservices NSBAS
# Doit etre dans le PYTHON PATH et se nommer lib_ws_nsbas.py
# Le module (bibliotheque) specifique des webservices NSBAS
# Doit etre dans le PYTHON PATH et se nommer lib_ws_nsbas.py
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
from flask_cors import CORS, cross_origin
app = Flask(__name__, static_url_path = "")
cors = CORS(app, resources={r"*": {"origins": "*"}})

# Parametres specifiques a ce webservice
wsName = 'ws_dnldDem2Clstr'
wsVersion = '1.0'
wsPortNumber = 5023

# Incluons un fichier de parametres communs a tous les webservices
execfile("parametres.py")

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
    return jsonify( { "id": "01", "label": "ForM@Ter - NSBAS API", "type": "WPS", "url": ""+ url_for("get_capabilities", _external=True) +"", "contact": "contact@poleterresolide.fr" })

@app.route('/v' + wsVersion + '/services/'+wsName, methods = ['GET'])
@auth.login_required
def describe_process():
    return jsonify( {
          "id": ""+wsName+"",
          "label": "ForM@Ter/Etalab ws_dnldDem2Clstr webservice",
          "description": "Downloads Digital Elevation Model tiles from Nasa to the computing cluster and merges them into a single tiff file.",
          "inputs":  [
                      [{"processToken" : "<token>"},
                               { "type": "Feature",
                                 "bbox": [ "<long min>" , "<lat min>" ,
                                           "<long max>" , "<lat max>" ]
                              }]
                             ],
                  "outputs": [
                              { "jobId" : "<jobId>", "processToken" : "<token>" }
                         ]
                    }
          )

@app.route('/v' + wsVersion + '/services/'+wsName+'/<int:job_id>/<process_token>', methods = ['GET'])
@auth.login_required
def get_status(job_id, process_token):
    statusJson = getJobStatus(job_id,process_token)
    return jsonify(statusJson)

@app.route('/v' + wsVersion + '/services/'+wsName, methods = ['POST'])
@auth.login_required
def execute():
# L'execute synchrone renvoit le resultat et la reponse http 200 : OK
# L'execute asynchrone doit renvoyer la reponse du GetStatus et la reponse http 201 ou celle du GetResult et la reponse http 200, selon
#
# L'execute du webservice ws_dnldDem2Clstr doit
#
#
    logging.critical("getting: %s", str(request.json[0]['processToken']))
    process_token = request.json[0]['processToken']

    if request.values['mode'] == "async":
        # TODO estimer dynamiquement walltime
        process_ressources = {"nodes" : 1, "cores" : 1, "walltime" : "00:50:00", "workdir": remote_prefix}
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
        token_dir = config['clstrBaseDir'] + '/' + process_token
        dem_dir = token_dir + '/DEM'
        slc_dir = token_dir + '/SLC'
        command = " ".join(["mkdir", dem_dir + '; ',
                            "nsb_getDemFile.py", "fromRadarImage",
                            slc_dir, dem_dir])
        try:
            logging.critical("launching command: %s", command)
            job_id = lws_connect.run_on_cluster_node(ssh_client, command, str(process_token),
                                                  process_ressources)
            logging.critical("returned from submission %s", job_id)
        except Exception as excpt:
            error = error + "fail to run command on server: {}".format(excpt)
            logging.error(error)
        ssh_client.close()
        # Des lors qu'il est lance, le webservice donne son jeton via son GetStatus, sans attendre d'avoir terminé
        resultJson = {"job_id" : job_id , "processToken": process_token}
        return jsonify(resultJson), 201
    else :
        # En mode synchrone, le webservice donne illico sa réponse GetResult
        resultJson = {"job_id" : job_id , "processToken": process_token}
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
