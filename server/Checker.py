import requests
import pandas as pd
import os
from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError

class Checker(object):
    """
    Checks content for any accessibility errors and reports out the exact
    location as best as it can
    """
    def __init__(self):
        self._wave_key = "uV4b9SR11819" #this is the real one
        #self._wave_key = "Z7a4FBT41820" # this is the one 'I'm using to test around with
        self.DATA_FILE = 'data/sample_errors.csv'
        return
        
    def check(self, url):
        """
        Checks the HTML content for any accessibility errors,
        and reports out errors. Uses the WAVE API to do it.
        
        Input:
            url: a valid URL
        Output:
            a list of dicts (containing all the errors found by WAVE API)
        """
        
        wave_url = "https://wave.webaim.org/api/request?key=%s&url=%s&reporttype=4" % (
                        self._wave_key, url
                    )
        response = requests.get(wave_url)
        
        if response.status_code != 200:
            msg = "could not send URL to WAVE! Response: %s" % response.text
            raise Exception(msg)
        
        # parse out the errors, contrast, and alerts
        content = response.json()
        
        contrast_errors = self.get_contrast_errors(content)
        errors          = self.get_errors(content, 'error')
        warnings        = self.get_errors(content, 'alert')
        
        all_items = contrast_errors + errors + warnings
        return all_items
        
    def check_with_save(self, url):
        """
        Testing function to use when we just want to use data from
        the data file instead of making a new request

        Input:
            URL
        Output:
            the same list of dicts as with check
        """

        # load up the data
        dataset = pd.read_csv(self.DATA_FILE, index_col=0)
        
        # find all the data that matches this URL
        data = dataset[dataset['url'] == url]
        return data.to_dict('records')
 
    def check_and_save(self, url):
        """
        Checks for any issues, and then saves those issues to a CSV
        file (not to mention the HTML of the URL) for later checking
        
        If a datafile already exists, it will add it to that file (as
        long as we haven't already checked that website.) Otherwise
        
        Input:
            url: a valid URL
        Output:
            nothing, but saves to self.DATA_FILE
        """
        
        try: 
            full_dataset = pd.read_csv(self.DATA_FILE, index_col=0)
            # get last used id, add one

            id = full_dataset.iloc[-1]['site_id'] + 1
        except Exception as e:
            print(e)
            print("dataset does not exist yet!!! will be making a new dataset")
            cols = ['background', 'foreground', 'level', 'ratio', 
                    'selector', 'type', 'site_id', 'url']
            full_dataset = pd.DataFrame(columns = cols)
            id = 0
            
        # load up the URL using requests
        try:
            x = requests.get(url)
            
            # save the HTML to file
            filename = 'data/%d.html' % id
            with open(filename, 'w', encoding='utf-8') as fi:
                fi.write(x.text)
            
            # get accessibility results (but only if it's not in the dataset yet)
            if url not in list(full_dataset['url']):
                print('checking %s!' % url)
                results = self.check(url)
                dataset = pd.DataFrame(results)
                
                # add some bookkeeping
                dataset['site_id'] = id
                dataset['url']     = url  
                
                # # save them to the CSV (adding them to the existing)
                if full_dataset.shape[0] == 0:
                    dataset.to_csv(self.DATA_FILE)
                else:
                    dataset.to_csv(self.DATA_FILE, mode = 'a', header = False)
                
            else:
                print("don't need to check %s; already have that data!" % url)

        except ConnectionError as ce:
            print("error parsing %s! Skipping" % url)
        
    def get_contrast_errors(self, response):
        """
        Parses the JSON to find contrast errors and parse them for
        easier understanding
        
        Input:
            response: dict the json response
        Ouput:
             a list of dicts with keys:
                ratio: the color contrast ratio
                forground: hex foreground color
                background: hex background color
                selector: css selector to this item.
        """
        if len(response['categories']['contrast']['items']) > 0:
            contrasts = response['categories']['contrast']['items']['contrast']
        else:
            return []
        
        # rearrange contrast in a more meaningful way
        items = []
        for loc, data in zip(contrasts['selectors'], contrasts['contrastdata']):
        
            item = {
                'type': 'contrast',
                'ratio': data[0],
                'foreground': data[1],
                'background': data[2],
                'selector': self._preprocess_selector(loc),
                'level': 'error' # They are easy-to-fix errors :)
            }
            items.append(item)
            
        return items
        

    def get_errors(self, response, level = 'error'):
        """
        Parses the JSON to find errors and parse them for
        easier understanding
        
        Input:
            response: dict the json response
            level: string: either 'error' or 'alert'
        Ouput:
             a list of dicts with keys:
                ratio: the color contrast ratio
                forground: hex foreground color
                background: hex background color
                selector: selector to this item.
        """
        
        errors = response['categories'][level]['items']
        items = []
        for key in errors:
            for selector in errors[key]['selectors']:
                try:
                    item = {
                        'type': key,
                        'ratio': 0.0, # placeholder,
                        'background': '', # placeholder,
                        'foreground': '',
                        'selector': self._preprocess_selector(selector),
                        'level': level
                    }
                    items.append(item)
                except:
                    import pdb
                    pdb.set_trace()
        return items
        
    def _preprocess_selector(self, selector):
        """Preprocess the selector to make it valid for beautiful soup"""
        if selector == False:
            s = '' # that means there is no selector
        else:
            s = selector.lower() # for some reason it all-caps everything
            s = s.replace('first-child', 'nth-of-type(1)')
        return s
        
        
    
        
if __name__ == "__main__":

    import pandas as pd
    import os
    from bs4 import BeautifulSoup
    from requests.exceptions import ConnectionError

    # make the checker
    finder = Checker()
    
    #urls = ['https://yahoo.com', 'https://odu.edu', 'https://www.txstate.edu/',
    #        'https://wikipedia.org', 'https://www.virginia.gov/']
    
    urls = ['https://nasa.gov', 'https://www.nhc.noaa.gov/', 'https://www.irs.gov/'] 
    
    for url in urls:
        finder.check_and_save(url)
    
    # # get the content from the url
    # url = 'https://yahoo.com'
    # site_name = 'YahooHome'
    # x = requests.get(url)
    # x_new = x.text.lower() # preprocess because the beautiful soup thing (for now) has issues with capitalization 
    # soup = BeautifulSoup(x_new, 'lxml')
    
    # # get the accessibility results (only if we haven't done it yet!)
    # filename = site_name + '.csv'
    # if os.path.isfile(site_name + '.csv'):
        # dataset = pd.read_csv(filename)
    # else:
        # results = checker.check(url)
        # dataset = pd.DataFrame(results)
    
        # # also save it so we don't have to make this request later. :) Save some money!
        # dataset.to_csv(filename)








