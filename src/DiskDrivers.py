import os
import struct
import logging

#TODO: should inherit after EncryptedBlockDevice
class DiskDriver(object):
	def __init__(self,size,sector_size):
		logging.basicConfig(filename='blockcrypt.log',level=logging.DEBUG)
		self.size = size
		self.sector_size = sector_size
		self.logger = logging.getLogger("blockcrypt")

	def read(self,sector):
		pass
	def write(self,data):
		pass
	def seek(self,offset,from_what):
		pass
	def flush(self):
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

	def seek(self,offset,from_what=0):
		self.fp.seek(offset,from_what)

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
		random_data = open(rand_source, "rb")

		left = disk_size
		while left > 0:

			if left % sector_size==0:
				to_read=sector_size
			else:
				to_read=left

			data = random_data.read(to_read)
			fp.write(data)
			left-=to_read
		fp.flush()
		fp.close()
	def flush(self):
		self.fp.flush()
		

