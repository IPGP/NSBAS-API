#!/bin/bash
# This script generates jpg versions of .unw and .unw.rsc interferograms contained in a directory 
# and publishes them onto irods for sharing with the user
# finally cleans up the origin directory computing directory
# To fit with the specs, files must be made available in /<davrodsBaseDir>/v1.0/services/ws_dnldResult/<processToken>/<fileName>
# If several interferograms must be published, says one per subswath, this script must be called for each
#
# Arguments :
# $1 : directory where are available .unw and .unw.rsc files
# $2 : target directory to be created on irods, typically /<davrodsBaseDir>/v1.0/services/ws_dnldResult/<processToken>
#
# Naming convention
# The full resolution jpeg version is named like the .unw native file but with the .jpg extension
# The low resolution jpeg version is named like the full resolution one but with the "th_" prefix

workdir=$1
irods_dir=$2
unwnames=$workdir/*.unw
thwidth=300

cd $workdir 
imkdir $irods_dir ; 

# Creons les versions jpeg a cote des versions natives puis envoyons-les sur irods
for unwname in $unwnames
do
    jpgname=`basename $unwname .unw`.jpg
    thname="th_"$jpgname
    echo $unwname $jpgname $thname
	wsc_unw2jpg.py -i $jpgname -s $workdir 
    wsc_unw2jpg.py -i $thname -s $workdir -w $thwidth 
    iput $jpgname $irods_dir 
done

cd .. 
rm -rf $workdir


exit 0
