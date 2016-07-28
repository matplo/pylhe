import os
import sys

class LHEFile(object):
    def __init__(self):
        pass

class LHEEvent(object):
    def __init__(self,eventinfo,particles):
        self.eventinfo = eventinfo
        self.particles = particles
        for p in self.particles:
            p.event = self

class LHEEventInfo(object):
    fieldnames = ['nparticles', 'pid', 'weight', 'scale', 'aqed', 'aqcd']
    def __init__(self, **kwargs):
        if not set(kwargs.keys()) == set(self.fieldnames):
            raise RuntimeError
        for k,v in kwargs.iteritems():
            setattr(self,k,v)
    
    @classmethod
    def fromstring(cls,string):
        return cls(**dict(zip(cls.fieldnames,map(float,string.split()))))
    

class LHEParticle(object):
    fieldnames = fieldnames = ['id','status','mother1','mother2','color1','color2','px','py','pz','e','m','lifetime','spin']
    def __init__(self, **kwargs):
        if not set(kwargs.keys()) == set(self.fieldnames):
            raise RuntimeError
        for k,v in kwargs.iteritems():
            setattr(self,k,v)
    
    @classmethod
    def fromstring(cls,string):
        obj = cls(**dict(zip(cls.fieldnames,map(float,string.split()))))
        return obj
    
    def mothers(self):
        mothers = []
        first_idx  =  int(self.mother1)-1
        second_idx =  int(self.mother2)-1
        for idx in set([first_idx,second_idx]):
            if idx >= 0: mothers.append(self.event.particles[idx])
        return mothers
    
    def __getitem__(self, s):
        return getattr(self, s)

def loads():
    pass

class SourceFile(object):
    def __init__(self, fname, subfile=None):
        self.fname   = fname
        self.subfile = subfile
        self.buffer  = None
        self.tarfile = None
        self.setup_buffer()

    def close(self):
        if self.tarfile != None:
            self.tarfile.close()
        if self.is_gzip == True:
            self.buffer.close()

    def exists(self):
        try:
            f = open(self.fname, 'r')
            f.close()
        except:
            return False
        return True

    def is_valid(self):
        if self.buffer != None:
            return True
        return False

    def setup_buffer(self):
        if self.exists == False:
            return None
        if self.subfile == None:
            # assume a regular file or gzipped
            filename, file_extension = os.path.splitext(self.fname)
            if file_extension == '.gzip' or file_extension == '.gz':
                import gzip
                try:
                    self.buffer = gzip.open(self.fname, 'r')
                    self.is_gzip = True
                except:
                    pass
                    #print >> sys.stderr,'[e] bad gzip file?',self.fname
            else:
                self.buffer = self.fname
        else:
            import tarfile
            if tarfile.is_tarfile(self.fname):
                self.tarfile = tarfile.open(self.fname, "r:gz")
                try:
                    tarinfo = self.tarfile.getmember(self.subfile)
                except:
                    print >> sys.stderr,'[e] file in archive not found:',self.subfile
                    tarinfo = None
                    self.buffer = None
                if tarinfo != None:
                    if tarinfo.isreg():
                        self.buffer = self.tarfile.extractfile(tarinfo)
                    else:
                        self.buffer = None
            else:
                self.buffer = None

import xml.etree.ElementTree as ET
def readLHE(thefile, subfile=None):
    sf = SourceFile(thefile, subfile)
    if not sf.is_valid():
        print >> sys.stderr, '[e] unable to read from:',thefile
        return
    try:
        for event,element in ET.iterparse(sf.buffer,events=['end']):      
            if element.tag == 'event':
                data = element.text.split('\n')[1:-1]
                eventdata,particles = data[0],data[1:]
                eventinfo = LHEEventInfo.fromstring(eventdata)
                particle_objs = []
                for p in particles:
                    # POWHEG for example injects extra info into the event record.; just skip lines with '#'
                    if p[0] == '#':
                      continue
                    particle_objs+=[LHEParticle.fromstring(p)]
                yield LHEEvent(eventinfo,particle_objs)
    
    except ET.ParseError:
        print "WARNING. Parse Error."
        return
    sf.close()

import networkx as nx
import pypdt
import tex2pix
import subprocess
def visualize(event,outputname):
    g = nx.DiGraph()
    for i,p in enumerate(event.particles):
        g.add_node(i,attr_dict=p.__dict__)
        name = pypdt.particle(p.id).name
        greek = ['gamma','nu','mu','tau','rho','Xi','Sigma','Lambda','omega','Omega','Alpha','psi','phi','pi','chi']
        for greekname in greek:
            if greekname in name:
                name = name.replace(greekname,'\\'+greekname)
        if 'susy-' in name:
            name = name.replace('susy-','\\tilde ')
        g.node[i].update(texlbl = "${}$".format(name))
    for i,p in enumerate(event.particles):
        for mom in p.mothers():
            g.add_edge(event.particles.index(mom),i)
    nx.write_dot(g,'event.dot')
    p = subprocess.Popen(['dot2tex','event.dot'], stdout = subprocess.PIPE)
    tex2pix.Renderer(texfile = p.stdout).mkpdf(outputname)
    subprocess.check_call(['pdfcrop',outputname,outputname])
    # shutil.move('event-cropped.pdf','event.pdf')
    os.remove('event.dot')