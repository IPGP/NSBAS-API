#!flask/bin/python
# -*- coding: utf-8 -*-
# Webservice ws_createProcFile , ex WS2
# Version PHA du 8/3/2017
#
# Fonction : 
# Créer, dans le dossier de travail, le répertoire de chaque sous-fauchée où le fichier nsbas.proc est généré.
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
# Execute avec curl -i -umiguel:python -H "Content-Type: application/json" -X POST -d '[{"processToken" : "f5e6f9g8t5232n5d5d6s56"},{ "type": "Feature","bbox": [ 2.8784608840942383 , 42.694144332492674 , 2.8876025772094727 , 42.69814795493774] }]' http://gravi155.step.univ-paris-diderot.fr:5024/v1.0/services/ws_createProcFile?mode=async
# 
# GetResult : curl -i -umiguel:python -X GET http://gravi155.step.univ-paris-diderot.fr:5024/v1.0/services/ws_createProcFile/5698/67b373c6-4c6f-443b-8cb0-0986d7c76598/outputs
# GetStatus : curl -i -umiguel:python -X GET http://gravi155.step.univ-paris-diderot.fr:5024/v1.0/services/ws_createProcFile/5698/67b373c6-4c6f-443b-8cb0-0986d7c76598
# GetCapabilities : curl -i -umiguel:python -X GET http://gravi155.step.univ-paris-diderot.fr:5024/v1.0/services
# DescribeProcess : curl -i -umiguel:python -X GET http://gravi155.step.univ-paris-diderot.fr:5024/v1.0/services/ws_createProcFile
#
#
# Backlog :
# 
# Donner une valeur au repertoire workingDir utilisés par les commandes
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


from flask import Flask, jsonify, abort, request, make_response, url_for
from flask_httpauth import HTTPBasicAuth
import paramiko
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
wsName = 'ws_createProcFile'
wsVersion = '1.0'
wsPortNumber = 5024

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
    return jsonify( { "id": "02", "label": "ForM@Ter - NSBAS API", "type": "WPS", "url": ""+ url_for("get_capabilities", _external=True) +"", "contact": "contact@poleterresolide.fr" })

@app.route('/v' + wsVersion + '/services/'+wsName, methods = ['GET'])
@auth.login_required
def describe_process():
    return jsonify( {
		  "id": ""+wsName+"",
		  "label": "ForM@Ter/Etalab ws_createProcFile webservice",
		  "description": "Create on the cluster subwath directories and .proc parameters files",
		  "inputs":  [
		              [{"processToken" : "<token>"},
                              {"subSwath" : "<subswathnb>"},
                              { "type": "Feature",
                                "bbox": [ "<long min>"  ,  "<lat min>"  , 
                                          "<long max>"  ,  "<lat max>" ]
                              }]
                             ], 
                  "outputs": [
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
# L'execute du webservice ws_createProcFile doit 
#
# 

    # Creons le jeton du processus (a finaliser)
    processToken = "d9dc5248-e741-4ef0-a54fee1a0"

    ssh.connect(clstrHostName, username=clstrUserName, password=clstrPassWord,allow_agent=False,look_for_keys=False)
	
    # Donner des valeurs aux repertoires utilisés par les commandes
    workingDir="/home/adminsrv/xxxxxxxx"

    command2 = 'oarsub --project iste-equ-cycle -l /nodes=1/core=1,walltime=01:00:00 -d ' + workingDir + ' "python nsb_mkworkdir.py -s s1 -d/data/ist-sar/baie1/work-marzougui/11107_iw/DEM /data/ist-sar/baie1/work-marzougui/11107_iw/SLC iw1"&' 
		
    idj ='$command2 | grep "OAR_JOB_ID" '
		
		
    #oar_job_id=oarsub $command2 | grep "OAR_JOB_ID" | cut -d '=' -f2

    #command2 = "nsb_mkworkdir.py -s s1 -d/home/marzougd/WorkingDir/test/DEM SLC " + "".join("iw"+request.values["subSwath"])
    ##stdin, stdout, stderr = ssh.exec_command(command2 , get_pty=True)
    ##stdin1, stdout1, stderr1 = ssh.exec_command(idj , get_pty=True)
    #stdin.channel.shutdown_write()
	
    #return stdout.read() + stdout1.read()
	
    #return stdout.read() + job_id
    ssh.close()
	
    #return command2
    # Pour avoir une idée de la structure des données reçues
    # print repr(request.json)
    # GeoJson : pour lire la quatrième du bbox geojson, situé à l'indice 3 du tableau
    # print request.json[1]['bbox'][3]
    # Un petit truc à toutes fins utiles
    #for numid in request.json:
    #    print repr(numid)
 
    job_id = 156

    if request.values['mode'] == "async" :

        # Des lors qu'il est lance, le webservice donne son jeton via son GetStatus, sans attendre d'avoir terminé
        statusJson = getJobStatus(job_id,processToken)
        return jsonify(statusJson), 201        
    else :
        # En mode synchrone, le webservice donne illico sa réponse GetResult
        resultJson = { "job_id" : job_id , "processToken": processToken }
        return jsonify(resultJson), 200

@app.route('/v' + wsVersion + '/services/'+wsName+'/<int:job_id>/<uuid:process_token>/outputs', methods = ['GET'])
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
    app.run(debug=debugMode,host=wsHostName, port=wsPortNumber)
