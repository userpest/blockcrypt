#!/usr/bin/python2.7
import math
import logging

#TODO:merge DiskDrivers and EncryptedBlockDevice into one
class EncryptedBlockDevice(object):

	def __init__(self,crypto_driver,disk_driver):

		logging.basicConfig(filename='blockcrypt.log',level=logging.DEBUG)
		self.crypto = crypto_driver
		self.device = disk_driver
		self.sector_size = disk_driver.sector_size
		self.offset=0
		self.size = disk_driver.size
		self.logger = logging.getLogger("blockcrypt")

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
			plaintext=plaintext[write_end:]
			self.offset+=write_size
			plaintext_size-=write_size

		self.logger.debug("EBD write end")
	def flush(self):
		self.logger.debug("EBD flush")
		self.device.flush()
