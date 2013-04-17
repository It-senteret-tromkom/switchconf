#!/usr/bin/python3.3
# coding: iso-8859-15

import getpass
import sys
import telnetlib
import logging
import re
import subprocess

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',filename='switchconf.log',level=logging.DEBUG)
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
    res = subprocess.call(['ping', '-c', '3', '-n', '-w', '3', '-q', ipaddr])
    if res == 0: # 0 = ping OK
        msg = "ping to", ipaddr, "OK"
        print(msg)
        logging.info(msg)
        return True
    
    elif res == 1: # 1 = ingen svar eller f�rre enn 'count' (-c) antall pakker mottatt innen 'deadline' (-w)
        msg = "No response from", ipaddr
        print(msg)
        logging.info(msg)
        return False
    
    elif res == 2: # 2 = ping med andre feil
        msg = "Some ping error on", ipaddr
        print(msg)
        logging.warning(msg)
        return False
    
    else:
        msg = "ping to ", ipaddr, "failed"
        print(msg)
        logging.warning(msg)
        return False

def _run_cmd(connection, cmdList):
    """Running commands given in cmdList using connection
    
    Returns .. """
    i = 0
    
    for cmd in cmdList:
        # TODO: Sjekke om kommandoen ikke er i FY lista
        if (cmd in blacklist):
            loggin.error("Command 2")
            return False
        cmd = cmd.encode('utf8')
        connection.write(b"show running-config | i hostname\n")
        (index, match, text) = connection.expect([b'\#$'], 5)
        matchObj = re.search(b'(hostname)*(.*)$', text)
        hn = matchObj.group(0)
        # Kj�rer kommando
        connection.write(cmd)
        connection.write('\n'.encode('utf8'))
        (fys, fjas, result) = connection.expect([hn], 5) 
        
        if (b'Invalid' in result):
            print("## Command error. The following command is not working: " + cmd.decode('utf8') + "\nResult:\n" + result.decode('utf8'))
            logging.critical("Invalid command: " + cmd.decode('utf8'))
            return False
        
        logging.info('Command %s and result: %s', i , result.decode('utf8'))
        print(result.decode('utf8'))
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
    # Venter p� string som sp�r etter passord
    passString = [b"Password:", b"password:"]
    (index, match, text) = conn.expect(passString, 5)
    # Hvis ingen treff p� expect returneres index -1    
    if (index == -1):
        logging.error("Password timeout on %s", ip )
        print(("Password timeout on " + ip + "\n"))
        return 1
    # Sender passord
    conn.write(strpassword)
    conn.write('\n'.encode('utf8'))
            
    loginResult = [b"\#$", b"\>$", b"invalid", b"username:", b"Username:", b"failed", b"Enter old password"]
    (index, matchObject, receivedText) = conn.expect(loginResult,timeout)
    if (index == 0):
        logging.info('%s: Login OK', ip)
        return 0
    if (index == 1):
        conn.write("enable\n")
        conn.write(password + "\n")
        # Hvis det sp�rres etter passord enda engang er enable passordet feil
        enableResult = ["\#$", "foo"]
        (index, matchObject, receivedText) = conn.expect(enableResult,timeout)
        print (receivedText)
        if (index == 1):
            logging.error("Enable passoword is wrong on %s", ip)
            print(("Enable password is wrong on " + ip))
            return 1
        logging.info('%s: > enable OK', ip)
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
        logging.warning('Connection error to host %s on port %s', host, port)
        print(("\nConnection error to host " + host + "\n"))
        return False
    # TODO: Legge til en sjekk av om telnet innlogging er OK eller om det m� pr�ves med ssh istedet.
    
    # Venter p� angitt string og hvis ikke mottatt p� x sekunder legges mottat string i s
    (x, y, s) = tn.expect([b"fjopps"], 1)
    if tacacsStr in str(s): # TACACS user?
        loginResult = _login(tn, host, userpass['tacacsUser'], userpass['tacacsPassword'])
        if (loginResult == 0):
            return tn
        else:
            return False
        
    elif ( (noTacacsStr in str(s)) and (userpass['noTacacsUser'] != False) ): # Local user?
        loginResult = _login(tn, host, userpass['noTacacsUser'], userpass['noTacacsPassword'])
        
        if(loginResult == 2):
            loginResult = _login(tn, host, userpass['oldUser'], userpass['oldPassword'])
            
            if(loginResult == 2):
                # Gammelgammelt passord virket ikke det heller s� vi avslutter
                logging.error("OldOld password was invalid on %s", host)
                print(("OldOld password was invalid on " + host))
                tn.close()
                return False
                        
    elif str(s) not in (tacacsStr, noTacacsStr):
        logging.warning("Not possible to log in")
        print ("Not possible to log in")
        return False
    
def do_conf(ip, cmdlist, updict):
    """Tries to connect and log into given IP address using usernames and 
    passwords in updict (dictionary) and runs command(s) in the commands list
    
    Returns xx"""
    # If no answer to ping there is no need to try to connect and run commands
    logging.info("------------------ %s --------------------", ip)
    if (_ping_test(ip)):
        con = _connect(ip, updict)
        if (con):
            cmd_success = _run_cmd(con, cmdlist)
            return cmd_success
    else:
        return False         
    