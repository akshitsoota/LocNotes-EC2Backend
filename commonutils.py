# Import MySQL Connector
import mysql.connector as mysql
# File I/O
import os.path
# Datetime functionality
from datetime import datetime
# Import system and getopt
import sys, getopt

# Logger function
def log(output):
	if ( "logger_output" not in env_var ) or ( "logger_output" in env_var and env_var["logger_output"] == "true" ):
		# By default, we will output
		print("{0}: {1}".format(str(datetime.now()), output))

# Function that reads from a given configuration file and returns True if the read was successful
def read_from_config(file_name="config"):
	if not os.path.isfile(file_name):
		log("Configuration file doesn't exist {0}".format(file_name))
		exit(EXIT_CODE_FAIL_CONFIG_FILE_READ)
	# Initialize the global
	global env_var
	env_var = {}
	# File exists; Read the file
	try:
		with open(file_name, "r") as file:
			for line in file:
				# Iterating over each of the lines in the file
				if len(line.strip()) == 0 or line.strip()[0] == "#": continue
				# Split the line
				splitted = line.strip().split("=")
				key, value = splitted[0], "=".join(splitted[1:])
				# Add it to the environment variables
				log("Adding environment_variables[{0}] = {1}".format(key, value))
				env_var[key] = value
	except IOError as exception:
		log("Failed to open the configuration file {0}".format(file_name))
		exit(EXIT_CODE_FAIL_CONFIG_FILE_READ)
	# We were successful, so:
	log("Successfully read the configuration file {0}".format(file_name))
	return True

# Attempts to connect to MySQL and returns the MySQL connection
def connect_to_mysql():
	mysql_conn = None
	try:
		mysql_conn = mysql.connect(host=env_var["mysql_db.hostname"], 
									user=env_var["mysql_db.user"], 
									password=env_var["mysql_db.pass"].decode("base64"),
									database=env_var["mysql_db.dbname"],
									buffered=True)
		log("Generated one MySQL connection with username {0} at {1}".format(env_var["mysql_db.user"], env_var["mysql_db.hostname"]))
	except mysql.Error as exception:
		log("Failed to connect to the MySQL database with username {0} at {1}".format(env_var["mysql_db.user"], env_var["mysql_db.hostname"]))
		exit(EXIT_CODE_FAIL_CONNECT_MYSQL_DB)
	# Return the connection
	return mysql_conn

# Closes a MySQL Connection
def close_mysql_connection(mysql_connection):
	mysql_connection.close()
	log("Closed MySQL connection with server {0}".format(env_var["mysql_db.hostname"]))