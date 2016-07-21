'''

AUTHOR:
  Akshit (Axe) Soota

VERSIONS:
1.0 - Initial Release

COMMENTS:
--> To kill the server, press Ctrl+C on a Windows machine/Control+C on a Mac machine
--> Recommended to run this server if you plan to exit the SSH session:
1) Log into your EC2 server via SSH
2) Run: sudo yum install tmux
3) Run: tmux
4) Run: sudo python server.py &
5) Press Ctrl+B then D on a Windows machine/Control+B then D on a Mac to detach from the tmux session
6) To reconnect to the tmux session, run: tmux attach
7) To list all your tmux sessions, run: tmux ls

'''

VERSION = '1.0'

# Multi-threaded Python Server thanks to:
# - Multi-threaded Server in Python
# --- http://stackoverflow.com/a/14089457/705471
# --- https://pymotw.com/2/BaseHTTPServer/index.html#module-BaseHTTPServer
# - Server handling GET and POST Requesrts
# --- http://joelinoff.com/blog/?p=1658

# Some basic imports
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import threading
# Import MySQL Connector
import mysql.connector as mysql
# Import system and getopt
import sys, getopt
# Import cgi for POST variable parsing
import cgi
# Import some hash functions
import hashlib
# Import random number generator
import random
# Import JSON, String, regular expressions, time
import json, string, re, time

# Create Table Queries
TABLE_CREATE_QUERIES = {}
TABLE_CREATE_QUERIES["new_user"] = (
	"CREATE TABLE `{0}` ("
	" `logid` VARCHAR(128) NOT NULL,"
	" `logtitle` VARCHAR(255) NOT NULL,"
	" `description` TEXT NOT NULL,"
	" `s3ids` TEXT NOT NULL,"
	" `locationnames` TEXT NOT NULL,"
	" `locationpoints` TEXT NOT NULL,"
	" `addeddate` INT(11) UNSIGNED NOT NULL,"
	" `lastupdatetime` INT(11) UNSIGNED NOT NULL"
	")")

# Insert Into Table Queries
TABLE_INSERT_QUERIES = {}
TABLE_INSERT_QUERIES["register"] = (
	"INSERT INTO `users` VALUES "
	"(%(fullname)s, %(emailadd)s, %(username)s, %(saltedpwd)s, %(pwdsalt)s, %(loginhash)s, %(loginhashexpiry)s, %(userlogtablename)s, %(acccreationtime)s)")
TABLE_INSERT_QUERIES["add_s3_image"] = (
	"INSERT INTO `s3ids` VALUES "
	"(%(assoclogid)s, %(uniqueimgid)s, %(amazonimgurl)s, %(imgheight)s, %(imgwidth)s, %(latlng)s, %(addedtime)s)"
	)
TABLE_INSERT_QUERIES["add_location_log"] = (
	"INSERT INTO `{0}` VALUES "
	"(%(logid)s, %(logtitle)s, %(description)s, %(imgids)s, %(locnames)s, %(locpoints)s, %(addeddate)s, %(lastupdatetime)s)"
	)

# Select Queries
TABLE_SELECT_QUERIES = {}
TABLE_SELECT_QUERIES["register_email"] = (
	"SELECT `email` FROM `users` "
	"WHERE `email` = %(emailadd)s")
TABLE_SELECT_QUERIES["register_username"] = (
	"SELECT `username` FROM `users`"
	"WHERE `username` = %(username)s")
TABLE_SELECT_QUERIES["login_pullsalt"] = (
	"SELECT `username`, `password_salt` FROM `users` "
	"WHERE `username` = %(username)s"
	)
TABLE_SELECT_QUERIES["login_get_ltexpiry"] = (
	"SELECT `login_hash_granted`, `login_hash_expiry` FROM `users` "
	"WHERE `username` = %(username)s "
	"AND `password` = %(saltedpwd)s"
	)
TABLE_SELECT_QUERIES["login_test"] = (
	"SELECT `username` FROM `users` "
	"WHERE `username` = %(username)s "
	"AND `password` = %(saltedpwd)s"
	)
TABLE_SELECT_QUERIES["renew_token_validate"] = (
	"SELECT `username` FROM `users` "
	"WHERE `username` = %(username)s "
	"AND `login_hash_granted` = %(logintoken)s "
	"AND `login_hash_expiry` = %(logintokenexpiry)s"
	)
TABLE_SELECT_QUERIES["invalidate_token_check"] = (
	"SELECT `username` FROM `users` "
	"WHERE `username` = %(username)s "
	"AND `login_hash_granted` = %(logintoken)s "
	"AND `login_hash_expiry` = %(logintokenexpiry)s"
	)
TABLE_SELECT_QUERIES["location_logs_validate_auth"] = (
	"SELECT `login_hash_granted`, `login_hash_expiry`, `log_table_name` FROM `users` "
	"WHERE `username` = %(username)s"
	)
TABLE_SELECT_QUERIES["fetch_location_log"] = (
	"SELECT * FROM `{0}` "
	"ORDER BY `addeddate` DESC"
	)
TABLE_SELECT_QUERIES["fetch_s3_image_prop"] = (
	"SELECT * FROM `s3ids` "
	"WHERE `assoclogid` = %(logid)s "
	"AND `uniques3id` = %(s3id)s"
	)

# Update Queries
TABLE_UPDATE_QUERIES = {}
TABLE_UPDATE_QUERIES["login_token_generate"] = (
	"UPDATE `users` "
	"SET `login_hash_granted` = %(logintoken)s, "
	"`login_hash_expiry` = %(logintokenexpiry)s "
	"WHERE `username` = %(username)s "
	"AND `password` = %(saltedpwd)s"
	)
TABLE_UPDATE_QUERIES["renew_token_execute"] = (
	"UPDATE `users` "
	"SET `login_hash_granted` = %(logintoken)s, "
	"`login_hash_expiry` = %(logintokenexpiry)s "
	"WHERE `username` = %(username)s "
	"AND `login_hash_granted` = %(oldlogintoken)s "
	"AND `login_hash_expiry` = %(oldlogintokenexpiry)s"
	)
TABLE_UPDATE_QUERIES["invalidate_token_execute"] = (
	"UPDATE `users` "
	"SET `login_hash_granted` = '', "
	"`login_hash_expiry` = 0 "
	"WHERE `username` = %(username)s "
	"AND `login_hash_granted` = %(logintoken)s "
	"AND `login_hash_expiry` = %(logintokenexpiry)s"
	)

# Delete Queries
TABLE_DELETE_QUERIES = {}
TABLE_DELETE_QUERIES["delete_location_log_entry"] = (
	"DELETE FROM `{0}` "
	"WHERE `logid` = %(logid)s"
	)
TABLE_DELETE_QUERIES["delete_location_log_s3_entries"] = (
	"DELETE FROM `s3ids` "
	"WHERE `assoclogid` = %(logid)s"
	)
TABLE_DELETE_QUERIES["delete_all_location_logs"] = (
	"DELETE FROM `{0}`"
	)

# Some constants
EXIT_CODE_SUCCESS = 0
EXIT_CODE_INVALID_COMMAND_LINE_ARGS = 1
EXIT_CODE_UNKNOWN_FAILURE = 5

FILE_COMMON_UTILS = "commonutils.py"

# Global variables
env_var = {}

class Handler(BaseHTTPRequestHandler):
	def do_GET(self):
		self.send_response(405)
		self.send_header('Content-type', 'text/html')
		self.end_headers()
		self.wfile.write("<h1>405 - Method not allowed</h1>")
		return

	def do_POST(self):
		# Grab all the POST variables
		# CITATION: http://stackoverflow.com/questions/4233218/python-basehttprequesthandler-post-variables
		ctype, pdict = cgi.parse_header(self.headers['content-type'])
		if ctype == 'multipart/form-data':
			postvars = cgi.parse_multipart(self.rfile, pdict)
		elif ctype == 'application/x-www-form-urlencoded':
			length = int(self.headers['content-length'])
			postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
		else:
			postvars = {}

		# Check what matches
		if self.path == "/register":
			# User wants to sign up; Check if we've got all that we need
			if "fullname" in postvars and "emailadd" in postvars and "username" in postvars and "password" in postvars:
				self.userSignup(postvars["fullname"][0], postvars["emailadd"][0], postvars["username"][0], postvars["password"][0])
				return
			else:
				self.returnJSON(403, {"status": "missing_fields"})
		elif self.path == "/login":
			# User wants to login; Check if we've got all that we need
			if "username" in postvars and "password" in postvars:
				self.userLogin(postvars["username"][0], postvars["password"][0])
				return
			else:
				self.returnJSON(403, {"status": "missing_fields"})
		elif self.path == "/renewtoken":
			# User wants to renew their login token; Check if we've got all that we need
			if "username" in postvars and "logintoken" in postvars and "logintokenexpiry" in postvars:
				self.userRenewToken(postvars["username"][0], postvars["logintoken"][0], postvars["logintokenexpiry"][0])
				return
			else:
				self.returnJSON(403, {"status": "missing_fields"})
		elif self.path == "/invalidatetoken":
			# User wants to invalidate their token; Check if we've got all that we need
			if "username" in postvars and "logintoken" in postvars and "logintokenexpiry" in postvars:
				self.userInvalidateToken(postvars["username"][0], postvars["logintoken"][0], postvars["logintokenexpiry"][0])
				return
			else:
				self.returnJSON(403, {"status": "missing_fields"})
		elif self.path == "/fetchlogs":
			# User wants to fetch their location logs; Check the authorization and then proceed
			if self.headers.getheader('Authorization') == None:
				setAuthenticationMissingResponseHeaders()
				return
			else:
				self.fetchAllLocationLogs(self.getUsernameAndLoginToken())
				return
		elif self.path == "/adds3image":
			# User wants to add a S3 Image to our S3 images table; Check the authorization and then proceed
			if self.headers.getheader('Authorization') == None:
				setAuthenticationMissingResponseHeaders()
				return
			else:
				if "locationlogid" in postvars and "imageurl" in postvars and "s3id" in postvars and "width" in postvars and "height" in postvars and "latlng" in postvars:
					self.addAmazonS3Image(self.getUsernameAndLoginToken(), postvars["locationlogid"][0], postvars["imageurl"][0], postvars["s3id"][0], postvars["width"][0], postvars["height"][0], postvars["latlng"][0])
					return
				else:
					self.returnJSON(403, {"status": "missing_fields"})
		elif self.path == "/addlocationlog":
			# User wants to add a location log; Check the authorization and then proceed
			if self.headers.getheader('Authorization') == None:
				setAuthenticationMissingResponseHeaders()
				return
			else:
				if "locationlogid" in postvars and "title" in postvars and "desc" in postvars and "s3ids" in postvars and "locnames" in postvars and "locpoints" in postvars:
					self.addLocationLog(self.getUsernameAndLoginToken(), postvars["locationlogid"][0], postvars["title"][0], postvars["desc"][0], postvars["s3ids"][0], postvars["locnames"][0], postvars["locpoints"][0])
					return
				else:
					self.returnJSON(403, {"status": "missing_fields"})
		elif self.path == "/deletelocationlog":
			# User wants to delete a location log; Check the authorization and then proceed
			if self.headers.getheader('Authorization') == None:
				setAuthenticationMissingResponseHeaders()
				return
			else:
				if "locationlogid" in postvars:
					self.deleteLocationLog(self.getUsernameAndLoginToken(), postvars["locationlogid"][0])
					return
				else:
					self.returnJSON(403, {"status": "missing_fields"})
		elif self.path == "/fetchminiloclogs":
			# User wants to fetch their Location Logs in a minified form (location log ID, added time, updated time); Check authentication then proceed
			if self.headers.getheader('Authorization') == None:
				setAuthenticationMissingResponseHeaders()
				return
			else:
				self.fetchMiniLocationLogs(self.getUsernameAndLoginToken())
				return
		elif self.path == "/deletealllocationlogs":
			# User wants to delete all their Location Logs; Check authentication then proceed
			if self.headers.getheader('Authorization') == None:
				setAuthenticationMissingResponseHeaders()
				return
			else:
				self.deleteAllLocationLogs(self.getUsernameAndLoginToken())
				return
		elif self.path == "/updatelocationlog":
			# TODO: Not implemented in the Application so I've not yet implemented it here
			pass
		elif self.path == "/fetchaccountdetails":
			# TODO: Not implemented in the Application so I've not yet implemented it here
			pass

	# Authentication Functions
	def setAuthenticationMissingResponseHeaders(self):
		self.returnJSON(401, {"status": "unauthorized", "reason": "missing_auth"})

	def getUsernameAndLoginToken(self):
		# Assumption, we've got Basic Authorization Call
		basicCred = self.headers.getheader("Authorization")[6:]
		# Return
		return basicCred.decode("base64").split(":")

	def verifyAuthCredAndGetLogTableName(self, auth):
		# Check if the username and login token is valid
		mysql_connection = connect_to_mysql()
		cursor = mysql_connection.cursor()
		# Query and check
		cursor.execute(TABLE_SELECT_QUERIES["location_logs_validate_auth"], {
			"username": auth[0]
		})
		user_log_table_name = None

		for (cursor_login_hash, cursor_login_token_expiry, cursor_log_table_name) in cursor:
			if cursor_login_hash == auth[1] and int(cursor_login_token_expiry) >= int(time.time()):
				user_log_table_name = cursor_log_table_name
		# Close the cursor
		cursor.close()
		# Close the MySQL Connection
		close_mysql_connection(mysql_connection)

		# Check and return
		if user_log_table_name == None:
			return False
		return user_log_table_name

	# Common functions
	def returnJSON(self, statusCode, response):
		self.send_response(statusCode)
		self.send_header('Content-Type', 'application/json')
		self.end_headers()
		self.wfile.write(json.dumps(response))

	# User Action Functions
	def userSignup(self, fullname, emailadd, username, password):
		log("A user with username '{0}' would like to signup".format(username))

		# Check valid email
		if not re.match(r"[^@]+@[^@]+\.[^@]+", emailadd):
			log("Invalid email address provided by username '{0}'".format(username))
			self.returnJSON(403, {"status": "invalid_email"})
			return

		# Check valid username
		if len(username.strip()) < int(env_var["user.username.minlength"]):
			log("User with username '{0}' has a username that is too short".format(username))
			self.returnJSON(403, {"status": "username_too_short"})
			return
		if " " in username.strip():
			log("User with username '{0}' has spaces in their username".format(username))
			self.returnJSON(403, {"status": "username_has_spaces"})
			return

		# Check valid password length
		if len(password) < int(env_var["user.password.minlength"]):
			log("User with username '{0}' has a password that is too short".format(username))
			self.returnJSON(403, {"status": "password_too_short"})
			return

		# Connect to MySQL
		mysql_connection = connect_to_mysql()
		# Create the cursor
		cursor = mysql_connection.cursor()
		# Check duplicate username
		cursor.execute(TABLE_SELECT_QUERIES["register_username"], {"username": username})
		clash_count = 0

		for (cursor_username) in cursor:
			if cursor_username[0] == username:
				clash_count = 1 # We found a problem
				break
		if clash_count == 1:
			# Close the cursor, connection and return
			cursor.close()
			close_mysql_connection(mysql_connection)
			# Return
			log("A duplicate user with the same username as '{0}' was found".format(username))
			self.returnJSON(403, {"status": "duplicate_username", "username": username})
			return

		# Check for duplicate email address
		cursor.close()
		cursor = mysql_connection.cursor()

		cursor.execute(TABLE_SELECT_QUERIES["register_email"], {"emailadd": emailadd})

		for (cursor_email) in cursor:
			if cursor_email[0] == emailadd:
				clash_count = 1 # We found a problem
				break
		if clash_count == 1:
			# Close the cursor, connection and return
			cursor.close()
			close_mysql_connection(mysql_connection)
			# Return
			log("Another user with the same email address was found for user '{0}'".format(username))
			self.returnJSON(403, {"status": "duplicate_email", "emailadd": emailadd})
			return

		cursor.close()
		cursor = mysql_connection.cursor() # Fetch a new cursor
		# Now proceed to creating the user; Create password salt
		password_salt = ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(20))
		hashed_password = hashlib.sha512(password_salt + password + str(random.randint(0, 128))).hexdigest()
		# Also create the log table name
		userlogtablename = hashlib.sha1(username).hexdigest()
		userlogtablename = userlogtablename + ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(24))
		# Now create the dictionary
		registration = {
			"fullname": fullname,
			"emailadd": emailadd.lower(),
			"username": username.lower(),
			"saltedpwd": hashed_password,
			"pwdsalt": password_salt,
			"loginhash": "",
			"loginhashexpiry": 0,
			"userlogtablename": userlogtablename,
			"acccreationtime": int(time.time())
		}
		# Now attempt to create the new user
		try:
			# Insert the user into the table of users
			cursor.execute(TABLE_INSERT_QUERIES["register"], registration)
			# Also create the logs table for the user
			cursor.execute(TABLE_CREATE_QUERIES["new_user"].format(userlogtablename))
			# Successful, close the cursor and MySQL Connection and return
			cursor.close()
			# Commit the changes and then close the connection
			mysql_connection.commit()
			close_mysql_connection(mysql_connection)
			# Return the HTTP Response
			log("A user profile for the user '{0}' was successfully created".format(username))
			self.returnJSON(200, {"status": "successful"})
		except mysql.Error as exception:
			print(exception)
			# Close the cursor and MySQL Connection
			cursor.close()
			close_mysql_connection(mysql_connection)
			# Return
			log("Couldn't create the user profile for user '{0}' in the database".format(username))
			self.returnJSON(500, {"status": "failed"})

	def userLogin(self, username, password):
		log("User with username '{0}' is requesting to login".format(username))

		# Connect to MySQL
		mysql_connection = connect_to_mysql()
		# Create the cursor
		cursor = mysql_connection.cursor()
		# Find the respective user's salt
		cursor.execute(TABLE_SELECT_QUERIES["login_pullsalt"], {"username": username})
		user_salt = None

		for (cursor_username, cursor_salt) in cursor:
			if cursor_username == username:
				user_salt = cursor_salt # We found the salt
				break
		if user_salt == None:
			# No username match; Close the cursor, connection and return
			cursor.close()
			close_mysql_connection(mysql_connection)
			# Return
			log("No user with matching username '{0}' was found".format(username))
			self.returnJSON(403, {"status": "no_match"})
			return

		# Iterate over all the possible peppers
		cursor.close()

		user_match = None
		for pepper in range(0, 128):
			# Form the hashed password
			hashed_password = hashlib.sha512(user_salt + password + str(pepper)).hexdigest()
			# Create a cursor; query the DB
			cursor = mysql_connection.cursor()
			# Check for a match
			cursor.execute(TABLE_SELECT_QUERIES["login_test"], {"username": username, "saltedpwd": hashed_password})
			for (cursor_username) in cursor:
				if cursor_username[0] == username:
					user_match = hashed_password # Found the match, save the password
					break # Exit out of this loop
			# Close the cursor
			cursor.close()
			# If we found a match, stop iterating
			if not user_match == None:
				break

		# Check if we got a match
		if user_match == None:
			# Close the MySQL Connection
			close_mysql_connection(mysql_connection)
			# Return
			log("User with username '{0}' provided an invalid password".format(username))
			self.returnJSON(403, {"status": "no_match"})
			return

		# Fetch the login token to see if we need to generate a new one or not
		cursor = mysql_connection.cursor()
		cursor.execute(TABLE_SELECT_QUERIES["login_get_ltexpiry"], {
			"username": username,
			"saltedpwd": user_match
		})

		for (login_token, login_token_expiry) in cursor:
			if login_token_expiry > int(time.time()):
				# This token is still valid
				log("User '{0}' was successfully logged in and a previously issued valid token was sent back".format(username))
				self.returnJSON(200, {"status": "correct_credentials_old_token_passed", "login_token": login_token, "token_expiry": login_token_expiry})
				# Close the cursor and MySQL Connection and return
				cursor.close()
				close_mysql_connection(mysql_connection)
				# Return
				return

		# Create a login token
		login_token = ''.join(random.SystemRandom().choice(string.ascii_letters + string.punctuation + string.digits) for _ in range(128))
		login_token = hashlib.sha512(login_token + str(int(time.time()))).hexdigest()
		# Created at time
		created_at = int(time.time())
		token_expiry = created_at + int(env_var["user.logintoken.validity"])

		# Update
		cursor = mysql_connection.cursor()
		try:
			cursor.execute(TABLE_UPDATE_QUERIES["login_token_generate"], {
				"username": username,
				"saltedpwd": user_match,
				"logintoken": login_token,
				"logintokenexpiry": token_expiry
			})
			cursor.close()
			# If successful, return; Commit the changes and then close the connection
			mysql_connection.commit()
			close_mysql_connection(mysql_connection)
			# Return the HTTP Response
			log("User '{0}' was successfully logged in and was granted a fresh login token".format(username))
			self.returnJSON(200, {"status": "correct_credentials_new_token_generated", "login_token": login_token, "token_expiry": token_expiry, "current_server_time": created_at})
		except mysql.Error as exception:
			# Close the cursor and MySQL Connection
			cursor.close()
			close_mysql_connection(mysql_connection)
			# Return
			log("Unable to create a login token for user '{0}'".format(username))
			self.returnJSON(500, {"status": "failed"})

	def userRenewToken(self, username, old_logintoken, old_logintokenexpiry):
		log("User with username '{0}' would like their login token renewed".format(username))

		# Check if the token is valid before granting a new one; Connect to MySQL
		mysql_connection = connect_to_mysql()
		# Create the cursor
		cursor = mysql_connection.cursor()
		# Run the query
		cursor.execute(TABLE_SELECT_QUERIES["renew_token_validate"], {
			"username": username,
			"logintoken": old_logintoken,
			"logintokenexpiry": int(float(old_logintokenexpiry))
		})
		user_match = False

		for (cursor_username) in cursor:
			if cursor_username[0] == username:
				user_match = True # We found a match
				break
		# Check if we found a match
		if not user_match:
			# Close the cursor and connection
			cursor.close()
			close_mysql_connection(mysql_connection)
			# No match was found
			log("User with username '{0}' requested renewal of their login token but couldn't be found".format(username))
			self.returnJSON(403, {"status": "not_renewed", "reason": "no_match"})
			return
		# Close the cursor
		cursor.close()

		# Login Token and expiry match. Now check if renewal is actually needed
		if int(float(old_logintokenexpiry)) - int(time.time()) > int(env_var["user.logintoken.max_duration_renewal"]):
			close_mysql_connection(mysql_connection)
			# No renewal needed
			log("User with username '{0}' requested renewal of their login token while it wasn't needed".format(username))
			self.returnJSON(403, {"status": "not_renewed", "reason": "not_needed"})
			return

		# Generate a new login token
		login_token = ''.join(random.SystemRandom().choice(string.ascii_letters + string.punctuation + string.digits) for _ in range(128))
		login_token = hashlib.sha512(login_token + str(int(time.time()))).hexdigest()
		# Created at time
		created_at = int(time.time())
		token_expiry = created_at + int(env_var["user.logintoken.validity"])

		# Update
		cursor = mysql_connection.cursor()
		try:
			cursor.execute(TABLE_UPDATE_QUERIES["renew_token_execute"], {
				"username": username,
				"oldlogintoken": old_logintoken,
				"oldlogintokenexpiry": old_logintokenexpiry,
				"logintoken": login_token,
				"logintokenexpiry": token_expiry
			})
			cursor.close()
			# If successful, return; Commit the changes and then close the connection
			mysql_connection.commit()
			close_mysql_connection(mysql_connection)
			# Return the HTTP Response
			log("Login token reneweal for user '{0}' was successful".format(username))
			self.returnJSON(200, {"status": "renew_success", "new_login_token": login_token, "new_token_expiry": token_expiry, "current_server_time": created_at})
		except mysql.Error as exception:
			# Close the cursor and MySQL Connection
			cursor.close()
			close_mysql_connection(mysql_connection)
			# Return
			log("Unable to update login token for user '{0}'".format(username))
			self.returnJSON(500, {"status": "not_renewed", "reason": "failed"})
		return

	def userInvalidateToken(self, username, logintoken, logintokenexpiry):
		log("User '{0}' wants to invalidate their login token".format(username))
		# Check if the token is valid
		mysql_connection = connect_to_mysql()
		# Create a cursor
		cursor = mysql_connection.cursor()
		# Query and check
		user_match = False

		cursor.execute(TABLE_SELECT_QUERIES["invalidate_token_check"], {
			"username": username,
			"logintoken": logintoken,
			"logintokenexpiry": logintokenexpiry	
		})
		for (cursor_username) in cursor:
			if cursor_username[0] == username:
				user_match = True # We found a match
				break
		cursor.close()

		# Check now
		if user_match == False:
			log("User '{0}' requested an invalid login token to be invalidated".format(username))
			self.returnJSON(403, {"status": "not_invalidated", "reason": "no_match"})
			return

		# If matched, now execute an invalidation
		cursor = mysql_connection.cursor()
		try:
			cursor.execute(TABLE_UPDATE_QUERIES["invalidate_token_execute"], {
				"username": username,
				"logintoken": logintoken,
				"logintokenexpiry": logintokenexpiry
			})
			# Close the cursor and MySQL Database connection
			cursor.close()
			mysql_connection.commit()
			close_mysql_connection(mysql_connection)
			# Return the HTTP Response
			log("User '{0}' had their token invalidated successfully".format(username))
			self.returnJSON(200, {"status": "invalidation_successful"})
		except mysql.Error as exception:
			# Close the cursor and MySQL Connection
			cursor.close()
			close_mysql_connection(mysql_connection)
			# Return
			log("Unable to invalidate the login token for user '{0}'".format(username))
			self.returnJSON(500, {"status": "invalidation_failed", "reason": "failed"})
		return

	# Location Log functions
	def fetchAllLocationLogs(self, auth):
		# Verify the authentication given by the call
		log("User '{0}' has called to fetch all their location logs".format(auth[0]))
		# Check the authentication details given
		user_log_table_name = self.verifyAuthCredAndGetLogTableName(auth)
		if user_log_table_name == False:
			log("User '{0}' provided invalid credentials to access their location logs".format(auth[0]))
			self.returnJSON(401, {"status": "unauthorized", "reason": "invalid_auth"})
			return

		# Query the log table
		mysql_connection = connect_to_mysql()
		cursor = mysql_connection.cursor()
		cursor.execute(TABLE_SELECT_QUERIES["fetch_location_log"].format(user_log_table_name))

		logs = []
		for (cursor_log_id, cursor_log_title, cursor_log_description, cursor_log_s3_ids, cursor_location_names, cursor_location_points, cursor_added_date, cursor_updated_at) in cursor:
			# STEP 1: Process the S3 IDs to resolve their image properties
			cursor_s3ids = cursor_log_s3_ids.split(";") # Fetch an array of S3 IDs
			images = []
			# For each of the S3 IDs, fetch the image properties
			for s3id in cursor_s3ids:
				# Create a cursor
				inner_cursor = mysql_connection.cursor()
				# Run the search query
				inner_cursor.execute(TABLE_SELECT_QUERIES["fetch_s3_image_prop"], {
					"logid": cursor_log_id,
					"s3id": s3id	
				})

				for (assoclogid, uniques3id, amazons3url, imgheight, imgwidth, latlng, addedtime) in inner_cursor:
					# Add it to the images
					images.append({
						"s3id": s3id,
						"url": amazons3url,
						"height": imgheight,
						"width": imgwidth,
						"latlng": latlng,
						"addedtime": addedtime
					})
				# Close the inner cursor
				inner_cursor.close()
			# STEP 2: Convert cursor_location_points
			location_points = cursor_location_points.split(";")
			loc_points = []

			for location_point in location_points:
				# Split it up
				splitted = location_point.split(",")
				# Save it
				loc_points.append({
					"lat": splitted[0],
					"lng": splitted[1] if len(splitted) > 1 else ""
				})
			# STEP 3: Add this to the logs
			logs.append({
				"publishdate": cursor_added_date,
				"lastupdateddate": cursor_updated_at,
				"logid": cursor_log_id,
				"title": cursor_log_title,
				"desc": cursor_log_description,
				"images": images,
				"locnames": cursor_location_names,
				"locpoints": loc_points
			})
		# Close the cursor and the MySQL Connection
		cursor.close()
		close_mysql_connection(mysql_connection)
		# Now return
		log("Fetched all location logs for '{0}'".format(auth[0]))
		self.returnJSON(200, logs)
		return

	def addAmazonS3Image(self, auth, locationLogID, imageURL, uniques3id, imageWidth, imageHeight, latlng):
		# Verify the authentication given by the call
		log("User '{0}' wants to add an Amazon S3 image to the S3 images table".format(auth[0]))
		# Check the authentication details given
		user_log_table_name = self.verifyAuthCredAndGetLogTableName(auth)
		if user_log_table_name == False:
			log("User '{0}' provided invalid credentials to access the S3 images table".format(auth[0]))
			self.returnJSON(401, {"status": "unauthorized", "reason": "invalid_auth"})
			return

		# Query the log table
		mysql_connection = connect_to_mysql()
		cursor = mysql_connection.cursor()
		# Generate Unique S3 ID for the table
		#   uniques3id = hashlib.sha512(auth[1] + locationLogID + imageURL + str(int(time.time()))).hexdigest()
		#   We now expect the client to generate a unique S3 ID for the S3IDs Table
		# Insert the image
		try:
			cursor.execute(TABLE_INSERT_QUERIES["add_s3_image"], {
				"assoclogid": locationLogID,
				"uniqueimgid": uniques3id,
				"amazonimgurl": imageURL,
				"imgheight": int(imageHeight),
				"imgwidth": int(imageWidth),
				"latlng": latlng,
				"addedtime": int(time.time())
			})
			# Close the cursor and MySQL Database connection
			cursor.close()
			mysql_connection.commit()
			close_mysql_connection(mysql_connection)
			# Return the HTTP Response
			log("User '{0}' added their image to the S3 table successfully".format(auth[0]))
			self.returnJSON(200, {
				"status": "success", 
				"uniques3id": uniques3id
			})
		except mysql.Error as exception:
			# Close the cursor and MySQL Connection
			cursor.close()
			close_mysql_connection(mysql_connection)
			# Return
			log("Unable to add S3 image to our S3 table for user '{0}'".format(auth[0]))
			self.returnJSON(500, {
				"status": "failed",
				"reason": "unable_to_add"
			})

		# Now return
		return

	def addLocationLog(self, auth, locationLogID, logTitle, logDesc, logS3ids, logLocationNames, logLocationPoints):
		# Verify the authentication given by the call
		log("User '{0}' wants to add a location log to their location logs table".format(auth[0]))
		# Check the authentication details given
		user_log_table_name = self.verifyAuthCredAndGetLogTableName(auth)
		if user_log_table_name == False:
			log("User '{0}' provided invalid credentials to add a location log".format(auth[0]))
			self.returnJSON(401, {"status": "unauthorized", "reason": "invalid_auth"})
			return

		# Add to the table
		mysql_connection = connect_to_mysql()
		cursor = mysql_connection.cursor()
		# Insert the location log
		addedat = int(time.time())
		
		cursor.execute(TABLE_INSERT_QUERIES["add_location_log"].format(user_log_table_name), {
			"logid": locationLogID,
			"logtitle": logTitle,
			"description": logDesc,
			"imgids": logS3ids,
			"locnames": logLocationNames,
			"locpoints": logLocationPoints,
			"addeddate": addedat,
			"lastupdatetime": addedat
		})
		# Close the cursor and MySQL Database connection
		cursor.close()
		mysql_connection.commit()
		close_mysql_connection(mysql_connection)
		# Return the HTTP Response
		log("User '{0}' added their location log successfully".format(auth[0]))
		self.returnJSON(200, {
			"status": "success",
			"addedate": addedat
		})
		# Return
		return

	def deleteLocationLog(self, auth, locationLogID):
		# Verify the authentication given by the call
		log("User '{0}' wants to delete a location log from their location logs table".format(auth[0]))
		# Check the authentication details given
		user_log_table_name = self.verifyAuthCredAndGetLogTableName(auth)
		if user_log_table_name == False:
			log("User '{0}' provided invalid credentials to delete a location log from their table".format(auth[0]))
			self.returnJSON(401, {"status": "unauthorized", "reason": "invalid_auth"})
			return

		# Connect to the database
		mysql_connection = connect_to_mysql()
		cursor = mysql_connection.cursor()
		# Execute the two queries
		cursor.execute(TABLE_DELETE_QUERIES["delete_location_log_entry"].format(user_log_table_name), {
			"logid": locationLogID
		})
		cursor.execute(TABLE_DELETE_QUERIES["delete_location_log_s3_entries"], {
			"logid": locationLogID
		})
		# Close and commit the cursor and database connection
		cursor.close()
		mysql_connection.commit()
		close_mysql_connection(mysql_connection)
		# Return the HTTP Response
		log("User '{0}' successfully their location log".format(auth[0]))
		self.returnJSON(200, {"status": "success"})
		# Return
		return

	def fetchMiniLocationLogs(self, auth):
		# Verify the authentication given by the call
		log("User '{0}' wants to fetch their mini-location log list".format(auth[0]))
		# Check the authentication details given
		user_log_table_name = self.verifyAuthCredAndGetLogTableName(auth)
		if user_log_table_name == False:
			log("User '{0}' provided invalid credentials to fetch all their mini-location logs".format(auth[0]))
			self.returnJSON(401, {"status": "unauthorized", "reason": "invalid_auth"})
			return

		# Connect to the database
		mysql_connection = connect_to_mysql()
		cursor = mysql_connection.cursor()
		cursor.execute(TABLE_SELECT_QUERIES["fetch_location_log"].format(user_log_table_name))

		logs = []
		for (cursor_log_id, cursor_log_title, cursor_log_description, cursor_log_s3_ids, cursor_location_names, cursor_location_points, cursor_added_date, cursor_updated_at) in cursor:
			# Directly add the necessary information to the logs
			logs.append({
				"addeddate": cursor_added_date,
				"lastupdateddate": cursor_updated_at,
				"locationlogid": cursor_log_id
			})
		# Close the cursor and the MySQL Connection
		cursor.close()
		close_mysql_connection(mysql_connection)
		# Now return
		log("Fetched all mini-location logs for '{0}'".format(auth[0]))
		self.returnJSON(200, logs)
		return

	def deleteAllLocationLogs(self, auth):
		# Verify the authentication given by the call
		log("User '{0}' wants to delete ALL their location logs from their log table".format(auth[0]))
		# Check the authentication details given
		user_log_table_name = self.verifyAuthCredAndGetLogTableName(auth)
		if user_log_table_name == False:
			log("User '{0}' provided invalid credentials to delete all their location logs".format(auth[0]))
			self.returnJSON(401, {"status": "unauthorized", "reason": "invalid_auth"})
			return

		# Connect to the database
		mysql_connection = connect_to_mysql()
		cursor = mysql_connection.cursor()
		inner_cursor = mysql_connection.cursor()
		cursor.execute(TABLE_SELECT_QUERIES["fetch_location_log"].format(user_log_table_name))

		# Iterate over each of the logs and delete all the respective S3 IDs associated with it in the S3IDs table
		for (cursor_log_id, cursor_log_title, cursor_log_description, cursor_log_s3_ids, cursor_location_names, cursor_location_points, cursor_added_date, cursor_updated_at) in cursor:
			# Execute the S3IDs removal
			inner_cursor.execute(TABLE_DELETE_QUERIES["delete_location_log_s3_entries"], {
				"logid": cursor_log_id
			})
		# Now close the cursors
		inner_cursor.close()
		cursor.close()
		# Delete everything from this user's table
		cursor = mysql_connection.cursor()
		cursor.execute(TABLE_DELETE_QUERIES["delete_all_location_logs"].format(user_log_table_name))
		cursor.close()
		# Now commit, close and return
		mysql_connection.commit()
		close_mysql_connection(mysql_connection)
		# Now return
		log("User '{0}' had ALL their Location Logs deleted".format(auth[0]))
		self.returnJSON(200, {"status": "success"})
		return


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
	"""Handle requests in a separate thread."""

# Usage
def usage():
	print("[sudo] python server.py")
	print("  This script is run on an EC2 instance and is used to start up a Python server on")
	print("  the EC2 instance.")
	print("\n")
	print("Usage: [sudo] python server.py [-h|--help] [--config=<config_file_path>] [--hostname=<host_name>] [--port=<server_port>]")
	print("\n")
	print("  --help\tTo have the usage of this script printed")
	print("  --config\tPath to the configuration file from where the configuration for this script will be picked up.")
	print("\t\tDefault is picked up from the file \"config\" in the same directory as the running script.")
	print("  --hostname\tThe hostname the server should run on.")
	print("\t\tDefault host that the server will run on is 0.0.0.0. This makes the server accessible over the internet")
	print("\t\tprovided the firewall settings for the EC2 instance are configured to allow so.")
	print("  --port\tThe port that the server should run on.")
	print("\t\tThe default port is 80 to allow TCP and HTTP connections from web browsers.")
	print("\n")

def main():
	# Some variables
	config_file_path = "config"
	hostname = "0.0.0.0"
	port = 80

	if not len(sys.argv) == 1:
		# We've got some arguments to parse
		try:
			opts, args = getopt.getopt(sys.argv[1:], "h", ["help", "config=", "hostname=", "port="])
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
			elif opt in ("--hostname"):
				hostname = arg
			elif opt in ("--port"):
				port = int(arg)
			else:
				print("Invalid option(s)\n")
				usage()
				exit()
	# Read the configuration from the file
	if not read_from_config(config_file_path): exit(EXIT_CODE_UNKNOWN_FAILURE)
	# Start up the server
	log("  _                _   _       _            ")
	log(" | |              | \ | |     | |           ")
	log(" | |     ___   ___|  \| | ___ | |_ ___  ___ ")
	log(" | |    / _ \ / __| . ` |/ _ \| __/ _ \/ __|")
	log(" | |___| (_) | (__| |\  | (_) | ||  __/\__ \\")
	log(" |______\___/ \___|_| \_|\___/ \__\___||___/")
	log("")
	log("Serving the server at {0}:{1} forever".format(hostname, port))
	log("To shutdown the server, press Ctrl+C / Command+C")

	# Start the server and wait for KeyboardInterrupt
	try:
		ThreadedHTTPServer((hostname, port), Handler).serve_forever()
	except KeyboardInterrupt:
		log("Server is shutting down. Reason: Ctrl+C/Command+C")

if __name__ == '__main__':
	# Import the commonutils.py file
	execfile(FILE_COMMON_UTILS)
	# Log and call main
	if not len(sys.argv) == 1:
		log("Server fired up with arguments: {0}".format(" ".join(sys.argv[1:])))
	else:
		log("Server fired up started")
	# Main time
	main()