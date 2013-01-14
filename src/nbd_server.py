#!/usr/bin/python2.7
import struct, socket, sys, time
#modified version of 
#https://code.activestate.com/recipes/577569-nbd-server-in-python/
#i#license:unknown
class NBDServer(object):
	def __init__(self,fp,port):
		self.dev = fp
		self.port = int(port)

	def run(self):
		lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		lsock.bind(('', self.port))
		lsock.listen(5)
		while True:
			(self.asock, self.addr) = lsock.accept()
			self.serveclient()

	def recvall(self,sock, length):
		rv = []
		while sum(map(len, rv)) < length:
			rv.append(sock.recv(length-sum(map(len, rv))))

		assert rv[-1], "no more data to read"
		return ''.join(rv)

	def serveclient(self):
		asock = self.asock
		dev = self.dev
		READ, WRITE, CLOSE = 0,1,2
		"Serves a single client until it exits."
		asock.send('NBDMAGIC\x00\x00\x42\x02\x81\x86\x12\x53' + struct.pack('>Q', dev.size) + '\0'*128);
		while True:
			header = self.recvall(asock, struct.calcsize('>LL8sQL'))
			magic, request, handle, offset, dlen = struct.unpack('>LL8sQL', header)
			assert magic == 0x25609513
			if request == READ:
				self.dev.seek(offset)
				asock.send('gDf\x98\0\0\0\0'+handle)
				#print "begin r"
				asock.send(dev.read(dlen))
				#print "read"
			elif request == WRITE:
				dev.seek(offset)
				dev.write(self.recvall(asock, dlen))
				dev.flush()
				#print "begin w"
				asock.send('gDf\x98\0\0\0\0'+handle)
				#print "write"
			elif request == CLOSE:
				asock.close()
				dev.flush()
				print "close"
				return
			else:
				print "ignored request", request
