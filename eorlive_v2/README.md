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

### Deployment ###

TBA
