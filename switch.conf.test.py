#!/usr/bin/python
# coding: iso-8859-15

import getpass
import sys
import telnetlib
import logging
import argparse
import re
import ipaddress

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',filename='switchconf.log',level=logging.DEBUG)
timeout = 5

def pingTest(ipaddr):
	"""Uses ping to test availability of network devices in subnet given
	
	Returns 0 on success else 1 """
	
	res = subprocess.call(['ping', '-c', '3', '-n', '-w', '1', '-q', ipaddr])
	if res == 0:
		print("ping to ", addr, "OK")
		logging.info('ping to %s OK', addr)
		return True
	elif res == 2:
		print("no response from", addr)
		loggin.info('No response from %s', addr)
		return False
	else:
		print("ping to ", addr, "failed")
		logging.warning('ping to %s failed', addr)
		return False

def runCmd(connection, cmdList):
	"""Running commands given in cmdList using connection
	
	Returns .. """
	i = 0
	
	for cmd in cmdList:
		connection.write("show running-config | i hostname\n")
		(index, match, text) = connection.expect(['\#$'], 5)
		matchObj = re.search(r'(hostname)*(.*)$', text)
		hn = matchObj.group(0)
	#	print("HN: " + matchObj.group() + "\n")
		# Kjører kommando
		connection.write(cmd + "\n")
		(fys, fjas, result) = connection.expect([hn], 5) 
		
		if ('Invalid' in result):
			print ("## Command error. The following command is not working: " + cmd + "\nResult:\n" + result)
			logging.critical("Invalid command: " + cmd)
			return
		
		#(x, y, result) = connection.expect([hn],5)
		logging.info('Command %s and result: %s', i , result)
		i += 1
	return

def login(conn, ip, userName, password):
	"""Logging in to the switch with given ip, username and password
	
	Returns int telling if the login was OK or not""" 
	conn.write(userName + "\n")
		# Venter på string som spør etter passord
	passString = ["Password:", "password:"]
	(index, match, text) = conn.expect(passString, 5)
	# Hvis ingen treff på expect returneres index -1	
	if (index == -1):
		logging.error("Password timeout on %s", ip )
		print("Password timeout on " + ip + "\n")
		return 1
	# Sender passord
	conn.write(password + "\n")
			
	loginResult = ["\#$", "\>$", "invalid", "username:", "Username:", "failed"]
	(index, matchObject, receivedText) = conn.expect(loginResult,timeout)
	if (index == 0):
		logging.info('%s: Login OK', ip)
		return 0
	if (index == 1):
		conn.write("enable\n")
		conn.write(password + "\n")
		# Hvis det spørres etter passord enda engang er enable passordet feil
		enableResult = ["\#$", "foo"]
		(index, matchObject, receivedText) = conn.expect(enableResult,timeout)
		print (receivedText)
		if (index == 1):
			logging.error("Enable passoword is wrong on %s", ip)
			print("Enable password is wrong on " + ip)
			return 1
		logging.info('%s: > enable OK', ip)
		return 0
	if (index > 1):
		logging.error('%s: Invalid login.', ip)
		return 2
	return
	
def tempfunc1(host, cmdlist):
	port = 23
	tacacsStr = 'username:'
	noTacacsStr = 'Username:'
	
	logging.info("------------------ %s --------------------", host)
	# Kobler til host med telnet
	try:
		tn = telnetlib.Telnet(host, port, timeout)
	except:
		logging.warning('Connection error to host %s on port %s', host, port)
		print("\nConnection error to host " + host + "\n")
		return
	# TODO: Legge til en sjekk av om telnet innlogging er OK eller om det må prøves med ssh istedet.
	
	# Venter på angitt string og hvis ikke mottatt på x sekunder legges mottat string i s
	#s = tn.read_until("snorkelfore",timeout)
	(x, y, s) = tn.expect(["sjobing"], 1)
	# Sjekker om det er tacacs brukernavn det spørres etter
	if tacacsStr in s:
		login(tn, host, tUser, tPassword)
			
	# Sjekker om det er lokal bruker det spørres etter
	elif noTacacsStr in s:
		loginResult = login(tn, host, ntUser, ntPassword)
		if(loginResult == 2):
			loginResult = login(tn, host, ontUser, ontPassword)
			if(loginResult == 2):
				# Gammelgammelt passord virket ikke det heller så vi avslutter
				logging.error("OldOld password was invalid on %s", host)
				print("OldOld password was invalid on " + host)
				tn.close()
				return
						
	elif s not in (tacacsStr, noTacacsStr):
		print ("tja")
		sys.exit()
		
	 # Kjører kommando(er)
	runCmd(tn, cmdlist)
	tn.write("exit\n")
	tn.close()
	return

parser = argparse.ArgumentParser(description='Loops through all IPv4 addresses given and executes commands given in <commands>')
group = parser.add_mutually_exclusive_group()
group.add_argument('-i', '--hosts', help='file containing IP addresses of hosts')
group.add_argument('-a', '--address', help='subnet mask in CIDR notation, eg. 10.11.12.0/24 or single IP address')
parser.add_argument('-c', '--commands', default='commands.txt', help='file containing the commands to run')
args = parser.parse_args()

try:
	commandlist = [line.strip() for line in open(args.commands)]
except:
	logging.error('The file %s seems to not exist', args.commands)
	sys.exit("The command file given seems to not exist")

# Brukernavn for tacacs bruker
tUser = input("Entet tacacs username: ")
tPassword = getpass.getpass()

# Brukernavn for bruker konfigurert lokalt på switchen
#ntUser = input("Enter local (not tacacs) username: ")
#ntPassword = getpass.getpass()

# Brukernavn for bruker konfigurert lokalt på switchen (gammel)
#ontUser = input("Enter old local (not tacacs) username: ")
#ontPassword = getpass.getpass()

# Hvis det er gitt en fil med liste over ip adresser legges disse i en liste.
if args.hosts:
	try:
		hostlist = [line.strip() for line in open(args.hosts)]
	except:
		logging.error('The file %s seems to not exist', args.hosts)
		sys.exit("The host file given seems to not exist")
	
	# Går igjennom alle IPene i lista
	for ip in hostlist:
		# Sjekker om dings med IP svarer på ping
		if pingTest(ip):
			# Hvis svar på ping; kjør på
			tempfunc1(ip, commandlist)
	sys.exit()

if args.address:
	iprange = True
	singleIP = True
	
	# TODO: Bruk args.address.num_addresses for å finne ut om det er 1 eller flere adresser.
	# Bruk try til dette for å finne ut om det er gitt en gyldig IP/subnet
	#  
	
	
	try:
		iprange = ipaddress.ip_network(args.address) # Er dette en subnet maske?
	except ValueError:
		iprange = False
		
	try:
		ipaddr = ipaddress.ip_address(args.address) # Er dette en enkel IP adresse?
	except ValueError:
		singleIP = False

	print(args.address)
	print(iprange)
	print(singleIP)
	sys.exit()
	
	if not (iprange or singleIP):
		print('Invalid subnet or IP address.')
		sys.exit()

for ip in hostlist:
	if pingTest(ipaddr):
		tempfunc1(ip, commandlist)
sys.exit()