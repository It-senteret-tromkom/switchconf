#!/usr/bin/python3.3
# coding: iso-8859-15

import getpass
import sys
import telnetlib
import logging
import re
import ipaddress
import subprocess

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',filename='switchconf.log',level=logging.DEBUG)
timeout = 5

def user_pass(tac, notac, old):
    # Dictionary to keep usernames and passwords
    userpassdict = {}
    
    if tac:
        # Ask for tacacs user name and password
        userpassdict['tacacsUser'] = input('Entet tacacs username: ')
        userpassdict['tacacsPassword'] = getpass.getpass()
    
    if notac:
        # Ask for locally configured username and password
        userpassdict['noTacacsUser'] = input("Enter local (not tacacs) username: ")
        userpassdict['noTacacsPassword'] = getpass.getpass()
    
    if old:
        # Ask for old locally configured username and password
        userpassdict['oldUser'] = input("Enter old local (not tacacs) username: ")
        userpassdict['oldPassword'] = getpass.getpass()
    
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
    
    elif res == 1: # 1 = ingen svar eller færre enn 'count' (-c) antall pakker mottatt innen 'deadline' (-w)
        msg = "No response from", ipaddr
        print(msg)
        logging.warning(msg)
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
        connection.write("show running-config | i hostname\n")
        (index, match, text) = connection.expect(['\#$'], 5)
        matchObj = re.search(r'(hostname)*(.*)$', text)
        hn = matchObj.group(0)
        # Kjører kommando
        connection.write(cmd + "\n")
        (fys, fjas, result) = connection.expect([hn], 5) 
        
        if ('Invalid' in result):
            print ("## Command error. The following command is not working: " + cmd + "\nResult:\n" + result)
            logging.critical("Invalid command: " + cmd)
            return False
        
        logging.info('Command %s and result: %s', i , result)
        i += 1
    # Exists and closes connection
    connection.write("exit\n")
    connection.write("exit\n")
    connection.close()
    return True

def _login(conn, ip, userName, password):
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
        
def _connect(host, userpass):
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
        return False
    # TODO: Legge til en sjekk av om telnet innlogging er OK eller om det må prøves med ssh istedet.
    
    # Venter på angitt string og hvis ikke mottatt på x sekunder legges mottat string i s
    (x, y, s) = tn.expect(["sjobing"], 1)
    if tacacsStr in s: # TACACS user?
        _login(tn, host, userpass['tacasUser'], userpass['tacacsPassword'])
        
    elif noTacacsStr in s: # Local user?
        loginResult = _login(tn, host, userpass['noTacacstUser'], userpass['noTacacsPassword'])
        
        if(loginResult == 2):
            loginResult = _login(tn, host, userpass['oldUser'], userpass['oldPassword'])
            
            if(loginResult == 2):
                # Gammelgammelt passord virket ikke det heller så vi avslutter
                logging.error("OldOld password was invalid on %s", host)
                print("OldOld password was invalid on " + host)
                tn.close()
                return False
                        
    elif s not in (tacacsStr, noTacacsStr):
        print ("tja")
        sys.exit()
    
    return tn

def do_conf(ip, cmdlist, updict):
    """Tries to connect and log into given IP address using usernames and 
    passwords in updict (dictionary) and runs command(s) in the commands list
    
    Returns xx"""
    # If no answer to ping there is no need to try to connect and run commands
    if (_ping_test(ip)):
        con = _connect(ip, updict)
        if (con):
            cmd_success = _run_cmd(con, cmdlist)
            return cmd_success
    else:
        return False         
    