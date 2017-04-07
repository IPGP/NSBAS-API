#! /usr/bin/env python

import json
import time
import os
import sys
import re

#from datetime import date
import argparse
import subprocess
import shlex
import logging
import pdb
import shutil

# Parameters on the cluster scripts side
import wsc_parametres

def get_file_type(filename):
    """ check the file type of the file

    :param filename: the input filename to check
    :type filename: str
    :return: the type of the filename
    :rtype: str
    """
    with os.popen("/usr/bin/file -bi " + filename) as f:
        ret = f.read()
        f.close()
    return  ret

############### Unzip

def unzip_files(directory):
        """
        Unzip all files in directory that ends with .zip
        :param directory: the directory containing the zip files
        :type directory: str
        """

        files = ["{}/{}".format(directory, f) for f in os.listdir(directory)
                      if f.endswith(".zip")]
        FNULL = open(os.devnull, 'w')
        for zfile in files:
            try:
                proc = subprocess.Popen(["unzip", zfile, "-d", directory],
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = proc.communicate()
                exitcode = proc.returncode
            except OSError:
                raise OSError("unzip command not found")
            if exitcode is not 0:
                raise RuntimeError("zip command failed for file {}.\nExit code={}\nstdout={}\nstderr={}"
                                   .format(zfile, exitcode, out, err))
        FNULL.close()
        logging.info("Data unzipped")

################# Delete zip data

def delete_zip_files(directory):
	"""
	Delete zip files in directory
	:param directory: the directory containing zip files
	:type directory: str
	"""

	files = ["{}/{}".format(directory, f) for f in os.listdir(directory)
                      if f.endswith(".zip")]
        for zfile in files:
            os.remove(zfile)
        logging.info("zip files deleted")

############# Download

def download_data (directory, id_data, email, passwd):
    """
	Download data from PEPS in the defined directory.

    :param directory: the directory containing the zip files
	:param email: email adress to connect to PEPS
	:param passwd: password to connect to PEPS
	:param id_data: the identity of the data to be downloaded in directory
	:type directory: str
	:type email: str
	:type passwd: str
	:type id_data: str
	"""
    #import pdb
    #pdb.set_trace()
    tmpfile="%s/tmp.tmp"%directory
    get_product='curl -s -S -o %s -k -u %s:%s https://peps.cnes.fr/resto/collections/%s/%s/download/?issuerId=peps'%(tmpfile,email,passwd,collection,id_data)
    logging.debug(get_product)
    ret = subprocess.check_call(shlex.split(get_product))
    logging.info("product saved")
    file_format = get_file_type(tmpfile)
    if "zip" not in file_format.lower():
        logging.error("error while fetching file %s", tmpfile)
        raise RuntimeError("error while fetching file {}/{}".format(directory, id_data))
    logging.info("file type ok (zip), continuating")
    logging.info("moving  from {} to {}".format(tmpfile, "%s/%s.zip"%(directory,id_data)))
    target_name = "{}/{}.zip".format(directory, id_data)
    os.rename(tmpfile,target_name)
    logging.info("product saved as: %s: %d", target_name, os.path.getsize(target_name))
    try:
        unzip_files (directory)
    except RuntimeError as excpt:
        logging.error("cannot unzip file: %s", str(excpt))
        raise RuntimeError("cannot unzip file: {}".format(excpt))
    try:
        delete_zip_files(directory)
    except Exception as excpt:
        raise RuntimeError("unable to unzip file")

	logging.info("Data downloaded")

def move_safes_do_date_dir(directory):
    """for each .SAFE in directory create a directory
    with the correct name ie YYYMMDD and move the safe
    to it

    :param directory: the directory where .SAFE dirs are
    :type directory: str
    """
    for fic in os.listdir(directory):
        if fic.endswith(".SAFE"):
            abs_fic = directory + '/' + fic
            logging.info("dealing with %s", abs_fic)
            m = re.search("_(\d{8})T\d{6}_", fic)
            if m:
                safe_dir = m.groups()[0]
                new_dir =directory + '/' + safe_dir
                os.makedirs(new_dir)
                logging.info("renaming %s -> %s", abs_fic, new_dir)
                shutil.move(abs_fic, new_dir)


################# Main function

if __name__ == "__main__":


    #=====================
    # Parse arguments
    #=====================

    parser = argparse.ArgumentParser(description="Download data from PEPS ")
    parser.add_argument("-l", type=str, default=None, help="log file. stdout if not set")
    parser.add_argument("-v", type=int, default=3, help="set logging level: 0 critical, 1 error, 2 warning, 3 info, 4 debug, default=info")
    parser.add_argument("-wd",type=str,  help="the workingDir where to download data")
    parser.add_argument("-token",type=str, default = "notoken", help="a kind of id provided when called")
    parser.add_argument("Id_data",type=str, metavar='images ids', nargs='+',
                        help="Id of the selected data to be downloaded")
    args = parser.parse_args()

    logging_translate = [logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
    #=====================
    # Define parameters
    #=====================

    collection=wsc_parametres.wsc_config['PepsCollection']
    email=wsc_parametres.wsc_config['PepsEmailLogin']
    passwd=wsc_parametres.wsc_config['PepsPassWord']
    log_level = logging_translate[args.v]
    if args.l is not None:
        logging.basicConfig(filename=args.l, level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=log_level)
    logging.info("id={} token={}".format(os.getpid(), args.token))
    #=====================
    # Call functions
    #=====================
    # checking workdir exist
    err = 0
    if not os.path.exists(args.wd):
        try:
           os.makedirs(args.wd)
           os.chdir(args.wd)
        except Exception as e:
            logging.critical("cannot create image working dir %s, ABORTING", args.wd)
            sys.exit(1)
    else:
        logging.info("uploading image dir in %s", args.wd)
    for img in args.Id_data:
        try:
            logging.info("processing image %s", img)
            download_data (args.wd, img, email, passwd)
        except Exception as excpt:
           logging.error("failure when processing image %s, keep going", img)
           err += 1
    move_safes_do_date_dir(args.wd)
    sys.exit(err)

