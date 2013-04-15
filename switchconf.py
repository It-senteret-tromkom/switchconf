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

import getpass
import sys
import telnetlib
import logging
import argparse
import re
import ipaddress
import subprocess

# Brukernavn for tacacs bruker
#tUser = input('Entet tacacs username: ')
#tPassword = getpass.getpass()

# Brukernavn for bruker konfigurert lokalt på switchen
#ntUser = input("Enter local (not tacacs) username: ")
#ntPassword = getpass.getpass()

# Brukernavn for bruker konfigurert lokalt på switchen (gammel)
#ontUser = input("Enter old local (not tacacs) username: ")
#ontPassword = getpass.getpass()



parser = argparse.ArgumentParser(description='Loops through all IPv4 addresses given and executes commands given in <commands>')
group = parser.add_mutually_exclusive_group()
group.add_argument('-i', '--hosts', help='file containing IP addresses of hosts')
group.add_argument('-a', '--address', help='subnet mask in CIDR notation, eg. 10.11.12.0/24 or single IP address')
parser.add_argument('-c', '--commands', default='commands.txt', help='file containing the commands to run')
args = parser.parse_args()

# Sjekker om fila som skal inneholde kommandoer er tilgjengelig
try:
	commandlist = [line.strip() for line in open(args.commands)]
except:
	logging.error('The file %s seems to not exist', args.commands)
	sys.exit("The commands file given seems to not exist")

# Hvis det er gitt en fil med ip adresser legges disse i en liste.
if args.hosts:
	try:
		hostsfromfile = [line.strip() for line in open(args.hosts)]
	except:
		logging.error('The file %s seems to not exist', args.hosts)
		sys.exit("The host file given seems to not exist")
	
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

	#print(args.address)
	#print(IPrange)
	#print(singleIP)
			
	if IPrange:
		for ip in IPrange.hosts():
			stringIP = str(ip)
			if pingTest(stringIP):
				tempfunc1(stringIP, commandlist)
	elif singleIP:
		stringIP = str(singleIP)
		if pingTest(stringIP):
			tempfunc1(stringIP, commandlist)
	else:
		print('Invalid subnet or IP address.')
		sys.exit()
	
if args.hosts:
	hostsfromfile = args.hosts	
	for ip in hostsfromfile:
		if pingTest(ip):
			tempfunc1(ip, commandlist)
sys.exit()