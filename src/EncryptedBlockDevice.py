#!/usr/bin/python2.7
import math
import logging
from Crypto.Hash import SHA256, HMAC
import struct
from util import *
class SectorHmacDoesntMatch(Exception):
	def __init__(self,message):
		super(SectorHmacDoesntMatch, self).__init__()
		self.message=message


#TODO:merge DiskDrivers and EncryptedBlockDevice into one
class EncryptedBlockDevice(object):

	def __init__(self,crypto_driver,disk_driver):

		self.crypto = crypto_driver
		self.device = disk_driver
		self.sector_size = disk_driver.sector_size
		self.offset=0
		self.size = disk_driver.size


	def seek(self,offset,from_what=0):
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
		return (int(math.floor(self.offset/self.sector_size)), self.offset%self.sector_size)

	def _read(self,size):
		sector_size = self.sector_size
		device = self.device
		while size > 0:
			(sector, sector_offset) = self.get_current_sector()
			read_size = min(size,sector_size-sector_offset)
			read_begin = sector_offset
			read_end = min(sector_offset+size, sector_size)	
			size-=read_size
			self.offset+=read_size
			ciphertext = self.read_sector(sector)	
			yield (sector,ciphertext,read_begin,read_end,read_size) 		



	def read_sector(self,sector):
		return self.device.read(sector)

	def read(self,size):
		buf = bytearray()
		crypto = self.crypto

		for (sector,ciphertext,read_begin, read_end,read_size) in self._read(size):
			plaintext = crypto.decrypt(sector,ciphertext)	
			buf+=plaintext[read_begin:read_end]

		return buf

	#meh
	def write_sector(self,sector,data):
		self.device.write(sector,data)

	def write(self,plaintext):
		#TODO:optimize
		crypto = self.crypto
		device = self.device
		sector_size = self.sector_size
		plaintext_size = len(plaintext)
		while plaintext_size > 0 :
			(sector, sector_offset) = self.get_current_sector()	
			write_begin = sector_offset
			write_end = min(plaintext_size+sector_offset,sector_size)
			write_size = write_end-write_begin

			ciphertext = self.read_sector(sector)

			sector_data = crypto.decrypt(sector,ciphertext)
			sector_data = sector_data[:write_begin]+plaintext[:write_size]+sector_data[write_end:]
			ciphertext = crypto.encrypt(sector,sector_data)

			self.write_sector(sector,ciphertext)

			plaintext=plaintext[write_size:]
			self.offset+=write_size
			plaintext_size-=write_size

	def flush(self):
		self.device.flush()

class EncryptedBlockDeviceWithHmac(EncryptedBlockDevice):

	def __init__(self,crypto_driver,disk_driver,hmac_key):

		super(EncryptedBlockDeviceWithHmac,self).__init__(crypto_driver,disk_driver)

		self.hmac_key = hmac_key
		self.hmac_size=SHA256.digest_size

		self.hmac_entry_size=self.hmac_size
		active_sectors = int(math.floor(self.size/(self.sector_size+self.hmac_entry_size)))

		self.hmac_pos = active_sectors*self.sector_size
		self.hmac_section_begin=self.hmac_pos

		self.realsize = self.size
		self.size -= self.hmac_entry_size*active_sectors
		self.compute_hmac = True
		self.check_hmac = True
		self.active_sectors = active_sectors

	def save_sector_hmac(self,sector,data):
		#print "saving hmac for %d" % (sector)
		hmac = self.get_hmac(data)
		buf=hmac.digest()
		#print to_hex(buf)
		offset2 = self.offset
		self.seek(self.get_sector_hmac_offset(sector))
		self.compute_hmac=False
		self.write(buf)
		self.seek(offset2)

		self.compute_hmac = True

	def write_sector(self,sector,data):
		if self.compute_hmac:
			self.save_sector_hmac(sector,data)
		self.device.write(sector,data)

	def get_sector_hmac_offset(self,sector):
		return int(self.hmac_section_begin + sector*self.hmac_entry_size)

	def get_hmac(self,data):
		return HMAC.new(self.hmac_key,data, SHA256)		

	def read_sector(self,sector):

		buf = self.device.read(sector)

		if self.check_hmac :
			computed_hmac = self.get_hmac(buf).digest()

			self.check_hmac = False
			offset2 = self.offset
			self.seek(self.get_sector_hmac_offset(sector))
			data = self.read(self.hmac_entry_size)
			self.seek(offset2)
			self.check_hmac = True
			saved_hmac = data

			if computed_hmac != saved_hmac:
				s = "sector %d has been modified "  %  (sector)
				print s
				print "reading from %d" % (self.get_sector_hmac_offset(sector))
				print to_hex(computed_hmac)
				print to_hex(str(saved_hmac))
				raise SectorHmacDoesntMatch(s)
		return buf

	def compute_disk_hmac(self):
		
		#print

		for i in range(0,self.active_sectors):
			s = self.device.read(i)
			self.save_sector_hmac(i,s)

		#print "zuo"
		#print self.hmac_section_begin

	def find_modified_sectors(self):
		ret = []
		for i in range(0,int(math.floor(self.size/self.sector_size))):
			if not self.sector_hmac_valid(i):
				ret.append(i)

		return ret


