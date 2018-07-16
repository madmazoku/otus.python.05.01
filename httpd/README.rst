============
httpd server
============

Introduction
============

Simple HTTP server based on prefork/epoll idea

.. contents::


Usage
=====

Options

.. code-block:: 

    ./httpd.py [-a ADDRESS] [-p PORT] [-l LOG_FILE_NAME] [-w WORKERS] [-r ROOT]

        simple http server

        -a : adrress to bind to, default localhost (127.0.0.1)

        -p : port to be listened, default 8080

        -l : log file name, default print to stderr

        -w : number of forked processes, default 4

        -r : root where to take files to server, default '.'


Example
-------

Execute script:

.. code-block:: 

    ./httpd.py


Test results
============

Server execution

.. code-block::

    ./httpd.py -p 8080 -w 4 -l test.log -r ../material/http-test-suite/

Feature testing
---------------

.. code-block:: 

    http-test-suite$ ./httptest.py 
    directory index file exists ... ok
    document root escaping forbidden ... ok
    Send bad http headers ... ok
    file located in nested folders ... ok
    absent file returns 404 ... ok
    urlencoded filename ... ok
    file with two dots in name ... ok
    query string after filename ... ok
    filename with spaces ... ok
    Content-Type for .css ... ok
    Content-Type for .gif ... ok
    Content-Type for .html ... ok
    Content-Type for .jpeg ... ok
    Content-Type for .jpg ... ok
    Content-Type for .js ... ok
    Content-Type for .png ... ok
    Content-Type for .swf ... ok
    head method support ... ok
    directory index file absent ... ok
    large file downloaded correctly ... ok
    post method forbidden ... ok
    Server header exists ... ok

    ----------------------------------------------------------------------
    Ran 22 tests in 0.201s

Performance testing
-------------------

Light:

.. code-block:: 

    http-test-suite$ ab -n 50000 -c 100 -r http://127.0.0.1:8080/
    This is ApacheBench, Version 2.3 <$Revision: 1706008 $>
    Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
    Licensed to The Apache Software Foundation, http://www.apache.org/

    Benchmarking 127.0.0.1 (be patient)
    Completed 5000 requests
    Completed 10000 requests
    Completed 15000 requests
    Completed 20000 requests
    Completed 25000 requests
    Completed 30000 requests
    Completed 35000 requests
    Completed 40000 requests
    Completed 45000 requests
    Completed 50000 requests
    Finished 50000 requests


    Server Software:        httpd.py
    Server Hostname:        127.0.0.1
    Server Port:            8080

    Document Path:          /
    Document Length:        0 bytes

    Concurrency Level:      100
    Time taken for tests:   16.529 seconds
    Complete requests:      50000
    Failed requests:        0
    Non-2xx responses:      50000
    Total transferred:      5000000 bytes
    HTML transferred:       0 bytes
    Requests per second:    3024.92 [#/sec] (mean)
    Time per request:       33.059 [ms] (mean)
    Time per request:       0.331 [ms] (mean, across all concurrent requests)
    Transfer rate:          295.40 [Kbytes/sec] received

    Connection Times (ms)
                  min  mean[+/-sd] median   max
    Connect:        0    0   0.9      0      32
    Processing:     7   33   7.0     30      86
    Waiting:        7   33   7.0     30      85
    Total:         13   33   7.0     30      86

    Percentage of the requests served within a certain time (ms)
      50%     30
      66%     36
      75%     39
      80%     40
      90%     43
      95%     45
      98%     49
      99%     51
     100%     86 (longest request)

Heavy:

.. code-block:: 

    http-test-suite$ ab -n 50000 -c 100 -r http://127.0.0.1:8080/httptest/wikipedia_russia.html
    This is ApacheBench, Version 2.3 <$Revision: 1706008 $>
    Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
    Licensed to The Apache Software Foundation, http://www.apache.org/

    Benchmarking 127.0.0.1 (be patient)
    Completed 5000 requests
    Completed 10000 requests
    Completed 15000 requests
    Completed 20000 requests
    Completed 25000 requests
    Completed 30000 requests
    Completed 35000 requests
    Completed 40000 requests
    Completed 45000 requests
    Completed 50000 requests
    Finished 50000 requests


    Server Software:        httpd.py
    Server Hostname:        127.0.0.1
    Server Port:            8080

    Document Path:          /httptest/wikipedia_russia.html
    Document Length:        954824 bytes

    Concurrency Level:      100
    Time taken for tests:   212.564 seconds
    Complete requests:      50000
    Failed requests:        245
       (Connect: 0, Receive: 0, Length: 245, Exceptions: 0)
    Total transferred:      47725529208 bytes
    HTML transferred:       47718429208 bytes
    Requests per second:    235.22 [#/sec] (mean)
    Time per request:       425.128 [ms] (mean)
    Time per request:       4.251 [ms] (mean, across all concurrent requests)
    Transfer rate:          219260.78 [Kbytes/sec] received

    Connection Times (ms)
                  min  mean[+/-sd] median   max
    Connect:        0    0   0.7      0      19
    Processing:    88  425 184.3    399    1064
    Waiting:        0    5  12.1      2     153
    Total:         88  425 184.3    399    1064

    Percentage of the requests served within a certain time (ms)
      50%    399
      66%    482
      75%    540
      80%    580
      90%    681
      95%    768
      98%    871
      99%    938
     100%   1064 (longest request)
