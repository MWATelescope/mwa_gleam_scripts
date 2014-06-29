#!/usr/bin/env bash
echo -------------------- provision.sh --------------------
echo Starting to provision server post script

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

# Web Framework
# TODO

#copy the apache config and restart apache
sudo cp /mnt/MWA_Tools/eorlive_v2/server_configs/eorlive_dev.conf /etc/apache2/sites-available/
sudo rm /etc/apache2/sites-enabled/*.conf
sudo ln -s /etc/apache2/sites-available/eorlive_dev.conf /etc/apache2/sites-enabled/eorlive_dev.conf
sudo service apache2 restart
