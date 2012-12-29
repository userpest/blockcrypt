import os
import struct
import logging
from collections import deque
from dropbox import client, rest, session
from StringIO import StringIO

#use /dev/random if security matters

def get_random_sector(sector_size, source ="/dev/urandom" )
	fp = open(source,"rb")
	data = fp.read(sector_size)
	fp.close()
	return data

#TODO: should inherit after EncryptedBlockDevice
class DiskDriver(object):
	#TODO: use *args and **kwargs
	def __init__(self,size,sector_size):
		logging.basicConfig(filename='blockcrypt.log',level=logging.DEBUG)
		self.size = size
		self.sector_size = sector_size
		self.logger = logging.getLogger("blockcrypt")

	def read(self,sector):
		pass
	def write(self,data):
		pass
	def flush(self):
		pass
	@staticmethod
	def create_disk():
		pass

class FileDiskDriver(DiskDriver):
	def __init__(self,filename):

		size = os.stat(filename).st_size
		sector_size = 10
		super(FileDiskDriver,self).__init__(size,sector_size)
		self.disk_begin = 0 
		self.fp = open(filename,"r+b")

		self.sector_size = self.read_disk_info()[0]

	def write(self,sector,data):
		offset = self.sector_size*sector+self.disk_begin
		self.logger.debug("FDD: write %d data at %d, sector: %d",len(data),offset,sector) 
		self.fp.seek(offset)
		self.fp.write(data)


	def read(self,sector):
		offset = self.sector_size*sector+self.disk_begin

		self.fp.seek(offset)
		self.logger.debug("FDD: read offset %d, sector %d, tell %d", offset,sector,self.fp.tell())
		buf = self.fp.read(self.sector_size)
		return buf

	def read_disk_info(self):
		self.logger.debug("FDD: read disk info ")
		info_size = struct.calcsize('Q')
		info = self.fp.read(info_size)
		self.disk_begin = info_size
		self.fp.seek(self.disk_begin)
		self.logger.debug("FDD: info_size %d , disk_begin %d", info_size, self.disk_begin)
		return struct.unpack('Q', info)

	#TODO: source should be random, urandom is for speed
	@staticmethod
	def create_disk(filename, disk_size,sector_size,rand_source='/dev/urandom'):
		fp = open(filename, "wb")
		header = struct.pack('Q', sector_size)
		fp.write(header)

		left = disk_size
		while left > 0:

			if left % sector_size==0:
				to_read=sector_size
			else:
				to_read=left

			data = get_random_sector(sector_size,rand_source)
			fp.write(data)
			left-=to_read
		fp.flush()
		fp.close()
	def flush(self):
		self.fp.flush()
		
class CachedDiskDriver(DiskDriver):
	#TODO: change to *args & **kwargs
	"""
	the unit of cache_size is number of sectors
	"""
	def __init__(self,size,sector_size,cache_size):
		super(CachedDiskDriver,self).__init__(size,sector_size)
		sectors_accessed = deque()
		sector_cache = {}
		self.cache_size = cache_size

	def read(self,sector):
		sector_cache = self.sector_cache
		sectors_accessed=self.sectors_accessed

		if sector in sector_cache:
			self.update_sector_status(sector)
			data = sector_cache[sector]
		else:
			self.make_space()
			data = self.get_sector(sector)
			sector_cache[sector]=data
			sectors_accessed.appendleft(sector)

		return data

	

	def write(self,sector,data):
		sector_cache = self.sector_cache
		sectors_accessed=self.sectors_accessed

		if sector in sector_cache:
			self.update_sector_status(sector)
			sector_cache[sector]=data
		else:
			self.make_space()
			sector_cache[sector]=data
			sectors_accessed.appendleft(sector)

	def update_sector_status(self,sector):
		self.sectors_accessed.remove(sector)
		self.sectors_accessed.appendleft(sector)


	def make_space(self):
		if len(sectors_accessed) > self.cache_size:
			self.uncache_last()

	def uncache_last(self,sector):
		sector = self.sectors_accessed.pop()
		data = self.sector_cache.pop(sector)
		self.write_sector(sector,data)

	def flush(self):
		sector_cache = self.sector_cache
		sectors_accessed=self.sectors_accessed

		while len(sectors_accessed)>0:
			self.uncache_last()


	def get_sector(self,sector):
		pass
	def write_sector(self,sector,data):
		pass

class DropboxDiskDriver(CachedDiskDriver):
	def __init__(self,username,password):
		self.authenticate()

	def get_sector(self,sector):
		f, metadata = client.get_file_and_metadata(self.get_sector_name(sector))
		data = f.read(self.sector_size)
		return data

	def write_sector(self,sector,data):
		f = StringIO(data)	
		client.put_file(self.get_sector_name(sector), f)

	def get_sector_name(sector):
		sector_name = '/'+str(sector)
		return sector_name


	def authenticate(self):
		sess = session.DropboxSession(APP_KEY, APP_SECRET, ACCESS_TYPE)
		request_token = sess.obtain_request_token()
		url = sess.build_authorize_url(request_token)
		print "url:", url
		print "Please visit this website and press the 'Allow' button, then hit 'Enter' here."
		raw_input()
		access_token = sess.obtain_access_token(request_token)
		self.client =  client.DropboxClient(sess)


	def create_disk(size,sector_size,rand_source='/dev/urandom'):	
		for i in range(0,size/sector_size):
			s = get_random_sector(sector_size,rand_source)
			self.write_sector(i,s)



