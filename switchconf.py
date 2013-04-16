#!/usr/bin/python3.3
# coding: iso-8859-15

'''
switchmod -- shortdesc

switchmod is a description

It defines classes_and_methods

@author:     Tomas Løkken
        
@copyright:  2013 IT-senteret, Tromsø kommune. All rights reserved.
        
@license:    license

@contact:    tomas.lokken@tromso.kommune.no
@deffield    updated: Updated
'''

import sys
import logging
import argparse
import ipaddress
import switchmod

parser = argparse.ArgumentParser(description=
								'Loops through all IPv4 addresses given and executes commands given in <commands>')
group = parser.add_mutually_exclusive_group()
group.add_argument('-f', '--file', help='file containing IP addresses of hosts')
group.add_argument('-a', '--address',
					help='subnet mask in CIDR notation, eg. 10.11.12.0/24 or single IP address')
parser.add_argument('-c', '--commands',
					default='commands.txt', help='file containing the commands to run')
parser.add_argument('-t', '--tacacsuser', help='ask for TACACS username and password', 
					action="store_true")
parser.add_argument('-l', '--localuser', help='ask for local username and password',
					action="store_true")
parser.add_argument('-o', '--olduser', help='ask for old local username and password',
					action="store_true")
args = parser.parse_args()

# If not argument is given, print help and exit
if (len(sys.argv) == 1):
	parser.print_help()
	sys.exit(1)

# Sjekker om fila som skal inneholde kommandoer er tilgjengelig
try:
	commandlist = [line.strip() for line in open(args.commands)]
except:
	logging.error('The file %s seems to not exist', args.commands)
	sys.exit("The commands file given seems to not exist")

askpassd = {}
askpassd['tac'] = args.tacacsuser
askpassd['notac'] = args.localuser
askpassd['old'] = args.olduser  

def run(askpassd, ip):
	userpassd = switchmod.user_pass(askpassd)
	switchmod.do_conf(ip, commandlist, userpassd)

# If a file with IP addresses is given
if args.file:
	try:
		hostsfromfile = [line.strip() for line in open(args.file)] # Make list
	except:
		logging.error('The file %s seems to not exist', args.file)
		sys.exit("The host file given seems to not exist")
		
	# Run commands on each IP in the file
	for ip in hostsfromfile:
		run(askpassd, ip)
	
# Hvis IP adresser er gitt med '-a'
if args.address:
	IPrange = True
	singleIP = True
	
	try:
		IPrange = ipaddress.ip_network(args.address) # Er dette en subnet maske?
		if IPrange.num_addresses < 2:
			IPrange = False
	except ValueError:
		IPrange = False

	try:
		singleIP = ipaddress.ip_address(args.address) # Er dette en enkel IP adresse?
	except ValueError:
		singleIP = False

	if IPrange:
		for ip in IPrange.hosts():
			stringIP = str(ip)
			run(askpassd, stringIP)
			
	elif singleIP:
		stringIP = str(singleIP)
		run(askpassd, stringIP)
		
	else:
		print('Invalid subnet or IP address.')
		sys.exit()

sys.exit()