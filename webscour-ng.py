import requests
import sys
import time
import os
import getopt
import re
from lxml import etree
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *


class ScreenShot(QWebView):

    def __init__(self):
        self.app = QApplication(sys.argv)
        QWebView.__init__(self)
        self._loaded = False
        self.settings().setAttribute(QWebSettings.JavascriptEnabled, False)
        self.loadFinished.connect(self._loadFinished)

    def capture(self, html, url, folder, output_file):
        self.page().networkAccessManager().sslErrors.connect(self.on_ssl_errors)

        self.setHtml(html, QUrl(url))

        #self.load(QUrl(url))
        if not '.shtml' in url:
            self.wait_load()

        frame = self.page().mainFrame()
        frame.setScrollBarPolicy(Qt.Horizontal, Qt.ScrollBarAlwaysOff)
        frame.setScrollBarPolicy(Qt.Vertical, Qt.ScrollBarAlwaysOff)
        self.page().setViewportSize(QSize(1024, 768))
        image = QImage(1024, 768, QImage.Format_ARGB32)
        painter = QPainter(image)
        frame.render(painter)
        painter.end()

        scale = image.scaled(
            300, 300, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        #crop = scale.copy(0,0,300,300)
        scale.save('./'+folder+'/' + output_file)

    def on_ssl_errors(self, reply, errors):
        reply.ignoreSslErrors()

    def wait_load(self, delay=0):

        while not self._loaded:
            self.app.processEvents()
            time.sleep(delay)
        self._loaded = False

    def _loadFinished(self, result):
        self._loaded = True


def main(argv):
    try:
        (opts, args) = getopt.getopt(argv, 'hl:o:', ['list=', 'output='
                                                     ])
    except getopt.GetoptError:
        print('webscour-ng.py -l <inputfile> -o <outputfile>')
        sys.exit(2)
    for (opt, arg) in opts:
        if opt == '-h':
            print('webscour-ng.py -l list -o output.html')
            sys.exit()
        elif opt in ('-l', '--list'):
            ifile = arg
        elif opt in ('-o', '--output'):
            ofile = arg
    create_directory(ofile+'_thumbnails')
    process = Process(ifile, ofile, ofile+'_thumbnails')
    process.process_requests()


def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


class Process:

    def __init__(self, ifile, ofile, thumbnails):
        self.ifile = ifile
        self.ofile = ofile
        self.thumbnails = thumbnails
        self.screenshot = ScreenShot()
        self.timeout = 5
        self.line = 0
        self.alternator = 0
        self.color = 'd0'
        self.counter = 0

    def process_requests(self):
        self.write_header()
        input = open(self.ifile)
        contents = input.readlines()
        input.close()
        for host in contents:
            host = host.strip()
            host = host.rstrip('\r\n')
            if 'http' not in host and 'https' not in host:
                responses = self.check_protocol(host.strip())
                if responses:
                    for response in responses:
                        redirect_response = self.check_redirects(response)
                        self.write_row(redirect_response)
                        self.write_url_row(redirect_response)
                    else:
                        try:
                            response = self.get(host)
                        except Exception as e:
                            print(e)
                        else:
                            self.write_row(response)
                            self.write_url_row(response)
                            self.write_footer()

    def check_redirects(self, response):
        redirect = self.check_meta_redirects(response)
        if redirect is not False:
            response = redirect
            #redirect = self.check_script_redirects(response)
            #if redirect is not False:
            #	response = redirect
            #redirect = self.check_301_redirect(response)
            #if redirect is not False:
            #	response = redirect
            return response

    def check_301_redirect(self, response):
        if response is 301:
            parser = etree.HTMLParser()
            tree = etree.fromstring(response.content, parser)
            result = tree.xpath('//a/@href')
            url = result
            try:
                response = self.get(url)
            except Exception as e:
                print(e)
            else:
                return False

    def check_meta_redirects(self, response):
        redirect = ''
        parser = etree.HTMLParser()
        try:
            tree = etree.fromstring(response.content, parser)
        except Exception as e:
            return False
        else:
            try:
                result = tree.xpath('//meta[@http-equiv="refresh"]/@content')
                if not result:
                    result = tree.xpath('//meta[@http-equiv="Refresh"]/@content')
                if not result:
                    result = tree.xpath('//meta[@http-equiv="REFRESH"]/@content')
                if result:
                    redirect = result[0][7:]
                    url = response.url + redirect
                    try:
                        response = self.get(url)
                    except Exception as e:
                        print(e)
                    else:
                        return response
                else:
                    return False
            except Exception as e:
                return False

    def check_script_redirects(self, response):
        parser = etree.HTMLParser()
        tree = etree.fromstring(response.content, parser)
        result = tree.xpath('//script')
        for item in result:
            if 'location.replace' in str(item.text):
                print(item.text)
                redirect = re.findall('"([^"]*)"', str(item.text))
                print(redirect)
                url = response.url + redirect[0]
                try:
                    response = self.get(url.strip())
                except Exception as e:
                    print(e)
                else:
                    return response
                    #elif 'window.location' in str(item.text):
                    #	redirect = re.findall('"([^"]*)"',str(item.text))
                    #	print redirect
                    #	url = response.url + redirect[0]
                    #	try:
                    #	    response = self.get(url.strip())
                    #	except Exception, e:
                    #	    print e
                    #	else:
                    #		return response
                    return False

    def check_protocol(self, host):
        protocols = ['http', 'https']
        results = []
        for protocol in protocols:
            try:
                response = self.get(protocol + '://' + host)
            except Exception as e:
                print(e)
            else:
                results.append(response)
                if len(results) == 2:
                    if results[0] == results[1]:
                        results.remove(results[1])
                        return results
                    else:
                        return results
                    elif len(results) == 1:
                        return results
                    else:
                        return 0

    def get(self, host):
        try:
            request = requests.get(host, verify=False, timeout=self.timeout)
        except Exception, e:
            print e
            raise Exception
        else:
            return request

            def write_url_row(self, response):
                f = open("urls.txt", 'a+')
                url = response.url
                f.write(url+"\n")
                f.close()

    def write_row(self, response):
        f = open(self.ofile, 'a')
        url = response.url
        self.screenshot.capture(response.content, url,
        self.thumbnails, str(self.line) + '.png')
        parser = etree.HTMLParser()
        try:
            tree = etree.fromstring(response.content, parser)
        except Exception, e:
            tree = 'NONE'
            f.write('<tr class=' + self.color + '><td>')
            f.write('<a href=' + url + '><img src=./'+self.thumbnails+'/'+ str(self.line) + '.png></a></td><td>')
            try:
                f.write('<h2>' + tree.find(".//title").text + '</h2>'
                )
            except as e:
                f.write('<h2>No Title</h2>')
                f.write('<pre><a href=' + url + '>' + url + '</a><pre>\n')
                f.write('<pre>RESPONSE HEADERS:</pre><pre>')
                for key, value in response.headers.iteritems():
                    f.write(key + ': ' + value + '\n')
                    f.write('\n</pre></td></tr>')
                    self.line = self.line + 1
                    self.alternator = (self.alternator + 1) % 2
                    if self.alternator == 0:
                        self.color = 'd0'
                    else:
                        self.color = 'd1'
                        print str(self.counter) + ' ' + response.url
                        self.counter = self.counter + 1
                        f.close()

    def write_header(self):
        header = \
        """<html>
        <head>
        <STYLE type="text/css">
        tr.d0 td {
        background-color: #E8EDFF; color: black;
        }
        tr.d1 td {
        background-color: #FFFFFF; color: black;
        }
        body, h1, h2 {
        font-size: 10pt;
        font-family: Verdana, Tahoma, Helvetica, Arial;
        }
        </STYLE>
        </head>
        <body>
        <table>"""
        f = open(self.ofile, 'w')
        f.write(header)
        f.close()

    def write_footer(self):
        f = open(self.ofile, 'a')
        f.write('</table></body>')
        f.close()


if __name__ == '__main__':
    main(sys.argv[1:])
