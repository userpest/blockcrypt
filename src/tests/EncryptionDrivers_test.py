import unittest
from ..EncryptionDrivers import *
from ..util import get_random_sector
import hashlib

class EncryptionTest(object):

	@classmethod
	def setUpClass(self):
		self.sector_size = 512
		self.crypto = None
		self.tweak = 1337
		self.plaintext = get_random_sector(self.sector_size)
	

	def test_full_encryption(self):
		for tweak in range(0,500):
			plaintext = get_random_sector(self.sector_size)
			cipher = self.crypto.encrypt(tweak,plaintext)
			decrypted = self.crypto.decrypt(tweak,cipher)
			self.assertEqual(decrypted,plaintext)


class DummyEncryptionTest( EncryptionTest,unittest.TestCase ):
	@classmethod
	def setUpClass(self):
		super(DummyEncryptionTest,self).setUpClass()
		self.crypto = DummyEncryptionDriver(self.sector_size)

class CbcEssivEncryptionDriverTest(EncryptionTest, unittest.TestCase):
	@classmethod
	def setUpClass(self):
		super(CbcEssivEncryptionDriverTest,self).setUpClass()
		key = hashlib.sha256("666").digest() 
		self.crypto = CbcEssivEncryptionDriver(key,self.sector_size)


class TweakableEncryptionTest(EncryptionTest):
	def block_encryption_test(self):
		for i in  range(0,self.sector_size, self.crypto.block_size):
			block = self.plaintext[i:i+self.crypto.block_size]
			cblock = self.crypto.encrypt_block(self.tweak, i/(self.crypto.block_size), block)
			block2 = self.crypto.decrypt_block(self.tweak, i/(self.crypto.block_size),cblock)
			self.assertEqual(block,block2)

		tweak2 = self.tweak+1
		i1 = 0
		i2 = 1
		b1 = self.crypto.encrypt_block(self.tweak,i1, block)
		b2 = self.crypto.encrypt_block(self.tweak,i2,block)
		self.assertNotEqual(b1,b2)

		b1 = self.crypto.encrypt_block(self.tweak,i1, block)
		b2 = self.crypto.encrypt_block(tweak2,i1,block)
		self.assertNotEqual(b1,b2)

		b1 = self.crypto.encrypt_block(self.tweak,i1, block)
		b2 = self.crypto.encrypt_block(tweak2,i2,block)
		self.assertNotEqual(b1,b2)







#class TweakableBlockEncryptionDriverTest(TweakableEncryptionTest,unittest.TestCase):
#	@classmethod
#	def setUpClass(self):
#		super(TweakableBlockEncryptionDriverTest,self).setUpClass()
#		key = hashlib.sha256("666").digest() 
#		self.crypto = TweakableBlockEncryptionDummyDriver(key,self.sector_size)

class LRWEncryptionDriverTest(TweakableEncryptionTest,unittest.TestCase):
	@classmethod
	def setUpClass(self):
		super(LRWEncryptionDriverTest,self).setUpClass()
		key = hashlib.sha256("666").digest() 
		key2 = hashlib.md5("666").digest()
		self.crypto = LRWEncryptionDriver((key,key2),self.sector_size)

class XTSEncryptionDriverTest(TweakableEncryptionTest,unittest.TestCase):
	@classmethod
	def setUpClass(self):
		super(XTSEncryptionDriverTest,self).setUpClass()
		key = hashlib.sha256("666").digest() 
		key2 = hashlib.sha256("1337").digest() 
		self.crypto = XTSEncryptionDriver((key,key2),self.sector_size)

class XEXEncryptionDriverTest(TweakableEncryptionTest,unittest.TestCase):
	@classmethod
	def setUpClass(self):
		super(XEXEncryptionDriverTest,self).setUpClass()
		key = hashlib.sha256("666").digest() 
		self.crypto = XEXEncryptionDriver(key,self.sector_size)

