#!/bin/bash
set -e
set -o pipefail
set -u
set -v

MINICONDA_PATH="/root/miniconda3"

conda build -q conda-recipe
if [ $? != 0 ]; then
	echo failed to build
	exit 1
fi

#This seems to be needed for "artifacts" to work.
if [ "$BRANCH" != 'master'  ] && [ "$UPLOAD_NON_MASTER" == false ];
then
  	echo "
Skiping upload because this is not master and you have not
set the UPLOAD_NON_MASTER variable."
	exit 0
fi

echo "Uploading package to the NNPDF server"
KEY=$( mktemp )
#This is defined in the Gitlab variables, under the Settings Menu.
echo "$NNPDF_SSH_KEY" | base64 --decode > "$KEY"

scp -i "$KEY" -o StrictHostKeyChecking=no\
    "$MINICONDA_PATH"/conda-bld/linux-64/*.tar.bz2 \
    dummy@packages.nnpdf.science:~/packages/conda/linux-64

if [ $? == 0 ]; then
	echo "Upload suceeded"
else
	echo "Upload failed"
	exit 1
fi
