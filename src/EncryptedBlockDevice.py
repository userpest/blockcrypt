#!/usr/bin/python2.7
import math
import logging
from Crypto.Hash import SHA256, HMAC

#TODO:merge DiskDrivers and EncryptedBlockDevice into one
class EncryptedBlockDevice(object):

	def __init__(self,crypto_driver,disk_driver,use_hmac=False):

		logging.basicConfig(filename='blockcrypt.log',level=logging.DEBUG)
		self.crypto = crypto_driver
		self.device = disk_driver
		self.sector_size = disk_driver.sector_size
		self.offset=0
		self.size = disk_driver.size
		self.logger = logging.getLogger("blockcrypt")

		if use_hmac:
			self.hmac_init()

	def hmac_init(self):
		self.hmac_size=SHA256.digest_size

		self.hmac_entry_size=struct.calcsize('Q')+self.hmac_size
		active_sectors = math.floor(self.size/(self.sector_size+self.hmac_entry_size))
		self.hmac_pos = active_sectors*self.sector_size
		self.hmac_section_begin=self.hmac_pos+self.hmac_size
		self.realsize = self.size
		self.size -= self.hmac_size + self.hmac_entry_size*active_sectors

	def seek(self,offset,from_what=0):
		self.logger.debug("EBD seek %d %d", offset,from_what)
		if from_what==0:
			self.offset=offset
		elif from_what==1:
			self.offset+=offset
		elif from_what==2:
			self.offset=self.size+offset

	def get_current_sector(self):
		"""
		returns a pair (sector_number,sector_offset)
		"""
		return (math.floor(self.offset/self.sector_size), self.offset%self.sector_size)

	def _read(self,size):
		self.logger.debug("_read %d", size)
		sector_size = self.sector_size
		device = self.device
		while size > 0:
			(sector, sector_offset) = self.get_current_sector()
			read_size = min(size,sector_size-sector_offset)
			read_begin = sector_offset
			read_end = min(sector_offset+size, sector_size)	
			size-=read_size
			self.offset+=read_size
			ciphertext = device.read(sector)	
			yield (sector,ciphertext,read_begin,read_end,read_size) 		



	def read(self,size):
		buf = bytearray()
		crypto = self.crypto
		self.logger.debug("EBD read offset %d, size %d",self.offset,size)
		for (sector,ciphertext,read_begin, read_end,read_size) in self._read(size):
			self.logger.debug("EBD: sector %d begin %d end %d size %d", sector,read_begin,read_end,read_size) 
			plaintext = crypto.decrypt(sector,ciphertext)	
			self.logger.debug("EBD: read crypto returned %d data", len(ciphertext))
			buf+=plaintext[read_begin:read_end]
		self.logger.debug("EBD read successfull read size: %d", len(buf))
		return buf


	def write(self,plaintext):
		#TODO:optimize
		crypto = self.crypto
		device = self.device
		sector_size = self.sector_size
		self.logger.debug("EBD write, offset %d, len: %d ", self.offset, len(plaintext))
		plaintext_size = len(plaintext)
		while plaintext_size > 0 :
			(sector, sector_offset) = self.get_current_sector()	
			write_begin = sector_offset
			write_end = min(plaintext_size+sector_offset,sector_size)
			write_size = write_end-write_begin

			ciphertext = self.device.read(sector)

			ciphertext = crypto.encrypt(sector,plaintext[:write_size],ciphertext,write_begin,write_end)
			self.logger.debug("EBD write_begin: %d write_end: %d size: %d plaintext_size %d",write_begin,write_end,write_size,plaintext_size)	
			device.write(sector,ciphertext)
			plaintext=plaintext[write_size:]
			self.offset+=write_size
			plaintext_size-=write_size

		self.logger.debug("EBD write end")
	def flush(self):
		self.logger.debug("EBD flush")
		self.device.flush()

	def save_sector_hmac(self,sector,data):
		hmac = self.get_hmac(data)
		buf = struct.pack('Q', sector)
		buf+=hmac.digest()
		self.write(self.get_sector_hmac_offset(sector),buf)

	def get_sector_hmac_offset(self,sector):
		return self.hmac_section_begin+sector*self.hmac_entry_size

	def get_hmac(self,data):
		return HMAC.new(self.hmac_key,data, SHA256)		

	def sector_hmac_valid(self,sector):
		buf = self.device.read(sector)
		computed_hmac = self.get_hmac(data)
		data = self.read(self.get_sector_hmac_offset(sector),self.hmac_entry_size)
		saved_hmac=data[infosize:]

		if computed_hmac != saved_hmac:
			return False
		else:
			return True

	def saved_disk_hmac(self):
		hmac = self.read(self.hmac_pos,self.hmac_size)

	def compute_disk_hmac(self):
		hmac = HMAC.new(self.hmac_key,"",SHA256)

		for i in range(0,self.size/self.sector_size):
			s = self.device.read(i)
			hmac.update(s)

		return hmac.digest()

	def check_disk_hmac(self):
		if self.saved_disk_hmac() != self.compute_disk_hmac():
			return False
		else:
			return True

	def find_modified_sectors(self):
		ret = []
		for i in range(0,self.size/self.sector_size):
			if not self.sector_hmac_valid(i):
				ret.append(i)

		return ret
