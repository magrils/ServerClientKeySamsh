import socket
import select
import time
import scapy.all
import struct
from _thread import *
import threading
import signal


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

#Global variables
#Network Parmaters:

HOST =   scapy.all.get_if_addr('eth1') #'172.17.0.1'                   # Host IP
PORT = 13000			                                             # specified PORT to connect
BROADCAST_DEST_PORT = 13117  # destenation PORT for broadcast
BROADCAST_ADDR =   '172.1.255.255' #'172.17.255.255'             # broadcast IP
#Game Paramters
GAME_DURATION=10
WAIT_TIME=10
BROADCAST_INTERVAL = 1.0
#Game Data
start_msg = ''
summary_msg=''
game_is_alive = True
groups = [[], []]
score_board = [0,0]
#statictics (count,...)
game_lock = threading.Lock()
server_lock = threading.Lock()
latch = threading.Condition()


def Main():
    # start tcp socket
    tcp_sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)	    #make IP address reusable
    tcp_sock.bind((HOST,PORT))
    tcp_sock.listen()
    print (bcolors.OKBLUE+ "Server started, listening on IP address ",HOST + bcolors.ENDC)

    #start udp socket
    udp_sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)  # UDP socket
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def int_handler(sig, frame):
        print("exiting gracefully")
        try:
            tcp_sock.close()
        except:
            print("Error closing server TCP socket...") #debug print
        try:
            udp_sock.close()
        except:
            print("Error closing server TCP socket...")  # debug print
        exit()

    signal.signal(signal.SIGINT, int_handler)

    while True:
        start_server(PORT,udp_sock,tcp_sock)
        game_mode()
        print(bcolors.BOLD + "Game over, sending out offer requests..." + bcolors.ENDC)



def make_offer(port):
    offer=struct.pack('LBH',0xfeedbeef,0x2,port)
    return offer


def start_server(PORT,udp_sock,tcp_sock):
    offer_str = make_offer(PORT)

    nextCastTime = time.time()                                      # When we want to send the next periodic-ping-message out
    start_time=nextCastTime
    team_index=0
    while (start_time+WAIT_TIME>=time.time()):
        secondsUntilNextCast = nextCastTime - time.time()
        if (secondsUntilNextCast < 0):
            secondsUntilNextCast = 0

                                                                    # select() won't return until 'udp_sock' has some data
                                                                    # ready-for-read, OR until secondsUntilNextPing seconds
                                                                    # have passed, whichever comes first
        ready_to_read_list, _ , _ = select.select([tcp_sock], [], [], secondsUntilNextCast) #using select timeout in order to time 
        if (tcp_sock in ready_to_read_list):                   # There's an a new TCP connection to accept!
            if gather_client(tcp_sock,team_index):
                team_index+=1


        now = time.time()
        if (now >= nextCastTime):
            # Time to send out the next Cast!
            udp_sock.sendto(offer_str, (BROADCAST_ADDR, BROADCAST_DEST_PORT))
            nextCastTime = now + BROADCAST_INTERVAL  # do it again in another second



def gather_client(tcp_sock,team_index):
    try:
        client_sock,addr=tcp_sock.accept()
        team_name= client_sock.recv(128)
        #server_lock.acquire()
        start_new_thread(thread_life, (client_sock,team_name.decode(),team_index))
        #server_lock.release()
        return True
    except:
        return False


def thread_life(c, team_name,team_index):
    sign_up(team_index,team_name)       # add team to a group
    latch.acquire()
    latch.wait()                        # wait until game starts
    latch.release()
    end_game_time= time.time() + GAME_DURATION
    try:
        c.send(start_msg.encode())
    except:
        print('team \'', team_name , '\' has disconnected')             #debug print

    while True:
        try:

            to_read,_,_=select.select([c],[],[],(end_game_time-time.time()))
            if(c in to_read):
                data = c.recv(1024)
                if not data:
                    break
                update_to_game_stats(team_index,team_name,data.decode())    # update score and other statistic
        except:
            break
    latch.acquire()
    if game_is_alive:
        latch.wait() # check if game is over
    latch.release()
                                                               # connection closed

    try:
        c.send(summary_msg.encode())
    except:
        print("sending summary message failed")
    try:
        c.close()
    except:
        print('team \'', team_name, '\' has disconnected')              # debug print


def sign_up(team_index,team_name):
    game_lock.acquire()
    groups[team_index%len(groups)].append(str(team_name))
    game_lock.release()


def update_to_game_stats(team_index,team_name,data):
    global score_board
    game_lock.acquire()
    score_board[team_index] += len(data)
    game_lock.release()

def game_mode():
    make_start_msg()
    print(bcolors.OKCYAN + start_msg + bcolors.ENDC)
    latch.acquire()
    latch.notify_all()          # notify all threads about game starting
    latch.release()

    time.sleep(GAME_DURATION)

    latch.acquire()
    global game_is_alive
    game_is_alive = False
    make_summary_msg()
    latch.notify_all()
    latch.release()

    init_game_data()        #re-instate initial (new) game data


def make_start_msg():
    global start_msg
    game_lock.acquire()
    seperator = '\n'
    start_msg = f"Group 1:\n ==\n{seperator.join(groups[0])}\nGroup 2:\n==\n{seperator.join(groups[1])}\n\nStart pressing keys on your keyboard as fast as you can!!"
    game_lock.release()


def make_summary_msg():

    game_lock.acquire()
    global summary_msg
    winner_index= 0
    winner_str = "Group 1 wins!"
    if score_board[0] < score_board[1] :
        winner_index= 1
        winner_str = "Group 2 wins!"
    group_string = '\n'.join(groups[winner_index])
    winner_str+="\nCongratulations to the winners:\n==\n"+group_string
    if score_board[0] == score_board[1]:
        winner_str = "its a TIE!!!!!"
    summary_msg = """Game over!\nGroup 1 typed in """+str(score_board[0])+""" characters. Group 2 typed in """+str(score_board[1])+""" characters.\n"""+winner_str
    game_lock.release()
    print(bcolors.OKGREEN + summary_msg + bcolors.ENDC)


def init_game_data():
    global score_board
    global groups
    global game_is_alive
    game_lock.acquire()
    score_board=[0,0]
    groups = [[], []]
    game_is_alive = True
    game_lock.release()




if __name__ == '__main__':
    Main()
