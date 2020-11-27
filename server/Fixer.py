

class Fixer(object):


    def __init__(self):
    
        # create the supported fixers
        self.fixers = {}
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
    
        for error in errors:
            print("working on error of type %s" % error['type'])
            
            # get the correct subfixer
            if error['type'] in self.fixers:
                subfixer = self.fixer[error['type']]
            else:
                subfixer = self.default_fixer
                
            # get the better window
            better_window = subfixer.fix(error, html) # make this not HTML
            
            # replace the old window with the new in the html
            
        return html
                
        
        
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
    