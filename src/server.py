#!/usr/bin/python2.7
import struct, socket, sys, time,argparse
from EncryptedBlockDevice import *
from DiskDrivers import *
from EncryptionDrivers import *
import logging
import hashlib
from Crypto.Hash import MD5
from nbd_server import NBDServer

parser = argparse.ArgumentParser(description="NBD server for encrypted block devices\
		please ensure that the server port is protected by firewall\
		and there are no other users present in the system")
parser.add_argument("-k1", "--key1", help="1rst encryption key", type=str,required=True)
parser.add_argument("-k2", "--key2", help="2cnd encryption key required for xts and lrw", type=str)
parser.add_argument("-c", "--encryption", help="encryption mode, default is cbc", type=str,choices=['cbc','xts','xex', 'lrw'],default='cbc')
parser.add_argument("-d", "--device", help="block device of your choice, default is file", type=str,choices=['file','hdd', 'dropbox'], default='file')
parser.add_argument("--hmac-key", help="hmac key required if -m specified", type=str)
parser.add_argument("-m", "--use_hmac", help="specify whether to use hmac or not", action='store_true')
parser.add_argument("-f", "--filename", help="encrypted file/hard disk required for -d=file & hdd", type=str)
parser.add_argument("--create", help="specify whether to create a new disk or not", action='store_true')
parser.add_argument("--sector_size", help="disk sector size in bytes, obsolete for --create must be a multiple of 16 , defaults to 1024", type=int, default = 1024)
parser.add_argument("--disk_size", help="disk size in bytes, obsolete for --create, must be a multiple of sector_size defaults to 1MB", type=int, default = 1024*1024)
parser.add_argument("-p","--port", type=int, default=1337, help="server port, defaults to 1337")
parser.add_argument("-cs", "--cache_size", help="disk cache size, defaults to 10MB", default=1024*1024*10,type=int)

args = parser.parse_args()

key1 = expand_to_256bit(args.key1)
sector_size = args.sector_size

if args.device== 'file':
	if args.filename==None:
		print "you must specify the file path for the image file"
		sys.exit(1)
	if args.create:
		FileDiskDriver.create_disk(args.filename,  args.disk_size,args.sector_size)

	fp = FileDiskDriver(args.filename)


if args.device =='hdd':
	fp = HDDDiskDriver(filename)

if args.device == 'dropbox':
	if args.create:
		DropboxDiskDriver().create(sector_size,args.disk_size)

	fp = DropboxDiskDriver(args.cache_size)


if args.encryption == 'cbc':
	crypto = CbcEssivEncryptionDriver(key1,sector_size)

if args.encryption == 'xts':
	if args.key2 == None:
		print "xts mode requires two keys"
		sys.exit(1)
	key2 = expand_to_256bit(args.key2)
	crypto = XTSEncryptionDriver((key1,key2),sector_size)

if args.encryption == 'xex':
	crypto = XEXEncryptionDriver(key1,sector_size)

if args.encryption == 'lrw':
	if args.key2 == None:
		print "lrw mode requires two keys"
		sys.exit(1)
	print "there are some security concerns about this mode"
	print "check https://en.wikipedia.org/wiki/IEEE_P1619#LRW_issue for additional details"

	key2 = expand_to_128bit(args.key2)
	crypto = LRWEncryptionDriver((key1,key2),sector_size)

if args.use_hmac:
	if args.hmac_key == None:
		print "you need to specify hmac key"
		sys.exit(1)
	dev = EncryptedBlockDeviceWithHmac(crypto,fp,args.hmac_key)

	if args.create:
		dev.compute_disk_hmac()
else:
	dev = EncryptedBlockDevice(crypto,fp)


server = NBDServer(dev,args.port)
server.run()
