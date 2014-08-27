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
(Make sure you 'sourced' the virtualenv if it runs in virtualenv and cd into the eorlive_v2 dir first)
```
python -m eorlive db revision -m "create user table"
```
To run the migration to make the database schema up to date, use
```
python -m eorlive db upgrade head
```
For more information and documentation about the migrations, please see Google Alembic and take a look at their docs.

### Command Line User Management ###

For initial user setup and maintenance. Use the instructions below.

To create a admin user.
```
python -m eorlive user create_admin -n <name> -e <email> -u <username> -p <password>
```
To reset user password
```
python -m eorlive user reset_password -u <username> -p <password>
```
To set admin level (0 for regular user and 1 for admin user)
```
python -m eorlive user set_admin_level -u <username> -a <admin_level>
```

### Deployment ###

Right now, we're simply using rsync commend to copy files to target instances.

For example,

```
rsync -avL --progress --exclude='.git/' -e "ssh -i <path to EoR.pem file>" ./MWA_Tools ubuntu@<hostname>:
```

When server side changes had been made, it might be necessary to reset the apache server by using the following command while connected to the server via ssh,
```
sudo service apache2 restart
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

### Front-end Notes ###

The frontend is currently built using Boostrap and jQuery with heavy DOM injections and manipulation.
It might be a good idea to use Jinja (Flask templating engine) and partial templating for mark ups (or converting the whole thing to an Angular app).
Overall, there is a lot of room for improvement in the front end. Features are isolated into separate javascript files. See static/js directory.
To change order or placements of widgets, one can just move the respetable div with id=id_of_feature in the templates/index.html.

### Back-end Notes ###

- **Scripts** - see eorlive/scripts directory where some important scripts are stored. Readme file in that directory provides explanation to each script.
- **Apache Configs** - eorlive/server_configs has apache server configs. They are all for Apache 2.4, and they won't work in Apache 2.2 because of rules have changed. When these files are updated, copy them to instances' apache2 config dir.
- **Cronjob** - see eorlive/server_configs/crontab to get some hint on how to set up cron jobs for image creation and graph data fetching.
