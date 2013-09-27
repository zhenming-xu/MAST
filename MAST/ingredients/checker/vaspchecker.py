from pymatgen.io.vaspio import Poscar
from pymatgen.io.vaspio import Outcar
from pymatgen.io.vaspio import Potcar
from pymatgen.io.vaspio import Incar
from pymatgen.io.vaspio import Kpoints
from pymatgen.io.vaspio.vasp_output import Vasprun
from pymatgen.io.cifio import CifParser
from pymatgen.core.sites import PeriodicSite
from pymatgen.core.structure import Structure
from MAST.utility import dirutil
from MAST.utility.mastfile import MASTFile
from MAST.utility import MASTError
from MAST.utility.metadata import Metadata
from MAST.ingredients.pmgextend.structure_extensions import StructureExtensions
import os
import shutil
import logging
from MAST.ingredients.checker import BaseChecker
class VaspChecker(BaseChecker):
    """VASP checker functions
    """
    def __init__(self, **kwargs):
        allowed_keys = {
            'name' : (str, str(), 'Name of directory'),
            'program_keys': (dict, dict(), 'Dictionary of program keywords'),
            'structure': (Structure, None, 'Pymatgen Structure object')
            }
        BaseChecker.__init__(self, allowed_keys, **kwargs)

        logging.basicConfig(filename="%s/mast.log" % os.getenv("MAST_CONTROL"), level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

    def get_structure_from_file(self, myfilepath=""):
        """Get the structure from a specified file path.
            For VASP, this is a POSCAR-type file.
            Args:
                myfilepath <str>: File path for structure.
        """
        return Poscar.from_file(myfilepath).structure

    def get_initial_structure_from_directory(self,mydir=""):
        """Get the initial structure.
            For VASP, this is the POSCAR file.
            Args:
                mydir <str>: Directory. If no directory is given,
                    use current ingredient directory given as
                    keyword 'name'
        """
        if mydir == "":
            mydir = self.keywords['name']
        return Poscar.from_file("%s/POSCAR" % mydir).structure
    
    def get_final_structure_from_directory(self, mydir=""):
        """Get the final structure.
            For VASP, this is the CONTCAR file.
            Args:
                mydir <str>: Directory. If no directory is given,
                    use current ingredient directory given
                    as keyword 'name'
        """
        if mydir == "":
            mydir = self.keywords['name']
        return Poscar.from_file("%s/CONTCAR" % mydir).structure
    
    def forward_final_structure_file(self, childpath, newname="POSCAR"):
        """Forward the final structure.
            For VASP, this is the CONTCAR.
            Args:
                childpath <str>: Path of child ingredient
                newname <str>: new name (default 'POSCAR')
        """
        dirutil.lock_directory(childpath)
        shutil.copy(os.path.join(self.keywords['name'], "CONTCAR"),os.path.join(childpath, newname))
        dirutil.unlock_directory(childpath)
        return

    def forward_initial_structure_file(self, childpath, newname="POSCAR"):
        """Forward the initial structure.
            For VASP, this is the POSCAR. This function is
            used after phonon calculations, where the CONTCAR
            contains the last displacement. To forward to PHON,
            the POSCAR (without displacements) should be used.
            Args:
                childpath <str>: Path of child ingredient
                newname <str>: new name (default 'POSCAR')
        """
        dirutil.lock_directory(childpath)
        shutil.copy(os.path.join(self.keywords['name'], "POSCAR"),os.path.join(childpath, newname))
        dirutil.unlock_directory(childpath)
        return

    def forward_dynamical_matrix_file(self, childpath, newname="DYNMAT"):
        """Forward the dynamical matrix.
            For VASP, this is the DYNMAT file.
            Args:
                childpath <str>: Path of child ingredient
                newname <str>: new name (default 'DYNMAT')
        """
        dirutil.lock_directory(childpath)
        shutil.copy(os.path.join(self.keywords['name'], "DYNMAT"),os.path.join(childpath, newname))
        dirutil.unlock_directory(childpath)
        return

    def forward_displacement_file(self, childpath, newname="XDATCAR"):
        """Forward displacement information.
            For VASP, this is the XDATCAR file.
            Args:
                childpath <str>: Path of child ingredient
                newname <str>: new name (default 'XDATCAR')
        """
        dirutil.lock_directory(childpath)
        shutil.copy(os.path.join(self.keywords['name'], "XDATCAR"),os.path.join(childpath, newname))
        dirutil.unlock_directory(childpath)
        return

    def forward_energy_file(self, childpath, newname="OSZICAR"):
        """Forward the energy file.
            For VASP, this is the OSZICAR file.
            Args:
                childpath <str>: Path of child ingredient
                newname <str>: new name (default 'OSZICAR')
        """
        dirutil.lock_directory(childpath)
        shutil.copy(os.path.join(self.keywords['name'], "OSZICAR"),os.path.join(childpath, newname))
        dirutil.unlock_directory(childpath)
        return

    def is_complete(self):
        """Check if single VASP non-NEB calculation is complete.
        """
        try:
            myoutcar = Outcar(os.path.join(self.keywords['name'], "OUTCAR"))
        except (IOError):
            return False

        #hw 04/19/13
        try:
            if myoutcar.run_stats['User time (sec)'] > 0:
                return True
            else:
                return False
        except KeyError:
            return False

    def is_ready_to_run(self):
        """Check if single VASP non-NEB ingredient is 
            ready to run.
        """
        dirname = self.keywords['name']
        notready=0
        if not(os.path.isfile(dirname + "/KPOINTS")):
            notready = notready + 1
        if not(os.path.isfile(dirname + "/POTCAR")):
            notready = notready + 1
        if not(os.path.isfile(dirname + "/INCAR")):
            notready = notready + 1
        if not(os.path.isfile(dirname + "/POSCAR")):
            notready = notready + 1
        if not(os.path.isfile(dirname + "/submit.sh")):
            notready = notready + 1
        if notready > 0:
            return False
        else:
            return True

    def _vasp_poscar_setup(self):
        """Set up the POSCAR file for a single VASP run.
        """
        name = self.keywords['name']
        pospath = os.path.join(name, "POSCAR")
        if os.path.isfile(pospath):
            my_poscar = Poscar.from_file(pospath) 
            #parent should have given a structure
        else: #this is an originating run; mast should give it a structure
            my_poscar = Poscar(self.keywords['structure'])
            self.logger.info("No POSCAR found from a parent; base structure used for %s" % self.keywords['name'])
        if 'mast_coordinates' in self.keywords['program_keys'].keys():
            sxtend = StructureExtensions(struc_work1=my_poscar.structure)
            coordstrucs=self.get_coordinates_only_structure_from_input()
            newstruc = sxtend.graft_coordinates_onto_structure(coordstrucs[0])
            my_poscar.structure=newstruc.copy()
        dirutil.lock_directory(name)
        my_poscar.write_file(pospath)
        dirutil.unlock_directory(name)
        return my_poscar

    def _vasp_kpoints_setup(self):
        """Parse mast_kpoints string, which should take the format:
            number, number, number designation
            examples: "3x3x3 M", "1x1x1 G". If no designation is given,
            Monkhorst-Pack is assumed.
        """
        name = self.keywords['name']
        if 'mast_kpoints' in self.keywords['program_keys'].keys():
            kptlist = self.keywords['program_keys']['mast_kpoints']
        else:
            raise MASTError(self.__class__.__name__,"k-point instructions need to be set in ingredients keyword mast_kpoints")
        if len(kptlist) == 3:
            desig = "M"
        else:
            desig = kptlist[3].upper()
        if desig == "M":
            my_kpoints = Kpoints.monkhorst_automatic(kpts=(int(kptlist[0]),int(kptlist[1]),int(kptlist[2])),shift=(0,0,0))
        elif desig == "G":
            my_kpoints = Kpoints.gamma_automatic(kpts=(int(kptlist[0]),int(kptlist[1]),int(kptlist[2])),shift=(0,0,0))
        else:
            raise MASTError(self.__class__.__name__,"kpoint designation " + desig + " not recognized.")
        dirutil.lock_directory(name)
        my_kpoints.write_file(name + "/KPOINTS")
        dirutil.unlock_directory(name)
        return my_kpoints

    def _vasp_potcar_setup(self, my_poscar):
        """Set up the POTCAR file."""
        name = self.keywords['name']

        if 'mast_xc' in self.keywords['program_keys'].keys():
            myxc = self.keywords['program_keys']['mast_xc'].upper() #Uppercase
        else:
            raise MASTError("vasp_checker, _vasp_potcar_setup","Exchange correlation functional needs to be specified in ingredients keyword mast_xc")

        if ('mast_pp_setup' in self.keywords['program_keys'].keys()):
            sites = my_poscar.site_symbols
            setup = self.keywords['program_keys']['mast_pp_setup']
            pp_sites = list()
            for site in sites:
                try:
                    pp_sites.append(setup[site])
                except KeyError:
                    pp_sites.append(site)
            my_potcar = Potcar(symbols=pp_sites, functional=myxc, sym_potcar_map=None)
        else:
            my_potcar = Potcar(symbols=my_poscar.site_symbols, functional=myxc, sym_potcar_map=None)

        dirutil.lock_directory(name)
        my_potcar.write_file(name + "/POTCAR")
        dirutil.unlock_directory(name)
        return my_potcar

    def _vasp_incar_get_non_mast_keywords(self):
        """Get the non-VASP keywords and make a dictionary."""
        incar_dict=dict()
        allowedpath = os.path.join(dirutil.get_mast_install_path(), 'MAST',
                        'ingredients','programkeys','vasp_allowed_keywords.py')
        allowed_list = self._vasp_incar_get_allowed_keywords(allowedpath)
        for key, value in self.keywords['program_keys'].iteritems():
            if not key[0:5] == "mast_":
                keytry = key.upper()
                if not (keytry in allowed_list):
                    print "Ignoring program key %s for INCAR. To allow this keyword, add it to %s" % (keytry, allowedpath)
                else:
                    if type(value)==str and value.isalpha():
                        incar_dict[keytry]=value.capitalize() #First letter cap
                    else:
                        incar_dict[keytry]=value
        return incar_dict


    def _vasp_incar_get_allowed_keywords(self, allowedpath):
        """Get allowed vasp keywords.
            Args:
                allowedpath <str>: file path for allowed vasp keywords
        """
        allowed = MASTFile(allowedpath)
        allowed_list=list()
        for entry in allowed.data:
            allowed_list.append(entry.strip())
        return allowed_list

    def _vasp_incar_setup(self, my_potcar, my_poscar):
        """Set up the INCAR, including MAGMOM string, ENCUT, and NELECT."""
        name=self.keywords['name']
        myd = dict()
        myd = self._vasp_incar_get_non_mast_keywords()
        try:
            myd.pop("IMAGES")
        except KeyError:
            pass
        if 'mast_multiplyencut' in self.keywords['program_keys'].keys():
            mymult = float(self.keywords['program_keys']['mast_multiplyencut'])
        else:
            mymult = 1.5
        if 'ENCUT' in myd.keys():
            pass
        else:
            myd['ENCUT']=self._get_max_enmax_from_potcar(my_potcar)*mymult
        if 'mast_setmagmom' in self.keywords['program_keys'].keys():
            magstr = str(self.keywords['program_keys']['mast_setmagmom'])
            magmomstr=""
            maglist = magstr.split()
            numatoms = sum(my_poscar.natoms)
            if len(maglist) < numatoms:
                magct=0
                while magct < len(maglist):
                    magmomstr = magmomstr + str(my_poscar.natoms[magct]) + "*" + maglist[magct] + " " 
                    magct = magct + 1
            else:
                magmomstr = magstr
            myd['MAGMOM']=magmomstr
        if 'mast_charge' in self.keywords['program_keys'].keys():
            myelectrons = self.get_total_electrons(my_poscar, my_potcar)
            newelectrons=0.0
            try:
                adjustment = float(self.keywords['program_keys']['mast_charge'])
            except (ValueError, TypeError):
                raise MASTError("vasp_checker, vasp_incar_setup","Could not parse adjustment")
            #newelectrons = myelectrons + adjustment
            newelectrons = myelectrons - adjustment
            myd['NELECT']=str(newelectrons)
        my_incar = Incar(myd)
        dirutil.lock_directory(name)
        my_incar.write_file(name + "/INCAR")
        dirutil.unlock_directory(name)
        return my_incar

    def set_up_program_input(self):
        """Set up the program input files."""
        myposcar = self._vasp_poscar_setup()
        self._vasp_kpoints_setup()
        mypotcar = self._vasp_potcar_setup(myposcar)
        self._vasp_incar_setup(mypotcar, myposcar)
        return

    def forward_extra_restart_files(self, childpath):
        """Forward extra restart files: 
            For VASP, this entails a softlink to WAVECAR and 
            CHGCAR.
            Args:
                childpath <str>: path to child ingredient
        """
        parentpath = self.keywords['name']
        dirutil.lock_directory(childpath)
        import subprocess
        #print "cwd: ", os.getcwd()
        curpath = os.getcwd()
        os.chdir(childpath)
        #print parentpath
        #print childpath
        mylink=subprocess.Popen("ln -s %s/WAVECAR WAVECAR" % parentpath, shell=True)
        mylink.wait()
        mylink2=subprocess.Popen("ln -s %s/CHGCAR CHGCAR" % parentpath, shell=True)
        mylink2.wait()
        os.chdir(curpath)
        dirutil.unlock_directory(childpath)
    def add_selective_dynamics_to_structure_file(self, sdarray):
        """Add selective dynamics to a structure file.
            In the case of VASP, the structure file is 
            POSCAR-like
            Args:
                sdarray <numpy array of bool>: Numpy array of
                    booleans for T F F etc.
        """
        name = self.keywords['name']
        pname = os.path.join(name,"POSCAR")
        phposcar = Poscar.from_file(pname)
        phposcar.selective_dynamics = sdarray
        dirutil.lock_directory(name)
        os.rename(pname, pname + "_no_sd")
        phposcar.write_file(pname)
        dirutil.unlock_directory(name)
        return

    def get_energy(self):
        """Get the energy.
            For VASP, this is E0 energy from vasprun.xml
        """
        return Vasprun('%s/vasprun.xml' % self.keywords['name']).ionic_steps[-1]["electronic_steps"][-1]["e_0_energy"]

    def _get_max_enmax_from_potcar(self, mypotcar):
        """Get maximum enmax value (float) from Potcar 
            (combined list)
        """
        enmax_list=list()
        potcarct=0
        onepotcar=None
        while potcarct < len(mypotcar):
            onepotcar = mypotcar[potcarct] #A PotcarSingle object
            enmax_list.append(onepotcar.enmax)
            potcarct = potcarct + 1
        return max(enmax_list)

    def _make_one_unfrozen_atom_poscar(self, myposcar, natom):
        """Use selective dynamics to make a poscar with one unfrozen atom.
            myposcar = Poscar
            natom = the number of the atom to unfreeze
            Returns: Poscar (use write_file function on it).
        """
        mysd=np.zeros([sum(myposcar.natoms),3],bool)
        mysd[natom-1][0]=True #indexing starts at 0
        mysd[natom-1][1]=True
        mysd[natom-1][2]=True
        myposcar.selective_dynamics = mysd
        return myposcar

    def _make_one_unfrozen_direction_poscar(self, myposcar, natom, ndir):
        """Use selective dynamics to make a poscar with one unfrozen atom.
            myposcar = Poscar
            natom = the number of the atom to unfreeze
            ndir = the direction to freeze (0, 1, 2 for x, y, z)
            Returns: Poscar (use write_file function on it).
        """
        mysd=np.zeros([sum(myposcar.natoms),3],bool)
        mysd[natom-1][ndir]=True #indexing starts at 0
        myposcar.selective_dynamics = mysd
        return myposcar


    def read_my_dynamical_matrix_file(self, mydir="", fname="DYNMAT"):
        """Read a dynamical matrix file.
            For VASP this is DYNMAT.
            Args:
                mydir <str>: directory
                fname <str>: file name (default 'DYNMAT')
            Returns:
                dyndict <dict>: dictionary structured like this:
                    ['numspec'] = <int> number of species
                    ['numatoms'] = <int> number of atoms
                    ['numdisp'] = <int> number of displacements
                    ['massline'] = <str> masses line
                    ['atoms'][atom <int>][disp <int>]['displine'] =
                        displacement
                        vector (part of first line in dynmat block,
                        e.g. "0.01 0 0")
                    ['atoms'][atom <int>][disp <int>]['dynmat'] =
                            <list>
                            list of dynmat lines for this atom
                            and this displacement
        """
        mydyn = MASTFile(os.path.join(mydir, fname))
        mydata = list(mydyn.data) #whole new copy
        dyndict=dict()
        firstline = mydata.pop(0) #pop first value
        firstspl = firstline.strip().split()
        dyndict['numspec']=int(firstspl[0])
        numatoms = int(firstspl[1])
        dyndict['numatoms']=numatoms
        dyndict['numdisp']=int(firstspl[2])
        dyndict['massline']=mydata.pop(0)
        dyndict['atoms']=dict()
        atom=0
        disp=0
        thirdline=""
        while len(mydata) > 0:
            thirdline = mydata.pop(0)
            thirdspl = thirdline.strip().split()
            atom=int(thirdspl[0])
            disp=int(thirdspl[1])
            displine=' '.join(thirdspl[2:])
            if not atom in dyndict['atoms'].keys():
                dyndict['atoms'][atom]=dict()
            dyndict['atoms'][atom][disp]=dict()
            dyndict['atoms'][atom][disp]['displine'] = displine
            dyndict['atoms'][atom][disp]['dynmat']=list()
            for act in range(0, numatoms):
                dyndict['atoms'][atom][disp]['dynmat'].append(mydata.pop(0))
        return dyndict

    def write_my_dynamical_matrix_file(self, mydir, dyndict, fname="DYNMAT"):
        """Write a dynamical matrix file based on a dictionary.
            Args:
                mydir <str>: Directory in which to write
                dyndict <dict>: Dictionary of dynmat (see read_my_dynmat)
                fname <str>: filename (default DYNMAT)
        """
        dynwrite=MASTFile()
        dynwrite.data=list()
        firstline=str(dyndict['numspec']) + " " + str(dyndict['numatoms']) + " " + str(dyndict['numdisp']) + "\n"
        dynwrite.data.append(firstline)
        dynwrite.data.append(dyndict['massline'])
        atomlist=dyndict['atoms'].keys()
        atomlist.sort()
        for atom in atomlist:
            displist = dyndict['atoms'][atom].keys()
            displist.sort()
            for disp in displist:
                thirdline = str(atom) + " " + str(disp) + " " + dyndict['atoms'][atom][disp]['displine'] + "\n"
                dynwrite.data.append(thirdline)
                for line in dyndict['atoms'][atom][disp]['dynmat']:
                    dynwrite.data.append(line)
        dynwrite.to_file(os.path.join(mydir, fname))


    def write_my_dynmat_without_disp_or_mass(self, mydir, dyndict, fname="DYNMAT"):
        """Write a dynamical matrix file without the displacement indicators 1, 2, 3
            and without the masses line, and with first line having only
            the total number of displacements, for PHON.
            Args:
                mydir <str>: Directory in which to write
                dyndict <dict>: Dictionary of dynmat (see read_my_dynmat)
                fname <str>: filename (default DYNMAT)
        """
        dynwrite=MASTFile()
        dynwrite.data=list()
        firstline=str(dyndict['numdisp']) + "\n"
        dynwrite.data.append(firstline)
        atomlist=dyndict['atoms'].keys()
        atomlist.sort()
        for atom in atomlist:
            displist = dyndict['atoms'][atom].keys()
            displist.sort()
            for disp in displist:
                thirdline = str(atom) + " " + dyndict['atoms'][atom][disp]['displine'] + "\n"
                dynwrite.data.append(thirdline)
                for line in dyndict['atoms'][atom][disp]['dynmat']:
                    dynwrite.data.append(line)
        dynwrite.to_file(os.path.join(mydir, fname))

    def read_my_displacement_file(self, mydir, fname="XDATCAR"):
        """Read a displacement file. For VASP this is XDATCAR.
            Returns:
                xdatdict <dict>: Dictionary of configurations
                    xdatdict['descline'] = <str> description line
                    xdatdict['specline'] = <str> species line
                    xdatdict['numline'] = <str> numbers lines
                    xdatdict['type'] = <str> Direct or not
                    xdatdict['numatoms'] = <int> number of atoms
                    xdatdict['configs'][config <int>] = <list>
                            list of lines in this configuration
                    xdatdict['scale'] = <str> scale
                    xdatdict['latta'] = <str> lattice vector a
                    xdatdict['lattb'] = <str> lattice vector b
                    xdatdict['lattc'] = <str> lattice vector c
        """
        myxdat = MASTFile(os.path.join(mydir, fname))
        mydata = list(myxdat.data) #whole new copy
        xdatdict=dict()
        xdatdict['descline'] = mydata.pop(0) #pop first value
        tryspec = mydata.pop(0)
        tryspecstrip = tryspec.strip()
        tryspecstrip = tryspecstrip.replace(" ","x")
        if not tryspecstrip.isalpha(): # version 5.2.11 and on
            xdatdict['scale'] = tryspec
            xdatdict['latta'] = mydata.pop(0)
            xdatdict['lattb'] = mydata.pop(0)
            xdatdict['lattc'] = mydata.pop(0)
            xdatdict['specline'] = mydata.pop(0)
        else:
            xdatdict['scale'] = ""
            xdatdict['latta'] = ""
            xdatdict['lattb'] = ""
            xdatdict['lattc'] = ""
            xdatdict['specline'] = tryspec
        numline = mydata.pop(0)
        xdatdict['numline'] = numline
        numatoms = sum(map(int, numline.strip().split()))
        xdatdict['numatoms'] = numatoms
        if not tryspecstrip.isalpha(): #version 5.2.11 and on
            xdatdict['type'] = ""
        else:
            xdatdict['type'] = mydata.pop(0)
        xdatdict['configs']=dict()
        kfgct=1
        while len(mydata) > 0:
            mydata.pop(0) # Konfig line, or a blank line
            xdatdict['configs'][kfgct] = list()
            for act in range(0,numatoms):
                if len(mydata) > 0:
                    xdatdict['configs'][kfgct].append(mydata.pop(0))
            kfgct=kfgct+1
        return xdatdict

    def write_my_displacement_file(self, mydir, xdatdict, fname="XDATCAR"):
        """Write a displacement file.
            Args:
                mydir <str>: Directory in which to write
                xdatdict <dict>: Dictionary of XDATCAR (see read_my_xdatcar)
                fname <str>: filename (default DYNMAT)
        """
        xdatwrite=MASTFile()
        xdatwrite.data=list()
        xdatwrite.data.append(xdatdict['descline'])
        if not (xdatdict['scale'] == ""):
            xdatwrite.data.append(xdatdict['scale'])
            xdatwrite.data.append(xdatdict['latta'])
            xdatwrite.data.append(xdatdict['lattb'])
            xdatwrite.data.append(xdatdict['lattc'])
        xdatwrite.data.append(xdatdict['specline'])
        xdatwrite.data.append(xdatdict['numline'])
        if not (xdatdict['type'] == ""):
            xdatwrite.data.append(xdatdict['type'])
        configlist = xdatdict['configs'].keys()
        configlist.sort()
        for cfg in configlist:
            xdatwrite.data.append("Konfig=%1i\n" % cfg)
            xdatwrite.data.extend(xdatdict['configs'][cfg])
        xdatwrite.to_file(os.path.join(mydir, fname))

    def combine_dynamical_matrix_files(self, mydir):
        """Combine dynamical matrix files into one file.
            Args:
                mydir <str>: top directory for DYNMAT files
        """
        dynmatlist = walkfiles(mydir, 2, 5, "*DYNMAT*") #start one level below
        if len(dynmatlist) == 0:
            raise MASTError("pmgextend combine_dynmats", "No DYNMATs found under " + mydir)
        totnumdisp=0
        largedyn=dict()
        largedyn['atoms'] = dict()
        for onedynmat in dynmatlist:
            dyndir = os.path.dirname(onedynmat)
            onedyn = self.read_my_dynamical_matrix_file(dyndir)
            totnumdisp = totnumdisp + onedyn['numdisp']
            for atom in onedyn['atoms'].keys():
                if not atom in largedyn['atoms'].keys():
                    largedyn['atoms'][atom]=dict()
                    mydisp=1 #start at 1
                for disp in onedyn['atoms'][atom].keys():
                    if disp in largedyn['atoms'][atom].keys():
                        mydisp=mydisp + 1 #increment
                    largedyn['atoms'][atom][mydisp]=dict()
                    largedyn['atoms'][atom][mydisp]['displine'] = str(onedyn['atoms'][atom][disp]['displine'])
                    largedyn['atoms'][atom][mydisp]['dynmat']=list(onedyn['atoms'][atom][disp]['dynmat'])
        largedyn['numspec'] = onedyn['numspec'] #should all be the same
        largedyn['numatoms'] = onedyn['numatoms']
        largedyn['massline'] = onedyn['massline']
        largedyn['numdisp'] = totnumdisp
        self.write_my_dynamical_matrix_file(mydir, largedyn, "DYNMAT_combined")
        self.write_my_dynamical_matrix_file(mydir, largedyn, "DYNMAT")

    def combine_displacement_files(self, mydir):
        """Combine displacement files (here XDATCARs) into one file.
            Args:
                mydir <str>: top directory for DYNMAT files
        """
        largexdat=dict()
        xdatlist = walkfiles(mydir, 2, 5, "*XDATCAR*") #start one level below
        if len(xdatlist) == 0:
            raise MASTError("pmgextend combine_displacements", "No XDATCARs found under " + mydir)
        kfgct=1 # skip config 1 until the end
        largexdat['configs']=dict()
        xdatlist.sort() #get them in order
        for onexdatmat in xdatlist:
            xdatdir = os.path.dirname(onexdatmat)
            onexdat = self.read_my_displacement_file(xdatdir)
            for kfg in onexdat['configs'].keys():
                if kfg == 1: #skip config 1 until the end
                    pass
                else:
                    kfgct = kfgct + 1 #start at 2
                    largexdat['configs'][kfgct] = onexdat['configs'][kfg]
        largexdat['configs'][1] = onexdat['configs'][1] #get one of the first configs (the first should be the same for all the XDATCARs)
        largexdat['descline'] = onexdat['descline'] #should all be the same
        largexdat['specline'] = onexdat['specline']
        largexdat['scale'] = onexdat['scale']
        largexdat['latta'] = onexdat['latta']
        largexdat['lattb'] = onexdat['lattb']
        largexdat['lattc'] = onexdat['lattc']
        largexdat['numline'] = onexdat['numline']
        largexdat['numatoms'] = onexdat['numatoms']
        largexdat['type'] = onexdat['type']
        self.write_my_displacement_file(mydir, largexdat, "XDATCAR_combined")
        self.write_my_displacement_file(mydir, largexdat, "XDATCAR")
    def make_hessian(self, myposcar, mydir):
        """Combine DYNMATs into one hessian and solve for frequencies.
            myposcar = Poscar
            mydir = top directory for DYNMAT files
        """
        raise MASTError(self.__class__.__name__, "This method is abandoned and should not be used.")
        natoms = sum(myposcar.natoms)
        myhess=np.zeros([natoms*3, natoms*3])
        #arrange as x1, y1, z1, x2, y2, z2, etc.
        dynmatlist = walkfiles(mydir, 1, 5, "*DYNMAT*")
        if len(dynmatlist) == 0:
            raise MASTError("pmgextend combine_dynmats", "No DYNMATs found under " + mydir)
        opendyn=""
        print "DYNMATLIST:"
        print dynmatlist
        datoms=0
        for onedynmat in dynmatlist:
            dynlines=[]
            opendyn = open(onedynmat,'rb')
            dynlines=opendyn.readlines()
            opendyn.close()
            datoms = int(dynlines[0].split()[1])
            dmats = int(dynlines[0].split()[2])
            mycount=2 #starting line
            while mycount < len(dynlines)-datoms:
                littlemat=[]
                topatom = int(dynlines[mycount].split()[0])
                whichdir = int(dynlines[mycount].split()[1])
                littlemat = dynlines[mycount+1:mycount+datoms+1]
                print littlemat
                act = 0
                while act < datoms:
                    dactx=float(littlemat[act].split()[0])
                    dacty=float(littlemat[act].split()[1])
                    dactz=float(littlemat[act].split()[2])
                    colidx = (topatom-1)*3 + (whichdir-1)
                    #so 2  3  on first line means atom 2's z direction
                    #then with atom 1x, 1y, 1z; 2x, 2y, 2z, etc.
                    myhess[colidx][act*3+0]=dactx
                    myhess[colidx][act*3+1]=dacty
                    myhess[colidx][act*3+2]=dactz
                    act = act + 1
                mycount = mycount + datoms + 1
                print mycount
        print "UNALTERED HESSIAN:"
        print(myhess)
        #create mass matrix
        masses=dynlines[1].split()
        print "MASSES:", masses
        massarr=np.zeros([datoms*3,1])
        act=0
        print myposcar.natoms
        nspec=len(myposcar.natoms)
        totatoms=0
        while act < datoms:
            mymass=0
            nct=0
            totatoms=0
            while (mymass==0) and nct < nspec:
                totatoms = totatoms + myposcar.natoms[nct]
                if act < totatoms:
                    mymass = float(masses[nct])
                nct = nct + 1
            print mymass
            massarr[act*3+0][0]=mymass
            massarr[act*3+1][0]=mymass
            massarr[act*3+2][0]=mymass
            act = act + 1
        massmat = massarr*np.transpose(massarr)
        print "MASS MAT:"
        print massmat
        print "STEP:"
        step = float(dynlines[2].split()[2])
        print step
        print "HESSIAN * -1 / step / sqrt(mass1*mass2)"
        normhess=np.zeros([natoms*3,natoms*3])
        cidx=0
        while cidx < natoms*3:
            ridx=0
            while ridx < natoms*3:
                normhess[ridx][cidx]=-1*myhess[ridx][cidx]/step/np.sqrt(massmat[ridx][cidx])
                ridx = ridx + 1
            cidx = cidx + 1
        print normhess
        print "EIGENVALUES:"
        myeig = np.linalg.eig(normhess)[0]
        print myeig
        print "SQRT of EIGENVALUES in sqrt(eV/AMU)/Angstrom/2pi:"
        myfreq = np.sqrt(myeig)
        print myfreq
        print "SQRT OF EIGENVALUES in THz:"
        myfreqThz = myfreq*15.633302
        print myfreqThz
        myfreqThzsorted = myfreqThz
        myfreqThzsorted.sort()
        print myfreqThzsorted
        return myfreqThzsorted

    def get_total_electrons(self, myposcar, mypotcar):
        """Get the total number of considered electrons in the system."""
        atomlist = myposcar.natoms
        zvallist = self.get_valence_list(mypotcar)
        totzval = 0.0
        atomct = 0
        if not (len(zvallist) == len(atomlist)):
            raise MASTError(self.__class__.__name__,
                "Number of species and number of POTCARs do not match.")
        while atomct < len(atomlist):
            totzval = totzval + (atomlist[atomct] * zvallist[atomct])
            atomct = atomct + 1
        return totzval

    def get_valence_list(self, mypotcar):
        """Get list of number of valence electrons for species.
            For VASP, this is a list of zvals from POTCAR.
            Args:
                mypotcar <list of PotcarSingle objects>
            Returns:
                zval_list <list of int>: List of number of
                                        valence electrons
        """
        zval_list=list()
        potcarct=0
        onepotcar=None
        while potcarct < len(mypotcar):
            onepotcar = mypotcar[potcarct] #A PotcarSingle object
            zval_list.append(onepotcar.zval)
            potcarct = potcarct + 1
        return zval_list
    def get_energy_from_energy_file(self):
        """Get the energy from the energy file.
            For VASP, this is the last E0 energy from OSZICAR,
            and this function should be used if vasprun.xml
            is corrupted or not available.
            Args:
                mydir <str>: Directory in which to look.
            Returns:
                <float>: last E0 energy from OSZICAR
        """
        fullpath=os.path.join(self.keywords['name'], "OSZICAR")
        if not os.path.isfile(fullpath):
            raise MASTError(self.__class__.__name__, "No OSZICAR file at %s" % self.keywords['name'])
        myosz = MASTFile(fullpath)
        mye0 = myosz.get_segment_from_last_line_match("E0", "E0=","d E =")
        return float(mye0)
    def is_started(self):
        """See if the ingredient has been started on
            the queue.
        """
        if os.path.isfile(os.path.join(self.keywords['name'],'OUTCAR')):
            return True
        else:
            return False

    def write_final_structure_file(self, mystruc):
        """Write the final structure to a file.
            For VASP, this is CONTCAR.
        """
        mycontcar = Poscar(mystruc)
        mycontcar.write_file(os.path.join(self.keywords['name'],'CONTCAR'))
