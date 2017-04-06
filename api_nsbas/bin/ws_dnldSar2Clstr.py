#!flask/bin/python
# -*- coding: utf-8 -*-
# Webservice ws_dnldSar2Clstr , ex WS0
# Version PHA du 8/3/2017
#
# Fonction : 
# Ce webservice a plusieurs fonctions :
# - Telecharger les donnees a traiter sur le cluster apres selection des differents parametres depuis l'interface. (collection, polarisation, sens de l'orbite, date, zone, …).
# - Fournir a l'application interlocutrice un jeton qui lui permette de designer aux autres webservices l'instance de processus en cours.
# Note : GetStatus et GetResult attendent le jobId et le processToken de l'application cliente
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
# Execute avec curl -i -umiguel:python -H "Content-Type: application/json" -X POST -d '{"pepsDataIds" :[{"id":"cfafa369-e89b-53d9-94bf-d7c68496970f"} , {"id":"f9f1b727-7a14-5b7c-96b0-456d53d3c1fe"} , {"id":"0ef5e877-7596-5166-b20f-94eea05933eb"}]}' http://gravi155.step.univ-paris-diderot.fr:5022/v1.0/services/ws_dnldSar2Clstr?mode=async
# Attention : les id fournies par Peps ne fonctionnent que pendant un court laps de temps
# Des id opérationnelles pour tester peuvent être trouvées sur Peps par des requêtes comme 
# https://peps.cnes.fr/resto/api/collections/S1/search.json?location=amiens&_pretty=true
# Chercher FeatureCollection > features > Feature / id
#
# GetResult : curl -i -umiguel:python -X GET http://gravi155.step.univ-paris-diderot.fr:5022/v1.0/services/ws_dnldSar2Clstr/5698/67b373c6-4c6f-443b-8cb0-0986d7c76598/outputs
# GetStatus : curl -i -umiguel:python -X GET http://gravi155.step.univ-paris-diderot.fr:5022/v1.0/services/ws_dnldSar2Clstr/5698/67b373c6-4c6f-443b-8cb0-0986d7c76598
# GetCapabilities : curl -i -umiguel:python -X GET http://gravi155.step.univ-paris-diderot.fr:5022/v1.0/services
# DescribeProcess : curl -i -umiguel:python -X GET http://gravi155.step.univ-paris-diderot.fr:5022/v1.0/services/ws_dnldSar2Clstr
#
#
# Backlog :
# 
# Si le workindir n'est pas le meme pour tous les telechargements, integrer le choix du nom du workingdir et sa creation 
# Variabiliser et sortir les chemins en dur
# Faire en sorte de fermer la connexion ssh sans tuer les process
# Gerer le cas ou le GetResult est demande avant que le process soit termine: renvoyer le GetStatus
# Comment faire le lien entre jeton du processus et jobId ? 
#    - Déposer sur le cluster, a cote des fichiers telecharges, un fichier nomme comme le jobId et contenant le jeton ? 
#    - Mettre les fichiers dans un repertoire dont le nom contienne le jobId et le jeton ?
# 
# Dernières modifications:
# 


from flask import Flask, jsonify, abort, request, make_response, url_for
from flask_httpauth import HTTPBasicAuth
import paramiko, uuid
# cet import os et subproces est-il bien utile ? Ne sert-il pas qu'en local ?
import os, subprocess

# Le module (bibliotheque) specifique des webservices NSBAS
# Doit etre dans le PYTHON PATH et se nommer lib_ws_nsbas.py
from lib_ws_nsbas import *

# Preparons la connexion ssh via Paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Autorisons les requetes provenant de domaines distincts du domaine qui heberge le webservice
from flask_cors import CORS, cross_origin
app = Flask(__name__, static_url_path = "")
cors = CORS(app, resources={r"*": {"origins": "*"}})

# Parametres specifiques a ce webservice
wsName = 'ws_dnldSar2Clstr'
wsVersion = '1.0'
wsPortNumber = 5022

# Incluons un fichier de parametres communs a tous les webservices
execfile("parametres.py")

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
    return jsonify( { "id": "00", "label": "ForM@Ter - NSBAS API", "type": "WPS", "url": ""+ url_for("get_capabilities", _external=True) +"", "contact": "contact@poleterresolide.fr" })

@app.route('/v' + wsVersion + '/services/'+wsName, methods = ['GET'])
@auth.login_required
def describe_process():
    return jsonify( {
		  "id": ""+wsName+"",
		  "label": "ForM@Ter/Etalab ws_dnldSar2Clstr webservice",
		  "description": "Downloads SAR data to the computing cluster. Produces a token to drive and survey the computing process",
		  "inputs": [
		             {"pepsDataIds" :
                             [{"id":"<pepsId1>"} , {"id":"<pepsId2>"} , {"id":"<pepsId3>"} , {"id":"..."}]
                             }
                            ], 
                  "outputs":[
                             { "jobId" : "<jobId>", "processToken" : "<token>" }
	                    ] 
                    }
		 )

@app.route('/v' + wsVersion + '/services/'+wsName+'/<int:job_id>/<uuid:process_token>', methods = ['GET'])
@auth.login_required
def get_status(job_id,process_token):
    statusJson = getJobStatus(job_id,process_token)
    return jsonify(statusJson)

@app.route('/v' + wsVersion + '/services/'+wsName, methods = ['POST'])
@auth.login_required
def execute():
# L'execute synchrone renvoit le resultat et la reponse http 200 : OK
# L'execute asynchrone doit renvoyer la reponse du GetStatus et la reponse http 201 ou celle du GetResult et la reponse http 200, selon
#
# Le script WS0_samy.py utilisait une chaine passee comme valeur d'une variable de formulaire "jsondata" et formatee 
# dans le style {"IDS":"987,654,321"}
# L'execute du webservice ws_dnldSar2Clstr doit 
# - prendre en arguments, dans les data de la requete http, un json listant les ids des images Peps a telecharger, ex : {"pepsDataIds" :[{"id":"56987456"} , {"id":"287946133"} , {"id":"4789654123"} , {"id":"852147963"}]}
# afin que request.json produise un tableau du style request.json['ids'][0]['id']
# - donner en sortie un ticket permettant d'interroger le getstatus pour savoir o en est le telechargement. Ce ticket pourrait etre un jobid.

    # Creons le jeton du processus
    processToken = uuid.uuid4()

    if request.values['mode'] == "async" :

	##ssh.connect(clstrHostName, username=clstrUserName, password=clstrPassWord,allow_agent=False,look_for_keys=False)
	
	global p
	
	#command1 = "mkdir " + os.path.join(request.values["workingDir"],"SLC")
	#stdin, stdout, stderr = ssh.exec_command(command1, get_pty=True)
	#ssh.close()

        # Info issue de la version DMA 20170223
	workingDir="/home/adminsrv/WS_Download_JSON"
        # Selon ATO 20170307 : workingDir="/home/adminsrv"

        # Concatenons les id des features a telecharger
	idlist=" "
        for numid in request.json['pepsDataIds']:
            idlist += numid['id']+" "

	command2 = "echo $$ ; for i in " + " " + idlist + " ; do python /home/adminsrv/WS_Download_JSON/downloadUneImage5.py $i" + " " + workingDir + " ; done "
	
	##stdin, stdout, stderr = ssh.exec_command(command2, get_pty=True)
	
	#return command2
	#for i in range(len(data)):
		#command2="echo $$ ;  python" + " " + " /home/marzougd/Documents/ProjetFormater/WS_python/WS0/downloadUneImage5.py" + " " + data['IDS'][i]
		#stdin, stdout, stderr = ssh.exec_command(command2, get_pty=True)

	##return stdout.read() 
        #return pid
        ##ssh.close()
        #Faisons comme si nous disposions du jobId
        job_id = 7899478
        # Des lors qu'il est lance, le webservice donne son jeton via son GetStatus, sans attendre d'avoir terminé
        statusJson = getJobStatus(job_id,processToken)
        return jsonify(statusJson), 201        
    else :
        # En mode synchrone, le webservice donne illico sa réponse GetResult
        resultJson = { "job_id" : job_id , "processToken": processToken }
        return jsonify(resultJson), 200

@app.route('/v' + wsVersion + '/services/'+wsName+'/<int:job_id>/<uuid:process_token>/outputs', methods = ['GET'])
@auth.login_required
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
    app.run(debug=debugMode,host=wsHostName, port=wsPortNumber)
