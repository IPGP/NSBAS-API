#!/bin/bash
# This script geocodes interferograms, 
# generates jpg versions of .unw and .unw.rsc interferograms contained in the current directory 
# and publishes them onto irods for sharing with the user
# finally cleans up the computing directory
# To fit with the specs, files must be made available in /<davrodsBaseDir>/v<apiVersion>/services/ws_dnldResult/<processToken>/<fileName>
# If several interferograms must be published, says one per subswath, this script must be called for each
#
# Note : it could be usefull to return the content of the publishing directory
#
# Arguments :
# $1 : width of the thumbnail, low resolution version of the interferogram, in px
# $2 : target directory to be created on irods, typically /<davrodsBaseDir>/v<apiVersion>/services/ws_dnldResult/<processToken>
#
# Naming convention
# The full resolution jpeg version is named like the .unw native file but with the .jpg extension
# The low resolution jpeg version is named like the full resolution one but with the "th_" prefix
#
# We suppose the local dir set by our caller is the one where the geocoded interferogram and its jpeg versions must be generated.

thwidth=$1
publishDir=$2
$workdir=pwd

# Let's geocode this subswath interferogram
nsb_make_geomaptrans.py nsbas.proc 4

# Let's get the name of the interferogram
unwnames=*.unw
#We suppose only the last directory level has to be created
imkdir $publishDir

# Creons les versions jpeg a cote des versions natives puis envoyons-les sur irods
# La boucle n'est sans doute pas indispensable
for unwname in $unwnames
do
    jpgname=`basename $unwname .unw`.jpg
    thname="th_"$jpgname
    echo $unwname $jpgname $thname
	wsc_unw2jpg.py -i $unwname -s $jpgname -b p -C 95 
    wsc_unw2jpg.py -i $unwname -s $thname -w $thwidth -b p -C 95 
#    touch $jpgname $thname
    iput $jpgname $thname $publishDir 
done

cd .. 
# To be activated to destroy the directory we created the files in
#rm -rf $workdir

exit 0
