import os

SETTINGS = {
	'store_path': os.environ['CERTMAN_STORE_PATH'],
	'default_password': os.environ['CERTMAN_DEFAULT_PASSWORD'],
	'db': os.environ['CERTMAN_DB']
}