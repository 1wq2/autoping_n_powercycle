#!/usr/bin/env python
import subprocess
from netaddr import IPNetwork
import os
import time
import socket
import multiprocessing

hosttoping = "1.1.1.1"
successdelay = 2  # How many seconds to wait after a successful ping
failretry = 2  # How many cycles of failed pings before power cycle
faildelay = 1  # How long to wait after a failed ping before trying again
poweroffdelay = 1  # How long to stay powered off
bootdelay = 1  # How many seconds to wait after power cycle
powercyclefaildelay = 2  # How long to wait after a power cycle failed before starting over
reboot_flag = False


def power_cycle():
    global reboot_flag

    print("Switching power of")
    print("Power is off. Sleeping for " + str(poweroffdelay) + " seconds before switching back on")
    time.sleep(poweroffdelay)
    print("Power is on. Sleeping for " + str(bootdelay) + " seconds for things to reboot")
    time.sleep(bootdelay)
    print("Pinging after reboot")
    if ping(hosttoping):
        print(hosttoping + " is now pingable, returning to our normaly scheduled programming.")
        time.sleep(successdelay)
    else:
        reboot_flag = True


def bad_ping():
    global reboot_flag

    if reboot_flag:
        print("Strange things happened, so we're going to sleep for " +
              str(powercyclefaildelay) + " and then try again.")
        time.sleep(powercyclefaildelay)
        print("OK lets try this again.")
        reboot_flag = False
    if ping(hosttoping):
        print(hosttoping + " is pingable. Sleeping for " + str(successdelay) + " seconds before checking again.")
        time.sleep(successdelay)
    else:
        print("No answer from " + hosttoping)
        retrycount = 0
        while retrycount <= failretry:
            print("Sleeping for " + str(faildelay) + " seconds before pinging again.")
            time.sleep(faildelay)
            if ping(hosttoping):
                print("It's pingable now")
                break
            else:
                if retrycount >= failretry:
                    print("It hasn't been pingable for too long so we're going to kick it.")
                    power_cycle()
                    break
                else:
                    retrycount += 1
                    print(hosttoping + " still wasn't pingable after " + str(
                        retrycount) + " tries.  We will keep trying until we have tried " + str(failretry) + " times.")


def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("255.255.255.1", 80))
    return s.getsockname()[0]


def ping(hosttoping):
    response = subprocess.call(["ping", "-c", "1", hosttoping], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if response == 0:
        return True
    else:
        return False


def pinger(job_q, results_q):
    DEVNULL = open(os.devnull, 'w')
    while True:
        ip = job_q.get()
        if ip is None: break

        try:
            # print "ping", ip
            subprocess.check_call(['ping', '-c1', '-W', '1', str(ip)],
                                  stdout=DEVNULL)
            results_q.put(ip)
        except:
            print("ping failed", ip)
            global hosttoping
            hosttoping = ip
            bad_ping()


jobs = multiprocessing.Queue()
results = multiprocessing.Queue()

ip = get_ip_address()
proc = subprocess.Popen('ifconfig', stdout=subprocess.PIPE)
while True:
    line = proc.stdout.readline()
    if ip.encode() in line:
        break
mask = line.rstrip().split(b':')[-1].replace(b' ', b'').decode()
# print mask
cidrnet = ip + "/" + mask
# print cidrnet

netaddress = str(IPNetwork(cidrnet).cidr)
print("Ping sweeping: ", netaddress)
# netbits = sum([bin(int(x)).count("1") for x in mask.split(".")])
# print netbits
l = list(IPNetwork(netaddress).iter_hosts())
# All the IP Adresses
print(l)

pool = [multiprocessing.Process(target=pinger, args=(jobs, results)) for i in l]

for p in pool:
    p.start()

for i in l:
    jobs.put(str(i))

for p in pool:
    jobs.put(None)

for p in pool:
    p.join()

while not results.empty():
    ip = results.get()
    print(ip)
