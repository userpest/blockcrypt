import os
import struct
import logging
from collections import deque
from dropbox import client, rest, session
from StringIO import StringIO
from util import *
import re
from appkeys import *
#use /dev/random if security matters

class WrongDiskSize(Exception):
	def __init__(self,message):
		super(WrongDiskSize, self).__init__()
		self.message=message



#TODO: should inherit after EncryptedBlockDevice
class DiskDriver(object):
	#TODO: use *args and **kwargs
	def __init__(self,size,sector_size):
		logging.basicConfig(filename='blockcrypt.log',level=logging.DEBUG)
		self.size = size
		self.sector_size = sector_size
		self.logger = logging.getLogger("blockcrypt")
		if size % sector_size != 0:
			print "DD init received %d %d" %(size,sector_size)
			raise WrongDiskSize("disk size must the multiple of sector size %d %d" % (size,sector_size))

	def read(self,sector):
		pass
	def write(self,data):
		pass
	def flush(self):
		pass
	@staticmethod
	def create_disk():
		pass


class FileBasedDiskDriver(DiskDriver):
	def __init__(self,fp,size,sector_size,disk_begin=0):
		super(FileBasedDiskDriver,self).__init__(size,sector_size)
		self.fp = fp
		self.disk_begin = disk_begin


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

		#TODO: source should be random, urandom is for speed
	def flush(self):
		self.fp.flush()

class FileDiskDriver(FileBasedDiskDriver):
	def __init__(self,filename):
		fp = open(filename,"r+b")
		(size,sector_size,disk_begin) = self.read_disk_info(filename)
		super(FileDiskDriver,self).__init__(fp,size,sector_size,disk_begin)

	@staticmethod
	def read_disk_info(filename):
		fp = open(filename,'rb')
		info_size = struct.calcsize('Q')
		info = fp.read(info_size)
		disk_begin = info_size

		size = os.stat(filename).st_size - info_size
		fp.close()
		sector_size = struct.unpack('Q', info)[0]
		return (size,sector_size,disk_begin)


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

class HDDDiskDriver(FileBasedDiskDriver):

	def __init__(self,disk):
		fp = open(disk,'r+b')
		(size,sector_size) = self.get_sector_size(disk)
		super(HDDDiskDriver,self).__init__(fp,size,sector_size)

	def get_sector_size(disk):
		dev = disk.split('/')[-1]
		name = re.sub("[^a-zA-Z]", "", dev)
		path = "/sys/block"+name
		sector_size = int(open(path+"/queue/hw_sector_size",'r').read())
		size = int(open(path+dev+"size","r").read())
		return (size,sector_size)


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

		for i in sectors_accessed:
			self.write_sector(sector,sector_cache[sector])


	def get_sector(self,sector):
		pass
	def write_sector(self,sector,data):
		pass

class DropboxDiskDriver(CachedDiskDriver):
	def __init__(self,cache_size):
		self.authenticate()
		#bit sloppy but shouldnt be able to lead to a significant attack
		try:
			f,meta = self.client.get_file_and_metadata("/config")	
			hack = StringIO(f.read())
			hack.seek(0)
			size = int(hack.readline())
			sector_size = int(hack.readline())
			super(DropboxDiskDriver,self).__init__(size,sector_size,cache_size)
			f.close()
		except rest.ErrorResponse:
			print "config doesnt exist on server"
			pass

	def get_sector(self,sector):
		f, metadata = self.client.get_file_and_metadata(self.get_sector_name(sector))
		data = f.read(self.sector_size)
		f.close()
		return data

	def write_sector(self,sector,data):
		f = StringIO(data)	
		self.client.put_file(self.get_sector_name(sector), f)

	def get_sector_name(self,sector):
		sector_name = '/'+str(sector)
		return sector_name


	def authenticate(self):
		ACCESS_TYPE='dropbox'
		sess = session.DropboxSession(APP_KEY, APP_SECRET, ACCESS_TYPE)
		request_token = sess.obtain_request_token()
		url = sess.build_authorize_url(request_token)
		print "url:", url
		print "Please visit this website and press the 'Allow' button, then hit 'Enter' here."
		raw_input()
		access_token = sess.obtain_access_token(request_token)
		self.client =  client.DropboxClient(sess)


	def create_disk(self,size,sector_size,rand_source='/dev/urandom'):	
		config = StringIO()
		s = "%d\n%d" %(size,sector_size)
		config.write(s)
		config.seek(0)
		self.client.put_file("/config", config)

		for i in range(0,int(size/sector_size)):
			s = get_random_sector(sector_size,rand_source)
			self.write_sector(i,s)
		self.size = size
		self.sector_size = sector_size

	def delete_disk(self):
		self.client.file_delete("/config", config)

		for i in range(0,int(size/sector_size)):
			self.client.file_delete(self.get_sector_name(i))

		self.size = size
		self.sector_size = sector_size


