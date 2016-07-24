# LocNotes - Smarter Travel Logs

![Python 2.7.10](https://img.shields.io/badge/python-2.7.10-brightgreen.svg)
![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)

This is the server component for the application, LocNotes, which is posted [here](https://github.com/akshitsoota/LocNotes).
This web server is completely written in Python and is meant to be run on an Amazon Web Services Elastic Cloud Compute (AWS EC2) Server.

The entire documentation provides information pertaining to an AWS EC2 instance running Amazon Linux AMI 2016.03.3.

### How to setup the backend and have it running?

* SSH into your AWS EC2 instance using a command similar to:

```shell
ssh -i <path-to-pem-file> ec2-user@<public-dns-for-ec2-instance>
```

* If you don't have Git installed on this EC2 instance, run the command: `sudo yum install git`
* If you don't have Python installed on this EC2 instance, run the command: `sudo yum install python`
* If you don't have MySQL Connector for Python installed on this EC2 instance (which you probably don't by default), run the following commands:

```bash
git clone https://github.com/mysql/mysql-connector-python.git
cd mysql-connector-python/
python ./setup.py build
sudo python ./setup.py install
cd ..
```

I would recommend you leave the MySQL Connector for Python folder around. However, if you wish to delete it, run the command: `sudo rm -rf mysql-connector-python/`

* Next, create a new directory and change your current directory to it using a command similar to:

```bash
mkdir <your-directory-name>
cd <your-directory-name>
```

* Clone this Git Repo into that directory with the command:

```bash
git clone git@github.com:akshitsoota/LocNotes-EC2Backend.git .
```

* Rename `config_template` to `config` with the command:

```bash
mv config_template config
```

* Edit `config` using your favorite text editor and fill in atleast all the required fields and uncomment those lines by removing the leading
pound sign followed by the space.
* Next, run the following command to setup your MySQL Database: `python setup.py`
* If it succeeds without any problems, fire up the server with the command: `sudo python server.py`

A few important points to note:

* If you fail to fire up the server, try running the server script as `root`
* Firing up the server as a foreground process blocks you from interacting with the terminal until you kill the server with 
<kbd>Ctrl</kbd>+<kbd>C</kbd>/<kbd>Control</kbd>+<kbd>C</kbd>
* If you plan to log out of your SSH session, `tmux` is a preferred way of running this server as a background process. You could do the following steps:

```bash
tmux
[sudo] python server.py &
```

And then hit <kbd>Ctrl</kbd>+<kbd>B</kbd> then <kbd>D</kbd>/<kbd>Control</kbd>+<kbd>B</kbd> then <kbd>D</kbd> to **detach** from the `tmux` session. 
Use the command `tmux attach` to attach back to your session. If you have multiple sessions, you can run `tmux ls` to list them all.

* In case you want to kill the server but don't know/forgot the process ID of the Python server that is running, use the following command:

```bash
[sudo] netstat -tulnp | grep :80
```

You should see something like:

```
tcp        0      0 0.0.0.0:80                  0.0.0.0:*                   LISTEN      32087/python
```

In this case, to kill the server, you would run: `[sudo] kill 32087`

Or, if you prefer those one-liners, I hacked one thanks to [this StackOverflow answer](http://stackoverflow.com/a/4248254/705471).
You could try:

```bash
sudo kill $(sudo lsof -i tcp:80 | tail -n +2 | awk '{print $2}')
```

### Server Setup and Server Help

You can run: `python setup.py -h` to view the help for the Server Setup script.

```
python setup.py
  This script is run on an EC2 instance and is used to setup a Amazon RDS instance
  to be used by LocNotes - the location logs application.

Usage: python setup.py [-h|--help] [--config=<config_file_path>]

  --help	  To have the usage of this script printed
  --config	  Path to the configuration file from where the configuration for this script will be picked up
              Default is picked up from the file "config" in the same directory as the running script.
```

You can also run: `python server.py -h` to view help for the Server script.

```
[sudo] python server.py
  This script is run on an EC2 instance and is used to start up a Python server on
  the EC2 instance.

Usage: [sudo] python server.py [-h|--help] [--config=<config_file_path>] [--hostname=<host_name>] [--port=<server_port>]

  --help	  To have the usage of this script printed
  --config	  Path to the configuration file from where the configuration for this script will be picked up.
              Default is picked up from the file "config" in the same directory as the running script.
  --hostname  The hostname the server should run on.
              Default host that the server will run on is 0.0.0.0. This makes the server accessible over the internet
              provided the firewall settings for the EC2 instance are configured to allow so.
  --port	  The port that the server should run on.
              The default port is 80 to allow TCP and HTTP connections from web browsers.
```

### Configuration File

Unless otherwise stated in the command-line arguments, the server and the server setup scrips pickup their configuration from the `config`
file placed in the same directory as the scripts themselves.

**Required fields**:

* **mysql_db.hostname**: The MySQL Hostname which the server would connect to save/fetch records
* **mysql_db.user**: The username with which the server would connect to the MySQL database
* **mysql_db.pass**: Base64 encoded version of the password with which the server would connect to the MySQL database
* **mysql_db.dbname**: The database name that the server would connect to
* **user.username.minlength**: The minimum number of characters required for a user's username
* **user.password.minlength**: The minimum number of characters required for a user's password
* **user.logintoken.validity**: The maxmium number of seconds a user's login token is valid for
* **user.logintoken.max_duration_renewal**: The maximum number of seconds **before** a user's login token expiry, a user can request for a new login token and be granted one

**Options fields**:

* **logger_output**: Allowed values `true` (default) and `false`. If set to `true` all the logger messages will be printed out to `stdout`

**Sample `config` file**:

```
mysql_db.hostname=
mysql_db.user=
mysql_db.pass=<base64 encoded mysql database password>
mysql_db.dbname=

user.username.minlength=<number of characters required in the username>
user.password.minlength=<number of characters required in the password>
user.logintoken.validity=<seconds each login token is suppose to be valid for>
user.logintoken.max_duration_renewal=<seconds before expiry the token can be renewed>
```

### How are account passwords and login tokens stored?

After taking a cryptography class during my undergraduate studies, exposed me to storing passwords with a password salt and pepper.
A user's password in the database is stored in the following manner:

```
SHA512("<password_salt>" + "<user_password>" + str(<password_pepper>))
```

A password salt is a 20 character random string formed with lowercase, uppercase letters and digits from 0 through 9.
A password pepper is a random integer between 0 and 128. The entire password string is then applied to SHA512.

When a user logs in, a login token is granted to the user which is generated in the following manner:

```
SHA512("<randomized_128_char_string>" + str(<unix_epoch_time>))
```

The randomized 128 character string is formed with ASCII characters, digits from 0 through 9 and punctuation characters.
The UNIX epoch time in a string format is appended to this string and the entire string is then applied to SHA512 to generate the login token.

### Server Endpoints

For a detailed documentation of the server endpoints, visit [list of server endpoints](https://github.com/akshitsoota/LocNotes-EC2Backend/blob/master/endpoints.md)

### Known Issues

* <a name="logintokenissue"></a>The login tokens granted to a user are **not** device specific. This means if *device 1* logs in for the first time, 
a new login token is generated. Then if *device 2* almost immediately logs in, the same old login token is granted to that device. Once the login
token expires, if let's say *device 1* requests for a new one, the old login token and expiry are overwritten, forcing *device 2* to go through
the entire login process again!

**Potential Fix**:

For each device that logs in through a given user, assign a separate **device-specific** login token. 
This would prevent other device(s) to go through the entire login process over again.

* The database setup doesn't alter tables to support emojis in table fields. This results in emojis being lost and shown as `????` in the
LocNotes app after a fresh install and a refresh location logs action or a logout and a refresh location logs action.

**Potential Fix**:

Change character sets used throughout the database and LocNotes application to `utf8mb4`. A good StackOverflow Question to address this problem
can be found [here](http://stackoverflow.com/questions/7814293/how-to-insert-utf-8-mb4-characteremoji-in-ios5-in-mysql).

* Lack of SSL - A few of the server endpoints require `Basic Authentication` to authenticate the user. However, as the server doesn't
currently doesn't support traffic over SSL, the contents of the `Basic Authentication` header are transferred unencrypted over the 
internet. This makes it easy for a man-in-the-middle to sniff off the `Authentication` header, run `base64_decode` and extract the user's
username and login token. This theoretically gives the man-in-the-middle **full** access to the user's location logs and account.

**Potential Fix**:

Spawn a server which listens over port `443` instead of port `80` and have the server serve a self-signed certificate to prove its
identity.
