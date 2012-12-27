class EncryptionDriver(object):
	"""
	virtal+testing class
	it DOES NOT PROVIDE ANY FORM OF ENCRYPTION
	"""
	def __init__(self,sector_size):
		self.sector_size = sector_size
	def encrypt(self,sector,plaintext,ciphertext,write_begin,write_end):
		pass
	def decrypt(self,sector,ciphertext):
		pass

class DummyEncryptionDriver(EncryptionDriver):
	"""
	testing class
	it DOES NOT PROVIDE ANY FORM OF ENCRYPTION
	"""
	def __init__(self,sector_size):
		super(DummyEncryptionDriver,self).__init__(sector_size)
	def encrypt(self,sector,plaintext,ciphertext,write_begin,write_end):
		buf = ciphertext[:write_begin]+plaintext+ciphertext[write_end:]
		return buf
	def decrypt(self,sector,ciphertext):
		return ciphertext


