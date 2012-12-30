from hashlib import sha256, md5

def to_hex(s):
	lst = []
	for ch in s:
		hv = hex(ord(ch)).replace('0x', '')
		if len(hv) == 1:
			hv = '0'+hv
		lst.append(hv)

	return reduce(lambda x,y:x+y, lst)

def expand_to_256bit(key):
	return sha256(key).digest()
def expand_to_128bit(key):
	return md5.digest(key)

def get_random_sector(sector_size, source ="/dev/urandom" ):
	fp = open(source,"rb")
	data = fp.read(sector_size)
	fp.close()
	return data
#meh we cant use struct to convert 16bytes int ;f
#generally speaking gief python3
def to_bytes(n):
	buf = bytearray()
	while n > 0:
		c = n % 256
		buf=chr(c)+buf
		n = n>>8
	buf=bytearray(16-len(buf))+buf
	return buf

def from_bytes(buf):
	l = len(buf)
	ret = 0 
	while l > 0:
		ret=ret<<8
		ret+=ord(buf[0])
		buf=buf[8:]
		l -= 8

	return ret


#meh i should add operator to bytearray instead
#strings should be equal
def xor_bytes(a,b):
	assert len(a)==len(b)

	ret = bytearray(len(a))
	for i in range(0,len(a)):
		ret[i]=a[i]^b[i]
	return ret

class DummyCrypto(object):
	def __init__(self):
		self.block_size = 16
	def encrypt(self,data):
		return data
	def decrypt(self,data):
		return data
