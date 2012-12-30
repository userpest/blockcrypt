#!/usr/bin/python2.7
import struct, socket, sys, time
from EncryptedBlockDevice import *
from DiskDrivers import *
from EncryptionDrivers import *
import logging
import hashlib
from Crypto.Hash import MD5
# Working: nbd protocol, read/write serving up files, error handling, file size detection, in theory, large file support... not really, so_reuseaddr, nonforking

def recvall(sock, length):
  rv = []
  while sum(map(len, rv)) < length:
    rv.append(sock.recv(length-sum(map(len, rv))))
    assert rv[-1], "no more data to read"
  return ''.join(rv)

def serveclient():
    READ, WRITE, CLOSE = 0,1,2
    "Serves a single client until it exits."
    dev.seek(0, 2)
    asock.send('NBDMAGIC\x00\x00\x42\x02\x81\x86\x12\x53' + struct.pack('>Q', dev.size) + '\0'*128);
    while True:
        header = recvall(asock, struct.calcsize('>LL8sQL'))
        magic, request, handle, offset, dlen = struct.unpack('>LL8sQL', header)
        assert magic == 0x25609513
        if request == READ:
            dev.seek(offset)
            asock.send('gDf\x98\0\0\0\0'+handle)
            asock.send(dev.read(dlen))
            print "read\t0x%08x\t0x%08x" % (offset, dlen), time.time()
        elif request == WRITE:
            dev.seek(offset)
            dev.write(recvall(asock, dlen))
            dev.flush()
            asock.send('gDf\x98\0\0\0\0'+handle)
            print "write\t0x%08x\t0x%08x" % (offset, dlen), time.time()
        elif request == CLOSE:
            asock.close()
	    dev.flush()
            print "closed"
            return
        else:
            print "ignored request", request

if __name__ == '__main__':
    "Given a port and a filename, serves up the file."
    filename = "testing_disk"
    logging.basicConfig(filename='blockcrypt.log',level=logging.DEBUG)
    if not os.path.exists(filename):
	    print "no such file... creating"
	    FileDiskDriver.create_disk(filename, 1024*1024,1024)

    disk = FileDiskDriver(filename)
    key = hashlib.sha256("666").digest() 
    key2 = hashlib.md5("666").digest()
    keys=(key,key2)
    crypto = LRWEncryptionDriver(keys,disk.sector_size)

    dev = EncryptedBlockDevice(crypto,disk)

    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lsock.bind(('', int(sys.argv[1])))
    lsock.listen(5)
    while True:
        (asock, addr) = lsock.accept()
        print "connection from", addr
        serveclient()
