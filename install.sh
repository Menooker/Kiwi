set -ex
if [ -z "$1" ]
then
      echo "Expecting an argument of install path"
      exit 1
fi
if [ -z "$2" ]
then
      echo "Expecting an argument of shared state path"
      exit 1
fi

python3 -m pip install psutil
KIWI_INSTALL_PATH=$1/lib/kiwi/
mkdir -p $KIWI_INSTALL_PATH
gcc -O2 c/housekeeper.c -DKIWI_INSTALL_PATH="\"$KIWI_INSTALL_PATH\"" -o $KIWI_INSTALL_PATH/housekeeper
chmod +s $KIWI_INSTALL_PATH/housekeeper

cp ./ssh_checker.py $KIWI_INSTALL_PATH
cp ./housekeeper.py $KIWI_INSTALL_PATH
cp ./kiwi.py $KIWI_INSTALL_PATH
cp ./kiwi_manage.py $KIWI_INSTALL_PATH

chmod +x $KIWI_INSTALL_PATH/ssh_checker.py
chmod +x $KIWI_INSTALL_PATH/kiwi.py
chmod +x $KIWI_INSTALL_PATH/kiwi_manage.py

echo "$2" > $KIWI_INSTALL_PATH/checker_config.txt
echo "$2" > $KIWI_INSTALL_PATH/local_config.txt

chmod a+r -R $KIWI_INSTALL_PATH

rm -f $KIWI_INSTALL_PATH/../../bin/kiwi
rm -f $KIWI_INSTALL_PATH/../../bin/kiwi-manage
ln -s $KIWI_INSTALL_PATH/kiwi.py $KIWI_INSTALL_PATH/../../bin/kiwi
ln -s $KIWI_INSTALL_PATH/kiwi_manage.py $KIWI_INSTALL_PATH/../../bin/kiwi-manage
