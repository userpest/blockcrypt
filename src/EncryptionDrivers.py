from Crypto.Cipher import AES
import hashlib
import struct 

class WrongSectorSizeException(Exception):
	def __init__(self,message):
		self.message=message
		super(WrongSectorSizeException, self).__init__()

class EncryptionDriver(object):
	"""
	virtal+testing class
	it DOES NOT PROVIDE ANY FORM OF ENCRYPTION
	"""
	def __init__(self,key,sector_size,block_size):
		self.sector_size = sector_size
		self.key = key
		self.block_size = block_size
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

		if sector_size % self.block_size != 0:
			raise WrongSectorSizeException("sector size must a be multiply of %d", self.block_size)

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
