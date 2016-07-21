'''

AUTHOR:
  Akshit (Axe) Soota

VERSIONS:
1.0 - Initial Release

POSSIBLE EXIT CODES:
0 - No problems
1 - Invalid command line arguments
100 - Problem reading configuration file
101 - MySQL Connection Error
102 - Unable to create the tables

'''

VERSION = '1.0'

# Import MySQL Connector
import mysql.connector as mysql
# Import system and getopt
import sys, getopt

# Some constants
EXIT_CODE_SUCCESS = 0
EXIT_CODE_INVALID_COMMAND_LINE_ARGS = 1
EXIT_CODE_UNKNOWN_FAILURE = 5
EXIT_CODE_FAIL_CONFIG_FILE_READ = 100
EXIT_CODE_FAIL_CONNECT_MYSQL_DB = 101
EXIT_CODE_FAIL_CRATE_TABLE = 102

FILE_COMMON_UTILS = "commonutils.py"

# DROP COMMANDS
DROP_TABLES = {}
DROP_TABLES["s3ids"] = "DROP TABLE IF EXISTS `s3ids`"
DROP_TABLES["logtable"] = "DROP TABLE IF EXISTS `{0}`"
DROP_TABLES["users"] = "DROP TABLE IF EXISTS `users`"

# SELECT COMMANDS
TABLE_SELECT_QUERIES = {}
TABLE_SELECT_QUERIES["users_table_check"] = (
	"SELECT COUNT(*) "
	"FROM information_schema.tables "
	"WHERE table_schema = %(dbname)s "
	"AND table_name = %(tablename)s"
	)
TABLE_SELECT_QUERIES["userlogtable"] = (
	"SELECT `log_table_name`"
	" FROM `users`")

# Table definitions
TABLES = {}
TABLES["users"] = (
	"CREATE TABLE `users` ("
	" `full_name` VARCHAR(50) NOT NULL,"
	" `email` VARCHAR(255) NOT NULL,"
	" `username` VARCHAR(255) NOT NULL,"
	" `password` VARCHAR(128) NOT NULL,"
	" `password_salt` VARCHAR(20) NOT NULL,"
	" `login_hash_granted` VARCHAR(128) NOT NULL,"
	" `login_hash_expiry` INT(11) UNSIGNED NOT NULL,"
	" `log_table_name` VARCHAR(64) NOT NULL,"
	" `account_creation_time` INT(11) UNSIGNED NOT NULL"
	")")
TABLES["s3ids"] = (
	"CREATE TABLE `s3ids` ("
	" `assoclogid` VARCHAR(128) NOT NULL,"
	" `uniques3id` VARCHAR(128) NOT NULL,"
	" `amazons3url` TEXT NOT NULL,"
	" `imgheight` INT NOT NULL,"
	" `imgwidth` INT NOT NULL,"
	" `latlng` VARCHAR(100) NOT NULL,"
	" `addedtime` INT(11) UNSIGNED NOT NULL"
	")")

# Global Variables
env_var = {}

# Functions

# Create basic tables
def create_tables(connection):
	# Delete all user log tables
	cursor = connection.cursor(buffered = False) # Fetch the cursor from the connection
	cursor.execute(TABLE_SELECT_QUERIES["users_table_check"], {
		"dbname": env_var["mysql_db.dbname"],
		"tablename": "users"
	})
	for tup in cursor:
		pass # We've to go through all the rows as we've disabled buffering for this buffer before we can close it
	row_count = cursor.rowcount # Fetch the number of rows we've got
	# Counting the number of tables we've got
	cursor.close() # Close the cursor

	if row_count > 0:
		# If we've got a table to query, then:
		cursor = connection.cursor()
		tables_to_be_deleted = [] # Array of tables to be delete
		cursor.execute(TABLE_SELECT_QUERIES["userlogtable"]) # Fetch all the log table names
		for log_table_name, in cursor:
			tables_to_be_deleted.append(log_table_name)
		cursor.close() # Close this cursor

		cursor = connection.cursor() # Fetch the cursor from the connection
		for table_name in tables_to_be_deleted:
			log("Dropping user log table '{0}'".format(table_name))
			cursor.execute(DROP_TABLES["logtable"].format(table_name))
		cursor.close() # Close the cursor
		# Log it
		if len(tables_to_be_deleted) > 0:
			log("Dropped all user log tables successfully")

	# Drop the tables if they exist
	cursor = connection.cursor() # Fetch the cursor from the connection
	for name, cmd in DROP_TABLES.iteritems():
		# Skip "logtable" as that is for each user
		if name == "logtable": continue
		# Else, proceed to drop it
		try:
			log("Attempting to drop table '{0}' if it exists".format(name))
			cursor.execute(cmd)
			log("Command to drop table '{0}' was successful".format(name))
		except mysql.Error as exception:
			log("Failed to drop table '{0}'".format(name))
	# Create the table now
	for name, cmd in TABLES.iteritems():
		try:
			log("Creating table '{0}'".format(name))
			cursor.execute(cmd)
			log("Successfully created the table '{0}'".format(name))
		except mysql.Error as exception:
			log("Failed to create the table '{0}'".format(name))
			exit(EXIT_CODE_FAIL_CRATE_TABLE)
	# Close the cursor
	cursor.close()
	# Return
	log("Successfully created all tables")
	return True

# Usage
def usage():
	print("python setup.py")
	print("  This script is run on an EC2 instance and is used to setup a Amazon RDS instance")
	print("  to be used by LocNotes - the location logs application.")
	print("\n")
	print("Usage: python setup.py [-h|--help] [--config=<config_file_path>]")
	print("\n")
	print("  --help\tTo have the usage of this script printed")
	print("  --config\tPath to the configuration file from where the configuration for this script will be picked up")
	print("\t\tDefault is picked up from the file \"config\" in the same directory as the running script.")
	print("\n")

# Main function
def main():
	# Some variables
	config_file_path = "config"
	if not len(sys.argv) == 1:
		# We've got some arguments to parse
		try:
			opts, args = getopt.getopt(sys.argv[1:], "h", ["help", "config="])
		except getopt.GetoptError as err:
			print str(err)
			usage()
			exit(EXIT_CODE_INVALID_COMMAND_LINE_ARGS)
		# Now parse
		for opt, arg in opts:
			if opt in ("-h", "--help"):
				usage()
				exit()
			elif opt in ("--config"):
				config_file_path = arg
			else:
				print("Invalid option(s)\n")
				usage()
				exit()
	# Read the configuration from the file
	if not read_from_config(config_file_path): exit(EXIT_CODE_UNKNOWN_FAILURE)
	# Print LocNotes Logo
	log("  _                _   _       _            ")
	log(" | |              | \ | |     | |           ")
	log(" | |     ___   ___|  \| | ___ | |_ ___  ___ ")
	log(" | |    / _ \ / __| . ` |/ _ \| __/ _ \/ __|")
	log(" | |___| (_) | (__| |\  | (_) | ||  __/\__ \\")
	log(" |______\___/ \___|_| \_|\___/ \__\___||___/")
	log("")
	# Now, create the MySQL Connection
	mysql_connection = connect_to_mysql()
	# Create the tables
	create_tables(mysql_connection)
	# Close the connection
	mysql_connection.commit() # Commit all the changes before closing the MySQL connection
	close_mysql_connection(mysql_connection)
	# Exit the application
	log("Application successfully finished")

# Initialization block
if __name__ == "__main__":
	# Import the commonutils.py file
	execfile(FILE_COMMON_UTILS)
	# Call the main
	if not len(sys.argv) == 1 :
		log("Application started with arguments: {0}".format(" ".join(sys.argv[1:])))
	else:
		log("Application started")
	main()