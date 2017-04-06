#! /usr/bin/env python

import json
import time
import os,sys
#from datetime import date
import argparse
import subprocess
import logging


################### Logging  ############################

logger = logging.getLogger()
ch = logging.StreamHandler()
logger.setLevel(logging.DEBUG)
ch.setLevel(logging.DEBUG)
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(ch)

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
        logger.info("Data unzipped")
        
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
	      #try:
		  #proc = subprocess.Popen([os.remove(zfile), directory],
					  #stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		  #out, err = proc.communicate()
		  #exitcode = proc.returncode
	      #except OSError:
		  #raise OSError("command not found")
	      #if exitcode is not 0:
		  #raise RuntimeError("zip command failed for file {}.\nExit code={}\nstdout={}\nstderr={}"
                                   #.format(zfile, exitcode, out, err))
        logger.info("zip files deleted")
        
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
	
	# Filter catalog result

	tmpfile="%s/tmp.tmp"%directory
	get_product='curl -o %s -k -u %s:%s https://peps.cnes.fr/resto/collections/%s/%s/download/?issuerId=peps'%(tmpfile,email,passwd,collection,id_data)
	print get_product
	os.system(get_product)

	with open(tmpfile) as f_tmp:
                   try:
                       tmp_data=json.load(f_tmp)
                       print "Result is a text file"
                       print tmp_data
                       sys.exit(-1)
                   except ValueError:
                       pass
	os.rename("%s"%tmpfile,"%s/%s.zip"%(directory,id_data))
	print "product saved as : %s/%s.zip"%(directory,id_data)
		
	unzip_files (directory)
	delete_zip_files(directory)
		
	logger.info("Data downloaded")


################# Main function

if __name__ == "__main__":
	
   
    #=====================
    # Parse arguments
    #=====================
    
    parser = argparse.ArgumentParser(description="Download data from PEPS ")
    parser.add_argument("Id_data",type=str,  help="Id of the selected data to be downloaded")
    parser.add_argument("workingDir",type=str,  help="the workingDir where to download data")
    args = parser.parse_args()
    
    #=====================
    # Define parameters
    #=====================
  
    collection="S1"
    email="ccccc@jjj"
    passwd="xxxxx"
    
    #=====================
    # Call functions
    #=====================
    
    download_data (args.workingDir, args.Id_data, email, passwd)
    
    
    
    
    
    
    
