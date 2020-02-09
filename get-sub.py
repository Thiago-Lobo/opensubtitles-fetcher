#!/usr/local/bin/python

import sys
import os
import json

# Python 3 workaround imports
from xmlrpc import client as xmlrpclib
from io import BytesIO

import struct
import base64
import gzip

CREDS_FILE = 'dummy.creds'

def is_list(object):
	return isinstance(object, (list,))

def base64_decode_and_ungzip(base64_encoded):
	base64_decoded = base64.b64decode(base64_encoded)

	compressed_file = BytesIO()
	compressed_file.write(base64_decoded)
	compressed_file.seek(0)

	decompressed_file = gzip.GzipFile(fileobj=compressed_file, mode='rb')

	return decompressed_file

class File(object):
    def __init__(self, path):
        self.path = path
        self.size = str(os.path.getsize(path))

    def get_hash(self):
        longlongformat = 'q'  # long long
        bytesize = struct.calcsize(longlongformat)

        try:
            f = open(self.path, "rb")
        except(IOError):
            return "IOError"

        hash = int(self.size)

        if int(self.size) < 65536 * 2:
            return "SizeError"

        for x in range(65536 // bytesize):
            buffer = f.read(bytesize)
            (l_value, ) = struct.unpack(longlongformat, buffer)
            hash += l_value
            hash = hash & 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number

        f.seek(max(0, int(self.size) - 65536), 0)
        for x in range(65536 // bytesize):
            buffer = f.read(bytesize)
            (l_value, ) = struct.unpack(longlongformat, buffer)
            hash += l_value
            hash = hash & 0xFFFFFFFFFFFFFFFF

        f.close()
        returnedhash = "%016x" % hash
        return str(returnedhash)

class OpenSubtitlesClient(object):
	OPENSUBTITLES_SERVER = 'http://api.opensubtitles.org/xml-rpc'

	def __init__(self, language='en'):
		self.user_agent = 'TemporaryUserAgent'
		self.token = None
		self.language = language

		transport = xmlrpclib.Transport()
		transport.user_agent = self.user_agent

		self.xmlrpc = xmlrpclib.ServerProxy(OpenSubtitlesClient.OPENSUBTITLES_SERVER, allow_none=True, transport=transport)

	def login(self, username, password):
		data = self.xmlrpc.LogIn(username, password, self.language, self.user_agent)

		if 'token' in data:
			self.token = data['token']
			return True

		return False

	def logout(self):
		data = self.xmlrpc.LogOut(self.token)

	def search_subtitles(self, args):
		if not is_list(args):
			args = [args]

		data = self.xmlrpc.SearchSubtitles(self.token, args)

		if 'data' in data:
			return data['data']

		return None

	def download_subtitles(self, args):
		if not is_list(args):
			args = [args]

		data = self.xmlrpc.DownloadSubtitles(self.token, args)

		if 'data' in data:
			return data['data']

		return None

def extract_file_name_from_path(path, with_extension=True):
	result = os.path.basename(path)
	
	if not with_extension:
		return os.path.splitext(result)[0]

	return result

def download_subtitle(client, path):
	wrapped_movie_file = File(path)
	file_name = extract_file_name_from_path(path, with_extension=False)
	file_name_no_extension = extract_file_name_from_path(path, with_extension=False)
	
	found_subtitles = client.search_subtitles({'sublanguageid': 'pob', 'moviehash': wrapped_movie_file.get_hash(), 'moviebytesize': wrapped_movie_file.size})
	
	if len(found_subtitles) == 0:
		print('Found no subtitles by hash')
		found_subtitles = client.search_subtitles({'sublanguageid': 'pob', 'query': file_name})

	# found_subtitles = client.search_subtitles({'imdbid': '8075192'})
	
	for found_subtitle in found_subtitles:
		print('Found subtitle!')
		
		subtitle_id = found_subtitle['IDSubtitleFile']
		file_name = found_subtitle['SubFileName']
		file_hash = found_subtitle['MovieHash']

		print(file_name)
		print(file_hash)

		downloaded_subtitle = client.download_subtitles(subtitle_id)[0]
		decoded = base64_decode_and_ungzip(downloaded_subtitle['data'])

		with open(os.path.join(os.path.dirname(path), '{0}.srt'.format(file_name_no_extension)), 'wb') as outfile:
			outfile.write(decoded.read())
		
		break

def load_creds_file(path):
	username = None
	password = None
	
	with open(path, 'r') as f:
		username = f.readline().strip()
		password = f.readline().strip()
		f.close()

	return username, password

def main():
	if len(sys.argv) < 2:
		sys.exit('Please provide a file as input!')
	
	input_path = sys.argv[1]

	if not os.path.exists(input_path):
		sys.exit('Input file does not exist :(')

	api_username, api_password = load_creds_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), CREDS_FILE))

	client = OpenSubtitlesClient()
	client.login(api_username, api_password)

	download_subtitle(client, input_path)

	client.logout()

if __name__ == '__main__':
	main()

