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

    ./httpd.py -p 8080 -w 8 -l test.log -r ../material/http-test-suite/

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
    This is ApacheBench, Version 2.3 <$Revision: 1807734 $>
    Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
    Licensed to The Apache Software Foundation, http://www.apache.org/

    Benchmarking localhost (be patient)
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
    Server Hostname:        localhost
    Server Port:            8080

    Document Path:          /
    Document Length:        0 bytes

    Concurrency Level:      100
    Time taken for tests:   1.661 seconds
    Complete requests:      50000
    Failed requests:        0
    Non-2xx responses:      50000
    Total transferred:      5000000 bytes
    HTML transferred:       0 bytes
    Requests per second:    30097.20 [#/sec] (mean)
    Time per request:       3.323 [ms] (mean)
    Time per request:       0.033 [ms] (mean, across all concurrent requests)
    Transfer rate:          2939.18 [Kbytes/sec] received

    Connection Times (ms)
                  min  mean[+/-sd] median   max
    Connect:        0    0   0.4      0       3
    Processing:     0    3   2.8      2      23
    Waiting:        0    3   2.8      2      22
    Total:          0    3   2.8      3      23

    Percentage of the requests served within a certain time (ms)
      50%      3
      66%      4
      75%      4
      80%      5
      90%      7
      95%      9
      98%     11
      99%     13
     100%     23 (longest request)


Heavy Async File Read:

.. code-block:: 

    http-test-suite$ ab -n 50000 -c 100 -r http://127.0.0.1:8080/httptest/wikipedia_russia.html
    This is ApacheBench, Version 2.3 <$Revision: 1807734 $>
    Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
    Licensed to The Apache Software Foundation, http://www.apache.org/

    Benchmarking localhost (be patient)
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
    Server Hostname:        localhost
    Server Port:            8080

    Document Path:          /httptest/wikipedia_russia.html
    Document Length:        954824 bytes

    Concurrency Level:      100
    Time taken for tests:   64.666 seconds
    Complete requests:      50000
    Failed requests:        0
    Total transferred:      47748300000 bytes
    HTML transferred:       47741200000 bytes
    Requests per second:    773.21 [#/sec] (mean)
    Time per request:       129.331 [ms] (mean)
    Time per request:       1.293 [ms] (mean, across all concurrent requests)
    Transfer rate:          721081.91 [Kbytes/sec] received

    Connection Times (ms)
                  min  mean[+/-sd] median   max
    Connect:        0    0   0.2      0      16
    Processing:     7  129  68.8    118     521
    Waiting:        0    2   4.0      1      61
    Total:          7  129  68.8    118     521

    Percentage of the requests served within a certain time (ms)
      50%    118
      66%    145
      75%    165
      80%    178
      90%    217
      95%    258
      98%    314
      99%    362
     100%    521 (longest request)


Heavy Sync File Read:

.. code-block:: 

    http-test-suite$ ab -n 50000 -c 100 -r http://127.0.0.1:8080/httptest/wikipedia_russia.html
    This is ApacheBench, Version 2.3 <$Revision: 1807734 $>
    Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
    Licensed to The Apache Software Foundation, http://www.apache.org/

    Benchmarking localhost (be patient)
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
    Server Hostname:        localhost
    Server Port:            8080

    Document Path:          /httptest/wikipedia_russia.html
    Document Length:        954824 bytes

    Concurrency Level:      100
    Time taken for tests:   22.760 seconds
    Complete requests:      50000
    Failed requests:        0
    Total transferred:      47748300000 bytes
    HTML transferred:       47741200000 bytes
    Requests per second:    2196.84 [#/sec] (mean)
    Time per request:       45.520 [ms] (mean)
    Time per request:       0.455 [ms] (mean, across all concurrent requests)
    Transfer rate:          2048733.87 [Kbytes/sec] received

    Connection Times (ms)
                  min  mean[+/-sd] median   max
    Connect:        0    1   0.1      1       4
    Processing:    18   45   2.2     44      78
    Waiting:        0    1   1.2      1      29
    Total:         19   45   2.2     45      78

    Percentage of the requests served within a certain time (ms)
      50%     45
      66%     46
      75%     46
      80%     47
      90%     48
      95%     49
      98%     50
      99%     52
     100%     78 (longest request)

