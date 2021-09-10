#! /usr/bin/python

# source and info: https://github.com/pocoloko/idena-mining-monitor
# Idena Mining Check - check if an idena identity is active, which meains it is mining, meant to be used for identities that mine using their own nodes.
# Notify via email if it has not been active than the allowed time.
# Should not run this inside the same network as your mining node, since if your network goes offline, you will not receive an e-mail.
# supports local MTA for e-mailing only, without authentication and without encryption

import requests # http magic
import configparser # external config file loading
import os, logging # disk and logging stuff
from datetime import datetime # for time stuff
import smtplib # for sending results to email
from email.message import EmailMessage # for composing the email in an easy way, thanks Python!

#Set up basic logging to file
logging.basicConfig(filename = ('minewatch.log'), level=logging.DEBUG, format=' %(asctime)s -  %(levelname)s -  %(message)s')


# Initial setup of configuration.
def setup():
    ##### CONFIGURATION ##### use minewatch.ini for edits, edit the path to file below as needed
    config_file = 'minewatch.ini' # The configuration file, edit this if your config file is not in folder you are running the script from!

    # If we have a config file, load it. Note this doesn't necessarily mean that the config file is valid, just that it exists
    if os.path.exists(config_file) and os.path.getsize(config_file) > 0:
        config = configparser.ConfigParser(interpolation=None) # this is not ideal but disabling interpolation due to having % in URLs
        config.read(config_file) # Lets read our config file
        logging.info(f"Loaded config file: {config_file}")
    else: # If we don't have a config file, stop execution
        logging.error(f"A config file is required, we didn't find a config file where expected: {config_file}")
        raise SystemExit # Stops execution, throws an exception
    return config

# Check last seen of identity and return it and the online status, as strings
def check_identity(the_url, the_identity):
    try:
        res = requests.get(f"{the_url}{the_identity}").json()
        logging.info("successfully accesed identity from API")
    except Exception as e:
        logging.error(f"Couldn't access API: {e}")

    last_seen = res["result"]["lastActivity"].split(".")[0]
    is_online = res["result"]["online"]
    return last_seen, is_online

# compare last seen time with curent time, return time difference in seconds.
def compare_times(last_seen):
    last_seen_dt = datetime.strptime(last_seen, "%Y-%m-%dT%H:%M:%S")
    time_difference = datetime.utcnow() - last_seen_dt
    logging.info(f"Identity's activity last seen {str(time_difference)} ago")
    return time_difference

# return true if time difference is more than allowed difference
def time_status(time_difference, allowed_difference):
    if  time_difference > allowed_difference:
        return True
    else:
        return False

# composing body of email for later sending
def compose_email(add, last, delta, online):
    email_data = (f"Node is <b>OFFLINE!</b><br>")
    email_data += (f"Address: {add}<br>")
    email_data += (f"The online status of your identity is: {online}<br>")
    email_data += (f"Identity activity last seen: {last} UTC, which is <b>{delta}</b> ago<br>")
    email_data += (f"Please investigate! Remember that after 1 hour offline, a mining penalty will be applied<br>")
    logging.info('Composed email data')
    return email_data

# Send the email
def send_email(local_conf, email_data):
    themail = EmailMessage()
    themail.set_content(email_data, subtype='html')
    themail['Subject'] = (f"WARNING: Idena identity has no activity! It's possible that your node is offline")
    themail['From'] = (local_conf['MAIL']['FROM'])
    themail['To'] = (local_conf['MAIL']['TO'])
    themail['X-Priority'] = '2'
    try: # Lets send the email (use "with" instead?)
        smtp = smtplib.SMTP((local_conf['MAIL']['SERVER']))
        smtp.send_message(themail)
        logging.info('Sent e-mail of error')
    except smtplib.SMTPException as e: # log the error if any
        logging.error(f"Something went wrong! Couldn\'t send email: {e.args}")
    return

def main(config):
    if not (config['DEFAULT'].getboolean('LOGGING')):
        logging.disable(logging.CRITICAL) # disables all logging
    logging.info('--------------------------------START--------------------------------')

    url = config['DEFAULT']['APIURL'] # fetch API url from config file
    address = config['DEFAULT']['ADDRESS'] # fetch address of identity from config file
    last_seen, online_status = check_identity(url,address)
    time_delta = (compare_times(last_seen))
    time_delta_readable = (str(time_delta)).split(".")[0]

    # check if we have been offline longer than we are allowed, and send an e-mail if so
    if time_status(time_delta.seconds, int(config['DEFAULT']['ALLOWEDTIME'])):
        logging.info(f"Node is OFFLINE, last seen {str(last_seen)}, {time_delta_readable} ago")
        send_email(config, (compose_email(address, last_seen, time_delta_readable, online_status)) )
    else:
        logging.info(f"Node is online, last seen {str(last_seen)}, {time_delta_readable} ago")

    logging.info('--------------------------------STOP--------------------------------')

if __name__ == "__main__":
    main(setup()) # Call main with the configuration as parameter, which is loaded via setup()
    
