from ..DiskDrivers import *
from ..util import get_random_sector
import unittest
import os

class DiskDriverTest(object):
	def sector_rw_test(self):
		for i in range(0,self.disk.size,self.disk.sector_size):
			data = get_random_sector(self.disk.sector_size)
			index = int(i/self.disk.sector_size)
			self.disk.write(index,data)
			received  = self.disk.read(index)
			self.assertEqual(data,received)

class FileDiskDriverTest(DiskDriverTest, unittest.TestCase):
	@classmethod
	def setUpClass(self):
		FileDiskDriver.create_disk("unit_test", 1024*1024,1024)
		self.disk = FileDiskDriver("unit_test")
		super(FileDiskDriverTest,self).setUpClass()

	@classmethod
	def tearDownClass(self):
		os.remove("unit_test")


class DropboxDiskDriverTest(DiskDriverTest, unittest.TestCase):
	@classmethod
	def setUpClass(self):
		self.disk = DropboxDiskDriver(1024)
		self.disk.create_disk(10*1024,1024)
		super(DropboxDiskDriverTest,self).setUpClass()

	@classmethod
	def tearDownClass(self):
		self.disk.delete_disk()



