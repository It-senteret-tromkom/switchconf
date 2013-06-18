#!/usr/bin/python3.3
# coding: iso-8859-15

import os
import getpass
import telnetlib
import logging
import re
import subprocess
#from concurrent.futures._base import LOGGER
#from subprocess import STDOUT

# Set up logging to file
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s', #   %(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                 #   datefmt='%m-%d %H:%M',
                    filename='info.log',
                    filemode='w')
# Define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.INFO)
# Set a format which is simpler for console use
formatter = logging.Formatter('%(levelname)-8s %(message)s')
# Tell the handler to use this format
console.setFormatter(formatter)
# Add the handler to the root logger
logging.getLogger('').addHandler(console)

##logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',filename='switchconf.log',level=logging.DEBUG)
timeout = 5

def user_pass(askpassd):
    """Prompts for username and password
    
    Returns a dictionary with usernames and passwords"""
    # Dictionary to keep usernames and passwords
    userpassdict = {}
    
    if (askpassd['tac']):
        # Ask for tacacs user name and password
        userpassdict['tacacsUser'] = input('Enter tacacs username: ')
        userpassdict['tacacsPassword'] = getpass.getpass()
    else:
        userpassdict['tacacsUser'] = False
        userpassdict['tacacsPassword'] = False
    
    if (askpassd['notac']):
        # Ask for locally configured username and password
        userpassdict['noTacacsUser'] = input("Enter local (not tacacs) username: ")
        userpassdict['noTacacsPassword'] = getpass.getpass()
    else:
        userpassdict['noTacacsUser'] = False
        userpassdict['noTacacsPassword'] = False
    
    if (askpassd['old']):
        # Ask for old locally configured username and password
        userpassdict['oldUser'] = input("Enter old local (not tacacs) username: ")
        userpassdict['oldPassword'] = getpass.getpass()
    else:
        userpassdict['oldUser'] = False
        userpassdict['oldPassword'] = False
    
    return userpassdict

def _ping_test(ipaddr):
    """Uses ping to test availability of network devices in subnet given
    
    Returns True on success else False """
    FNULL = open(os.devnull, 'w')
    # TODO: Use subprocess.check_call instead
    res = subprocess.call(['ping', '-c', '3', '-n', '-w', '2', '-q', '-i', '0.3', ipaddr], stdout=FNULL, stderr=subprocess.STDOUT)
    if res == 0: # 0 = ping OK
        msg = "ping to", ipaddr, "OK"
        logging.debug(msg)
        return True
    
    elif res == 1: # 1 = ingen svar eller færre enn 'count' (-c) antall pakker mottatt innen 'deadline' (-w)
        msg = "No ping response from", ipaddr
        #print(msg)
        logging.debug(msg)
        return False
    
    elif res == 2: # 2 = ping med andre feil
        msg = "Some ping error on", ipaddr
        logging.warning(msg)
        return False
    
    else:
        msg = "ping to ", ipaddr, "failed"
        logging.warning(msg)
        return False

def _run_cmd(connection, cmdList):
    """Running commands given in cmdList using connection
    
    Returns .. """
    i = 0
    
    logging.debug('Running commands in command list.')
    for cmd in cmdList:
        # TODO: Sjekke om kommandoen ikke er i FY lista
      #  if (cmd in blacklist):
       #     logging.error("Command 2")
        #    return False
        cmd = cmd.encode('utf8')
        connection.write("show running-config | i hostname\n".encode('utf8'))
        (index, match, text) = connection.expect([b'\#$'], 2)
        matchObj = re.search(b'(hostname)*(.*)$', text)
        hn = matchObj.group(0)
        # Kjører kommando
        connection.write(cmd)
        connection.write('\n'.encode('utf8'))
        (fys, fjas, result) = connection.expect([hn], 2) 
        
        if (b'Invalid' in result):
            logging.error("Invalid command: " + cmd.decode('utf8') + '\n')
            return False
        
        logging.info(result.decode('utf8'))
        i += 1
    # Exists and closes connection
    connection.write("exit\n".encode('utf8'))
    connection.write("exit\n".encode('utf8'))
    connection.close()
    return True

def _login(conn, ip, userName, password):
    """Logging in to the switch with given ip, username and password
    
    Returns int telling if the login was OK or not"""
    try:
        strusername = userName.encode('utf8')
    except:
        strusername = userName
        
    try:
        strpassword = password.encode('utf8')
    except:
        strpassword = password
    
    conn.write(strusername)
    conn.write('\n'.encode('utf8'))
    # Venter på string som spør etter passord
    passString = [b"Password:", b"password:"]
    (index, match, text) = conn.expect(passString, 5)
    # Hvis ingen treff på expect returneres index -1    
    if (index == -1):
        logging.error("Password timeout on %s", ip )
        return 1
    # Sender passord
    conn.write(strpassword)
    conn.write('\n'.encode('utf8'))
            
    loginResult = [b"\#$", b"\>$", b"invalid", b"username:", b"Username:", b"failed", b"Enter old password"]
    (index, matchObject, receivedText) = conn.expect(loginResult,timeout)
    if (index == 0):
        logging.info('##### Login OK on %s #####', ip)
        return 0
    if (index == 1):
        conn.write("enable\n".encode('utf8'))
        conn.write(strpassword)
        conn.write('\n'.encode('utf8'))
        # Hvis det spørres etter passord enda engang er enable passordet feil
        enableResult = [b"\#$", b"foo"]
        (index, matchObject, receivedText) = conn.expect(enableResult,timeout)
        print (receivedText)
        if (index == 1):
            logging.error("Enable passoword is wrong on %s", ip)
            print(("Enable password is wrong on " + ip))
            return 1
        logging.debug('%s: > enable OK', ip)
        return 0
    if (index > 1):
        logging.error('%s: Invalid login.', ip)
        return 2
        
def _connect(host, userpass):
    port = 23
    tacacsStr = 'username:'
    noTacacsStr = 'Username:'
    
    # Kobler til host med telnet
    try:
        tn = telnetlib.Telnet(host, port, timeout)
    except:
        logging.info('Cant connect to %s on port %s. Probably no telnet support on device.', host, port)
        return False
    # TODO: Legge til en sjekk av om telnet innlogging er OK eller om det må prøves med ssh istedet.
    
    # Venter på angitt string og hvis ikke mottatt på x sekunder legges mottat string i s
    (x, y, s) = tn.expect([b"fjopps"], 1)
    if tacacsStr in str(s): # TACACS user?
        loginResult = _login(tn, host, userpass['tacacsUser'], userpass['tacacsPassword'])
        if (loginResult == 0):
            return tn
        else:
            return False
        
    elif ( (noTacacsStr in str(s)) and (userpass['noTacacsUser'] == True) ): # Local user?
        loginResult = _login(tn, host, userpass['noTacacsUser'], userpass['noTacacsPassword'])
        if (loginResult == 0):
            return tn
        
        elif( (loginResult == 2) and (userpass['oldUser'])):
            loginResult = _login(tn, host, userpass['oldUser'], userpass['oldPassword'])
            if (loginResult == 0):
                return tn
        
            elif(loginResult == 2):
                # Gammelgammelt passord virket ikke det heller så vi avslutter
                logging.error("OldOld password was invalid on %s", host)
                tn.close()
                return False
                        
    elif str(s) not in (tacacsStr, noTacacsStr):
        logging.info("Not possible to log in to %s. It might not be a Cisco switch.", host)
        return False
    
def do_conf(ip, cmdlist, updict):
    """Tries to connect and log into given IP address using usernames and 
    passwords in updict (dictionary) and runs command(s) in the commands list
    
    Returns xx"""
    # If no answer to ping there is no need to try to connect and run commands
    logging.debug("## ------------------ %s -------------------- ##", ip)
    if (_ping_test(ip)):
        con = _connect(ip, updict)
        if (con):
            cmd_success = _run_cmd(con, cmdlist)
            return cmd_success
    else:
        return False         
    