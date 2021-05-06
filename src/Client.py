import select
import signal
import socket
import sys
import time
import scapy.all
import struct
import fcntl, os
import getch
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
#Global Variables
GAME_DURATION=10
UDP_PORT = 13117  # specified port to connect
UDP_HOST = scapy.all.get_if_addr('eth1') #'172.17.0.1'			# The server's hostname or IP address
BROADCAST_LISTEN_ADDRESS= ""


def Main():
	sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)  	# UDP socket
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)	#make IP address reusable


	print (bcolors.BOLD + "UDP host IP:", str(UDP_HOST) + "" + bcolors.ENDC)
	print (bcolors.BOLD + "UDP host Port:", str(UDP_PORT) + "" + bcolors.ENDC)


	sock.bind((BROADCAST_LISTEN_ADDRESS, UDP_PORT))

	def verify_message(data):
		try:
			magic_cookie, message_type, port = struct.unpack('LBH', data)
			if((magic_cookie==0xfeedbeef) and (message_type==2)):
				return port
			else:
				return None
		except:
			return None


	while True:
		print ("Waiting for server..." )
		data,addr = sock.recvfrom(1024)				#receive data from client
		(host,_)=addr
		port=verify_message(data)
		print("server: ",addr[0]," ,",port)
		if(port):
			make_tcp_connection(host,port)


def make_tcp_connection(host,port):
	team_name = "Maccabi Kushilamam City\n"
	try:
		tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		tcp_sock.connect((host, port))					# connect to server on local computer
	except:
		return False
	try:
		# message you send to server
		tcp_sock.send(team_name.encode('ascii'))
	except:
		return False
	try:
		data = tcp_sock.recv(4096)
		if(data):
			print(bcolors.OKCYAN + str(data.decode('ascii')) + bcolors.ENDC)
			game_mode(tcp_sock)
			print("\n\n")
			print(bcolors.BOLD +"Server disconnected, listening for offer requests..." +bcolors.ENDC)
		else:
			return False
	except:
		return False
	try:
		tcp_sock.close()
		return True
	except:
		print("failed in properly closing the connection to server")
		return False

def handler(signal_num,frame):
    raise Exception()

def game_loop(tcp_sock,end_game_time):
	while True:
		try:
			to_read, _, _ = select.select([sys.stdin], [], [], (end_game_time - time.time()))
			if (to_read):
				x=getch.getch()
			tcp_sock.send(x.encode())
		except:
			break

def game_mode(tcp_sock):
	end_game_time= time.time()+GAME_DURATION

	signal.signal(signal.SIGALRM, handler)
	signal.alarm(GAME_DURATION)
	try:
		game_loop(tcp_sock,end_game_time)
	except:
		print("my error")

	signal.alarm(0)

	try:
		summary_msg=tcp_sock.recv(1024)
		if(summary_msg):
			print('\n'+summary_msg.decode())
	except:
		print("getting summary message failed")


if __name__ == '__main__':
	Main()
