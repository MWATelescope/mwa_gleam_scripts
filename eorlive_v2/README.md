## EORLive Web Application V2 ##

This is a successor of the old EORLive web application. The old EORLive code base is a dependency of this. Please do not delete or move it.

### Development Set Up ###

To run the server locally. Install the following on your computer. Do not use a Windows based machine. Use OS X or Linux.

- VirtualBox 4.3.8+
- Vagrant 1.5+

Then simply run this command in MWA_Tools/eorlive_v2 directory

```
vagrant up
```

After a series of provisioning executions, you will have the server running. Type 192.168.56.107 in your browser and you will see the eorlive website. I recommend adding something like the following line to /etc/hosts.

```
192.168.56.107  local.eorlive.org
```

So you can start typing something that resembles a real web site address instead of the ip address. Easier to remember. Up to you.

To ssh into the instance, use the following command.
```
vagrant ssh

```

Vagrant supports lots of commands. Use `vagrant --help` for more details. The most useful would be `suspend` and `resume`.

### DB Migration ###

Database migration is managed by alembic (flask extention is called Flask-Migration). To create a new migration script, use the following command.
```
python -m eorlive db revision -m "create user table"
```
To run the migration to make the database schema up to date, use
```
python -m eorlive db upgrade head
```
(Make sure you 'sourced' the virtualenv if it runs in virtualenv)

### Deployment ###

Right now, I'm using rsync commend to copy files to instances.

For example,

```
rsync -avL --progress --exclude='.git/' -e "ssh -i <path to EoR.pem file>" ./MWA_Tools ubuntu@<hostname>:
```

This can be improved later.

### Making Instances ###

Take a look at the provision.sh for basic set up. Modify the commends for the paths specific to the instance where it's being installed.

For any cronjobs that need virtualenv, make separate shell scripts with 'source /opt/pyvenv/eorlive/bin/activate' commend and execute them in crontab.

Recommended MWA_Tools install path is /home/ubuntu for any EC2 ubuntu images.

Make sure to set the envorinmental variable EOR_ENV to either 'prod' or 'stage'.
```
export EOR_ENV=stage
echo 'EOR_ENV=stage' >> /etc/environment

```
