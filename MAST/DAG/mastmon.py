import os
from MAST.utility.picklemanager import PickleManager
from MAST.DAG.dagscheduler import DAGScheduler
import time
from MAST.DAG.dagutil import *
abspath = os.path.abspath


class MASTmon(object):
    """MASTmon is a daemon to run dagscheduler class.
        This finds newly submitted session (recipe) and manage them.
        Also completed session is moved in archive directory by MASTmon.
        For consistency, users may touch sesssions in the archive directory."""
    
    def __init__(self):
        self.registered_dir = set()
        self.home = os.environ['MAST_SCRATCH']
        self.pm = PickleManager()
        self.pn_mastmon = os.path.join(self.home,'mastmon_info.pickle')
        self._ARCHIVE = 'archive'
        self.scheduler = DAGScheduler()
        self.version = 0.1
        
        try:
            if not os.path.exists(self.home):
                os.system('mkdir %s' % abspath(self.home))
                os.system('mkdir %s' % os.path.join(abspath(self.home), self._ARCHIVE))
        except:
            print 'Error to make directory for MASTmon and completed sessions'

    def add_sessions(self,new_session_dirs):
        """recipe_dirs is a set of sessions in MASTmon home directory"""
        for session_dir in  new_session_dirs:
            try:
                os.chdir(session_dir)
                mastobj = self.pm.load_variable('mast.pickle')
                depdict = mastobj.dependency_dict
                ingredients = mastobj.ingredients

                if self.scheduler is None:
                    print 'stpe 1: create DAGScheduler object'
                    self.scheduler = DAGScheduler()
                    
                self.scheduler.addjobs(ingredients_dict=ingredients, dependency_dict=depdict, sname=session_dir)
                    
            except:
                print 'Error in add_sessions'
                raise
                
            os.chdir(self.home)
                
        self.registered_dir = self.registered_dir.union(new_session_dirs)

    def _save(self):
        """Save current stauts of MASTmon such as registered_dir and scheduler"""
        var_dict = {}
        var_dict['registered_dir'] = self.registered_dir
        var_dict['scheduler'] = self.scheduler
        var_dict['version']  = self.version
        self.pm.save(var_dict,filename=self.pn_mastmon)
        
    def _load(self):
        """Load MASTmon's information pickle file"""

        if os.path.isfile(self.pn_mastmon):
            var_dict = self.pm.load_variable(self.pn_mastmon)
            if 'version' in var_dict and var_dict['version'] != self.version:
                print 'Error: mastmon_info.pickle is version %.2f' % var_dict['version']
                print 'Error: mastmon version %.2f' % self.version
                raise

            if 'registered_dir' in var_dict:
                self.registered_dir = var_dict['registered_dir']
                
            if 'scheduler' in var_dict:
                self.scheduler = var_dict['scheduler']
        
    def run(self, niter=None, stopcond=None, interval=None):
        """Run Mastmon. First of all, this makes MASTmon go to mastmon home load dagscheduler pickle.
            In addition, there are couple of options to run mastmon.
            ex) mastmon.run()  # run MASTmon forever as a real daemon. By default interval is 10 sec
            ex) mastmon.run(interval=30) # run MASTmon forever as a real daemon. By default interval is 30 sec
            ex) mastmon.run(niter=1) # run MASTmon one iteration for crontab user. By default interval is 10 sec
            ex) mastmon.run(niter=20,stopcond='NOSESSION') # run MASTmon for 20 iterations.
                                                             And stop it all sessions are done.
        """
        # move to mastmon home
        curdir = os.getcwd()
        try:
            os.chdir(self.home)    
        except:
            os.chdir(curdir)
            print 'Error: Failed to move to MASTmon home %s' % self.home
            raise
        
        if interval is None:
            interval = SCHEDULING_INTERVAL
            
        #load dagscheduler pickle
        self._load()
        iter = 0;
        while True:
            if niter is not None and iter >= niter:
                break
            
            iter = iter + 1
            # get directories from mast home
            session_dirs = os.walk('.').next()[1]

            # remove 'archive' directory
            if self._ARCHIVE in session_dirs:
                session_dirs.remove(self._ARCHIVE)

            else:
                # if masthome doesn't have 'archive', then make it
                os.system('mkdir %s' % os.path.join(abspath(self.home),self._ARCHIVE))

            new_session_dirs = set(session_dirs) - self.registered_dir

            # add new sessions
            self.add_sessions(new_session_dirs)

            # run it for n iterations or until all sessions are complete
            csnames = self.scheduler.run(niter=1)
            #remove complete sessions

            self.registered_dir = self.registered_dir - csnames

            # save scheduler object
            self._save()

            if stopcond is not None:
                if stopcond.upper() == 'NOSESSION' and len(self.registered_dir) == 0:
                    break
                
            time.sleep(interval)
                          
        # move back to original directory
        os.chdir(curdir)
            
                         




