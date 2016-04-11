
## mh-user-action-bench

Scripts for generating Matterhorn user tracking events, either through direct
MySQL inserts or by simulating web clients.

## Setup

* Python 2.7.x
* `pip install -r requirements.txt`

### client_simulator.py

This script creates a number of process threads that issue repeated http requests
to a Matterhorn usertracking endpoint. Currently all reqeusts will be "anonymous" 
and of type `HEARTBEAT`. Each client thread will get it's own fake user agent
string and a random episode to "watch" from a list fetched from the MH episode
search endpoint. **Important**: for obvious reasons, this won't work if your
Matterhorn instance doesn't have any published episodes to watch.

#### Example:

    ./client_simulator.py \
        --mh_host http://ec2-52-20-140-166.compute-1.amazonaws.com \
        --num-clients 100
        --hb-interval 30
        --reqs-per-session 100
        --mh_user <api user> --mh_pass <api pass>
        
Set `--reqs-per-session=1` to simulate the recent "anonymous" heartbeat issue
wherein each request created a new session id.

#### usage

    usage: client_simulator.py [-h] [--mh-host MH_HOST] [--mh-user MH_USER]
                               [--mh-pass MH_PASS] [--num-clients NUM_CLIENTS]
                               [--hb-interval HB_INTERVAL]
                               [--reqs-per-session REQS_PER_SESSION]
    
    optional arguments:
      -h, --help            show this help message and exit
      --mh-host MH_HOST     Matterhorn engage host
      --mh-user MH_USER     Matterhorn engage API user
      --mh-pass MH_PASS     Matterhorn engage API password
      --num-clients NUM_CLIENTS
                            The number of insert threads
      --hb-interval HB_INTERVAL
                            The number of seconds each worker waits between
                            heartbeats
      --reqs-per-session REQS_PER_SESSION
                            Number of requests before client will create new
                            session cookie


### insert_simulatory.py

Use this one to generate direct inserts into the `mh_user_action` table. Not so
useful in terms of simulating actual usage.

#### usage

    usage: insert_simulator.py [-h] [--host HOST] [--port PORT] [--user USER]
                               [--password PASSWORD] [--database DATABASE]
                               [--table TABLE] [--num-workers NUM_WORKERS]
                               [--num-inserts NUM_INSERTS] [--interval INTERVAL]
    
    optional arguments:
      -h, --help            show this help message and exit
      --host HOST           The hostname of the MySQL node to connect to
      --port PORT           The port of the MySQL node to connect to
      --user USER           The user of the MySQL node to connect to
      --password PASSWORD   The password of the MySQL node to connect to
      --database DATABASE   The database to use
      --table TABLE         The user action table to insert to
      --num-workers NUM_WORKERS
                            The number of insert threads
      --num-inserts NUM_INSERTS
                            The total number of insert to execute
      --interval INTERVAL   The number of seconds each worker waits between
                            inserts

