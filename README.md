netmon
======
Netmon is a simple daemon that tests your download and upload speesd (using
[Speedtest.net](https://speedtest.net) and tweets a complaint on your behalf
when the speed is below your expectations. For help, run `./netmon.py --help`.

Usage
-----
Run the command line passing the `-d` and `-u` parameters for your subscription
download and upload speeds respectively, `-c` for your Twitter app credentials
file, `-d` for the delay between checks (default to 120) and `-m` for your
message format. The message format receives 2 parameters, `download` and
`upload` (check code for details).

The script will only tweet if speed is below the expected for 5 consecutive
tests, i.e. it will only tweet after 10 minutes of slow internet if you use the
defaults.

It will also not tweet twice in a single shitty connection window, meaning it
will ignore that your connection is bad until it is above the minimum value
again. It will also not tweet more than once an hour.

**Don't forget to add your credentials to auth.json.sample and provide to the
script**

Example
-------
```
$ python netmon.py -d 35M -u 3.5M -c auth.json -m "Hey @ShittyISP_Support I'm paying for 10 Mbps/1 Mbps and I'm only getting %s/%s today!"
```
You set your expected speed to 35 Mbps (download) and 3.5 Mbps (upload) and it
will tweet as soon as any speed drops below 1/3 of the expected.

License
-------
This work is completely based on /u/AlekseyP and his
[@A\_Comcast\_User](https://twitter.com/a_comcast_user) account and is licensed
under the [MIT License](License)
