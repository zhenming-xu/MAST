import numpy as np

from pymatgen.core.structure import Structure
from pymatgen.io.vaspio import Poscar
from pymatgen.io.vaspio import Outcar
from pymatgen.io.vaspio import Kpoints
from pymatgen.io.vaspio import Potcar
from pymatgen.io.vaspio import Incar

from MAST.utility.mastobj import MASTObj
from MAST.ingredients.baseingredient import BaseIngredient
from MAST.ingredients.pmgextend import vasp_extensions

import os
import shutil
#import pdb
#TTM

class FrozenPhonons(BaseIngredient):
    def __init__(self, **kwargs):
        #pdb.set_trace()
        allowed_keys = {
                'dir_name' : (str, str(), 'Name of NEB directory'),
                'parent_path': (str, str(), 'Relaxed CONTCAR path'),
                'program': (str, str(), 'DFT program, e.g. "vasp"')
                }
        BaseIngredient.__init__(self, allowed_keys, **kwargs)
        #prog_kwarg_dict = options.get_item('vasp',ingredient_name)

    def is_complete(self):
        return BaseIngredient.images_complete(self)

    def generate_files(self):
        struct_init = BaseIngredient.get_structure_from_parent(self, self.keywords['parent_path'])
        if (struct_init == None):
            print "Error getting initial parent structure."
            return
        if self.keywords['program'] == 'vasp':
            self.set_up_vasp_folders(struct_init)
        else:
            print "Program not supported. No setup accomplished."
            return
        return
   
    def set_up_vasp_incar_dict(self, rep_structure, rep_potcar):
        myd=dict()
        myd['MAGMOM']=str(len(rep_structure.sites)) + "*5"
        myd['ENCUT']=vasp_extensions.get_max_enmax_from_potcar(rep_potcar)*1.5
        myd['LCHARG']="False"
        myd['LWAVE']="False"
        myd['PREC']="Accurate"
        myd['ISIF']=2
        myd['LREAL']="Auto"
        myd['ISPIN']=2
        myd['IBRION']=5
        myd['POTIM']=0.01
        myd['NFREE']=2
        myd['NSW']=191
        myd['ISMEAR']=1
        myd['SIGMA']=0.2
        return myd

    def set_up_vasp_folders(self, struct_init):
        dir_name = self.keywords['dir_name']
        if os.path.exists(dir_name):
            print "Directory exists."
            return
        os.makedirs(dir_name)
        imct=1
        mypos = Poscar(struct_init)
        topkpoints = Kpoints.monkhorst_automatic(kpts=(4,4,4),shift=(0,0,0))
        toppotcar = Potcar(symbols=mypos.site_symbols, functional='PBE', sym_potcar_map=None)
        incar_dict = self.set_up_vasp_incar_dict(struct_init, toppotcar)
        topincar = Incar(incar_dict)
        totatoms = sum(mypos.natoms)
        while imct <= totatoms:
            for ndir in [0,1,2]:
                imposcar = vasp_extensions.make_one_unfrozen_direction_poscar(mypos, imct, ndir)
                num_str = str(imct).zfill(2)+ "_d" + str(ndir)
                impath = os.path.join(dir_name, num_str)
                impospath = os.path.join(dir_name, "POSCAR_" + num_str)
                imposcar.write_file(impospath)
                os.makedirs(impath)
                imposcar.write_file(os.path.join(impath, "POSCAR"))
                topkpoints.write_file(impath + "/KPOINTS")
                toppotcar.write_file(impath + "/POTCAR")
                topincar.write_file(impath + "/INCAR")
            imct = imct + 1
        return
