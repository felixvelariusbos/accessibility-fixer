from bs4 import BeautifulSoup
import numpy as np
import spacy
import re

# load up spacy model globally
nlp = spacy.load("en_core_web_sm")

class Fixer(object):


    def __init__(self):
    
        # create the supported fixers
        
        self.fixers = {
            'contrast': ContrastFixer(),
            'link_empty': EmptyLinkFixer(),
            'button_empty': EmptyLinkFixer(),
        }
        self.default_fixer = SubFixer()
        return
        
    def fix_all(self, errors, html):
        """
        Does its best to fix all the errors in this HTML
        and returns an improved set of HTML
        
        Input:
            errors: a list of error dicts found by the ErrorFinder
            html: a string of HTML that the errors are based on.
            
        Output:
            a string of better HTML
        """
    
        # first, make a soup of HTML
        html = html.lower() # pre process to make the same
        soup = BeautifulSoup(html, 'lxml')
    
        for error in errors:
            print("working on error of type %s" % error['type'])
            
            # get the window of HTML (just the CSS Selector)
            selector = error['selector']
            
            try:
                window = soup.select(selector)[0]
            except Exception as e:
                print("could find this window! " + str(e))

            if len(window) > 0:
                # get the correct subfixer
                if error['type'] in self.fixers:
                    subfixer = self.fixers[error['type']]
                else:
                    subfixer = self.default_fixer
                    
                # get the better window
                better_window = subfixer.fix(error, window) # make this not HTML
                
                
                # replace the old window with the new in the html
                # no need to, because subfixer.fix() changes in place
            else:
                print("css selector is no longer valid!!!")
            
            
        return str(soup)
                
        
        
class SubFixer(object):
    """
    An abstract class to fix various things
    """
    
    def __init__(self):
        return
        
        
    def fix(self, error, window):
        """
        Using the error and the provided window of text, create a
        new window of text that fixes the issue.

        Input:
            error : a dict of error information
            window: a string of HTML
            
        Output:
            a new window of HTML
        """
        print("No subfixer implemented; returning the window as is")
    
        return window
    
    
    def _parse_attr(self, attr):
        """
        Given an attribute, clean it up by:
            1. creating multiple attributes if this is actually multiple
               words split by _, -, or /
            2. Ignore any stopwords or non-alphabetical words
            3. Ignore anything that is not a noun, pronoun, or verb
            
        KNOWN ISSUES: 
            for some reason "submit" is a proper noun?
            "next" is considered a stop word
            
        Input:
            attr: a string to parse
        Outpu:
            a list of attributes (or empty string if there were no good ones)
        """
    
        valid_pos = ['NOUN', 'PRON', 'VERB', 'ADJ', 'ADV', 'PROPN']
        
        # split things up so we have a list
        attrs = re.split(r'_|-|\W|/', attr)
        
        # for each attr, go through and filter out any that are noise
        better_attrs = []
        doc = nlp(' '.join(attrs))
        for token in doc:
            if not (not token.is_alpha or token.is_stop or 
                    token.pos_ not in valid_pos):
                
                # a bit hackish, but also kick out anything <4 chars; that's
                # usually noise
                if len(token.text) > 3:
                    better_attrs.append(token.text)
            
        return better_attrs
        
    def _add_attrs_to_list(self, item, all_attrs):
        """
        recursively creates a list of all the attributes for
        this item (including its children). 
        ignores style and href attributes
        
        Input:
            item : a beautifulsoup  object
            all_attrs: list of string attributes
        
        returns an updated all_attrs
        """
        
        for key in item.attrs:
            # don't want to include style or url-based attributes
            if key not in ['style','href']: 
                attr = item[key]
                
                if str is type(attr):
                    all_attrs.append(attr)
                else:
                    all_attrs = all_attrs + attr
                
        for child in item.children:
            if type(child) == type(item):
                all_attrs = self._add_attrs_to_list(child, all_attrs)
                
        
        return all_attrs
        
    
    
    
class EmptyLinkFixer(SubFixer):
    """
    subfixer specialized in adding alternate text to links that don't have
    any text or titles. 
    
    To do this, it looks in the attributes around to get some clues on what it
    should be, tries to extract any important verbs or nouns, and then make some
    informative title tag based on that.
    """
    
    def fix(self, error, window):
       
        # collect the text from all the various attributes (this includes the href!)
        # split the strings on spaces, dashes, and underscores to get a word list
        # make sure to strip out any un-wanted words
        attrs = super()._add_attrs_to_list(window, [])
        better_attrs = []
        for attr in attrs:
            better_attrs = better_attrs + super()._parse_attr(attr)
        
        # collect the unique nouns and verbs
        tags = list(np.unique(better_attrs))

        # create a string title tag based on these
        title = ' '.join(tags)

        # add the attribute to the window
        window['title'] = title
        
        return window
       
    
    
class ContrastFixer(SubFixer):

    def fix(self, error, window):
    
        contrast = error['ratio']
        bg = error['background']
        fg = error['foreground']
        
        # preprocess to make into a hex num
        bg_num = int('0x' + bg[1:], base=16)
        fg_num = int('0x' + fg[1:], base=16)
        
        # TEST TEST TEST
        # make a quick heuristic for testing purposes.
        # if it's light background, darken the foreground
        # if it's a dark background, lighten the foreground
        
        if bg_num > 0x666666:
            fg = fg[:1] + '00' + fg[3:]
        else:
            fg = fg[:1] + 'E' + fg[2] + 'E' + fg[4] + 'E' + fg[6]
        # END TEST
    
        # create a window with our new data
        if 'style' in window.attrs:
            window['style'] += ';color: %s !important;' % fg
        else:
            window['style'] = 'color: %s !important;' % fg
            
        # note we don't actually have to return because BS is pass by reference, so we
        # just changed the original HTML
        return window
        
    