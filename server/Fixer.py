from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import spacy
import re
import colorsys # why was this wonderful thing hiDING OMG WASTED SO MUCH TIME
from spacy_langdetect import LanguageDetector
import bs4

# load up spacy model globally
nlp = spacy.load("en_core_web_sm")
nlp.add_pipe(LanguageDetector(), name='language_detector', last=True)

class Fixer(object):


    def __init__(self):
    
        # create the supported fixers
        
        self.fixers = {
            'contrast': ContrastFixer(),
            'link_empty': EmptyLinkFixer(),
            'button_empty': EmptyLinkFixer(),
            'text_small'  : FontSizeFixer(),
            'table_layout': TableLayoutFixer(),
            'language_missing': MissingLangFixer(), 
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
        #html = html.lower() # pre process to make the same
        soup = BeautifulSoup(html, 'lxml')
    
        for error in errors:
            print("working on error of type %s" % error['type'])
            
            # get the window of HTML (just the CSS Selector)
            selector = error['selector']
            
            # hack: if this is a table_layout error, need to walk
            # back to get the actual table selector since WAVE gives
            # us the tr/td :/
            if error['type'] == 'table_layout':
                selector = selector[:selector.rfind('table') + 5]
            
            try:
                # if the selector isn't there, we're selecting "ALL" the HTML
                if selector == '' or pd.isna(selector):
                    window = soup.find('html')
                else:
                    window = soup.select_one(selector)
                if window is not None:
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
                    
            except Exception as e:
                print("couldnt find this window! " + str(e))
            
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
    
    
    
    def _collect_all_content(self, element):
        """
        Finds the TEXT content and adds it all to one string        
        Does this recursively for all children of the element
        
        Input:
            element: a beautifulsoup element
        Output:
            content: a string of all the elements text+its children
        """
        content = ''
        for child in element.children:

            if type(child) == bs4.element.NavigableString:
                content = content + ' ' + str(child)
            else:
                content = content + self._collect_all_content(child)
                
        return content
    
    
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

    def _hex_to_rgb(self, color):
        """
        Give the hex string, convert to an RGB group
        
        returns list of ints [r,g,b]
        """
        
        rgbs = [color[1:3], color[3:5], color[5:]]
        rgb = [int(rgbs[0], base=16), 
               int(rgbs[1], base=16), 
               int(rgbs[2], base=16)]
        return rgb
        
    def _rgb_to_hsl(self, rgb):
        """
        Given the list of [r,g,b] (from _hex_to_rgb), convert
        to a HSL group
        
        based on formulas here:
        https://www.rapidtables.com/convert/color/rgb-to-hsl.html
        
        returns a list of ints [h,s,l]
        """
        
        r_prime = rgb[0] / 255
        g_prime = rgb[1] / 255
        b_prime = rgb[2] / 255
        
        c_max_int = max(rgb)
        c_max = max(r_prime, g_prime, b_prime)
        c_min = min(r_prime, g_prime, b_prime)
        
        delta = c_max - c_min
        
        # calculate lum
        lum = (c_max + c_min) / 2
        
        # calculate sat
        if 0 == delta:
            sat = 0
        else:
            sat = delta / (1 - abs(2*lum - 1))
            
        # calculate hue
        if 0 == delta:
            hue = 0
        elif c_max_int == rgb[0]:
            hue = 60 * (((g_prime-b_prime) / delta) % 6)
        elif c_max_int == rgb[1]:
            hue = 60 * (((b_prime-r_prime) / delta) + 2)
        else: #if c_max_int == rgb[2]:
            hue = 60 * (((r_prime-g_prime) / delta) + 4)
        
        return [hue, sat, lum]
        
    def _stringify_hsl(self, hsl):
        """
        Given the HSL tuple, convert into a CSS friendly version
        """
    
    
        hue = int(hsl[0])
        sat = str(int(hsl[1] * 100)) + '%'
        lum = str(int(hsl[2] * 100)) + '%'
        
        return 'hsl(%d %s %s)' % (hue, sat, lum)
        

    def _hsl_to_hex(self, hsl):
        """
        Given the hsl list ([h,s,l]), return the hex string
        
        Input:
            [h,s,l]
        Output:
            Hex string like #ffffff (note it lacks the #)
        """

        # use my new favorite library to convert to RGB tuple
        rgb = colorsys.hls_to_rgb(hsl[0]/360, hsl[2], hsl[1])
        r = rgb[0] * 255
        g = rgb[1] * 255
        b = rgb[2] * 255
        
        # convert tuple to hex string (don't worry about it)
        r_h = hex(round(r))[2:]
        if len(r_h) < 2:
            r_h = '0' + r_h
            
        g_h = hex(round(g))[2:]
        if len(g_h) < 2:
            g_h = '0' + g_h
            
        b_h = hex(round(b))[2:]
        if len(b_h) < 2:
            b_h = '0' + b_h
            
        hex_str = '#' + r_h + g_h + b_h
        return hex_str

    def fix(self, error, window):
    
        contrast = error['ratio']
        bg = error['background']
        fg = error['foreground']

        # convert bg and fg to rgb
        bg = self._hex_to_rgb(bg)
        fg = self._hex_to_rgb(fg)
        
        # convert bg and fg to hsl
        bg_hsl = self._rgb_to_hsl(bg)
        fg_hsl = self._rgb_to_hsl(fg)
        
        # if bg_lum is > .5, darken fg
        # else, brighten fg
        if bg_hsl[2] >= .65:
            fg_hsl[2] = max (fg_hsl[2] - .3, 0.0)
        
        else:
            fg_hsl[2] = min(fg_hsl[2] + .3, 1.0)
            
        
        # convert the new fg hsl to a string
        fg_str = self._stringify_hsl(fg_hsl) 
    
        # create a window with our new data
        if 'style' in window.attrs:
            window['style'] += ';color: %s !important;' % fg_str
        else:
            window['style'] = 'color: %s !important;' % fg_str
            
        # note we don't actually have to return because BS is pass by reference, so we
        # just changed the original HTML
        return window
        
        
class FontSizeFixer(SubFixer):
    """
    Class specialized in forcing fonts to be bigger if they are not
    big enough. Specifically, forces it to be 12 pt
    """

    def fix(self, error, window):
     
        # create a window with our new data
        if 'style' in window.attrs:
            window['style'] += ';font-size: 12pt !important;' 
        else:
            window['style'] = 'font-size: 12pt !important;'    
    
        return window
    
class TableLayoutFixer(SubFixer):
    """
    Fixer specialized in correcting tables that are being used as layout.
    
    Does this by adding a "role:presentation" aria label to the <table>
    """
    
    def fix(self, error, window):
        
        # i really probably should do more than this, but it works?
        window['role'] = 'presentation'
        
        return window
    
    
class MissingLangFixer(SubFixer):
    """
    Fixer specialized in detecting and adding in a language attribute
    (when none was provided). Make sure to provide the BeautifulSoup 
    <html>...</html>, since there is no CSS selector for these errors.
    We need to be able to edit the <head>!
    """

    def fix(self, error, window):
        
        # find the body
        body = window.find('body')
        
        if not body:
            print("no body tag! cannot detect language")
            return window
        
        # get a big string of content
        content = super()._collect_all_content(body)
        
        # calculate the language
        doc = nlp(content)
        language = doc._.language
        
        # add that langauge to the html tag
        if len(language) > 0:
            #html_tag = window.find('html')
            html_tag = window
            html_tag.attrs['lang'] = language['language']
        else:
            print("could not figure out language!")
        
        # return!
        return window
    