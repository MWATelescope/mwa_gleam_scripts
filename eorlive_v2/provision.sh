#!/usr/bin/env bash
echo -------------------- provision.sh --------------------
echo Starting to provision server post script

MWA_PATH="/mnt/MWA_Tools"

# Create swapfile of 1GB with block size 1MB
/bin/dd if=/dev/zero of=/swapfile bs=1024 count=1048576
# Set up the swap file and enable
mkswap /swapfile
swapon /swapfile
echo '/swapfile   none    swap    sw    0   0' >> /etc/fstab

# Install global dependencies
sudo apt-get update -y
sudo apt-get -y install openssh-server libfreetype6-dev build-essential postgresql-9.3 postgresql-server-dev-9.3 postgresql-client apache2 python-pip python-dev php5 libapache2-mod-php5 php5-mcrypt pkg-config gfortran libopenblas-dev liblapack-dev
sudo pip install virtualenv

# Set up python virtual environment and install mwapy dependencies
virtualenv /opt/pyvenv/eorlive
source /opt/pyvenv/eorlive/bin/activate
pip install numpy
pip install scipy
pip install psycopg2 matplotlib ephem pyfits pytz
pip install pywcs

# PostgreSQL
# - set password so web server can access as postgres user
# THIS IS NOT A GOOD IDEA FOR PROD, BUT FOR LOCAL IT'S FINE
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
sudo -u postgres createdb -E UTF8 -T template0 --locale=en_US.utf8 eor

# Web Framework
sudo apt-get -y install libapache2-mod-wsgi
pip install -r $MWA_PATH/eorlive_v2/requirements.txt
# - Set Web Environment
export EOR_ENV=dev
echo 'EOR_ENV=dev' >> /etc/environment
export PYTHONPATH="/mnt/MWA_Tools:/mnt/MWA_Tools/configs:/mnt/MWA_Tools/scripts"
echo 'PYTHONPATH="/mnt/MWA_Tools:/mnt/MWA_Tools/configs:/mnt/MWA_Tools/scripts"' >> /etc/environment
# DB
cd $MWA_PATH/eorlive_v2/
python -m eorlive db upgrade head

#copy the apache config and restart apache
sudo cp $MWA_PATH/eorlive_v2/server_configs/eorlive_dev.conf /etc/apache2/sites-available/
sudo rm /etc/apache2/sites-enabled/*.conf
sudo ln -s /etc/apache2/sites-available/eorlive_dev.conf /etc/apache2/sites-enabled/eorlive_dev.conf
sudo service apache2 restart

#Place for images
mkdir /var/beam_images
chmod -R 777 /var/beam_images

#Build mwapy
$MWA_PATH/make_MWA_Tools.sh
cp $MWA_PATH/configs/mwa.conf /usr/local/etc
cd $MWA_PATH
python setup.py install
#$MWA_PATH/scripts/change_db.py -g mit
