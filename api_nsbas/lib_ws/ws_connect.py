#!/usr/bin/env python

import os
import logging
import paramiko
import parametres

def connect_with_sshconfig(cluster, ssh_config_file="~/.ssh/config"):
    """
    Connect using paramiko to a server using ssh configuration file

    :param cluster: information about the cluster (hostname, username, password)
    :type cluster: dictionnary (usefull keys: "hostname", "username", "password")
    :param ssh_config_file: name of the ssh config file (default to ~/.ssh/config)
    :type ssh_config_file: string
    :return: the ssh client or None if failure
    :rtype: a paramiko client
    """
    client = paramiko.SSHClient()
    client._policy = paramiko.WarningPolicy()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh_config = paramiko.SSHConfig()
    user_config_file = os.path.expanduser(ssh_config_file)
    if os.path.exists(user_config_file):
        with open(user_config_file) as fic_handle:
            ssh_config.parse(fic_handle)

    cfg = {'hostname': cluster["clstrHostName"], 'username': cluster["clstrUserName"]}

    user_config = ssh_config.lookup(cfg['hostname'])
    for k in ('hostname', 'username', 'port'):
        if k in user_config:
            cfg[k] = user_config[k]

    if 'proxycommand' in user_config:
        cfg['sock'] = paramiko.ProxyCommand(user_config['proxycommand'])

    client.connect(**cfg)
    return client

def run_on_cluster_node(ssh_client, command, token, task_desc):
    """for each  image in image_set, run wsc_downloadPepsData
       on workingDir, on the given server

    :param ssh_client: the paramiko client
    :param command: the command to run on  machine
    :type command: string
    :param token: the token that was assigned when launging the job
    :type token: string (uuid)
    :param task_desc: the description of the task
    :type task_desc: dictionnary describing the walltime, the number of cores,
    the number of nodes, and the working dir. only workingdir is mandatory. Other missing
    values are set to 1. .
    :return: the stout of the command (if not ran in background)
    :rtype: string (or None in case of authentification failure
    """
    if not "nodes" in task_desc:
        task_desc["nodes"] = 1
    if not "core" in task_desc:
        task_desc["core"] = 1
    if not "walltime" in task_desc:
        task_desc["walltime"] = "01:00:00"
    if not  "workdir" in task_desc:
        logging.error("ws_connect.py:run_on_cluster_node: task_desc should provide workdir key")
        raise ValueError("ws_connect.py:run_on_cluster_node: task_desc should provide workdir key")
    oarsub_prefix = "oarsub -n {} -l /nodes={}/core={},walltime={} --project nsbas -d {}".\
            format(token, task_desc["nodes"], task_desc["cores"], task_desc["walltime"],
                    task_desc["workdir"])
    logging.info("oar prefix: %s", oarsub_prefix)
    try:
        command = oarsub_prefix + " '" + command  + "'"
        logging.critical("launching command: %s", command)
        ret_tuple = ssh_client.exec_command(command)
        return ret_tuple[1].read()
    except Exception as excpt:
        logging.critical("fail to execute command '%s':  %s'", command, excpt)
        raise ValueError("fail to execute command '%s':  %s'", command, excpt)

def run_on_frontal(ssh_client, command):
    """ run on the frontal the given command ie without oarsub"""
    try:
        logging.critical("launching command: %s", command)
        ret_tuple = ssh_client.exec_command(command)
        return ret_tuple[1].read()
    except Exception as excpt:
        logging.critical("fail to execute command '%s':  %s'", command, excpt)
        raise ValueError("fail to execute command '%s':  %s'", command, excpt)

def get_job_status(ssh_client, token, log_dir):
    """ get the job id from the token
        the id can be either a pid or a oar id

    :param token: the token that was assigned when launging the job
    :type token: string (uuid)
    :return: the id
    :type: integer
    """
    command = "ws_cluster/bin/wsc_get_status.py --logdir {} --token {}".format(log_dir, token)
    logging.critical("asking for status: command=%s", command)
    ret = run_on_frontal(ssh_client, command)
    return ret

def test_connect_luke(cluster):
    """basic testing of connect with cluster config

    :param cluster: information about the cluster (hostname, username, password)
    :type cluster: dictionnary (usefull keys: "hostname", "username", "password")
    """
    ssh = connect_with_sshconfig({"hostname" : cluster["clstrHostName"], "username": cluster["clstrUserName"]})
    ret_tuple = ssh.exec_command("pwd")
    ret_stdout = ret_tuple[1].read()
    print "ret_stdout: ", ret_stdout
    assert "/home/"+cluster["clstrUserName"] in ret_stdout

def test_run_on_frontal(cluster):
    """basic testing of connect with cluster config

    :param cluster: information about the cluster (hostname, username, password)
    :type cluster: dictionnary (usefull keys: "hostname", "username", "password")
    """
    ssh = connect_with_sshconfig({"hostname" : cluster["clstrHostName"], "username": cluster["clstrUserName"]})
    out = run_on_frontal(ssh, "pwd")
    print "out: ", out
    assert "/home/"+cluster["clstrUserName"] in  out

if __name__ == "__main__":
    # doing basic test
    print "run test_connect on luke"
    test_connect_luke(parametres.configdic)
    print "run test_run_on_server on luke"
    test_run_on_frontal(parametres.configdic)
