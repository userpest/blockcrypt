from Crypto.Cipher import AES
import hashlib
import struct 
import math
from gf2n import * 
from util import *



class WrongSectorSizeException(Exception):
	def __init__(self,message):
		self.message=message
		super(WrongSectorSizeException, self).__init__()

class EncryptionDriver(object):
	"""
	virtual class
	"""
	def __init__(self,key,sector_size,block_size):
		self.sector_size = sector_size
		self.key = key
		self.block_size = block_size

		if sector_size % block_size != 0:
			raise WrongSectorSizeException("sector size must a be multiply of %d", self.block_size)
	def encrypt(self,sector,plaintext,ciphertext,write_begin,write_end):
		pass
	def decrypt(self,sector,ciphertext):
		pass

class DummyEncryptionDriver(EncryptionDriver):
	"""
	testing class
	it DOES NOT PROVIDE ANY FORM OF ENCRYPTION
	"""
	def __init__(self,key,sector_size):
		super(DummyEncryptionDriver,self).__init__(None,sector_size)
	def encrypt(self,sector,plaintext,ciphertext,write_begin,write_end):
		buf = ciphertext[:write_begin]+plaintext+ciphertext[write_end:]
		return buf
	def decrypt(self,sector,ciphertext):
		return ciphertext

class CbcEssivEncryptionDriver(EncryptionDriver):
	"""
	uses sha256 for the hash generation
	"""
	def __init__(self,key,sector_size):
		super(CbcEssivEncryptionDriver,self).__init__(key,sector_size,AES.block_size)
		#ECB mode! dont use for anything > 32 byte size pls
		essiv_key = hashlib.sha256(key).digest()
		self.essiv_cipher = AES.new(essiv_key,AES.MODE_ECB)


	def get_iv(self,sector):
		buf = struct.pack('Q',sector)
		buf+= chr(6)*(self.block_size-len(buf))
		buf = self.essiv_cipher.encrypt(buf)
		return buf

	def encrypt(self,sector,plaintext,ciphertext,write_begin,write_end):
		block = self.decrypt(sector,ciphertext)
		plaintext = block[:write_begin]+plaintext+block[write_end:]
		iv = self.get_iv(sector)
		cipher = AES.new(self.key,AES.MODE_CBC, IV = iv)
		ciphertext = cipher.encrypt(plaintext)
		return ciphertext
		
	def decrypt(self,sector,ciphertext):
		iv = self.get_iv(sector)	
		cipher = AES.new(self.key,AES.MODE_CBC, IV = iv)
		plaintext = cipher.decrypt(ciphertext)
		return plaintext

class TweakableBlockEncryptionDriver(EncryptionDriver):
	def get_block(self,offset):
		return (math.floor(offset/self.block_size), offset%self.block_size)

	def encrypt_block(self,sector,block,plaintext):
		return plaintext

	def decrypt_block(self,sector,block,ciphertext):
		return ciphertext

	def decrypt(self,sector,ciphertext):
		plaintext = bytearray()

		for i in range(0,self.sector_size,self.block_size):
			plaintext += self.decrypt_block(sector,i,ciphertext[i:i+self.block_size])

		return plaintext

	def encrypt(self,sector,plaintext,ciphertext,write_begin,write_end):
		block_size = self.block_size
		plaintext_size = len(plaintext)

		pos = write_begin
		end = write_end
		
		block =  self.get_block(pos)[0]
		modification_start=block*block_size
		block = self.get_block(end-1)[0]
		modification_end = (block)*block_size
		buf = bytearray()
		while plaintext_size > 0 :
			(block, block_offset) = self.get_block(pos)	
			write_begin = block_offset
			write_end = min(plaintext_size+block_offset,block_size)
			write_size = write_end-write_begin

			block_pos = block*block_size

			cipher_block = ciphertext[block_pos:block_pos+block_size]
			cipher_block = self.decrypt_block(sector,i,cipher_block)
			cipher_block=cipher_block[:write_begin]+plaintext[:write_size]+cipher_block[write_end:]
			cipher_block = self.encrypt_block(sector,block,cipher_block)

			buf+=cipher_block

			plaintext=plaintext[write_size:]
			plaintext_size-=write_size
			pos+=write_size

		ret = ciphertext[:modification_start]+buf+ciphertext[modification_end:]
		return ret
	
class LRWEncryptionDriver(TweakableBlockEncryptionDriver):
	def __init__(self,keys,sector_size):
		super(LRWEncryptionDriver,self).__init__(keys,sector_size)
		self.crypto = AES.new(self.key[0])
	def get_x(self,index):
		x = gf2pow128mul(self.key[1], index)
		x=to_bytes(x)
		return x

	def get_phys_index(self,sector,block):
		return sector*self.sector_size+block*self.block_size

	def encrypt_block(self,sector,block,plaintext):
		index = self.get_phys_index(sector,block)
		x = self.get_x(index)
		e = xor_bytes(x,plaintext)
		e = self.crypto.encrypt(e)
		e = xor_bytes(e,x)
		return e

		
	def decrypt_block(self,sector,block,ciphertext):
		index = self.get_phys_index(sector,block)
		x = self.get_x(index)
		e = xor_bytes(ciphertext,x)
		e = self.cipher.decrypt(e)
		e = xor_bytes(e,x)
		return e


class XTSEncryptionDriver(TweakableBlockEncryptionDriver):
	def __init__(self,key,sector_size):
		self.x_crypto = AES.new(key[1])
		self.crypto = AES.new(key[0])

	def get_x(self,sector,block):
		index = to_bytes(sector)
		x = self.x_crypto.encrypt(index)
		x = from_bytes(x)
		block = gf2pow128powof2(block)
		x = gf2pow128mul(x,block)
		x = to_bytes(x)
		return x
			
	def encrypt_block(self,sector,block,plaintext):
		x = self.get_x(sector,block)	
		buf = xor_bytes(x,plaintext)
		buf = self.crypto.encrypt(buf)
		buf = xor_bytes(x,buf)
		return buf


	def decrypt_block(self,sector,block,ciphertext):
		x = self.get_x(sector,block)
		buf = xor_bytes(x,ciphertext)
		buf = self.crypto.decrypt(buf)
		buf = xor_bytes(x,buf)
		return buf



class XEXEncryptionDriver(XTSEncryptionDriver):
	def __init__(self,key,sector_size):
		super(XEXEncryptionDriver,self).__init__((key,key),sector_size)


