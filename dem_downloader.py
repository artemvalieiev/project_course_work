from multiprocessing.pool import ThreadPool
import urllib
import urllib.request
import re
import os
import time
import sys
import glob
from bs4 import BeautifulSoup
from pyunpack import Archive
from threading import Lock

class  Downloader:

    def __init__(self, processes):
        directory = ""
        self.processes = processes
        self.lock = Lock()

    def get_match_ids(self, eventid):
        # Create an offset variable for lists that are paginated on HLTV
        offset = 0
        # Build the URL

        # Create an array of all of the Demo URLs on the page
        match_ids = self.find_match_ids_at_url(f'https://www.hltv.org/results?offset={offset}&event={eventid}')

        # If the length is = 50, offset by 50 and loop again
        if len(match_ids) == 50:
            print (f'Parsed first page. Found {(len(match_ids))} IDs')

            # Set a boolean to close the while loop and a page variable we can increment when paginating
            more_pages = True
            page = 1

            # While check is true, offset by 50
            while more_pages:
                offset += 50

                # Same URL building and parsing as above
                more_match_ids = self.find_match_ids_at_url(f'https://www.hltv.org/results?offset={offset}&event={eventid}')
                for match in more_match_ids:
                    match_ids.append(match)

                # Determine if there are additional pages to be found, if not the while loop ends
                if len(more_match_ids) < 50:
                    more_pages = False
                    page += 1
                    print( f'Parsed page {page}. Found {len(match_ids)} IDs.')
                else:
                    # Prints the current page and the number of parsed IDs
                    page += 1
                    print (f'Parsed page {page}. {len(match_ids)} IDs found so far.')

        elif len(match_ids) < 50:
            print (f'Total demos: {len(match_ids)}')
        elif len(match_ids) > 50:
            print ("HLTV altered demo page layout :(")
        return match_ids


    def find_match_ids_at_url(self,url):
        # Get the HTML using get_html()
        html = self.get_html(url)

        # Create an array of all of the Demo URLs on the page
        match_ids = re.findall(r'<div class=\"result-con\" data-zonedgrouping-entry-unix=\"(?:).*?\"><a href=\"/matches/(.*?)\"', html)

        return match_ids


    def convert_to_demo_ids(self,match_ids):
        # Tell the user what is happening
        print ("Converting Match IDs to Demo IDs")
        threads = self.processes
        # Define the number of threads
        pool = ThreadPool(threads)

        # Calls get_demo_ids() and adds the value returned each call to an array called demo_ids
        demo_ids = pool.map(self.get_demo_ids, match_ids)
        pool.close()
        pool.join()

        # Create an array to add any captured errors to
        errors = []

        # Find any errors, add them to the errors array, and remove them from demo_ids
        for demo_id in demo_ids:
            if "/" in demo_id:
                errors.append(demo_id)
        demo_ids = [x for x in demo_ids if x not in errors]

        # Print the errors (if there are any)
        self.print_errors(errors)
        return demo_ids


    def get_demo_ids(self,match_id):
        # URL building and opening
        url = f'https://www.hltv.org/matches/{match_id}'
        html = self.get_html(url)
        demo_id = re.findall('"/download/demo/(.*?)"', html)

        # Check if re.findall()'s array is empty
        # If it has an element, add that Demo ID to the demo_ids array
        if len(demo_id) > 0:
            # Loop through the demo_ids array and remove everything up to the last / to get the real Demo ID
            for i in range(0, len(demo_id)):
                print ("Converted " + str( match_id))
                #time.sleep(0)
                # Return the Demo ID
                return demo_id[0]

        # If there is no element, print which match has no demo
        elif len(demo_id) < 1:
            print (f'No demo found for {match_id}')
            # Return the Match ID with a space char so we can find it later
            return " %s" % match_id


    def download(self, demo_ids, folder_name, unzip=False):
        # Temporarily use 1 due to 503 errors
        # Convert the DemoIDs to URLs
        urls = self.convert_to_urls(demo_ids)

        # Make a folder for the event to save the files in
        self.directory = self.make_dir(folder_name)
        total_file_size = 0

        for url in urls:
           total_file_size += self.get(url,unzip)

        # Create a float to store the filesizes in and add them together
        #total_file_size = sum(filesizes)

        # Print the properly formatted filesize.
        print (f'Successfully transferred {(self.format_file_size(total_file_size))}. Enjoy!')
        return True


    def convert_to_urls(self,demo_ids):
        return [f'https://www.hltv.org/download/demo/{str(demo_id)}'  for demo_id in demo_ids]


    def get(self, url, unzip = False):
        self.lock.acquire()
        # Build and open the URL
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-Agent', r"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.170 Safari/537.36")]
        response = opener.open(url)

        # HLTV redicrects to a .rar or .zip file
        final_url = response.geturl()

        # Gets the filename (everything after the last trailing /)
        filename = final_url.rsplit('/', 1)[-1]
        if(os.path.exists(self.directory+"/"+filename)):
            self.lock.release()
            return 0

        filesize = 0
        # Gets the Content-Length from the metadata from final_url
        urllib.request.install_opener(opener)
        info = urllib.request.urlopen(final_url).info()
        filesize = (int(info["Content-Length"])/1024)/1024
        print (f'Starting {filename}: {filesize} MB.')


        # Downloads the file to the directory the user enters
        (filepath, message) = urllib.request.urlretrieve(final_url, self.directory+"/"+filename)
        if unzip:
            Archive(filepath).extractall(os.path.dirname(filepath))
            #os.remove(self.directory+"/"+filename)

        # Tell user the current status and file information
        print( f'Completed {filename}: {filesize} MB.')
       
        self.lock.release()

        return filesize


    def make_dir(self, folder_name):
        # Create a global variable so the different threads can access it
        directory = f'./{folder_name}'
        os.makedirs(directory, exist_ok=True)

        # Return the string so we can use it
        return directory


    def format_file_size(self, filesize):
        if filesize > 1024:
            return "%.2f GB" % (float(filesize) / 1024)
        else:
            return "%s MB" % (int(filesize))


    def get_html(self,url):
        # Open the URL
            opener = urllib.request.build_opener()

            # Spoof the user agent
            opener.addheaders = [('User-Agent', r"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.170 Safari/537.36")]
            response = opener.open(url)

            # Read the response as HTML
            html = response.read().decode('utf-8')
            return html


    def print_errors(self, errors):
        # Print URL(s) for the match(es) with no demo file(s)
        if len(errors) == 1:
            print (f'{len(errors)} matches have no demo:')
            for i in range(0, len(errors)):
                print (f'{i+1}: https://www.hltv.org/matches/{errors[i]}')
        elif len(errors) > 0:
            print (f'{len(errors)} matches have no demo:')
            for i in range(0, len(errors)):
                print (f'{i+1}: https://www.hltv.org/matches/{errors[i]}')
        else:
            print("No errors found!")
        return True

    def get_major_ids(self):
        major_archive_url =  'https://www.hltv.org/events/archive?eventType=MAJOR'
        major_html = self.get_html(major_archive_url)
        major_soup = BeautifulSoup(major_html, 'html.parser')
        majors_ids_names = {}
        for major_div in major_soup.find_all('div',{'class': 'events-month'}):
            major_hrefs = major_div.find_all('a',href=True)
            href = next((major_ref for major_ref in major_hrefs if major_ref['href'].startswith('/events')), None)
            if href is not None:
                #/events/3883/iem-katowice-2019
                splitted_href = href['href'].split('/')
                majors_ids_names[splitted_href[3]] = splitted_href[2]

        return majors_ids_names




if __name__ == "__main__":

        downloader = Downloader(1)
        majors = downloader.get_major_ids()
        for major in majors:
            match_ids = downloader.get_match_ids(majors[major])
            demo_ids = downloader.convert_to_demo_ids(match_ids)
            downloader.download(demo_ids,major, True)

        #downloader.unzip_all_archives()

