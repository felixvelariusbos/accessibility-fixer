from bs4 import BeautifulSoup

class Fixer(object):


    def __init__(self):
    
        # create the supported fixers
        
        self.fixers = {'contrast': ContrastFixer()}
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
    
    #087591
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
        
    