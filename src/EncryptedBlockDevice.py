#!/usr/bin/python2.7
import math

class EncryptedBlockDevice(object):

	def __init__(self,EncryptionDriver,DeviceDriver):
		self.crypto = EncryptionDriver
		self.device = DeviceDriver
		self.sector_size = DeviceDriver.sector_size

	def seek(self,offset,from_what):
		self.device.seek(offset,from_what)

	def read(self,size):
		buf = bytearray()
		device = self.device
		offset = device.offset
		for (sector,ciphertext) in device.read(size):
# 			sector data belongs to [sector_begin, sector_end)
			sector_begin = sector*device.sector_size
			sector_end = sector_begin+device.sector_size
			plaintext = self.crypto.decrypt(sector,ciphertext)	
			begin = 0
			end = sector_size 

			if sector_begin < offset:
				begin = offset-sector_begin

			if sector_end > offset+size:
				end = offset+size - sector_begin 

			buf+=plaintext[begin:end]

	
		return buf

	def write(self,plaintext):
		#TODO:optimize
		for i in range(0,math.ceil(float(data_len)/sector_size)):

			begin = 0 
			end = sector_size

			plaintext_len = len(plaintext)		
			plaintext_end = plaintext_len
			space_in_sector = sector_size

			(sector, ciphertext,offset) = device.get_current_sector()	

			if offset != 0:
				space_in_sector-=offset
				begin = offset	

			if plaintext_len > space_in_sector:
				data_end = space_in_sector + 1
				
			if plaintext_len < space_in_sector:
				end = begin+plaintext_len
		
			ciphertext = crypto.encrypt.(sector,plaintext[:plaintext_end],ciphertext,begin,end)
			
			device.write(sector,ciphertext,end)
			plaintext=plaintext[plaintext_end:]

			
		
