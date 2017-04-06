# Module (bibliotheque/library) specifique de l'API NSBAS lib_ws_nsbas.py
# Voir a importer ici les bibliotheques necessaires.
# Inclure eventuellement ici :
# Pour chaque webservice, une fonction realisant le coeur du Execute
# Pour chaque webservice, une fonction realisant le coeur du GetResult

# Observons l'etat de progression d'un job
def getJobStatus(id_du_job,jeton_du_processus, status):
# Version a perfectionner (!)
    # Avancement en pourcentage
    percentDone = 50
    terminated = False
    # Accepted / Terminated
    jobStatus = {
	    "StatusInfo": {
		"JobID": id_du_job,
        "processToken" : jeton_du_processus,
		"Status": "" +status+ "",
		"Progress": percentDone
		}
	}
    return jobStatus


