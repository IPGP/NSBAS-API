#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import re
import os
import subprocess
import json

re_extract_id = re.compile("OAR\.([^\.]+)\.(\d+)\.")


def get_oar_id(name, oar_log_dir):
    """ returns the id """
    for file_name in  os.listdir(oar_log_dir):
        if name in file_name:
            m = re_extract_id.search(file_name)
            if m:
                return m.groups()[1]
            else:
                raise ValueError("oar out log name not well formed")
    raise RuntimeError("check_oar did not find log file")

def get_return_code(oar_id):
    "gets the return code of the program that was launched"
    oar_str = subprocess.check_output(["/usr/bin/oarstat", "-f", "-j", str(oar_id)])
    match = re.search("exit_code\s+=\s+(\d+)\s+", oar_str)
    if match:
        return match.groups()[0]
    else:
        return ""

def get_oar_status(oar_id):
    "returns the status of the oar id"
    # first check if currently running
    oar_json = subprocess.check_output(["/usr/bin/oarstat", "-J", "-j", str(oar_id)])
    data = json.loads(oar_json)
    # they should be only one key in the array, the one we are looking for
    for keys, value in data.items():
        return value["state"]

if __name__ == "__main__":

    main_help = """Prints on stdout the status of a job given its token
                information are gathered from the log file with name
                logdir/token.log

                If logdir starts with /, it is considered absolute path name,
                else relative to $HOME

                """

    parser = argparse.ArgumentParser(description=main_help)
    parser.add_argument('--logdir', type=str, help='the directory that contains logs')
    parser.add_argument('--oarid', type=str, help='the process id')

    args = parser.parse_args()
    #pid = get_oar_id(args.token, args.logdir)
    pid = args.oarid

    # check if it is an oarid
    #print "{} ({})".format(get_oar_status(pid), get_return_code(pid)) 
    # Les messages d'erreur polluent la sortie standard de ce script, en l'occurence ce json
    # TODO : Trouver un moyen de les résumer dans le json de sortie sous forme de l'attribut "errorMessage", vide par défaut. 
    print json.dumps({'oarStatus' : get_oar_status(pid) , 'returnCode' : get_return_code(pid) , 'errorMessage' : ''})
    sys.exit(0)


