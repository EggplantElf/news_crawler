# news_crawler
news crawler from rss feeds

# dependencies
to run the crawler, you probably need to install some packages, available in pip:
* [pycurl]
* [feedparser]
* [interruptingcow]
* [python-readability]
* [pymongo]
* [segtok]

also the command line tool [lynx] is used

# usage
* in the file "feeds.txt" are some news feeds, you can add more feeds
* start the MongoDB deamon (@IMS people: please kindly ask Edgar to update MongoDB in the servers, the version is tooooo old)
```sh
$ mongod --dbpath [your-mongoDB-path]
```
* run the crawler
```sh
$ python crawler.py -t [num-of-threads] -d [database-name] -
```

#License
free to use under own risk, the author is cowardly not responsible for any unpleasant consequences.


[pycurl]:https://github.com/pycurl/pycurl
[feedparser]:https://github.com/kurtmckee/feedparser
[interruptingcow]:https://pypi.python.org/pypi/interruptingcow/
[python-readability]:https://github.com/buriy/python-readability
[pymongo]:http://docs.mongodb.org/ecosystem/drivers/python/
[segtok]:https://github.com/fnl/segtok
[lynx]:http://lynx.isc.org
