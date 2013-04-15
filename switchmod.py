#!/usr/bin/python3.3
# coding: iso-8859-15

def pingTest(ipaddr):
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

def runCmd(connection, cmdList):
    """Running commands given in cmdList using connection
    
    Returns .. """
    i = 0
    
    for cmd in cmdList:
        connection.write("show running-config | i hostname\n")
        (index, match, text) = connection.expect(['\#$'], 5)
        matchObj = re.search(r'(hostname)*(.*)$', text)
        hn = matchObj.group(0)
    #    print("HN: " + matchObj.group() + "\n")
        # Kjører kommando
        connection.write(cmd + "\n")
        (fys, fjas, result) = connection.expect([hn], 5) 
        
        if ('Invalid' in result):
            print ("## Command error. The following command is not working: " + cmd + "\nResult:\n" + result)
            logging.critical("Invalid command: " + cmd)
            return
        
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
    # Sjekker om det er tacacs brukernavn det spÃžrres etter
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