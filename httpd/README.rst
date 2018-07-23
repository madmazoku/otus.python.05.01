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
    Time taken for tests:   18.379 seconds
    Complete requests:      50000
    Failed requests:        0
    Non-2xx responses:      50000
    Total transferred:      5000000 bytes
    HTML transferred:       0 bytes
    Requests per second:    2720.54 [#/sec] (mean)
    Time per request:       36.757 [ms] (mean)
    Time per request:       0.368 [ms] (mean, across all concurrent requests)
    Transfer rate:          265.68 [Kbytes/sec] received

    Connection Times (ms)
                  min  mean[+/-sd] median   max
    Connect:        0    0   0.9      0      31
    Processing:     1   36  29.7     31     268
    Waiting:        0   36  29.7     30     268
    Total:          1   37  29.7     31     268

    Percentage of the requests served within a certain time (ms)
      50%     31
      66%     43
      75%     52
      80%     58
      90%     74
      95%     89
      98%    119
      99%    139
     100%    268 (longest request)


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
    Time taken for tests:   186.122 seconds
    Complete requests:      50000
    Failed requests:        0
    Total transferred:      47748300000 bytes
    HTML transferred:       47741200000 bytes
    Requests per second:    268.64 [#/sec] (mean)
    Time per request:       372.244 [ms] (mean)
    Time per request:       3.722 [ms] (mean, across all concurrent requests)
    Transfer rate:          250530.57 [Kbytes/sec] received

    Connection Times (ms)
                  min  mean[+/-sd] median   max
    Connect:        0    0   0.7      0      55
    Processing:    49  372 128.9    362     885
    Waiting:        0    8   5.3      6      97
    Total:         49  372 128.8    362     885

    Percentage of the requests served within a certain time (ms)
      50%    362
      66%    418
      75%    457
      80%    482
      90%    544
      95%    602
      98%    663
      99%    700
     100%    885 (longest request)
